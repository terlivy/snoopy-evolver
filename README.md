# 🦞 snoopy-evolver

> Evolver 启发而来的自进化引擎 Python/Skill 实现版 | MIT 许可证

**snoopy-evolver** 是受 [Evolver (GPL-3.0)](https://github.com/EvoMap/evolver) 架构启发，用 Python 实现的轻量级自进化引擎，专为 [OpenClaw](https://openclaw.ai) Agent 系统设计。

---

## 🎯 是什么

snoopy-evolver 让 SC（SnoopyClaw 主脑）具备**自进化能力**：

- 🔧 **Ops 模块** — 健康检查矩阵（6项自动巡检）
- 🧬 **基因库** — 从历史教训自动提取可复用解决方案
- 📊 **演进审计** — EvolutionEvent 全生命周期追踪
- 🤝 **跨 Agent 共享** — ClawTeam 多智能体经验共享

---

## ⚖️ 许可证说明

| 项目 | 许可证 | 原因 |
|------|--------|------|
| **snoopy-evolver** | **MIT** | 纯 Python 实现，无 Evolver 源码复制 |
| **Evolver** | GPL-3.0 | 原始项目 |

snoopy-evolver 从 Evolver 架构中**汲取灵感**，但**完全独立实现**：
- ✅ 不包含 Evolver 的任何源码
- ✅ 使用自己的 Python + Skill 实现
- ✅ 不受 GPL 传染，可闭源商业使用

---

## 🏗️ 架构

```
snoopy-evolver/
├── SKILL.md                    # OpenClaw Skill 入口
├── ops/
│   └── health_check.py         # P0: 6项健康检查矩阵
├── evolver/
│   ├── genes/
│   │   └── genes.json          # P1: 基因库（19条基因，12类别）
│   ├── selector.py              # P1: 信号→基因选择器
│   ├── events/
│   │   ├── logger.py            # P2: EvolutionEvent 审计日志
│   │   └── events.jsonl        # P2: 审计记录
│   └── clawteam_integration.py # P3: ClawTeam 跨Agent共享
    ├── models.py                # 数据模型
    ├── tracker.py               # 追踪器
    ├── analytics.py             # 性能分析
    └── cli.py                   # CLI工具
```

---

## 🚀 快速开始

### 前置要求
- Python 3.10+
- OpenClaw（已安装）

### 安装

```bash
# 克隆到本地
git clone https://github.com/terlivy/snoopy-evolver.git
cd snoopy-evolver

# 或直接使用代码
cp -r ops/ evolver/ ~/.openclaw/workspace/
```

### 健康检查

```bash
# 标准输出
python3 ops/health_check.py

# JSON 格式（程序化调用）
python3 ops/health_check.py --json

# 退出码：0=正常，1=警告，2=错误
```

**输出示例：**
```
【Ops 健康报告 - 2026-04-22 00:22:00】

✅ Ollama:      运行中 (PID 375)
✅ Gateway:     运行中 (PID 8768)
✅ 磁盘使用率:  3%（正常）
✅ 上下文使用:  Gateway 正常
✅ 子Agent存活: ClawTeam 正常
✅ Memory DB:   LanceDB 数据文件正常

🟢 状态：全部正常
```

---

## 🧬 P1: 基因库

### 什么是基因（Gene）？

基因是**可复用的经验单元**——SC 遇到问题时，先查基因库而不是重新想办法。

```json
{
  "gene_id": "gene_ollama_restart",
  "name": "Ollama 重启流程",
  "signals": ["ollama", "crash", "11434", "model_load_failed"],
  "solution": "1. pgrep -x ollama\n2. kill PID\n3. ollama serve",
  "validation": "pgrep -x ollama",
  "success_rate": 0.95,
  "usage_count": 12,
  "category": "system_operation"
}
```

### 当前基因库

| 类别 | 基因数 | 示例 |
|------|--------|------|
| system_operation | 4 | Gateway重启、npm install、端口冲突 |
| agent_management | 3 | 子智能体Spawn、角色隔离 |
| workflow | 2 | 计划先行、试运行也出计划 |
| memory_management | 1 | Memory即时写入 |
| integration | 1 | 飞书群双向配置 |
| ... | ... | ... |

**总统计**：19条基因 | 12个类别 | 358次使用 | 94%成功率

---

## 📊 P2: EvolutionEvent 审计

每次关键事件自动记录，形成能力演进追踪：

| 事件类型 | 用途 |
|---------|------|
| `task_started/completed/failed` | 任务生命周期 |
| `phase_started/completed` | SAS阶段演进 |
| `gene_discovered/applied/success/failed` | 基因操作 |
| `strategy_switched` | 策略模式切换 |
| `health_check/system_repair` | 系统运维 |
| `agent_spawned/completed` | Agent状态 |
| `lesson_learned` | 教训记录 |

```json
{"ts":"2026-04-22T00:00:00Z","type":"gene_applied","gene_id":"gene_ollama_restart","outcome":"success","recovery_time":30}
```

---

## 🤝 P3: ClawTeam 跨Agent共享

当 ClawTeam 中的 Agent 发现新解决方案时：

1. **自动检测** — 分析 Agent 输出中的修复行为
2. **信号提取** — 提取技术关键词（gateway/port/restart）
3. **去重检查** — 已有相似基因（≥0.8相似度）则更新统计
4. **新基因入库** — 创建新基因并广播给团队
5. **跨Agent查询** — 其他Agent可直接复用

---

## 🔧 模块详解

### Ops 健康检查矩阵

| # | 检查项 | 检查方式 | 阈值 |
|---|--------|---------|------|
| 1 | Ollama | `pgrep -x ollama` | 进程存在 |
| 2 | Gateway | `pgrep -f openclaw.*gateway` | 进程存在 |
| 3 | 磁盘使用率 | `df -h /` | <80% |
| 4 | 上下文使用 | Gateway HTTP API | 健康 |
| 5 | 子Agent存活 | `clawteam team discover` | 有存活 |
| 6 | Memory DB | 文件存在 | 文件存在 |

### 基因选择器

```python
from evolver import selector

# 根据信号匹配最合适的基因
gene = selector.select_gene(["ollama", "crash", "11434"])
if gene:
    print(f"匹配基因: {gene.name}")
    print(f"解决方案: {gene.solution}")
```

### 事件日志器

```python
from evolver.events import logger

# 记录基因应用事件
logger.log("gene_applied", {
    "gene_id": "gene_ollama_restart",
    "trigger_signal": "ollama_down",
    "outcome": "success"
})

# 查询历史
events = logger.query(type="gene_applied", limit=10)
```

---

## 📁 与 SC 现有系统的关系

| 已有系统 | snoopy-evolver 集成方式 |
|---------|----------------------|
| `memory-lancedb-pro` | 基因库可存储在 LanceDB |
| `lossless-claw` | context 使用量检查 |
| `clawteam` | 跨Agent经验共享 |
| `system-healer` | 基因驱动自愈（替代硬编码） |
| SAS v1.7 | EvolutionEvent 增强任务归档 |

---


---

## 🗺️ 路线图

- [ ] P4: 基因驱动的 SAS 自动优化（根据历史任务自动调整策略）
- [ ] P5: Gene Capsule 完整解决方案打包
- [ ] Web UI: 健康检查看板
- [ ] API: 基因库 CRUD 管理界面

---

## 📄 许可证

MIT License - 可闭源商业使用，无需开源

**注意**：本项目从 [Evolver (GPL-3.0)](https://github.com/EvoMap/evolver) 架构汲取灵感，但**完全独立实现**，不包含任何 GPL 源码，不受 GPL 传染。

---

## 🙏 致谢

- [Evolver](https://github.com/EvoMap/evolver) — GEP 协议启发
- [OpenClaw](https://openclaw.ai) — Agent 框架基础
- [ClawTeam](https://github.com/HKUDS/ClawTeam) — 多Agent协作参考

---

*由 SnoopyClaw (SC) 主脑维护 | https://github.com/terlivy/snoopy-evolver*
