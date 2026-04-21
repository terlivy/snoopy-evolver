#!/usr/bin/env python3
"""
snoopy-evolver/agent_tracker/cli.py
Agent 追踪器 CLI

用法：
    python3 -m agent_tracker.cli spawn <parent> <label> <model> <task> <type> [--complexity L1]
    python3 -m agent_tracker.cli complete <spawn_id> --success --score 8.5 --duration 180
    python3 -m agent_tracker.cli summary
    python3 -m agent_tracker.cli ranking
    python3 -m agent_tracker.cli matrix
    python3 -m agent_tracker.cli report
"""

import sys
import argparse
from pathlib import Path

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from agent_tracker import (
    get_tracker, log_spawn, log_completion, get_records,
    AgentAnalytics, TASK_TYPES, COMPLEXITY_LEVELS
)

def cmd_spawn(args):
    record = log_spawn(
        parent_agent=args.parent,
        child_agent_label=args.label,
        model_used=args.model,
        task_description=args.task,
        task_type=args.type,
        complexity=args.complexity or "L1",
        spawning_method=args.method or "sessions_spawn"
    )
    print(f"派发已记录: {record.spawn_id}")
    print(f"   模型: {record.model_used}")
    print(f"   任务: {record.task_description[:50]}...")
    print(f"   类型: {record.task_type} ({COMPLEXITY_LEVELS.get(record.complexity, '')})")

def cmd_complete(args):
    kwargs = {"spawn_id": args.spawn_id, "success": args.success}
    if args.score is not None:
        kwargs["quality_score"] = args.score
    if args.duration:
        kwargs["duration_seconds"] = args.duration
    if args.tokens_in:
        kwargs["tokens_in"] = args.tokens_in
    if args.tokens_out:
        kwargs["tokens_out"] = args.tokens_out
    if args.cost:
        kwargs["total_cost"] = args.cost
    if args.failure:
        kwargs["failure_reason"] = args.failure
        kwargs["success"] = False

    log_completion(**kwargs)
    print(f"完成已记录: {args.spawn_id}")
    print(f"   成功: {kwargs['success']}")
    if kwargs.get("quality_score"):
        print(f"   评分: {kwargs['quality_score']}")

def cmd_summary(args):
    analytics = AgentAnalytics()
    s = analytics.summary()
    print("【Agent追踪汇总】")
    print(f"  总派发: {s['total_spawns']}")
    print(f"  已完成: {s['total_completed']} | 成功: {s['total_successful']}")
    print(f"  成功率: {s['overall_success_rate']}%")
    print(f"  总Token: {s['total_tokens']:,}")
    print(f"  总成本: ${s['total_cost_usd']}")
    print(f"  模型数: {s['unique_models']} | 任务类型: {s['unique_task_types']}")

def cmd_ranking(args):
    analytics = AgentAnalytics()
    ranking = analytics.get_model_ranking()
    print("【模型排名】")
    for i, item in enumerate(ranking[:10], 1):
        print(f"{i}. {item['model']}")
        print(f"   任务:{item['total_tasks']} | 成功:{item['success_rate']}% | 质量:{item.get('avg_quality_score') or 'N/A'} | 成本:${item.get('avg_cost')}")

def cmd_matrix(args):
    analytics = AgentAnalytics()
    matrix = analytics.get_model_task_matrix()
    print("【模型x任务矩阵】")
    for key, stats in sorted(matrix.items(), key=lambda x: x[1]["total"], reverse=True)[:20]:
        print(f"  {key}: {stats['total']}次 | 成功:{stats['success_rate']}% | 质量:{stats.get('avg_quality_score') or 'N/A'}")

def cmd_report(args):
    analytics = AgentAnalytics()
    print(analytics.generate_recommendations())

def main():
    parser = argparse.ArgumentParser(description="Agent 性能追踪器 CLI")
    sub = parser.add_subparsers()

    p_spawn = sub.add_parser("spawn", help="记录派发")
    p_spawn.add_argument("parent", help="派发方")
    p_spawn.add_argument("label", help="子Agent标签")
    p_spawn.add_argument("model", help="模型")
    p_spawn.add_argument("task", help="任务描述")
    p_spawn.add_argument("type", choices=list(TASK_TYPES.keys()), help="任务类型")
    p_spawn.add_argument("--complexity", choices=["L1","L2","L3"], help="复杂度")
    p_spawn.add_argument("--method", help="派发方式")
    p_spawn.set_defaults(func=cmd_spawn)

    p_complete = sub.add_parser("complete", help="记录完成")
    p_complete.add_argument("spawn_id", help="派发ID")
    p_complete.add_argument("--success", action="store_true", help="是否成功")
    p_complete.add_argument("--score", type=float, help="质量评分 0-10")
    p_complete.add_argument("--duration", type=int, help="执行时长(秒)")
    p_complete.add_argument("--tokens-in", type=int, dest="tokens_in", help="输入Token")
    p_complete.add_argument("--tokens-out", type=int, dest="tokens_out", help="输出Token")
    p_complete.add_argument("--cost", type=float, help="成本USD")
    p_complete.add_argument("--failure", help="失败原因")
    p_complete.set_defaults(func=cmd_complete)

    sub.add_parser("summary", help="汇总统计").set_defaults(func=cmd_summary)
    sub.add_parser("ranking", help="模型排名").set_defaults(func=cmd_ranking)
    sub.add_parser("matrix", help="模型x任务矩阵").set_defaults(func=cmd_matrix)
    sub.add_parser("report", help="生成优化建议").set_defaults(func=cmd_report)

    args = parser.parse_args()
    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
