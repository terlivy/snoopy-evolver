"""
snoopy-evolver/agent_tracker/models.py
Agent 性能记录的数据模型
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional
import json

TASK_TYPES = ["development", "research", "analysis", "deployment", "testing", "documentation", "review", "planning", "other"]
COMPLEXITY_LEVELS = ["L1", "L2", "L3"]

@dataclass
class AgentSpawnRecord:
    """单次 Agent 派发记录"""

    # === 必填字段 (无默认值) ===
    spawn_id: str                    # 唯一ID (UUID)
    spawn_timestamp: str             # ISO 时间戳
    parent_agent: str                # 派发方 (如 "SC")
    child_agent_id: str              # 子Agent ID (派发时为空，完成后填充)
    child_agent_label: str          # 子Agent 标签 (如 "sas-leader")
    model_used: str                  # 使用的模型
    model_provider: str              # Provider
    task_description: str            # 任务描述
    task_type: str                   # 任务类型
    complexity: str                  # 复杂度 (L1/L2/L3)
    completion_status: str            # pending/completed/failed/timeout/cancelled
    spawning_method: str              # sessions_spawn / clawteam

    # === 可选字段 (有默认值) ===
    task_subtype: Optional[str] = None
    success: Optional[bool] = None
    quality_score: Optional[float] = None
    duration_seconds: Optional[int] = None
    tokens_in: Optional[int] = None
    tokens_out: Optional[int] = None
    total_cost: Optional[float] = None
    failure_reason: Optional[str] = None
    error_type: Optional[str] = None
    session_key: Optional[str] = None
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)

    @classmethod
    def from_dict(cls, d: dict) -> "AgentSpawnRecord":
        return cls(**d)


@dataclass
class TaskMetrics:
    """任务指标快照"""
    task_id: str
    complexity: str
    model: str
    duration_seconds: int
    tokens_total: int
    cost_total: float
    success: bool
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
