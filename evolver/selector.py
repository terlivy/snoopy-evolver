"""
Evolver Gene Selector - 信号 → 基因匹配选择器

功能：
1. 根据输入信号匹配最佳基因
2. 支持精确匹配和模糊匹配
3. 返回匹配度最高的基因及其解决方案
"""

import json
import os
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime


@dataclass
class GeneMatch:
    """基因匹配结果"""
    gene_id: str
    name: str
    match_score: float  # 0.0 ~ 1.0
    match_type: str  # "exact" | "partial" | "fuzzy"
    solution: str
    validation: str
    success_rate: float
    usage_count: int


class GeneSelector:
    """基因选择器"""
    
    def __init__(self, genes_path: Optional[str] = None):
        if genes_path is None:
            genes_path = os.path.join(
                os.path.dirname(__file__),
                "genes",
                "genes.json"
            )
        self.genes_path = genes_path
        self.genes_data = self._load_genes()
    
    def _load_genes(self) -> Dict:
        """加载基因库"""
        if os.path.exists(self.genes_path):
            with open(self.genes_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"version": "1.0.0", "genes": []}
    
    def _normalize_signal(self, signal: str) -> str:
        """标准化信号（转小写、去除特殊字符）"""
        return signal.lower().strip()
    
    def _calculate_match_score(
        self,
        gene_signals: List[str],
        input_signals: List[str]
    ) -> Tuple[float, str]:
        """
        计算匹配分数
        
        Args:
            gene_signals: 基因的信号列表
            input_signals: 输入的信号列表
        
        Returns:
            (match_score, match_type)
        """
        gene_signals_norm = [self._normalize_signal(s) for s in gene_signals]
        input_signals_norm = [self._normalize_signal(s) for s in input_signals]
        
        # 精确匹配：输入信号在基因信号中
        exact_matches = sum(
            1 for inp in input_signals_norm
            if inp in gene_signals_norm
        )
        
        # 部分匹配：输入信号包含在基因信号中（双向）
        partial_matches = 0
        for inp in input_signals_norm:
            for gene_sig in gene_signals_norm:
                if inp in gene_sig or gene_sig in inp:
                    partial_matches += 0.5
        
        # 计算匹配度
        if exact_matches > 0:
            # 精确匹配优先
            score = exact_matches / len(input_signals_norm)
            return score, "exact" if score >= 0.8 else "partial"
        elif partial_matches > 0:
            score = partial_matches / len(input_signals_norm)
            return score * 0.8, "partial"
        else:
            return 0.0, "none"
    
    def select(
        self,
        signals: List[str],
        category: Optional[str] = None,
        top_k: int = 3
    ) -> List[GeneMatch]:
        """
        根据信号选择最佳匹配的基因
        
        Args:
            signals: 输入信号列表
            category: 可选，限定基因类别
            top_k: 返回前 k 个匹配结果
        
        Returns:
            按匹配度排序的基因列表
        """
        candidates = self.genes_data.get("genes", [])
        
        # 如果指定了类别，先过滤
        if category:
            candidates = [g for g in candidates if g.get("category") == category]
        
        matches = []
        for gene in candidates:
            gene_signals = gene.get("signals", [])
            score, match_type = self._calculate_match_score(
                gene_signals, signals
            )
            
            if score > 0:
                matches.append(GeneMatch(
                    gene_id=gene.get("gene_id", ""),
                    name=gene.get("name", ""),
                    match_score=score,
                    match_type=match_type,
                    solution=gene.get("solution", ""),
                    validation=gene.get("validation", ""),
                    success_rate=gene.get("success_rate", 0.0),
                    usage_count=gene.get("usage_count", 0)
                ))
        
        # 按匹配度排序
        matches.sort(key=lambda x: (-x.match_score, -x.success_rate))
        
        return matches[:top_k]
    
    def get_best(self, signals: List[str], category: Optional[str] = None) -> Optional[GeneMatch]:
        """获取最佳匹配的基因"""
        matches = self.select(signals, category, top_k=1)
        return matches[0] if matches else None
    
    def add_gene(self, gene: Dict) -> bool:
        """
        添加新基因到基因库
        
        Args:
            gene: 基因数据（应包含 gene_id, name, signals, solution 等字段）
        
        Returns:
            是否成功
        """
        genes = self.genes_data.get("genes", [])
        
        # 检查是否已存在
        for existing in genes:
            if existing.get("gene_id") == gene.get("gene_id"):
                return False
        
        # 添加时间戳
        gene["last_used"] = datetime.now().isoformat() + "+08:00"
        gene.setdefault("usage_count", 0)
        gene.setdefault("success_rate", 0.0)
        
        genes.append(gene)
        self.genes_data["genes"] = genes
        
        self._save_genes()
        return True
    
    def update_gene_usage(self, gene_id: str, success: bool) -> bool:
        """
        更新基因使用统计
        
        Args:
            gene_id: 基因ID
            success: 是否成功
        
        Returns:
            是否成功
        """
        genes = self.genes_data.get("genes", [])
        
        for gene in genes:
            if gene.get("gene_id") == gene_id:
                # 更新使用次数
                gene["usage_count"] = gene.get("usage_count", 0) + 1
                
                # 更新成功率（滑动平均）
                old_rate = gene.get("success_rate", 0.0)
                if success:
                    gene["success_rate"] = old_rate * 0.9 + 0.1
                else:
                    gene["success_rate"] = old_rate * 0.9
                
                # 更新时间戳
                gene["last_used"] = datetime.now().isoformat() + "+08:00"
                
                self._save_genes()
                return True
        
        return False
    
    def _save_genes(self):
        """保存基因库到文件"""
        with open(self.genes_path, "w", encoding="utf-8") as f:
            json.dump(self.genes_data, f, ensure_ascii=False, indent=2)
    
    def get_stats(self) -> Dict:
        """获取基因库统计信息"""
        genes = self.genes_data.get("genes", [])
        return {
            "total_genes": len(genes),
            "categories": list(set(g.get("category", "unknown") for g in genes)),
            "total_usage": sum(g.get("usage_count", 0) for g in genes),
            "avg_success_rate": (
                sum(g.get("success_rate", 0) for g in genes) / len(genes)
                if genes else 0
            )
        }


# 便捷函数
_selector_instance = None

def get_selector() -> GeneSelector:
    """获取基因选择器单例"""
    global _selector_instance
    if _selector_instance is None:
        _selector_instance = GeneSelector()
    return _selector_instance


def select_genes(signals: List[str], category: Optional[str] = None) -> List[GeneMatch]:
    """根据信号选择匹配的基因"""
    return get_selector().select(signals, category)


def get_best_gene(signals: List[str], category: Optional[str] = None) -> Optional[GeneMatch]:
    """获取最佳匹配的基因"""
    return get_selector().get_best(signals, category)


if __name__ == "__main__":
    # 测试
    selector = GeneSelector()
    
    # 测试：spawn 相关问题
    result = selector.select(["spawn", "subagent", "template"])
    print(f"=== 测试：spawn 问题 ===")
    for r in result:
        print(f"  [{r.match_type}] {r.name} (score={r.match_score:.2f})")
        print(f"    Solution: {r.solution[:50]}...")
        print()
    
    # 测试：gateway 重启
    result = selector.select(["gateway", "restart", "断线"])
    print(f"=== 测试：gateway 重启 ===")
    for r in result:
        print(f"  [{r.match_type}] {r.name} (score={r.match_score:.2f})")
        print()
    
    # 统计
    print(f"=== 基因库统计 ===")
    stats = selector.get_stats()
    for k, v in stats.items():
        print(f"  {k}: {v}")