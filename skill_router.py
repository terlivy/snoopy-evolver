#!/usr/bin/env python3
"""
skill_router.py - SC Skill Router 核心模块
查询 skill_inventory.yaml，基于任务描述匹配最合适的 Skill。

使用方式：
    from skill_router import SkillRouter
    router = SkillRouter()
    matches = router.match("帮我分析飞书消息")
    for m in matches:
        print(f"{m['name']} ({m['category']}) - 置信度: {m['confidence']}")
"""

import os
import yaml
from typing import List, Dict, Optional

SKILL_INVENTORY_PATH = os.path.join(
    os.path.dirname(__file__), "skill_inventory.yaml"
)


class SkillRouter:
    """Skill 路由器 - 基于任务描述匹配最佳 Skill"""

    def __init__(self, inventory_path: Optional[str] = None):
        self.inventory_path = inventory_path or SKILL_INVENTORY_PATH
        self._inventory = None

    @property
    def inventory(self) -> List[Dict]:
        """懒加载 Skill Inventory"""
        if self._inventory is None:
            with open(self.inventory_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            self._inventory = data.get("skill_inventory", [])
        return self._inventory

    def match(
        self,
        task_description: str,
        top_k: int = 3,
        min_confidence: float = 0.3,
    ) -> List[Dict]:
        """
        基于任务描述匹配 Skill。

        Args:
            task_description: 任务描述（如用户输入）
            top_k: 返回前 N 个最匹配的结果
            min_confidence: 最低置信度阈值（0-1）

        Returns:
            匹配结果列表，每项含 name/category/trigger/confidence/skill_path
        """
        task_lower = task_description.lower()
        scored = []

        for skill in self.inventory:
            score = self._calc_score(task_lower, skill)
            if score >= min_confidence:
                scored.append({
                    "name": skill.get("name", ""),
                    "category": skill.get("category", ""),
                    "trigger_words": skill.get("trigger_words", []),
                    "description": skill.get("description", ""),
                    "skill_path": skill.get("skill_path", ""),
                    "source": skill.get("source", ""),
                    "reliability": skill.get("reliability", 0.5),
                    "confidence": round(score, 3),
                })

        scored.sort(key=lambda x: -x["confidence"])
        return scored[:top_k]

    def _calc_score(self, task: str, skill: Dict) -> float:
        """计算任务与 Skill 的匹配分数（0-1）"""
        score = 0.0
        triggers = [t.lower() for t in skill.get("trigger_words", [])]
        desc = skill.get("description", "").lower()
        category = skill.get("category", "").lower()

        if not triggers:
            return 0.0

        # 1. trigger_words 命中（权重 0.6）
        trigger_hits = sum(1 for t in triggers if t in task)
        trigger_score = min(trigger_hits / len(triggers), 1.0) * 0.6
        score += trigger_score

        # 2. description 关键词命中（权重 0.2）
        desc_hits = sum(1 for kw in [task] if kw in desc)
        desc_score = min(desc_hits / 2, 1.0) * 0.2
        score += desc_score

        # 3. category 匹配（权重 0.1）
        if category and any(c in task for c in category.split("/")):
            score += 0.1

        # 4. reliability 加权（权重 0.1）
        reliability = skill.get("reliability", 0.5)
        score = score * (0.5 + 0.5 * reliability)

        return min(score, 1.0)

    def get_by_category(self, category: str, top_k: int = 5) -> List[Dict]:
        """按分类获取 Skill"""
        results = [
            s for s in self.inventory
            if category.lower() in s.get("category", "").lower()
        ][:top_k]
        return [{
            "name": s.get("name", ""),
            "category": s.get("category", ""),
            "trigger_words": s.get("trigger_words", []),
            "skill_path": s.get("skill_path", ""),
            "reliability": s.get("reliability", 0.5),
        } for s in results]

    def get_by_name(self, name: str) -> Optional[Dict]:
        """按名称精确查找 Skill"""
        for s in self.inventory:
            if s.get("name", "") == name:
                return s
        return None

    def list_categories(self) -> Dict[str, int]:
        """列出所有分类及 Skill 数量"""
        cats = {}
        for s in self.inventory:
            cat = s.get("category", "未分类")
            cats[cat] = cats.get(cat, 0) + 1
        return dict(sorted(cats.items(), key=lambda x: -x[1]))

    def stats(self) -> Dict:
        """返回 Inventory 统计信息"""
        return {
            "total_skills": len(self.inventory),
            "categories": self.list_categories(),
            "inventory_path": self.inventory_path,
        }


def match(task_description: str, top_k: int = 3) -> List[Dict]:
    """快速匹配接口"""
    return SkillRouter().match(task_description, top_k=top_k)


def stats() -> Dict:
    """快速统计接口"""
    return SkillRouter().stats()


if __name__ == "__main__":
    # 简单测试
    router = SkillRouter()
    print("=== Skill Router 自检 ===")
    s = router.stats()
    print(f"总技能数: {s['total_skills']}")
    print(f"分类: {list(s['categories'].keys())}")
    print()

    test_tasks = [
        "帮我分析飞书聊天记录",
        "写一个Python爬虫",
        "制定明天的任务计划",
        "处理Word文档",
    ]

    for task in test_tasks:
        print(f"任务: {task}")
        results = router.match(task, top_k=3)
        for r in results:
            print(f"  → {r['name']} ({r['category']}) 置信度:{r['confidence']} 触发:{r['trigger_words'][:2]}")
        print()
