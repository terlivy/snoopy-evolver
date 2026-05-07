"""
Agent Router — 任务类型 → Agent 路由规则

定义：
- 什么类型的任务，路由到哪个配置的 agentId
- agentId 对应 openclaw.json 里配置的 agents[].id
"""

from typing import Literal

# 路由表：任务类型 → agentId
TASK_TYPE_TO_AGENT: dict[str, str] = {
    # 研发类
    "code_development": "developer",
    "code_review": "code-reviewer",
    "security_audit": "security-reviewer",
    "testing": "tester",
    "performance_testing": "performance-tester",
    "devops_deploy": "devops",
    "frontend_dev": "developer",
    "backend_dev": "developer",
    "fullstack_dev": "developer",

    # 产品设计类
    "requirement_analysis": "requirement-analyst",
    "product_design": "product-manager",
    "tech_architecture": "technical-architect",
    "ui_design": "ui-designer",
    "ux_research": "product-manager",

    # 运营类
    "operations": "operations-agent",
    "data_analysis": "requirement-analyst",
    "research": "requirement-analyst",
    "document": "doc-expert",
    "hr_task": "hr",
    "weather_query": "weather",
    "tech_news": "tech-news",
}

# Agent 别名 → 标准 agentId（支持中文输入的 agent 名）
AGENT_ALIAS_TO_ID: dict[str, str] = {
    # 中文别名
    "需求分析": "requirement-analyst",
    "需求": "requirement-analyst",
    "产品": "product-manager",
    "产品经理": "product-manager",
    "技术架构": "technical-architect",
    "架构设计": "technical-architect",
    "ui设计": "ui-designer",
    "设计师": "ui-designer",
    "前端": "developer",
    "后端": "developer",
    "全栈": "developer",
    "开发": "developer",
    "代码开发": "developer",
    "代码审查": "code-reviewer",
    "安全审计": "security-reviewer",
    "测试": "tester",
    "性能测试": "performance-tester",
    "部署": "devops",
    "运营": "operations-agent",
    "文档": "doc-expert",
    "hr": "hr",
    "天气": "weather",
    "新闻": "tech-news",

    # 英文别名
    "requirement-analyst": "requirement-analyst",
    "product-manager": "product-manager",
    "technical-architect": "technical-architect",
    "ui-designer": "ui-designer",
    "developer": "developer",
    "code-reviewer": "code-reviewer",
    "security-reviewer": "security-reviewer",
    "tester": "tester",
    "performance-tester": "performance-tester",
    "devops": "devops",
    "operations-agent": "operations-agent",
    "doc-expert": "doc-expert",
    "hr": "hr",
    "weather": "weather",
    "tech-news": "tech-news",
    "sas-leader": "sas-leader",
    "prod-leader": "prod-leader",
    "sas-sop-expert": "sas-sop-expert",
    "sas-default": "sas-default",
    "sc": "main",
    "SC": "main",
}

# OpenClaw 配置里的有效 agentId 列表
CONFIGURED_AGENTS = {
    "main",           # SC 主脑
    "weather",         # 天气
    "hr",             # HR
    "tech-news",      # 技术新闻
    "doc-expert",     # 文档专家
    "sas-sop-expert", # SAS SOP 专家
    "sas-default",    # SAS Default
    "sas-leader",     # SAS Leader
    "prod-leader",     # 产研 Leader
    "requirement-analyst", # 需求分析
    "product-manager",    # 产品经理
    "technical-architect", # 技术架构
    "ui-designer",        # UI 设计
    "developer",          # 开发
    "code-reviewer",      # 代码审查
    "security-reviewer",  # 安全审计
    "tester",             # 测试
    "performance-tester",  # 性能测试
    "devops",             # DevOps
    "operations-agent",    # 运营
}


def resolve_agent_id(channel: str) -> str | None:
    """
    将任务指派的 channel（可能是中文、别名、agentId）解析为标准 agentId。

    Returns:
        标准 agentId（如果在 CONFIGURED_AGENTS 里）
        None（如果不是有效 agent）
    """
    if not channel:
        return None

    channel = channel.strip()

    # 直接命中
    if channel in CONFIGURED_AGENTS:
        return channel

    # 查别名表
    canonical = AGENT_ALIAS_TO_ID.get(channel)
    if canonical and canonical in CONFIGURED_AGENTS:
        return canonical

    return None


def route_task(task_type: str) -> str | None:
    """
    根据任务类型路由到对应 agent。

    Args:
        task_type: 任务类型（如 "code_development", "requirement_analysis"）

    Returns:
        对应的 agentId，或 None（未找到时返回 None）
    """
    return TASK_TYPE_TO_AGENT.get(task_type)


def get_agent_session_key(agent_id: str) -> str | None:
    """
    获取 agent 的活跃 session key。
    用于向特定 agent 发消息。

    注意：返回的是 agent 的主 session（agent:{agentId}:main），
    但实际消息路由应该通过 sessions_send 工具。

    Returns:
        session key 字符串，或 None
    """
    # 动态查找最新的活跃 session
    # 这个函数在实际发消息时由 openclaw 工具处理
    return None
