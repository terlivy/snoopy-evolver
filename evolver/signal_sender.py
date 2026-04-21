#!/usr/bin/env python3
"""
snoopy-evolver/evolver/signal_sender.py
信号发送器 - 在事件发生时调用，零token成本

用法：
    python3 evolver/signal_sender.py git_push --repo my-repo
    python3 evolver/signal_sender.py failure --error "connection timeout"
    python3 evolver/signal_sender.py migration --from snoop-evolver --to snoopyclaw-skills
    python3 evolver/signal_sender.py task_complete --task "实现健康检查" --success 1
"""

import sys
import json
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from evolver.signals import write_signal

SIGNALS = {
    "git_push": "Git push 操作",
    "task_complete": "任务完成",
    "failure": "失败/错误",
    "migration": "文件迁移",
    "new_module": "新模块创建",
    "retry": "重试/返工",
    "low_success_rate": "低成功率",
}

def main():
    parser = argparse.ArgumentParser(description="信号发送器")
    parser.add_argument("signal_type", choices=list(SIGNALS.keys()), help="信号类型")
    parser.add_argument("--repo", help="仓库名称（用于git_push）")
    parser.add_argument("--error", help="错误信息（用于failure）")
    parser.add_argument("--from_repo", help="源仓库（用于migration）")
    parser.add_argument("--to_repo", help="目标仓库（用于migration）")
    parser.add_argument("--task", help="任务描述（用于task_complete）")
    parser.add_argument("--success", type=int, choices=[0, 1], help="是否成功")
    parser.add_argument("--model", help="使用的模型")
    parser.add_argument("--tokens", type=int, help="Token消耗")

    args = parser.parse_args()

    metadata = {}
    if args.repo:
        metadata["repo"] = args.repo
    if args.error:
        metadata["error"] = args.error
    if args.from_repo:
        metadata["from"] = args.from_repo
    if args.to_repo:
        metadata["to"] = args.to_repo
    if args.task:
        metadata["task"] = args.task
    if args.success is not None:
        metadata["success"] = bool(args.success)
    if args.model:
        metadata["model"] = args.model
    if args.tokens:
        metadata["tokens"] = args.tokens

    write_signal(args.signal_type, metadata)
    print(f"[SignalSender] {args.signal_type} -> {SIGNALS[args.signal_type]}")

if __name__ == "__main__":
    main()
