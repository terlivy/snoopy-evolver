"""
Evolver ClawTeam Integration - 跨 Agent 经验共享

功能：
1. 当 ClawTeam Agent 发现新修复方案时，自动存入基因库
2. 其他 Agent 可查询和复用基因
3. 与 P1 基因库集成

工作流程：
Agent 发现问题 → 提取信号 → 匹配/创建基因 → 存入基因库 → 广播给其他 Agent
"""

import json
import os
import re
from typing import Dict, Optional, List, Any, Callable
from datetime import datetime
from dataclasses import dataclass, asdict

# 导入基因选择器
import sys
sys.path.insert(0, os.path.dirname(__file__))
from selector import GeneSelector, get_best_gene
from events.logger import EventLogger, EventType, log_event


@dataclass
class ClawTeamGeneCandidate:
    """ClawTeam 基因候选"""
    agent_id: str
    task_id: str
    problem: str
    solution: str
    signals: List[str]
    confidence: float  # 0.0 ~ 1.0
    raw_output: str


class ClawTeamIntegration:
    """ClawTeam 集成模块"""
    
    def __init__(
        self,
        genes_path: Optional[str] = None,
        events_path: Optional[str] = None
    ):
        self.gene_selector = GeneSelector(genes_path)
        self.event_logger = EventLogger(events_path)
        self._callbacks: List[Callable] = []
    
    def on_agent_output(
        self,
        agent_id: str,
        task_id: str,
        output: str,
        success: bool = True
    ) -> Optional[Dict]:
        """
        处理 Agent 输出，检测是否有值得存档的经验
        
        Args:
            agent_id: Agent ID
            task_id: 任务 ID
            output: Agent 输出内容
            success: 是否成功
        
        Returns:
            如果发现新基因，返回基因信息；否则返回 None
        """
        # 分析输出，提取信号和解决方案
        candidate = self._analyze_output(agent_id, task_id, output, success)
        
        if candidate is None:
            return None
        
        # 检查是否值得存档
        if not self._is_notable_fix(candidate):
            return None
        
        # 检查是否已存在相似基因
        existing = self.gene_selector.get_best(candidate.signals)
        
        if existing and existing.match_score >= 0.8:
            # 已存在高匹配基因，更新其使用统计
            self.gene_selector.update_gene_usage(existing.gene_id, success)
            
            # 记录事件
            log_event(
                "gene_reused",
                agent_id=agent_id,
                task_id=task_id,
                gene_id=existing.gene_id,
                gene_name=existing.name,
                outcome="success" if success else "failed"
            )
            
            return {
                "action": "reused",
                "gene_id": existing.gene_id,
                "gene_name": existing.name,
                "match_score": existing.match_score
            }
        
        # 创建新基因
        new_gene = self._create_gene_from_candidate(candidate)
        
        if new_gene:
            # 添加到基因库
            self.gene_selector.add_gene(new_gene)
            
            # 记录发现事件
            log_event(
                EventType.GENE_DISCOVERED.value,
                agent_id=agent_id,
                task_id=task_id,
                gene_id=new_gene["gene_id"],
                gene_name=new_gene["name"],
                context={"confidence": candidate.confidence}
            )
            
            # 广播给其他 Agent
            self._broadcast_new_gene(new_gene)
            
            return {
                "action": "discovered",
                "gene_id": new_gene["gene_id"],
                "gene_name": new_gene["name"],
                "signals": candidate.signals
            }
        
        return None
    
    def _analyze_output(
        self,
        agent_id: str,
        task_id: str,
        output: str,
        success: bool
    ) -> Optional[ClawTeamGeneCandidate]:
        """分析 Agent 输出，提取问题和解决方案"""
        # 简单的启发式分析
        # 实际情况可能需要结合 LLM 来做更精确的提取
        
        # 检测修复模式
        fix_patterns = [
            r"(?:修复|解决|fix|resolve).*?[:：]\s*(.+?)(?:\n|$)",
            r"(?:方案|solution).*?[:：]\s*(.+?)(?:\n|$)",
            r"(?:步骤|steps?).*?[:：]\s*(.+?)(?:\n|$)",
            r"(?:commands?|cmd).*?[:：]\s*(.+?)(?:\n|$)",
        ]
        
        problem = ""
        solution = ""
        signals = []
        
        # 尝试从输出中提取问题和解决方案
        if not success:
            # 失败情况 - 记录失败模式作为信号
            error_keywords = self._extract_error_keywords(output)
            if error_keywords:
                signals.extend(error_keywords)
        
        # 检测是否包含修复/解决相关的内容
        for pattern in fix_patterns:
            match = re.search(pattern, output, re.IGNORECASE | re.MULTILINE)
            if match:
                content = match.group(1).strip()
                if len(content) > 10:  # 排除太短的内容
                    if not solution:
                        solution = content
                        # 从解决方案中提取信号
                        signals.extend(self._extract_signals_from_text(content))
        
        if not solution:
            return None
        
        # 尝试提取问题描述
        problem_patterns = [
            r"(?:问题|issue|error|failed).*?[:：]\s*(.+?)(?:\n|$)",
            r"(?:遇到|encounter).*?[:：]\s*(.+?)(?:\n|$)",
        ]
        
        for pattern in problem_patterns:
            match = re.search(pattern, output, re.IGNORECASE | re.MULTILINE)
            if match:
                problem = match.group(1).strip()
                signals.extend(self._extract_signals_from_text(problem))
                break
        
        if not signals:
            return None
        
        # 计算置信度（基于信号数量和解决方案长度）
        confidence = min(1.0, (len(signals) * 0.1 + len(solution) / 500 * 0.5))
        
        return ClawTeamGeneCandidate(
            agent_id=agent_id,
            task_id=task_id,
            problem=problem,
            solution=solution,
            signals=signals[:10],  # 限制信号数量
            confidence=confidence,
            raw_output=output[:500]  # 截断原始输出
        )
    
    def _extract_signals_from_text(self, text: str) -> List[str]:
        """从文本中提取信号"""
        signals = []
        
        # 提取技术关键词
        tech_patterns = [
            r"\b(gateway|ollama|openclaw|clawteam|github|feishu)\b",
            r"\b(restart|kill|start|stop|serve)\b",
            r"\b(error|failed|timeout|port|path)\b",
            r"\b(spawn|subagent|agent|task)\b",
        ]
        
        for pattern in tech_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            signals.extend([m.lower() for m in matches])
        
        # 提取文件名、路径
        path_pattern = r"[\w\-\.]+(?:\.\w+)|/[a-zA-Z0-9_/\-\.]+"
        paths = re.findall(path_pattern, text)
        signals.extend([p for p in paths if len(p) > 3][:5])
        
        return list(set(signals))  # 去重
    
    def _extract_error_keywords(self, text: str) -> List[str]:
        """提取错误关键词"""
        errors = []
        
        # 错误模式
        error_patterns = [
            r"(?:Error|Exception|failed|Failed|ERROR)[:\s]+([^\n]{10,50})",
            r"(?:port|Port)[:\s]*(\d+)",
            r"(?:file|File)[:\s]*([^\n]+)",
            r"([a-zA-Z0-9_\-]+(?:\.[a-zA-Z]+)+)",  # 文件名
        ]
        
        for pattern in error_patterns:
            matches = re.findall(pattern, text)
            errors.extend([m.strip().lower() for m in matches if len(m) > 2])
        
        return errors[:5]
    
    def _is_notable_fix(self, candidate: ClawTeamGeneCandidate) -> bool:
        """判断是否值得存档为基因"""
        # 置信度阈值
        if candidate.confidence < 0.5:
            return False
        
        # 解决方案长度阈值
        if len(candidate.solution) < 20:
            return False
        
        # 信号数量阈值
        if len(candidate.signals) < 2:
            return False
        
        return True
    
    def _create_gene_from_candidate(
        self,
        candidate: ClawTeamGeneCandidate
    ) -> Optional[Dict]:
        """从候选创建基因"""
        gene_id = f"gene_cta_{candidate.agent_id.lower()}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        return {
            "gene_id": gene_id,
            "name": f"来自 {candidate.agent_id} 的修复方案",
            "category": "clawteam_discovered",
            "signals": candidate.signals,
            "signals_raw": candidate.signals,
            "problem": candidate.problem or "由 ClawTeam Agent 发现",
            "solution": candidate.solution,
            "validation": "通过实际使用验证",
            "success_rate": 0.85 if candidate.confidence > 0.7 else 0.7,
            "usage_count": 1,
            "last_used": datetime.now().isoformat() + "+08:00",
            "lessons_source": [f"ClawTeam/{candidate.agent_id}"],
            "tags": ["clawteam", "auto-discovered"],
            "discovered_by": candidate.agent_id,
            "task_id": candidate.task_id
        }
    
    def _broadcast_new_gene(self, gene: Dict):
        """广播新基因给其他 Agent"""
        message = {
            "type": "new_gene_discovered",
            "gene_id": gene["gene_id"],
            "gene_name": gene["name"],
            "signals": gene["signals"][:5],  # 只传前5个信号
            "discovered_by": gene.get("discovered_by", "unknown"),
            "ts": datetime.now().isoformat() + "+08:00"
        }
        
        # 调用所有注册的回调函数
        for callback in self._callbacks:
            try:
                callback(message)
            except Exception as e:
                print(f"[ClawTeamIntegration] Callback failed: {e}")
    
    def register_callback(self, callback: Callable):
        """注册回调函数，用于接收新基因通知"""
        self._callbacks.append(callback)
    
    def query_genes(
        self,
        signals: List[str],
        category: Optional[str] = None
    ) -> List[Dict]:
        """查询匹配的基因"""
        matches = self.gene_selector.select(signals, category, top_k=5)
        return [
            {
                "gene_id": m.gene_id,
                "name": m.name,
                "match_score": m.match_score,
                "match_type": m.match_type,
                "solution": m.solution,
                "success_rate": m.success_rate
            }
            for m in matches
        ]
    
    def get_gene_suggestions(self, context: Dict[str, Any]) -> List[Dict]:
        """
        根据上下文获取基因建议
        
        Args:
            context: 包含 agent_id, task_type, recent_errors 等信息
        
        Returns:
            建议的基因列表
        """
        signals = []
        
        # 从上下文提取信号
        if "task_type" in context:
            signals.append(context["task_type"])
        
        if "recent_errors" in context:
            if isinstance(context["recent_errors"], list):
                signals.extend(context["recent_errors"])
            else:
                signals.append(context["recent_errors"])
        
        if "technologies" in context:
            if isinstance(context["technologies"], list):
                signals.extend(context["technologies"])
        
        if not signals:
            return []
        
        return self.query_genes(signals)


# 便捷函数
_integration_instance = None

def get_integration() -> ClawTeamIntegration:
    """获取 ClawTeam 集成单例"""
    global _integration_instance
    if _integration_instance is None:
        _integration_instance = ClawTeamIntegration()
    return _integration_instance


def on_agent_output(agent_id: str, task_id: str, output: str, success: bool = True) -> Optional[Dict]:
    """处理 Agent 输出，检测新经验"""
    return get_integration().on_agent_output(agent_id, task_id, output, success)


def query_shared_genes(signals: List[str]) -> List[Dict]:
    """查询共享基因库"""
    return get_integration().query_genes(signals)


if __name__ == "__main__":
    # 测试
    integration = ClawTeamIntegration()
    
    # 模拟 Agent 输出
    test_output = """
    [Agent-Backend] 执行任务：
    
    问题: Gateway 重启后端口 18789 被占用
    解决步骤:
    1. 检查端口占用: lsof -i :18789
    2. kill 对应进程
    3. 执行 openclaw gateway restart
    4. 验证: curl http://127.0.0.1:18789/health
    
    结果: 成功修复
    """
    
    result = integration.on_agent_output(
        agent_id="Agent-Backend",
        task_id="TASK-001",
        output=test_output,
        success=True
    )
    
    print("=== 测试：ClawTeam Agent 输出分析 ===")
    if result:
        print(f"动作: {result['action']}")
        print(f"基因: {result.get('gene_name', result.get('gene_id'))}")
        if result['action'] == 'discovered':
            print(f"信号: {result['signals']}")
    else:
        print("未发现新基因")
    
    # 测试基因查询
    print("\n=== 测试：基因查询 ===")
    suggestions = integration.get_gene_suggestions({
        "task_type": "gateway",
        "recent_errors": ["port", "18789"]
    })
    for s in suggestions:
        print(f"  [{s['match_score']:.2f}] {s['name']}")
    
    print("\n=== 基因库统计 ===")
    stats = integration.gene_selector.get_stats()
    for k, v in stats.items():
        print(f"  {k}: {v}")