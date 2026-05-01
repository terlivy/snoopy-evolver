"""
snoopy-evolver/agent_tracker/integrations.py
SC 主脑集成层 — 自动记录 sessions_spawn 的派发和完成事件

使用方式：
    from agent_tracker.integrations import record_spawn, record_completion, auto_annotate_session

    # 在调用 sessions_spawn 后立即记录
    spawn_result = sessions_spawn(...)
    record_spawn(
        parent_agent="SC",
        child_agent_label=label,
        model_used=model,
        task_description=task[:200],
        task_type=infer_task_type(task),
        complexity=complexity,
        spawning_method="sessions_spawn",
        session_key=spawn_result["sessionKey"],
        child_agent_id=spawn_result.get("runId", "")
    )

    # 在收到完成事件时更新
    record_completion(
        session_key="agent:xxx:subagent:yyy",
        success=True,
        quality_score=9.0,
        duration_seconds=120,
        tokens_in=8000,
        tokens_out=2000,
        total_cost=0.015
    )
"""

import sys
from pathlib import Path
from typing import Optional

# 确保 agent_tracker 在路径中
_FILE_DIR = Path(__file__).parent
sys.path.insert(0, str(_FILE_DIR))

from agent_tracker.tracker import AgentTracker, log_spawn as _log_spawn, log_completion as _log_completion
from agent_tracker.models import TASK_TYPES, COMPLEXITY_LEVELS

# 全局 tracker 实例
_tracker: Optional[AgentTracker] = None

def get_tracker() -> AgentTracker:
    global _tracker
    if _tracker is None:
        _tracker = AgentTracker()
    return _tracker

def record_spawn(
    parent_agent: str,
    child_agent_label: str,
    model_used: str,
    task_description: str,
    task_type: str = "other",
    complexity: str = "L1",
    spawning_method: str = "sessions_spawn",
    session_key: Optional[str] = None,
    child_agent_id: str = "",
    **metadata
) -> str:
    """
    记录一次 Agent 派发事件。
    返回 spawn_id，可用于后续更新完成状态。
    """
    record = _log_spawn(
        parent_agent=parent_agent,
        child_agent_label=child_agent_label,
        model_used=model_used,
        task_description=task_description,
        task_type=task_type,
        complexity=complexity,
        spawning_method=spawning_method,
        session_key=session_key,
        child_agent_id=child_agent_id,
        **metadata
    )
    return record.spawn_id


def record_completion(
    session_key: str,
    success: bool,
    quality_score: Optional[float] = None,
    duration_seconds: Optional[int] = None,
    tokens_in: Optional[int] = None,
    tokens_out: Optional[int] = None,
    total_cost: Optional[float] = None,
    failure_reason: Optional[str] = None,
    error_type: Optional[str] = None,
    **metadata
) -> bool:
    """
    根据 session_key 更新对应的 spawn 记录。
    返回是否找到对应记录。
    """
    tracker = get_tracker()
    records = tracker._load_records()

    # 找到最新的 pending 记录，匹配 session_key
    matched_idx = -1
    for i, rec in enumerate(reversed(records)):
        if rec.get("session_key") == session_key and rec.get("completion_status") == "pending":
            matched_idx = len(records) - 1 - i
            break

    if matched_idx < 0:
        print(f"[agent_tracker] 未找到 session_key={session_key} 的 pending 记录")
        return False

    spawn_id = records[matched_idx]["spawn_id"]
    _log_completion(
        spawn_id=spawn_id,
        success=success,
        quality_score=quality_score,
        duration_seconds=duration_seconds,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        total_cost=total_cost,
        failure_reason=failure_reason,
        error_type=error_type,
        **metadata
    )
    return True


def infer_task_type(task_description: str) -> str:
    """根据任务描述推断任务类型"""
    task_lower = task_description.lower()
    if any(k in task_lower for k in ["修复", "debug", "错误", "bug", "fix"]):
        return "testing"
    if any(k in task_lower for k in ["开发", "实现", "写代码", "coding", "implement"]):
        return "development"
    if any(k in task_lower for k in ["研究", "调研", "分析", "research", "analyze"]):
        return "research"
    if any(k in task_lower for k in ["部署", "上线", "deploy"]):
        return "deployment"
    if any(k in task_lower for k in ["测试", "test", "验证"]):
        return "testing"
    if any(k in task_lower for k in ["文档", "doc", "说明"]):
        return "documentation"
    if any(k in task_lower for k in ["审查", "review", "检查"]):
        return "review"
    if any(k in task_lower for k in ["计划", "规划", "plan"]):
        return "planning"
    return "other"


def infer_complexity(task_description: str) -> str:
    """根据任务描述推断复杂度"""
    task_lower = task_description.lower()
    if any(k in task_lower for k in ["并行", "多个", "multi", "团队", " swarm", "复杂"]):
        return "L3"
    if any(k in task_lower for k in ["几个", "多个", "several", "l2"]):
        return "L2"
    return "L1"


if __name__ == "__main__":
    # 快速测试
    print("=== agent_tracker 集成测试 ===")
    spawn_id = record_spawn(
        parent_agent="SC",
        child_agent_label="test-integration",
        model_used="minimax/MiniMax-M2.7-highspeed",
        task_description="集成层测试任务",
        task_type="testing",
        complexity="L1",
        spawning_method="sessions_spawn",
        session_key="agent:SC:test:123"
    )
    print(f"spawn_id: {spawn_id}")

    ok = record_completion(
        session_key="agent:SC:test:123",
        success=True,
        quality_score=9.5,
        duration_seconds=60,
        tokens_in=5000,
        tokens_out=1500,
        total_cost=0.01
    )
    print(f"completion 更新: {'成功' if ok else '失败'}")

    from agent_tracker.analytics import AgentAnalytics
    a = AgentAnalytics()
    print(f"Summary: {a.summary()}")
