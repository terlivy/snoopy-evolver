"""
Evolver Event Logger - EvolutionEvent 演进审计日志

功能：
1. 记录 SAS 任务演进事件
2. 支持 JSONL 格式审计日志
3. 自动追踪任务完成、失败、基因发现等事件类型
"""

import json
import os
from typing import Dict, Optional, List, Any
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum


class EventType(str, Enum):
    """事件类型枚举"""
    # 任务生命周期
    TASK_STARTED = "task_started"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    
    # 阶段演进
    PHASE_STARTED = "phase_started"
    PHASE_COMPLETED = "phase_completed"
    
    # 基因相关
    GENE_DISCOVERED = "gene_discovered"
    GENE_APPLIED = "gene_applied"
    GENE_SUCCESS = "gene_success"
    GENE_FAILED = "gene_failed"
    
    # 策略相关
    STRATEGY_SWITCHED = "strategy_switched"
    
    # 系统事件
    HEALTH_CHECK = "health_check"
    SYSTEM_REPAIR = "system_repair"
    
    # ClawTeam 事件
    AGENT_SPAWNED = "agent_spawned"
    AGENT_COMPLETED = "agent_completed"
    
    # 教训相关
    LESSON_LEARNED = "lesson_learned"


@dataclass
class EvolutionEvent:
    """演进事件"""
    ts: str  # ISO8601 时间戳
    type: str  # 事件类型
    task_id: Optional[str] = None
    phase: Optional[str] = None
    agent_id: Optional[str] = None
    
    # 结果数据
    outcome: Optional[str] = None  # success/failed
    duration_ms: Optional[int] = None
    
    # 基因数据
    gene_id: Optional[str] = None
    gene_name: Optional[str] = None
    
    # 指标数据
    tokens_used: Optional[int] = None
    success_rate: Optional[float] = None
    
    # 上下文
    context: Optional[Dict[str, Any]] = None
    
    # 元数据
    mode: Optional[str] = None
    tags: Optional[List[str]] = None
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        d = asdict(self)
        # 移除 None 值
        return {k: v for k, v in d.items() if v is not None}
    
    def to_json(self) -> str:
        """转换为 JSON 字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False)
    
    @staticmethod
    def from_dict(d: Dict) -> "EvolutionEvent":
        """从字典创建"""
        return EvolutionEvent(
            ts=d.get("ts", datetime.now().isoformat()),
            type=d.get("type", ""),
            task_id=d.get("task_id"),
            phase=d.get("phase"),
            agent_id=d.get("agent_id"),
            outcome=d.get("outcome"),
            duration_ms=d.get("duration_ms"),
            gene_id=d.get("gene_id"),
            gene_name=d.get("gene_name"),
            tokens_used=d.get("tokens_used"),
            success_rate=d.get("success_rate"),
            context=d.get("context"),
            mode=d.get("mode"),
            tags=d.get("tags")
        )


class EventLogger:
    """事件日志记录器"""
    
    def __init__(self, events_path: Optional[str] = None):
        if events_path is None:
            events_path = os.path.join(
                os.path.dirname(__file__),
                "events",
                "events.jsonl"
            )
        self.events_path = events_path
        self._ensure_file_exists()
    
    def _ensure_file_exists(self):
        """确保事件文件存在"""
        os.makedirs(os.path.dirname(self.events_path), exist_ok=True)
        if not os.path.exists(self.events_path):
            with open(self.events_path, "w", encoding="utf-8") as f:
                pass  # 创建空文件
    
    def log(self, event: EvolutionEvent) -> bool:
        """
        记录事件
        
        Args:
            event: 演进事件
        
        Returns:
            是否成功
        """
        try:
            with open(self.events_path, "a", encoding="utf-8") as f:
                f.write(event.to_json() + "\n")
            return True
        except Exception as e:
            print(f"[EventLogger] Failed to log event: {e}")
            return False
    
    def log_simple(
        self,
        event_type: str,
        **kwargs
    ) -> bool:
        """
        简洁日志记录接口
        
        Args:
            event_type: 事件类型（来自 EventType 或字符串）
            **kwargs: 其他字段
        """
        event = EvolutionEvent(
            ts=datetime.now().isoformat() + "+08:00",
            type=event_type,
            **kwargs
        )
        return self.log(event)
    
    def query(
        self,
        event_type: Optional[str] = None,
        task_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        limit: int = 100
    ) -> List[EvolutionEvent]:
        """
        查询事件
        
        Args:
            event_type: 事件类型过滤
            task_id: 任务ID过滤
            agent_id: Agent ID 过滤
            limit: 返回数量限制
        
        Returns:
            匹配的事件列表
        """
        events = []
        try:
            with open(self.events_path, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        d = json.loads(line)
                        
                        # 应用过滤
                        if event_type and d.get("type") != event_type:
                            continue
                        if task_id and d.get("task_id") != task_id:
                            continue
                        if agent_id and d.get("agent_id") != agent_id:
                            continue
                        
                        events.append(EvolutionEvent.from_dict(d))
                        
                        if len(events) >= limit:
                            break
                    except json.JSONDecodeError:
                        continue
        except FileNotFoundError:
            pass
        
        return events
    
    def get_recent(self, limit: int = 20) -> List[EvolutionEvent]:
        """获取最近的事件"""
        all_events = []
        try:
            with open(self.events_path, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        all_events.append(EvolutionEvent.from_dict(json.loads(line)))
                    except json.JSONDecodeError:
                        continue
        except FileNotFoundError:
            pass
        
        return all_events[-limit:] if len(all_events) > limit else all_events
    
    def get_task_events(self, task_id: str) -> List[EvolutionEvent]:
        """获取指定任务的所有事件"""
        return self.query(task_id=task_id, limit=1000)
    
    def get_stats(self) -> Dict:
        """获取事件统计"""
        stats = {
            "total_events": 0,
            "by_type": {},
            "recent_tasks": []
        }
        
        try:
            tasks_seen = set()
            with open(self.events_path, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        d = json.loads(line)
                        stats["total_events"] += 1
                        
                        # 按类型统计
                        evt_type = d.get("type", "unknown")
                        stats["by_type"][evt_type] = stats["by_type"].get(evt_type, 0) + 1
                        
                        # 最近任务
                        task_id = d.get("task_id")
                        if task_id and task_id not in tasks_seen:
                            tasks_seen.add(task_id)
                            stats["recent_tasks"].append({
                                "task_id": task_id,
                                "type": d.get("type"),
                                "ts": d.get("ts")
                            })
                    except json.JSONDecodeError:
                        continue
        except FileNotFoundError:
            pass
        
        # 只保留最近 10 个任务
        stats["recent_tasks"] = stats["recent_tasks"][-10:]
        return stats


# 便捷函数
_logger_instance = None

def get_logger() -> EventLogger:
    """获取日志记录器单例"""
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = EventLogger()
    return _logger_instance


def log_event(event_type: str, **kwargs) -> bool:
    """记录事件的便捷函数"""
    return get_logger().log_simple(event_type, **kwargs)


def log_task_started(task_id: str, mode: str = "balanced", **kwargs) -> bool:
    """记录任务开始"""
    return log_event(EventType.TASK_STARTED.value, task_id=task_id, mode=mode, **kwargs)


def log_task_completed(task_id: str, outcome: str = "success", **kwargs) -> bool:
    """记录任务完成"""
    return log_event(EventType.TASK_COMPLETED.value, task_id=task_id, outcome=outcome, **kwargs)


def log_gene_applied(gene_id: str, gene_name: str, task_id: Optional[str] = None, **kwargs) -> bool:
    """记录基因应用"""
    return log_event(
        EventType.GENE_APPLIED.value,
        gene_id=gene_id,
        gene_name=gene_name,
        task_id=task_id,
        **kwargs
    )


def log_gene_result(gene_id: str, gene_name: str, success: bool, **kwargs) -> bool:
    """记录基因应用结果"""
    return log_event(
        EventType.GENE_SUCCESS.value if success else EventType.GENE_FAILED.value,
        gene_id=gene_id,
        gene_name=gene_name,
        outcome="success" if success else "failed",
        **kwargs
    )


if __name__ == "__main__":
    # 测试
    logger = EventLogger()
    
    # 记录测试事件
    logger.log_simple(EventType.TASK_STARTED.value, task_id="TEST-001", mode="balanced")
    logger.log_simple(EventType.PHASE_COMPLETED.value, task_id="TEST-001", phase="plan")
    logger.log_simple(EventType.GENE_APPLIED.value, gene_id="gene_spawn_template", gene_name="子智能体 Spawn 模板")
    logger.log_simple(EventType.TASK_COMPLETED.value, task_id="TEST-001", outcome="success")
    
    print("=== 测试：记录事件 ===")
    print(f"事件文件: {logger.events_path}")
    
    print("\n=== 测试：查询事件 ===")
    events = logger.query(task_id="TEST-001")
    for e in events:
        print(f"  [{e.ts}] {e.type}")
    
    print("\n=== 测试：统计 ===")
    stats = logger.get_stats()
    for k, v in stats.items():
        print(f"  {k}: {v}")