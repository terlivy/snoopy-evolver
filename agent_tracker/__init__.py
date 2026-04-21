"""
snoopy-evolver/agent_tracker/
Agent 性能追踪模块

使用方式：
    from agent_tracker import log_spawn, log_completion, get_tracker

    # 派发时记录
    record = log_spawn(
        parent_agent="sas-leader",
        child_agent_label="coder",
        model_used="minimax/MiniMax-M2.7",
        task_description="实现 health_check.py",
        task_type="coding",
        complexity="L2",
        spawning_method="sessions_spawn",
        session_key="agent:sas-leader:subagent:xxx"
    )

    # 任务完成时更新
    log_completion(
        spawn_id=record.spawn_id,
        success=True,
        quality_score=8.5,
        duration_seconds=180,
        tokens_in=15000,
        tokens_out=3000,
        total_cost=0.023
    )

    # 查询分析
    from agent_tracker.analytics import AgentAnalytics
    analytics = AgentAnalytics()
    print(analytics.summary())
"""

from .models import AgentSpawnRecord, TASK_TYPES, COMPLEXITY_LEVELS, QUALITY_DIMENSIONS
from .tracker import AgentTracker, get_tracker, log_spawn, log_completion, get_records
from .analytics import AgentAnalytics

__all__ = [
    "AgentSpawnRecord",
    "AgentTracker",
    "AgentAnalytics",
    "TASK_TYPES",
    "COMPLEXITY_LEVELS",
    "QUALITY_DIMENSIONS",
    "get_tracker",
    "log_spawn",
    "log_completion",
    "get_records"
]
