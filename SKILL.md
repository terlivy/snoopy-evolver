# Snoopy Evolver - 自愈与演进引擎

## 简介

Snoopy Evolver 是一个基因驱动的自愈和演进审计系统，灵感来自 Evolver (GPL-3.0)。

核心功能：
1. **基因库 (Gene Library)** - 结构化存储从教训和经验中提取的解决方案
2. **基因选择器 (Gene Selector)** - 根据信号匹配最佳基因解决方案
3. **演进事件日志 (EvolutionEvent Logger)** - 审计所有任务和基因相关事件
4. **ClawTeam 集成** - 跨 Agent 经验共享

---

## 目录结构

```
snoopy-evolver/
├── SKILL.md              # 本文件
├── evolver/
│   ├── __init__.py
│   ├── genes/
│   │   └── genes.json   # 基因库（从 lessons.md 提取）
│   ├── events/
│   │   ├── events.jsonl  # EvolutionEvent 审计日志
│   │   └── logger.py     # 事件日志记录器
│   ├── selector.py       # 信号 → 基因选择器
│   ├── clawteam_integration.py  # ClawTeam 跨 Agent 经验共享
│   └── capsules/         # 完整解决方案（未来扩展）
└── ops/                  # Ops 健康检查（P0 已完成）
```

---

## 使用方法

### 1. 基因选择器

```python
from snoopy_evolver.evolver import get_best_gene, select_genes

# 根据信号获取最佳基因
gene = get_best_gene(["spawn", "subagent", "template"])
if gene:
    print(f"解决方案: {gene.solution}")
    print(f"成功率: {gene.success_rate}")

# 获取多个匹配
matches = select_genes(["gateway", "restart", "断线"], top_k=3)
for m in matches:
    print(f"[{m.match_type}] {m.name} (score={m.match_score:.2f})")
```

### 2. 事件日志

```python
from snoopy_evolver.evolver import log_task_started, log_task_completed, log_gene_applied

# 记录任务开始
log_task_started("TASK-001", mode="balanced")

# 记录基因应用
log_gene_applied("gene_spawn_template", "子智能体 Spawn 模板", task_id="TASK-001")

# 记录任务完成
log_task_completed("TASK-001", outcome="success", duration_ms=5000)
```

### 3. ClawTeam 集成

```python
from snoopy_evolver.evolver.clawteam_integration import on_agent_output, query_shared_genes

# Agent 任务完成后调用
result = on_agent_output(
    agent_id="Agent-Backend",
    task_id="TASK-001",
    output="修复了 Gateway 端口冲突问题...",
    success=True
)

# 查询共享基因
genes = query_shared_genes(["gateway", "restart", "port"])
```

---

## 基因库结构

每个基因包含：
- `gene_id` - 唯一标识
- `name` - 基因名称
- `category` - 类别（agent_management, messaging, memory_management 等）
- `signals` - 信号列表（用于匹配）
- `problem` - 问题描述
- `solution` - 解决方案
- `validation` - 验证方法
- `success_rate` - 历史成功率
- `usage_count` - 使用次数
- `last_used` - 最后使用时间

---

## EvolutionEvent 类型

| 类型 | 描述 |
|------|------|
| `task_started` | 任务开始 |
| `task_completed` | 任务完成 |
| `task_failed` | 任务失败 |
| `phase_started` | 阶段开始 |
| `phase_completed` | 阶段完成 |
| `gene_discovered` | 发现新基因 |
| `gene_applied` | 应用基因 |
| `gene_success` | 基因应用成功 |
| `gene_failed` | 基因应用失败 |
| `strategy_switched` | 策略切换 |
| `health_check` | 健康检查 |
| `agent_spawned` | Agent 启动 |
| `agent_completed` | Agent 完成 |

---

## ClawTeam 经验共享机制

1. **自动检测**：当 Agent 输出包含修复方案时自动分析
2. **基因提取**：从输出中提取信号和解决方案
3. **去重检查**：如果已有相似基因（匹配度≥0.8），更新使用统计
4. **新基因入库**：否则创建新基因并广播通知
5. **跨 Agent 复用**：其他 Agent 可通过信号查询获得解决方案

---

## 当前基因库统计

- **总基因数**: 19 条
- **类别**: agent_management, messaging, memory_management, workflow, system_operation, task_management, integration, cron, git, workspace, file_handling, llm_guidance

---

> 本模块为 SnoopyClaw 自建实现，灵感来自 Evolver (GPL-3.0)，无 GPL 开源义务。