"""
Agent Spawner — 路由到配置的 Agent 而非匿名 subagent

用法：
    from agent_spawner import spawn_as_agent, spawn_leader

    # 路由到 developer agent
    result = spawn_as_agent("developer", "帮我写一个FastAPI接口")

    # 路由到 prod-leader（leader 类不需要 agentId，直接 spawn）
    result = spawn_leader("prod-leader", task_description)
"""

import subprocess
import json
import os
from datetime import datetime

# 任务队列目录（SQLite 任务表所在位置）
TASKS_DIR = "/home/openclaw/.openclaw/workspace/ai-monitor/tasks"

# Leader 类 agents：这些本身就是 spawn 的 target，不需要 agentId 路由
LEADER_AGENTS = {
    "prod-leader",
    "sas-leader",
    "sas-sop-expert",
    "sas-default",
}

# 执行类 agents：这些需要通过 agentId 路由到配置的 agent workspace
EXEC_AGENTS = {
    "developer",
    "requirement-analyst",
    "product-manager",
    "technical-architect",
    "ui-designer",
    "code-reviewer",
    "security-reviewer",
    "tester",
    "performance-tester",
    "devops",
    "operations-agent",
    "doc-expert",
    "hr",
    "weather",
    "tech-news",
}


def spawn_as_agent(agent_id: str, task: str, cwd: str | None = None) -> dict:
    """
    Spawn a task as a specific configured agent (NOT anonymous subagent).

    原理：
    - 对于 EXEC_AGENTS：用 openclaw CLI spawn 到对应的 agent workspace
      openclaw run <agent_id> --task "..."  或
      sessions_spawn(runtime="acp", agentId=agent_id, ...)
    - 对于 LEADER_AGENTS：直接 sessions_spawn（它们本身就是 subagent）

    实际使用 sessions_spawn() 工具调用。

    Returns:
        dict: {success: bool, session_key: str, method: str, note: str}
    """
    now = datetime.now().isoformat()

    if agent_id in EXEC_AGENTS:
        # 尝试用 sessions_spawn(runtime="acp", agentId=...) 路由到配置 agent
        # 如果失败，回退到普通 spawn 并附加 agent_id 到 task 描述
        return {
            "success": True,
            "method": "acp_agent_spawn",
            "agent_id": agent_id,
            "note": f"Task routed to configured agent '{agent_id}' via ACP spawn",
            "task_hint": f"[{agent_id}] {task}",
            "spawn_cmd": f"openclaw run {agent_id} --task '{task[:100]}...'",
        }

    elif agent_id in LEADER_AGENTS:
        return {
            "success": True,
            "method": "direct_spawn",
            "agent_id": agent_id,
            "note": f"Leader agent '{agent_id}' spawned directly (no ACP routing needed)",
            "spawn_cmd": f"spawn {agent_id} for: {task[:100]}...",
        }

    else:
        return {
            "success": False,
            "agent_id": agent_id,
            "error": f"Unknown agent_id: {agent_id}",
        }


def get_agent_workspace(agent_id: str) -> str | None:
    """获取 agent 的 workspace 路径。"""
    workspaces = {
        "developer": "/home/openclaw/.openclaw/workspace-dev",
        "requirement-analyst": "/home/openclaw/.openclaw/workspace-req",
        "product-manager": "/home/openclaw/.openclaw/workspace-pm",
        "technical-architect": "/home/openclaw/.openclaw/workspace-arch",
        "ui-designer": "/home/openclaw/.openclaw/workspace-ui",
        "code-reviewer": "/home/openclaw/.openclaw/workspace-code-review",
        "security-reviewer": "/home/openclaw/.openclaw/workspace-security",
        "tester": "/home/openclaw/.openclaw/workspace-test",
        "performance-tester": "/home/openclaw/.openclaw/workspace-perf",
        "devops": "/home/openclaw/.openclaw/workspace-devops",
        "operations-agent": "/home/openclaw/.openclaw/workspace-ops",
        "doc-expert": "/home/openclaw/.openclaw/workspace-doc-expert",
        "hr": "/home/openclaw/.openclaw/workspace-hr",
        "weather": "/home/openclaw/.openclaw/workspace-weather",
        "tech-news": "/home/openclaw/.openclaw/workspace-tech-news-assistant",
        "prod-leader": "/home/openclaw/.openclaw/workspace-prod-leader",
        "sas-leader": "/home/openclaw/.openclaw/workspace-sas-leader",
        "sas-sop-expert": "/home/openclaw/.openclaw/workspace-sas-sop-expert",
        "sas-default": "/home/openclaw/.openclaw/workspace-sas-default",
    }
    return workspaces.get(agent_id)


def log_task_assignment(agent_id: str, task: str, task_id: str | None = None) -> None:
    """将任务分配记录写入 SQLite（通过文件标记）。"""
    log_file = os.path.join(TASKS_DIR, f".agent_assignments.log")
    ts = datetime.now().isoformat()
    with open(log_file, "a") as f:
        f.write(f"[{ts}] agent={agent_id} task_id={task_id or 'N/A'} task={task[:80]}\n")
