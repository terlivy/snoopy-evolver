"""
snoopy-evolver/agent_tracker/tracker.py
Agent 性能追踪器 - 记录每次派发的数据
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional
from dataclasses import asdict

from .models import AgentSpawnRecord, TASK_TYPES, COMPLEXITY_LEVELS

# 默认记录文件
DEFAULT_LOG_FILE = Path(__file__).parent / "agent_spawn_log.jsonl"

class AgentTracker:
    """Agent 性能追踪器"""

    def __init__(self, log_file: Optional[Path] = None):
        self.log_file = Path(log_file) if log_file else DEFAULT_LOG_FILE
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

    def log_spawn(
        self,
        parent_agent: str,
        child_agent_label: str,
        model_used: str,
        task_description: str,
        task_type: str,
        complexity: str = "L1",
        spawning_method: str = "sessions_spawn",
        session_key: Optional[str] = None,
        **metadata
    ) -> AgentSpawnRecord:
        """记录一次 Agent 派发事件"""

        # 提取 provider
        model_provider = model_used.split("/")[0] if "/" in model_used else "unknown"

        record = AgentSpawnRecord(
            spawn_id=str(uuid.uuid4()),
            spawn_timestamp=datetime.now().isoformat(),
            parent_agent=parent_agent,
            child_agent_id="",  # 派发时还不知道
            child_agent_label=child_agent_label,
            model_used=model_used,
            model_provider=model_provider,
            task_description=task_description,
            task_type=task_type,
            complexity=complexity,
            spawning_method=spawning_method,
            session_key=session_key,
            completion_status="pending",
            metadata=metadata
        )

        self._append_record(record)
        return record

    def log_completion(
        self,
        spawn_id: str,
        success: bool,
        quality_score: Optional[float] = None,
        duration_seconds: Optional[int] = None,
        tokens_in: Optional[int] = None,
        tokens_out: Optional[int] = None,
        total_cost: Optional[float] = None,
        failure_reason: Optional[str] = None,
        error_type: Optional[str] = None,
        child_agent_id: Optional[str] = None,
        **metadata
    ) -> None:
        """记录任务完成/失败结果"""
        records = self._load_records()

        for i, rec in enumerate(records):
            if rec.get("spawn_id") == spawn_id:
                records[i]["completion_status"] = "completed" if success else "failed"
                records[i]["success"] = success
                records[i]["quality_score"] = quality_score
                records[i]["duration_seconds"] = duration_seconds
                records[i]["tokens_in"] = tokens_in
                records[i]["tokens_out"] = tokens_out
                records[i]["total_cost"] = total_cost
                records[i]["failure_reason"] = failure_reason
                records[i]["error_type"] = error_type
                if child_agent_id:
                    records[i]["child_agent_id"] = child_agent_id
                records[i].update(metadata)
                break

        self._save_records(records)

    def log_timeout(self, spawn_id: str, duration_seconds: int) -> None:
        """记录任务超时"""
        self.log_completion(spawn_id, success=False, duration_seconds=duration_seconds,
                          failure_reason="timeout", error_type="TIMEOUT")

    def log_cancelled(self, spawn_id: str) -> None:
        """记录任务取消"""
        self.log_completion(spawn_id, success=False, failure_reason="cancelled",
                          error_type="CANCELLED")

    def get_records(
        self,
        model: Optional[str] = None,
        task_type: Optional[str] = None,
        parent_agent: Optional[str] = None,
        limit: int = 100
    ) -> list:
        """查询记录"""
        records = self._load_records()
        results = []

        for rec in reversed(records):
            if model and rec.get("model_used") != model:
                continue
            if task_type and rec.get("task_type") != task_type:
                continue
            if parent_agent and rec.get("parent_agent") != parent_agent:
                continue
            results.append(rec)
            if len(results) >= limit:
                break

        return results

    def get_record_by_id(self, spawn_id: str) -> Optional[dict]:
        """按ID查询单条记录"""
        records = self._load_records()
        for rec in records:
            if rec.get("spawn_id") == spawn_id:
                return rec
        return None

    def _append_record(self, record: AgentSpawnRecord) -> None:
        """追加记录到文件"""
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(record.to_dict(), ensure_ascii=False) + "\n")

    def _load_records(self) -> list:
        """从文件加载所有记录"""
        if not self.log_file.exists():
            return []

        records = []
        with open(self.log_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        records.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        return records

    def _save_records(self, records: list) -> None:
        """保存所有记录到文件"""
        with open(self.log_file, "w", encoding="utf-8") as f:
            for rec in records:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    def count(self) -> int:
        """返回总记录数"""
        return len(self._load_records())

# 全局追踪器实例
_tracker: Optional[AgentTracker] = None

def get_tracker() -> AgentTracker:
    """获取全局追踪器实例"""
    global _tracker
    if _tracker is None:
        _tracker = AgentTracker()
    return _tracker

# 便捷函数
def log_spawn(**kwargs) -> AgentSpawnRecord:
    """快捷函数：记录派发"""
    return get_tracker().log_spawn(**kwargs)

def log_completion(**kwargs) -> None:
    """快捷函数：记录完成"""
    get_tracker().log_completion(**kwargs)

def get_records(**kwargs) -> list:
    """快捷函数：查询记录"""
    return get_tracker().get_records(**kwargs)
