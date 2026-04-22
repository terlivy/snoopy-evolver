#!/usr/bin/env python3
"""
snoopy-evolver/evolver/wrapper.py
P0 核心协调器：监听信号、触发检查、协调各模块

职责：
1. 检查信号文件（signals/）
2. 发现信号 → 记录事件
3. 选择相关基因
4. 决定是否需要演化
5. 协调 analyzer/mutator/solidify
6. 清除已处理信号
7. 报告结果
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# 导入各模块
from evolver.signals import (
    has_signals, get_signal_count, read_signals,
    clear_signal, clear_all_signals
)
from evolver.events.logger import log_event

# 基因选择器
try:
    from evolver.genes.selector import select_genes_for_signals
    HAS_SELECTOR = True
except ImportError:
    HAS_SELECTOR = False
    print("[Wrapper] Warning: selector not found, using basic mode")

# 分析器
try:
    from evolver.analyzer import analyze_signal
    HAS_ANALYZER = True
except ImportError:
    HAS_ANALYZER = False
    print("[Wrapper] Warning: analyzer not found, skipping analysis")

# 固化器
try:
    from evolver.solidify import apply_changes
    HAS_SOLIDIFY = True
except ImportError:
    HAS_SOLIDIFY = False
    print("[Wrapper] Warning: solidify not found, dry-run mode")

class EvolutionWrapper:
    """演化 Wrapper：协调所有模块"""

    def __init__(self):
        self.name = "snoopy-evolver Wrapper"
        self.version = "0.2"
        self.events_log = []

    def check_signals(self):
        """检查是否有待处理信号"""
        return has_signals()

    def count_signals(self):
        """返回待处理信号数量"""
        return get_signal_count()

    def process_signals(self, dry_run=True):
        """处理所有信号"""
        if not self.check_signals():
            return {"status": "no_signals", "processed": 0}

        signals = read_signals()
        processed = 0
        results = []
        errors = []

        for signal in signals:
            signal_type = signal.get("type", "unknown")
            metadata = signal.get("metadata", {})
            ts = signal.get("ts", datetime.now().isoformat())

            try:
                # 1. 记录事件
                log_event(signal_type, metadata)
                print(f"[Wrapper] Logged event: {signal_type}")

                # 2. 选择相关基因
                genes_selected = []
                if HAS_SELECTOR:
                    genes_selected = select_genes_for_signals(signal_type)
                    print(f"[Wrapper] Genes matched: {len(genes_selected)}")

                # 3. 分析信号（如有 analyzer）
                analysis_result = None
                if HAS_ANALYZER:
                    try:
                        analysis_result = analyze_signal(signal_type, metadata)
                        print(f"[Wrapper] Analysis: {analysis_result.get('status', 'unknown')}")
                    except Exception as e:
                        print(f"[Wrapper] Analysis error: {e}")
                        errors.append(f"analysis_error: {e}")

                # 4. 决定是否需要演化
                needs_evolution = self._should_evolve(
                    signal_type, metadata, genes_selected, analysis_result
                )

                # 5. 如果需要演化且非 dry_run，固化更改
                if needs_evolution and not dry_run:
                    if HAS_SOLIDIFY:
                        solidify_result = apply_changes(
                            signal_type, analysis_result
                        )
                        print(f"[Wrapper] Solidified: {solidify_result.get('status', 'unknown')}")
                    else:
                        print("[Wrapper] Solidify not available, dry-run mode")
                elif needs_evolution and dry_run:
                    print("[Wrapper] Dry-run: would solidify if enabled")

                # 6. 清除信号
                clear_signal(signal_type)
                processed += 1

                results.append({
                    "signal": signal_type,
                    "ts": ts,
                    "genes_matched": len(genes_selected),
                    "needs_evolution": needs_evolution,
                    "analysis": analysis_result,
                    "status": "processed"
                })

            except Exception as e:
                print(f"[Wrapper] Error processing {signal_type}: {e}")
                errors.append(f"{signal_type}_error: {e}")
                results.append({
                    "signal": signal_type,
                    "status": "error",
                    "error": str(e)
                })

        return {
            "status": "completed",
            "processed": processed,
            "total_signals": len(signals),
            "results": results,
            "errors": errors,
            "dry_run": dry_run
        }

    def _should_evolve(self, signal_type, metadata, genes, analysis):
        """判断是否需要演化"""
        # 高优先级信号强制演化
        HIGH_PRIORITY = ["failure", "low_success_rate", "migration", "retry"]

        if signal_type in HIGH_PRIORITY:
            return True

        # 有匹配基因但分析结果不好
        if genes and analysis:
            if analysis.get("status") == "problem_detected":
                return True

        # 基因太少且任务复杂
        if len(genes) == 0 and signal_type in ["task_complete", "git_push"]:
            # 没有现成基因，需要学习
            return True

        return False

    def run_daily(self):
        """每日定时运行：检查信号 + 生成报告"""
        print(f"[Wrapper] Running daily evolution check...")
        result = self.process_signals(dry_run=True)
        print(f"[Wrapper] Daily check: {result['processed']} signals processed")
        return result

    def run_once(self, dry_run=True):
        """单次运行"""
        print(f"[Wrapper] Running single check (dry_run={dry_run})...")
        return self.process_signals(dry_run=dry_run)

    def status(self):
        """返回 Wrapper 状态"""
        return {
            "name": self.name,
            "version": self.version,
            "pending_signals": self.count_signals(),
            "has_selector": HAS_SELECTOR,
            "has_analyzer": HAS_ANALYZER,
            "has_solidify": HAS_SOLIDIFY
        }


def main():
    """CLI 入口"""
    import argparse
    parser = argparse.ArgumentParser(description="snoopy-evolver Wrapper")
    parser.add_argument("--dry-run", action="store_true", help="不实际修改，只报告")
    parser.add_argument("--daily", action="store_true", help="每日定时模式")
    parser.add_argument("--status", action="store_true", help="显示状态")
    args = parser.parse_args()

    wrapper = EvolutionWrapper()

    if args.status:
        status = wrapper.status()
        print(json.dumps(status, indent=2))
        return

    if args.daily:
        result = wrapper.run_daily()
    else:
        result = wrapper.run_once(dry_run=args.dry_run)

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
