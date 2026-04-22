#!/usr/bin/env python3
"""
snoopy-evolver/evolver/analyzer.py
模式分析与改进建议生成器

功能：
1. 检测 signals 中的模式
2. 分析失败/成功模式
3. 生成改进建议
4. 检测基因缺失
5. 建议何时创建新基因

GEP 协议分析流程：
signal → Pattern Detection → Gene Gap Analysis → Suggestion Generation → Evolution Decision
"""

import json
import os
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from collections import Counter

from evolver.signals import SIGNALS
from evolver.selector import GeneSelector


@dataclass
class Pattern:
    """检测到的模式"""
    name: str
    description: str
    severity: str  # "high" | "medium" | "low"
    evidence: List[str] = field(default_factory=list)
    frequency: int = 1


@dataclass
class Suggestion:
    """改进建议"""
    type: str  # "new_gene" | "gene_improvement" | "workflow_change" | "no_action"
    priority: str  # "high" | "medium" | "low"
    title: str
    description: str
    suggested_gene: Optional[Dict] = None
    confidence: float = 0.0  # 0.0 ~ 1.0


class SignalAnalyzer:
    """信号分析器"""

    # 高频信号阈值（超过此值视为高频）
    HIGH_FREQ_THRESHOLD = 3

    # 严重模式信号类型
    SEVERE_SIGNALS = {"failure", "low_success_rate", "retry"}

    def __init__(self, events_path: Optional[str] = None, genes_path: Optional[str] = None):
        self.selector = GeneSelector(genes_path)

        # 事件日志路径
        if events_path is None:
            events_path = os.path.join(
                os.path.dirname(__file__),
                "events",
                "events.jsonl"
            )
        self.events_path = events_path

    def analyze_signal(
        self,
        signal_type: str,
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        分析单个信号

        Args:
            signal_type: 信号类型
            metadata: 信号元数据

        Returns:
            分析结果字典
        """
        result = {
            "status": "analyzed",
            "signal_type": signal_type,
            "ts": datetime.now().isoformat(),
            "patterns_detected": [],
            "suggestions": [],
            "gene_gap": None,
            "needs_evolution": False
        }

        # 1. 基础验证
        if signal_type not in SIGNALS:
            result["patterns_detected"].append({
                "name": "unknown_signal",
                "severity": "low",
                "description": f"未知信号类型: {signal_type}"
            })

        # 2. 严重信号检查
        if signal_type in self.SEVERE_SIGNALS:
            result["patterns_detected"].append({
                "name": "severe_signal",
                "severity": "high",
                "description": f"严重信号类型: {signal_type}，需要立即分析"
            })
            result["needs_evolution"] = True

        # 3. 检查相关基因
        genes_matched = self.selector.select([signal_type], top_k=5)

        if not genes_matched:
            result["gene_gap"] = {
                "signal_type": signal_type,
                "severity": "high" if signal_type in self.SEVERE_SIGNALS else "medium",
                "description": f"信号 {signal_type} 没有匹配基因",
                "recommendation": "建议从当前事件中提取新基因"
            }
            result["needs_evolution"] = True
        else:
            # 检查基因成功率
            low_success_genes = [g for g in genes_matched if g.success_rate < 0.8]
            if low_success_genes:
                result["patterns_detected"].append({
                    "name": "low_success_gene",
                    "severity": "medium",
                    "description": f"匹配的基因中有 {len(low_success_genes)} 个成功率较低",
                    "details": [
                        {"gene_id": g.gene_id, "success_rate": g.success_rate}
                        for g in low_success_genes
                    ]
                })

        # 4. 从 metadata 提取模式
        patterns = self._extract_patterns(signal_type, metadata)
        result["patterns_detected"].extend(patterns)

        # 5. 生成建议
        suggestions = self._generate_suggestions(signal_type, metadata, genes_matched, patterns)
        result["suggestions"] = suggestions

        # 6. 综合判断是否需要演化
        if not result["needs_evolution"]:
            result["needs_evolution"] = self._should_evolve(
                signal_type, patterns, suggestions
            )

        return result

    def _extract_patterns(
        self,
        signal_type: str,
        metadata: Dict[str, Any]
    ) -> List[Dict]:
        """从 metadata 中提取模式"""
        patterns = []

        # 失败模式检测
        if signal_type == "failure":
            error_msg = metadata.get("error", "")
            error_type = metadata.get("error_type", "")

            if "timeout" in error_msg.lower() or "timeout" in error_type.lower():
                patterns.append({
                    "name": "timeout_pattern",
                    "severity": "medium",
                    "description": "检测到超时错误模式"
                })

            if "network" in error_msg.lower() or "network" in error_type.lower():
                patterns.append({
                    "name": "network_error_pattern",
                    "severity": "medium",
                    "description": "检测到网络错误模式"
                })

            if "import" in error_msg.lower() or "ModuleNotFoundError" in error_msg:
                patterns.append({
                    "name": "import_error_pattern",
                    "severity": "high",
                    "description": "检测到导入错误，可能需要检查依赖"
                })

        # 重试模式检测
        if signal_type == "retry":
            retry_count = metadata.get("retry_count", 0)
            if retry_count >= 3:
                patterns.append({
                    "name": "frequent_retry_pattern",
                    "severity": "high",
                    "description": f"重试次数过多: {retry_count}次"
                })

        # 低成功率检测
        if signal_type == "low_success_rate":
            success_rate = metadata.get("success_rate", 0)
            if success_rate < 0.5:
                patterns.append({
                    "name": "critical_low_success_rate",
                    "severity": "high",
                    "description": f"成功率过低: {success_rate*100:.0f}%"
                })

        # Git push 模式
        if signal_type == "git_push":
            branch = metadata.get("branch", "unknown")
            files_changed = metadata.get("files_changed", [])
            if len(files_changed) > 10:
                patterns.append({
                    "name": "large_commit_pattern",
                    "severity": "low",
                    "description": f"单次提交变更过多: {len(files_changed)}个文件"
                })

        return patterns

    def _generate_suggestions(
        self,
        signal_type: str,
        metadata: Dict[str, Any],
        genes_matched: List,
        patterns: List[Dict]
    ) -> List[Dict]:
        """生成改进建议"""
        suggestions = []

        # 无基因匹配 → 建议创建新基因
        if not genes_matched:
            # 从 metadata 构建建议基因
            suggested_gene = self._build_gene_from_signal(signal_type, metadata)

            suggestions.append({
                "type": "new_gene",
                "priority": "high" if signal_type in self.SEVERE_SIGNALS else "medium",
                "title": f"为 {signal_type} 创建新基因",
                "description": f"信号类型 {signal_type} 没有匹配基因，建议从本次事件提取基因",
                "suggested_gene": suggested_gene,
                "confidence": 0.85
            })
            return suggestions

        # 有基因但有低成功率
        low_success = [g for g in genes_matched if g.success_rate < 0.8]
        if low_success:
            suggestions.append({
                "type": "gene_improvement",
                "priority": "medium",
                "title": "改进现有基因",
                "description": f"有 {len(low_success)} 个匹配基因成功率较低，建议分析原因并改进 solution",
                "details": [
                    {
                        "gene_id": g.gene_id,
                        "name": g.name,
                        "current_success_rate": g.success_rate,
                        "suggestion": "分析失败案例，更新 solution 和 validation"
                    }
                    for g in low_success
                ],
                "confidence": 0.75
            })

        # 从 patterns 生成建议
        high_severity_patterns = [p for p in patterns if p.get("severity") == "high"]
        if high_severity_patterns:
            for pattern in high_severity_patterns:
                if pattern["name"] == "timeout_pattern":
                    suggestions.append({
                        "type": "workflow_change",
                        "priority": "medium",
                        "title": "超时处理优化",
                        "description": "建议增加超时重试机制或调整超时阈值",
                        "confidence": 0.7
                    })
                elif pattern["name"] == "import_error_pattern":
                    suggestions.append({
                        "type": "workflow_change",
                        "priority": "high",
                        "title": "依赖检查流程",
                        "description": "建议在执行前增加依赖检查步骤",
                        "confidence": 0.8
                    })
                elif pattern["name"] == "frequent_retry_pattern":
                    suggestions.append({
                        "type": "workflow_change",
                        "priority": "high",
                        "title": "重试机制优化",
                        "description": "建议分析根本原因而非持续重试",
                        "confidence": 0.75
                    })

        if not suggestions:
            suggestions.append({
                "type": "no_action",
                "priority": "low",
                "title": "无需改进",
                "description": "信号已匹配合适基因，模式分析未发现问题",
                "confidence": 0.95
            })

        return suggestions

    def _build_gene_from_signal(
        self,
        signal_type: str,
        metadata: Dict[str, Any]
    ) -> Dict:
        """从信号构建建议基因"""
        # 提取问题描述
        problem = metadata.get("error", "") or metadata.get("description", "")
        if not problem and signal_type == "failure":
            problem = f"{signal_type} 信号触发，需要分析根因"
        elif not problem:
            problem = SIGNALS.get(signal_type, signal_type)

        # 生成基因 ID
        gene_id = f"gene_{signal_type}_{datetime.now().strftime('%Y%m%d%H%M')}"

        return {
            "gene_id": gene_id,
            "name": f"{SIGNALS.get(signal_type, signal_type)} 解决方案",
            "category": self._infer_category(signal_type),
            "signals": [signal_type],
            "signals_raw": [signal_type],
            "problem": problem[:200] if problem else "待补充",
            "solution": metadata.get("solution", "") or "待根据实际情况制定解决方案",
            "validation": metadata.get("validation", "") or "待制定验证标准",
            "success_rate": 0.0,  # 新基因初始为 0
            "usage_count": 0,
            "last_used": datetime.now().isoformat() + "+08:00",
            "lessons_source": [f"信号提取: {signal_type}"],
            "tags": [signal_type]
        }

    def _infer_category(self, signal_type: str) -> str:
        """推断基因类别"""
        category_map = {
            "git_push": "git",
            "task_complete": "workflow",
            "failure": "error_handling",
            "migration": "migration",
            "new_module": "module_management",
            "retry": "retry_strategy",
            "low_success_rate": "quality",
        }
        return category_map.get(signal_type, "general")

    def _should_evolve(
        self,
        signal_type: str,
        patterns: List[Dict],
        suggestions: List[Dict]
    ) -> bool:
        """判断是否需要演化"""
        # 有高严重性模式
        if any(p.get("severity") == "high" for p in patterns):
            return True

        # 有高优先级建议
        if any(s.get("priority") == "high" for s in suggestions):
            return True

        # 新基因建议
        if any(s.get("type") == "new_gene" for s in suggestions):
            return True

        return False

    def analyze_historical_patterns(
        self,
        days: int = 7
    ) -> Dict[str, Any]:
        """
        分析历史信号模式

        Args:
            days: 分析最近 N 天的数据

        Returns:
            历史模式分析结果
        """
        # 读取事件日志
        events = self._read_events()

        if not events:
            return {
                "status": "no_data",
                "message": "没有足够的历史数据",
                "signal_counts": {},
                "patterns": [],
                "recommendations": []
            }

        # 统计信号频率
        signal_counts = Counter(e.get("type") for e in events)

        # 检测高频信号
        high_freq = {
            sig: count for sig, count in signal_counts.items()
            if count >= self.HIGH_FREQ_THRESHOLD
        }

        # 检测频繁失败
        failures = [e for e in events if "failed" in e.get("type", "").lower()]
        failure_rate = len(failures) / len(events) if events else 0

        # 生成建议
        recommendations = []

        if high_freq:
            recommendations.append({
                "type": "high_frequency_signal",
                "priority": "high",
                "description": f"检测到 {len(high_freq)} 种高频信号",
                "details": high_freq,
                "suggestion": "高频信号表明存在系统性问题，建议创建专用基因"
            })

        if failure_rate > 0.3:
            recommendations.append({
                "type": "high_failure_rate",
                "priority": "critical",
                "description": f"失败率过高: {failure_rate*100:.1f}%",
                "suggestion": "失败率超过 30%，建议立即分析根因"
            })

        return {
            "status": "analyzed",
            "total_events": len(events),
            "signal_counts": dict(signal_counts),
            "high_frequency_signals": high_freq,
            "failure_rate": failure_rate,
            "patterns": self._detect_historical_patterns(events),
            "recommendations": recommendations
        }

    def _read_events(self) -> List[Dict]:
        """读取事件日志"""
        events = []
        try:
            with open(self.events_path, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        events.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        except FileNotFoundError:
            pass
        return events

    def _detect_historical_patterns(self, events: List[Dict]) -> List[Dict]:
        """从历史事件检测模式"""
        patterns = []

        # 检测任务完成但成功率下降
        task_completed = [e for e in events if e.get("type") == "task_completed"]
        if len(task_completed) >= 5:
            # 简化：按时间顺序分析
            patterns.append({
                "name": "task_completion_trend",
                "description": f"最近完成任务数: {len(task_completed)}",
                "severity": "low"
            })

        return patterns


# 便捷函数
def analyze_signal(signal_type: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
    """分析信号的便捷函数"""
    analyzer = SignalAnalyzer()
    return analyzer.analyze_signal(signal_type, metadata)


def analyze_historical(days: int = 7) -> Dict[str, Any]:
    """分析历史模式的便捷函数"""
    analyzer = SignalAnalyzer()
    return analyzer.analyze_historical_patterns(days)


if __name__ == "__main__":
    import sys

    analyzer = SignalAnalyzer()

    if len(sys.argv) > 1:
        if sys.argv[1] == "--history":
            # 历史分析
            days = int(sys.argv[2]) if len(sys.argv) > 2 else 7
            result = analyzer.analyze_historical_patterns(days)
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            # 单信号分析
            signal_type = sys.argv[1]
            metadata = {}
            if len(sys.argv) > 2:
                try:
                    metadata = json.loads(sys.argv[2])
                except:
                    metadata = {"raw": sys.argv[2]}

            result = analyzer.analyze_signal(signal_type, metadata)
            print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        # 默认测试
        print("=== 测试：failure 信号分析 ===")
        result = analyzer.analyze_signal("failure", {
            "error": "ModuleNotFoundError: No module named 'requests'",
            "error_type": "import_error"
        })
        print(json.dumps(result, indent=2, ensure_ascii=False))

        print("\n=== 测试：git_push 信号分析 ===")
        result = analyzer.analyze_signal("git_push", {
            "branch": "main",
            "files_changed": ["a.py", "b.py", "c.py"]
        })
        print(json.dumps(result, indent=2, ensure_ascii=False))

        print("\n=== 测试：retry 信号分析 ===")
        result = analyzer.analyze_signal("retry", {
            "retry_count": 5,
            "reason": "connection timeout"
        })
        print(json.dumps(result, indent=2, ensure_ascii=False))
