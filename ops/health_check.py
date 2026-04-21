#!/usr/bin/env python3
"""
snoopy-evolver/ops/health_check.py
P0 Ops 模块：健康检查矩阵（6项检查）

检查项：Ollama、Gateway、磁盘、上下文、Agent存活、Memory DB
输出：格式化健康报告

调用方式：
    python3 snoopy-evolver/ops/health_check.py
    python3 snoopy-evolver/ops/health_check.py --json    # JSON 格式输出
"""

import subprocess
import json
import sys
import re
from datetime import datetime
from typing import Dict, Any, Optional

# ============================================================
# 健康检查矩阵配置
# ============================================================

HEALTH_CHECK_ITEMS = {
    "ollama": {
        "name": "Ollama",
        "check_cmd": "pgrep -x ollama",
        "success_pattern": r"\d+",  # 有 PID 输出即存活
        "threshold": 1,
        "action": "restart_ollama",
        "action_cmd": "ollama serve &",
        "critical": True,
    },
    "gateway": {
        "name": "Gateway",
        "check_cmd": "pgrep -f openclaw.*gateway",
        "success_pattern": r"\d+",
        "threshold": 1,
        "action": "restart_gateway",
        "action_cmd": "openclaw gateway restart",
        "critical": True,
    },
    "disk": {
        "name": "磁盘使用率",
        "check_cmd": "df -h / | awk 'NR==2 {print $5}' | sed 's/%//'",
        "success_pattern": r"\d+",
        "threshold": 80,  # 超过 80% 报警
        "action": "cleanup_disk",
        "action_cmd": None,  # 磁盘清理需要人工判断
        "critical": False,
    },
    # === 以下 3 项已根据诊断结果修正 ===
    "context_usage": {
        "name": "上下文使用",
        # 修正：通过 Gateway HTTP API 检查，不依赖 CLI
        "check_cmd": "timeout 5 curl -s http://127.0.0.1:18789/health 2>/dev/null | grep -q 'ok\\|OK\\|healthy' && echo 'ok' || echo 'unknown'",
        "success_pattern": r"ok",
        "threshold": 1,
        "action": "archive_context",
        "action_cmd": None,
        "critical": False,
        "note": "通过 Gateway health API 检查，替代已废弃的 CLI 命令",
    },
    "agents": {
        "name": "子Agent存活",
        # 修正：team list → team discover
        "check_cmd": "timeout 5 clawteam team discover 2>/dev/null | head -5 || echo 'unknown'",
        "success_pattern": r"team|agent|worker",
        "threshold": 1,
        "action": "notify_and_repair",
        "action_cmd": None,
        "critical": False,
        "note": "clawteam team discover 是有效子命令，替代不存在的 team status",
    },
    "memory_db": {
        "name": "Memory DB",
        # 修正：不依赖 lancedb Python 包，检查文件存在 + 插件加载
        "check_cmd": "ls ~/.openclaw/memory/lancedb-pro/memories.lance 2>/dev/null && echo 'file_ok' || echo 'file_missing'",
        "success_pattern": r"file_ok",
        "threshold": 1,
        "action": "restart_lancedb",
        "action_cmd": None,
        "critical": False,
        "note": "检查 LanceDB 数据文件存在，不依赖 lancedb Python 包（插件自己管理连接）",
    },
}


def run_check(item_key: str, item_config: Dict[str, Any]) -> Dict[str, Any]:
    """执行单项检查"""
    check_cmd = item_config["check_cmd"]
    success_pattern = item_config["success_pattern"]
    threshold = item_config["threshold"]
    name = item_config["name"]
    action = item_config["action"]
    action_cmd = item_config.get("action_cmd")
    critical = item_config.get("critical", False)

    result = {
        "key": item_key,
        "name": name,
        "status": "unknown",
        "value": None,
        "message": "",
        "action_needed": False,
        "action_cmd": action_cmd,
        "critical": critical,
    }

    try:
        proc = subprocess.run(
            check_cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=15,  # 统一 15 秒超时
        )
        raw_output = proc.stdout.strip()

        # 解析输出值
        if item_key == "disk":
            try:
                result["value"] = int(raw_output)
            except ValueError:
                result["value"] = None
        else:
            result["value"] = raw_output if raw_output else None

        # 判断状态
        if item_key == "disk":
            if result["value"] is not None and result["value"] < threshold:
                result["status"] = "healthy"
                result["message"] = f"{result['value']}%（正常）"
            elif result["value"] is not None:
                result["status"] = "warning"
                result["message"] = f"{result['value']}%（建议清理）"
                result["action_needed"] = True
            else:
                result["status"] = "unknown"
                result["message"] = "无法获取磁盘使用率"

        elif item_key == "context_usage":
            if re.search(success_pattern, raw_output, re.IGNORECASE):
                result["status"] = "healthy"
                result["message"] = "Gateway 正常"
            elif "unknown" in raw_output.lower() or raw_output == "":
                result["status"] = "warning"
                result["message"] = "无法获取上下文使用量"
                result["action_needed"] = True
            else:
                result["status"] = "warning"
                result["message"] = "Gateway 响应异常"
                result["action_needed"] = True

        elif item_key == "agents":
            if "unknown" in raw_output.lower() or raw_output == "":
                result["status"] = "warning"
                result["message"] = "ClawTeam 未响应"
                result["action_needed"] = True
            elif re.search(success_pattern, raw_output, re.IGNORECASE):
                result["status"] = "healthy"
                result["message"] = "ClawTeam 正常"
                result["raw_output"] = raw_output[:100]
            else:
                result["status"] = "degraded"
                result["message"] = "ClawTeam 状态异常"
                result["action_needed"] = True

        elif item_key == "memory_db":
            if re.search(success_pattern, raw_output):
                result["status"] = "healthy"
                result["message"] = "LanceDB 数据文件正常"
            else:
                result["status"] = "error"
                result["message"] = "LanceDB 数据文件缺失"
                result["action_needed"] = True

        else:
            # ollama / gateway：进程检查
            if proc.returncode == 0 and raw_output:
                pid_match = re.search(r"\d+", raw_output)
                if pid_match:
                    result["status"] = "healthy"
                    result["message"] = f"运行中 (PID {pid_match.group()})"
                else:
                    result["status"] = "healthy"
                    result["message"] = "运行中"
            else:
                result["status"] = "down"
                result["message"] = "未运行"
                result["action_needed"] = True

    except subprocess.TimeoutExpired:
        result["status"] = "timeout"
        result["message"] = "检查超时"
        result["action_needed"] = critical
    except Exception as e:
        result["status"] = "error"
        result["message"] = f"检查异常: {str(e)}"
        result["action_needed"] = critical

    return result


def format_report(results: list, timestamp: str) -> str:
    """格式化健康报告（人类可读）"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines = []
    lines.append(f"【Ops 健康报告 - {now}】")
    lines.append("")
    lines.append(f"检查时间：{timestamp}")
    lines.append(f"检查项数：{len(results)}")
    lines.append("")

    has_warning = False
    has_error = False

    status_icon = {
        "healthy": "✅",
        "warning": "⚠️",
        "down": "❌",
        "error": "❌",
        "degraded": "⚠️",
        "unknown": "❓",
        "timeout": "⏱️",
    }

    for r in results:
        icon = status_icon.get(r["status"], "❓")
        lines.append(f"{icon} {r['name']}: {r['message']}")
        if r["status"] in ("warning", "degraded"):
            has_warning = True
        if r["status"] in ("down", "error", "timeout"):
            has_error = True

    lines.append("")
    if has_error:
        lines.append("🔴 状态：需要立即处理")
    elif has_warning:
        lines.append("🟡 状态：需要注意")
    else:
        lines.append("🟢 状态：全部正常")

    # 列出需要执行的操作
    actions_needed = [r for r in results if r["action_needed"] and r.get("action_cmd")]
    if actions_needed:
        lines.append("")
        lines.append("建议操作：")
        for r in actions_needed:
            lines.append(f"  • {r['name']} → {r['action_cmd']}")

    return "\n".join(lines)


def format_json(results: list, timestamp: str) -> str:
    """格式化健康报告（JSON）"""
    output = {
        "timestamp": timestamp,
        "total_items": len(results),
        "summary": {
            "healthy": sum(1 for r in results if r["status"] == "healthy"),
            "warning": sum(1 for r in results if r["status"] in ("warning", "degraded")),
            "error": sum(1 for r in results if r["status"] in ("down", "error", "timeout")),
            "unknown": sum(1 for r in results if r["status"] == "unknown"),
        },
        "items": results,
    }
    return json.dumps(output, ensure_ascii=False, indent=2)


def run_health_check(json_output: bool = False) -> Dict[str, Any]:
    """运行全部健康检查"""
    timestamp = datetime.now().isoformat()
    results = []

    for key, config in HEALTH_CHECK_ITEMS.items():
        result = run_check(key, config)
        results.append(result)

    if json_output:
        return {"format": "json", "data": json.loads(format_json(results, timestamp))}
    else:
        return {"format": "text", "data": format_report(results, timestamp), "raw_results": results}


def main():
    json_mode = "--json" in sys.argv

    report = run_health_check(json_output=json_mode)

    if json_mode:
        print(report["data"])
    else:
        print(report["data"])
        # 返回退出码：0=正常，1=有警告，2=有错误
        raw = report.get("raw_results", [])
        has_error = any(r["status"] in ("down", "error", "timeout") for r in raw)
        has_warning = any(r["status"] in ("warning", "degraded") for r in raw)

        if has_error:
            sys.exit(2)
        elif has_warning:
            sys.exit(1)
        else:
            sys.exit(0)


if __name__ == "__main__":
    main()
