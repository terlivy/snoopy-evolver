"""
snoopy-evolver/agent_tracker/analytics.py
Agent 性能分析器 - 从收集的数据中提取洞察
"""

from pathlib import Path
from typing import Optional
from collections import defaultdict
from .tracker import AgentTracker
from .models import TASK_TYPES, COMPLEXITY_LEVELS

class AgentAnalytics:
    """Agent 性能分析器"""

    def __init__(self, tracker: Optional[AgentTracker] = None):
        self.tracker = tracker or AgentTracker()

    def get_model_task_matrix(self) -> dict:
        """构建模型-任务类型矩阵"""
        records = self.tracker._load_records()
        matrix = defaultdict(lambda: {"total": 0, "success": 0, "total_cost": 0, "avg_duration": 0, "scores": []})

        for rec in records:
            if rec.get("completion_status") == "pending":
                continue

            model = rec.get("model_used", "unknown")
            task_type = rec.get("task_type", "other")
            success = rec.get("success", False)
            cost = rec.get("total_cost", 0) or 0
            duration = rec.get("duration_seconds", 0) or 0
            score = rec.get("quality_score")

            key = f"{model} × {task_type}"
            matrix[key]["total"] += 1
            matrix[key]["success"] += 1 if success else 0
            matrix[key]["total_cost"] += cost
            matrix[key]["avg_duration"] += duration
            if score is not None:
                matrix[key]["scores"].append(score)

        # 计算平均值
        result = {}
        for key, stats in matrix.items():
            total = stats["total"]
            avg_dur = stats["avg_duration"] / total if total > 0 else 0
            scores = stats["scores"]
            avg_score = sum(scores) / len(scores) if scores else None

            result[key] = {
                "total": total,
                "success_rate": stats["success"] / total if total > 0 else 0,
                "total_cost": round(stats["total_cost"], 4),
                "avg_duration_seconds": round(avg_dur, 1),
                "avg_quality_score": round(avg_score, 1) if avg_score else None,
                "model": key.split(" × ")[0],
                "task_type": key.split(" × ")[1]
            }

        return result

    def get_model_ranking(self) -> list:
        """模型综合排名"""
        records = self.tracker._load_records()
        by_model = defaultdict(lambda: {"total": 0, "success": 0, "total_cost": 0, "tokens_total": 0, "scores": [], "task_types": set()})

        for rec in records:
            if rec.get("completion_status") == "pending":
                continue

            model = rec.get("model_used", "unknown")
            success = rec.get("success", False)
            cost = rec.get("total_cost", 0) or 0
            tokens_in = rec.get("tokens_in", 0) or 0
            tokens_out = rec.get("tokens_out", 0) or 0
            score = rec.get("quality_score")
            task_type = rec.get("task_type", "other")

            by_model[model]["total"] += 1
            by_model[model]["success"] += 1 if success else 0
            by_model[model]["total_cost"] += cost
            by_model[model]["tokens_total"] += tokens_in + tokens_out
            by_model[model]["task_types"].add(task_type)
            if score is not None:
                by_model[model]["scores"].append(score)

        ranking = []
        for model, stats in by_model.items():
            total = stats["total"]
            scores = stats["scores"]
            avg_score = sum(scores) / len(scores) if scores else None

            ranking.append({
                "model": model,
                "total_tasks": total,
                "success_rate": round(stats["success"] / total * 100, 1) if total > 0 else 0,
                "avg_cost": round(stats["total_cost"] / total, 4) if total > 0 else 0,
                "avg_quality_score": round(avg_score, 1) if avg_score else None,
                "total_tokens": stats["tokens_total"],
                "task_type_count": len(stats["task_types"]),
                "task_types": list(stats["task_types"])
            })

        # 按成功率 + 质量评分综合排名
        ranking.sort(key=lambda x: (x["success_rate"], x["avg_quality_score"] or 0), reverse=True)
        return ranking

    def get_task_type_analysis(self) -> list:
        """各任务类型的最佳模型推荐"""
        records = self.tracker._load_records()
        by_type = defaultdict(lambda: {"records": [], "models": defaultdict(lambda: {"total": 0, "success": 0, "scores": []})})

        for rec in records:
            if rec.get("completion_status") == "pending":
                continue

            task_type = rec.get("task_type", "other")
            model = rec.get("model_used", "unknown")
            success = rec.get("success", False)
            score = rec.get("quality_score")

            by_type[task_type]["records"].append(rec)
            by_type[task_type]["models"][model]["total"] += 1
            by_type[task_type]["models"][model]["success"] += 1 if success else 0
            if score is not None:
                by_type[task_type]["models"][model]["scores"].append(score)

        result = []
        for task_type, data in by_type.items():
            best_model = None
            best_score = 0
            best_rate = 0

            for model, stats in data["models"].items():
                total = stats["total"]
                rate = stats["success"] / total if total > 0 else 0
                avg_score = sum(stats["scores"]) / len(stats["scores"]) if stats["scores"] else 0
                if rate > best_rate or (rate == best_rate and avg_score > best_score):
                    best_model = model
                    best_score = avg_score
                    best_rate = rate

            result.append({
                "task_type": task_type,
                "task_type_name": TASK_TYPES.get(task_type, task_type),
                "total_tasks": len(data["records"]),
                "best_model": best_model,
                "best_success_rate": round(best_rate * 100, 1),
                "best_avg_score": round(best_score, 1) if best_score > 0 else None,
                "model_count": len(data["models"]),
                "models": {
                    m: {
                        "total": s["total"],
                        "success_rate": round(s["success"] / s["total"] * 100, 1) if s["total"] > 0 else 0,
                        "avg_score": round(sum(s["scores"]) / len(s["scores"]), 1) if s["scores"] else None
                    }
                    for m, s in data["models"].items()
                }
            })

        result.sort(key=lambda x: x["total_tasks"], reverse=True)
        return result

    def generate_recommendations(self) -> str:
        """生成优化建议报告"""
        ranking = self.get_model_ranking()
        task_analysis = self.get_task_type_analysis()

        lines = []
        lines.append("【Agent 性能分析报告】")
        lines.append("")

        # 1. 最佳模型推荐
        lines.append("## 🏆 模型综合排名")
        lines.append("")
        for i, item in enumerate(ranking[:5], 1):
            lines.append(f"{i}. **{item['model']}**")
            lines.append(f"   - 任务数: {item['total_tasks']} | 成功率: {item['success_rate']}% | 质量: {item['avg_quality_score'] or 'N/A'}")
            lines.append(f"   - 平均成本: ${item['avg_cost']} | 总Token: {item['total_tokens']:,}")

        lines.append("")

        # 2. 任务类型最佳匹配
        lines.append("## 🎯 任务-模型最佳匹配")
        lines.append("")
        for item in task_analysis[:5]:
            if item["best_model"]:
                lines.append(f"**{item['task_type_name']}** → {item['best_model']}")
                lines.append(f"   成功率: {item['best_success_rate']}% | 质量: {item['best_avg_score'] or 'N/A'}")

        lines.append("")

        # 3. 待改进建议
        lines.append("## 📋 优化建议")
        low_performers = [r for r in ranking if r["success_rate"] < 70]
        if low_performers:
            lines.append("以下模型在某些任务上成功率较低，建议优化提示词或更换模型：")
            for item in low_performers:
                lines.append(f"- {item['model']}: {item['success_rate']}%")

        return "\n".join(lines)

    def summary(self) -> dict:
        """返回汇总统计"""
        records = self.tracker._load_records()
        completed = [r for r in records if r.get("completion_status") != "pending"]
        successful = [r for r in completed if r.get("success")]

        total_tokens = sum((r.get("tokens_in", 0) or 0) + (r.get("tokens_out", 0) or 0) for r in completed)
        total_cost = sum(r.get("total_cost", 0) or 0 for r in completed)

        return {
            "total_spawns": len(records),
            "total_completed": len(completed),
            "total_successful": len(successful),
            "overall_success_rate": round(len(successful) / len(completed) * 100, 1) if completed else 0,
            "total_tokens": total_tokens,
            "total_cost_usd": round(total_cost, 4),
            "unique_models": len(set(r.get("model_used") for r in completed)),
            "unique_task_types": len(set(r.get("task_type") for r in completed))
        }
