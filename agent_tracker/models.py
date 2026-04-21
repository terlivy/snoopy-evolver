"""
snoopy-evolver/agent_tracker/models.py
Agent 性能记录的数据模型
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional
import json

@dataclass
class AgentSpawnRecord:
    """单次 Agent 派发记录"""
    # 基础标识
    spawn_id: str                    # 唯一ID (UUID)
    spawn_timestamp: str              # ISO 时间戳

    # 派发关系
    parent_agent: str                 # 派发方 (如 "sas-leader")
    child_agent_id: str               # 子Agent ID (如 "agent:main:subagent:xxx")
    child_agent_label: str            # 子Agent 标签 (如 "coder", "researcher")

    # 模型信息
    model_used: str                  # 使用的模型 (如 "minimax/MiniMax-M2.7")
    model_provider: str                # Provider (如 "minimax")

    # 任务信息
    task_description: str           # 任务描述
    task_type: str                   # 任务类型 (见 TASK_TYPES)
    task_subtype: Optional[str]      # 子类型
    complexity: str                  # 复杂度 (L1/L2/L3)

    # 执行结果
    success: Optional[bool]           # 是否成功
    quality_score: Optional[float]     # 质量评分 (0-10)
    completion_status: str            # completed/failed/timeout/cancelled

    # 资源消耗
    duration_seconds: Optional[int]   # 执行时长 (秒)
    tokens_in: Optional[int]          # 输入 Token
    tokens_out: Optional[int]         # 输出 Token
    total_cost: Optional[float]       # 估算成本 (USD)

    # 失败信息
    failure_reason: Optional[str]     # 失败原因
    error_type: Optional[str]        # 错误类型

    # 额外信息
    spawning_method: str              # sessions_spawn / clawteam
    session_key: Optional[str]       # OpenClaw session key
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)

    @classmethod
    def from_dict(cls, d: dict) -> 'AgentSpawnRecord':
        return cls(**d)

# 任务类型枚举
TASK_TYPES = {
    "coding": "代码开发 (写代码/重构/修复bug)",
    "code_review": "代码审查",
    "research": "研究调研 (分析/报告/调研)",
    "document": "文档撰写 (文档/报告/文章)",
    "data_analysis": "数据分析 (数据处理/可视化)",
    "planning": "任务规划 (方案设计/架构设计)",
    "testing": "测试验证 (单元测试/集成测试)",
    "deployment": "部署运维 (部署/配置/监控)",
    "design": "设计创意 (UI/UX/架构)",
    "simple_query": "简单查询 (问答/信息检索)",
    "multi_agent": "多Agent协作",
    "other": "其他"
}

# 复杂度等级
COMPLEXITY_LEVELS = {
    "L1": "简单 (单文件/3步以内/无外部依赖)",
    "L2": "中等 (2-3个Agent/4-8步骤/有依赖)",
    "L3": "复杂 (3+Agent/8+步骤/跨系统/高风险)"
}

# 评分维度
QUALITY_DIMENSIONS = {
    "correctness": "正确性 (代码正确/逻辑无误)",
    "completeness": "完整性 (需求全覆盖)",
    "efficiency": "效率 (执行快/资源省)",
    "clarity": "清晰度 (代码可读/文档清晰)",
    "maintainability": "可维护性 (易扩展/易修改)"
}
