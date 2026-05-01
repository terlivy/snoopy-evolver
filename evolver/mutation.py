#!/usr/bin/env python3
"""
snoopy-evolver/evolver/mutation.py
基因变异器 - 从信号生成/适配基因

职责：
1. 从信号生成新基因
2. 适配现有基因到新场景
3. 验证基因有效性
4. 管理基因生命周期

参考：evolver-source/src/gep/mutation.js
"""

import json
import os
import re
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from dataclasses import dataclass, asdict
from pathlib import Path


# 基因文件路径
GENES_DIR = Path(__file__).parent / "genes"
GENES_PATH = GENES_DIR / "genes.json"

# 最小匹配分数阈值
MIN_MATCH_SCORE = 0.3

# 最大基因信号数
MAX_SIGNAL_TOKENS = 8


@dataclass
class MutationResult:
    """变异结果"""
    success: bool
    gene_id: Optional[str] = None
    gene_name: Optional[str] = None
    mutation_type: Optional[str] = None  # "new" | "adapted" | "none"
    match_score: float = 0.0
    problem: Optional[str] = None
    solution: Optional[str] = None
    validation: Optional[str] = None
    message: str = ""
    warnings: List[str] = None

    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []

    def to_dict(self) -> Dict:
        d = asdict(self)
        d["warnings"] = self.warnings
        return d


class GeneMutation:
    """基因变异器"""

    def __init__(self, genes_path: Optional[str] = None):
        if genes_path is None:
            genes_path = str(GENES_PATH)
        self.genes_path = genes_path
        self.genes_data = self._load_genes()

    def _load_genes(self) -> Dict:
        """加载基因库"""
        if os.path.exists(self.genes_path):
            try:
                with open(self.genes_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return {"version": "1.0.0", "genes": [], "created_at": datetime.now().isoformat() + "+08:00"}

    def _save_genes(self) -> bool:
        """保存基因库"""
        try:
            os.makedirs(os.path.dirname(self.genes_path), exist_ok=True)
            with open(self.genes_path, "w", encoding="utf-8") as f:
                json.dump(self.genes_data, f, ensure_ascii=False, indent=2)
            return True
        except IOError as e:
            print(f"[Mutation] Failed to save genes: {e}")
            return False

    def _generate_gene_id(self, base_name: str) -> str:
        """生成唯一的基因ID"""
        # 规范化名称作为基础
        normalized = re.sub(r'[^a-z0-9]', '_', base_name.lower())
        normalized = re.sub(r'_+', '_', normalized).strip('_')[:20]
        timestamp = datetime.now().strftime("%m%d%H%M")
        return f"gene_{normalized}_{timestamp}"

    def _extract_signals_from_context(self, context: Dict[str, Any]) -> List[str]:
        """从上下文提取信号特征"""
        signals = []

        # 从任务类型提取
        if "task_type" in context:
            signals.append(context["task_type"])

        # 从错误信息提取
        if "error" in context:
            error = context["error"]
            if isinstance(error, str):
                # 提取关键错误词
                error_words = re.findall(r'\b(\w+)\b', error.lower())
                signals.extend(error_words[:5])

        # 从操作类型提取
        if "operation" in context:
            signals.append(context["operation"])

        # 从相关文件提取
        if "files" in context:
            files = context["files"]
            if isinstance(files, list):
                for f in files[:3]:
                    if isinstance(f, str):
                        # 提取文件名特征
                        name = os.path.splitext(os.path.basename(f))[0]
                        signals.append(name)

        # 去重并限制数量
        signals = list(dict.fromkeys(signals))[:MAX_SIGNAL_TOKENS]
        return signals

    def _compute_match_score(self, gene_signals: List[str], input_signals: List[str]) -> float:
        """计算两个信号列表的匹配分数"""
        if not gene_signals or not input_signals:
            return 0.0

        gene_set = set(s.lower() for s in gene_signals)
        input_set = set(s.lower() for s in input_signals)

        # Jaccard 相似度
        intersection = len(gene_set & input_set)
        union = len(gene_set | input_set)

        if union == 0:
            return 0.0

        return intersection / union

    def find_similar_genes(self, signals: List[str], top_k: int = 3) -> List[Dict]:
        """查找相似的现有基因"""
        genes = self.genes_data.get("genes", [])
        scored = []

        for gene in genes:
            gene_signals = gene.get("signals", [])
            score = self._compute_match_score(gene_signals, signals)
            if score >= MIN_MATCH_SCORE:
                scored.append((score, gene))

        # 按分数排序
        scored.sort(key=lambda x: -x[0])
        return [g for _, g in scored[:top_k]]

    def mutate_from_signal(
        self,
        signal_type: str,
        context: Dict[str, Any]
    ) -> MutationResult:
        """
        从信号生成/适配基因

        Args:
            signal_type: 信号类型
            context: 包含 problem, existing_genes, task_info 等

        Returns:
            MutationResult
        """
        warnings = []
        problem = context.get("problem", "")
        task_info = context.get("task_info", {})
        existing_genes = context.get("existing_genes", [])

        # 1. 尝试找相似基因进行适配
        similar_genes = self.find_similar_genes([signal_type])

        if similar_genes and not context.get("force_new", False):
            # 适配模式：基于相似基因改进
            best_match = similar_genes[0]
            match_score = self._compute_match_score(
                best_match.get("signals", []),
                [signal_type]
            )

            # 提取现有解决方案
            old_solution = best_match.get("solution", "")

            # 生成适配后的解决方案
            adapted_solution = self._adapt_solution(
                old_solution,
                problem,
                task_info
            )

            if adapted_solution != old_solution:
                # 创建适配后的基因
                new_gene_id = self._generate_gene_id(best_match.get("name", signal_type))
                new_gene = {
                    "gene_id": new_gene_id,
                    "name": f"{best_match.get('name', signal_type)} (适配)",
                    "category": best_match.get("category", "adapted"),
                    "signals": list(set([signal_type] + best_match.get("signals", [])[:5]))[:MAX_SIGNAL_TOKENS],
                    "problem": problem or best_match.get("problem", ""),
                    "solution": adapted_solution,
                    "validation": best_match.get("validation", ""),
                    "success_rate": 0.5,  # 新基因，降低初始成功率
                    "usage_count": 0,
                    "last_used": datetime.now().isoformat() + "+08:00",
                    "adapted_from": best_match.get("gene_id", ""),
                    "tags": [signal_type]
                }

                return MutationResult(
                    success=True,
                    gene_id=new_gene_id,
                    gene_name=new_gene["name"],
                    mutation_type="adapted",
                    match_score=match_score,
                    problem=new_gene["problem"],
                    solution=adapted_solution,
                    validation=new_gene["validation"],
                    message=f"基于基因 {best_match.get('gene_id')} 适配生成",
                    warnings=[f"适配自 {best_match.get('name')}"],
                )
            else:
                warnings.append("解决方案无需适配，使用原基因")
                return MutationResult(
                    success=True,
                    gene_id=best_match.get("gene_id"),
                    gene_name=best_match.get("name"),
                    mutation_type="none",
                    match_score=match_score,
                    message="现有基因已足够",
                    warnings=warnings
                )

        # 2. 生成新基因
        # 提取问题描述
        if not problem and task_info:
            problem = self._summarize_problem(signal_type, task_info)

        # 生成解决方案
        solution = self._generate_solution(signal_type, problem, task_info)

        # 生成验证方法
        validation = self._generate_validation(signal_type, problem)

        # 创建新基因
        new_gene_id = self._generate_gene_id(signal_type)
        signals = self._extract_signals_from_context(context)
        if not signals:
            signals = [signal_type]

        new_gene = {
            "gene_id": new_gene_id,
            "name": f"新基因-{signal_type}",
            "category": "auto_generated",
            "signals": signals,
            "problem": problem,
            "solution": solution,
            "validation": validation,
            "success_rate": 0.5,  # 新基因初始成功率
            "usage_count": 0,
            "last_used": datetime.now().isoformat() + "+08:00",
            "source_signal": signal_type,
            "tags": [signal_type]
        }

        return MutationResult(
            success=True,
            gene_id=new_gene_id,
            gene_name=new_gene["name"],
            mutation_type="new",
            match_score=1.0,
            problem=problem,
            solution=solution,
            validation=validation,
            message=f"从信号 {signal_type} 生成新基因",
            warnings=warnings
        )

    def _summarize_problem(self, signal_type: str, task_info: Dict) -> str:
        """根据任务信息总结问题"""
        task_desc = task_info.get("description", "")
        if task_desc:
            return f"任务 {signal_type} 需要处理：{task_desc[:100]}"
        return f"信号 {signal_type} 触发的演化需求"

    def _generate_solution(
        self,
        signal_type: str,
        problem: str,
        task_info: Dict
    ) -> str:
        """生成解决方案"""
        solution_parts = []

        # 基于信号类型添加通用指导
        if "spawn" in signal_type.lower():
            solution_parts.append("Spawn 新智能体前准备完整参数：runtime、mode、channel、task描述")
            solution_parts.append("使用模板确保不遗漏关键配置")

        if "failure" in signal_type.lower() or "error" in signal_type.lower():
            solution_parts.append("分析错误日志，定位根本原因")
            solution_parts.append("如果是配置问题，参考现有成功案例调整参数")

        if "gateway" in signal_type.lower():
            solution_parts.append("Gateway 重启前确保任务状态已保存")
            solution_parts.append("重启后验证各 Agent 连接状态")

        # 从任务信息提取特定指导
        if task_info:
            action = task_info.get("action", "")
            if action:
                solution_parts.append(f"执行动作：{action}")

        if not solution_parts:
            solution_parts.append(f"针对 {signal_type} 类型信号进行专项处理")
            solution_parts.append("参考基因库中相似场景的成功经验")

        return "；".join(solution_parts)

    def _generate_validation(self, signal_type: str, problem: str) -> str:
        """生成验证方法"""
        if "spawn" in signal_type.lower():
            return "子智能体成功启动并完成分配任务"
        if "failure" in signal_type.lower():
            return "相同错误不再重现，任务正常完成"
        if "gateway" in signal_type.lower():
            return "Gateway 重启后所有连接恢复正常"
        return f"信号 {signal_type} 相关问题得到解决"

    def _adapt_solution(
        self,
        old_solution: str,
        problem: str,
        task_info: Dict
    ) -> str:
        """适配现有解决方案到新场景"""
        if not old_solution:
            return self._generate_solution("", problem, task_info)

        # 如果问题描述不同，在原方案基础上添加
        if problem and problem not in old_solution:
            return f"{old_solution}。补充：针对新问题 '{problem[:50]}' 需额外处理"

        return old_solution

    def save_gene(self, gene: Dict) -> bool:
        """
        保存基因到基因库

        Args:
            gene: 基因数据

        Returns:
            是否成功
        """
        genes = self.genes_data.get("genes", [])

        # 检查是否已存在
        gene_id = gene.get("gene_id")
        for i, existing in enumerate(genes):
            if existing.get("gene_id") == gene_id:
                # 更新现有基因
                genes[i] = gene
                self.genes_data["genes"] = genes
                return self._save_genes()

        # 添加新基因
        genes.append(gene)
        self.genes_data["genes"] = genes
        return self._save_genes()

    def update_gene_stats(self, gene_id: str, success: bool) -> bool:
        """更新基因使用统计"""
        genes = self.genes_data.get("genes", [])

        for gene in genes:
            if gene.get("gene_id") == gene_id:
                # 更新使用次数
                gene["usage_count"] = gene.get("usage_count", 0) + 1

                # 更新成功率（滑动平均）
                old_rate = gene.get("success_rate", 0.5)
                if success:
                    gene["success_rate"] = old_rate * 0.9 + 0.1
                else:
                    gene["success_rate"] = old_rate * 0.9

                # 更新时间戳
                gene["last_used"] = datetime.now().isoformat() + "+08:00"

                return self._save_genes()

        return False

    def get_gene(self, gene_id: str) -> Optional[Dict]:
        """获取指定基因"""
        genes = self.genes_data.get("genes", [])
        for gene in genes:
            if gene.get("gene_id") == gene_id:
                return gene
        return None

    def delete_gene(self, gene_id: str) -> bool:
        """删除基因"""
        genes = self.genes_data.get("genes", [])
        original_len = len(genes)
        genes = [g for g in genes if g.get("gene_id") != gene_id]

        if len(genes) < original_len:
            self.genes_data["genes"] = genes
            return self._save_genes()

        return False


# ============================================================================
# 便捷函数
# ============================================================================

_mutation_instance = None


def get_mutator() -> GeneMutation:
    """获取变异器单例"""
    global _mutation_instance
    if _mutation_instance is None:
        _mutation_instance = GeneMutation()
    return _mutation_instance


def mutate_signal(signal_type: str, context: Dict[str, Any]) -> MutationResult:
    """
    从信号生成基因变异的便捷函数

    Args:
        signal_type: 信号类型
        context: 上下文信息，包含 problem, task_info 等

    Returns:
        MutationResult
    """
    mutator = get_mutator()
    return mutator.mutate_from_signal(signal_type, context)


def save_mutated_gene(gene: Dict) -> bool:
    """保存变异后的基因"""
    return get_mutator().save_gene(gene)


def update_gene_success(gene_id: str, success: bool) -> bool:
    """更新基因成功统计"""
    return get_mutator().update_gene_stats(gene_id, success)


if __name__ == "__main__":
    # 测试
    print("=== Mutation 测试 ===")

    mutator = GeneMutation()

    # 测试1：从新信号生成基因
    result = mutator.mutate_from_signal("new_module", {
        "problem": "新模块需要标准化的错误处理",
        "task_info": {"description": "创建一个通用的错误处理模块"}
    })
    print(f"\n[新信号测试] {result.gene_name}")
    print(f"  类型: {result.mutation_type}")
    print(f"  解决方案: {result.solution[:60]}...")
    print(f"  基因ID: {result.gene_id}")

    # 测试2：查找相似基因
    similar = mutator.find_similar_genes(["spawn", "subagent"])
    print(f"\n[相似基因查找] 找到 {len(similar)} 个")
    for g in similar:
        print(f"  - {g.get('name')} (signals: {g.get('signals')[:3]})")

    # 测试3：保存新基因
    if result.success and result.mutation_type == "new":
        gene = {
            "gene_id": result.gene_id,
            "name": result.gene_name,
            "category": "auto_generated",
            "signals": [result.gene_id.split("_")[1]] if "_" in result.gene_id else [],
            "problem": result.problem,
            "solution": result.solution,
            "validation": result.validation,
            "success_rate": 0.5,
            "usage_count": 0,
            "last_used": datetime.now().isoformat() + "+08:00"
        }
        saved = mutator.save_gene(gene)
        print(f"\n[保存基因] {'成功' if saved else '失败'}")

    print("\n=== 测试完成 ===")
