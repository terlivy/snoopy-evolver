# SC 当前完整架构图
## SnoopyClaw OpenClaw Architecture — 单一事实来源 (SSOT)

> **版本**: 1.0
> **更新日期**: 2026-04-22
> **维护**: SC 主脑
> **用途**: 回答架构问题时的唯一参考，避免每次回答不一致

---

## 一、整体架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                    OpenClaw Gateway (2026.4.15)                    │
│                     端口: 18789 | 运行中 (PID 8768)                  │
└─────────────────────────────────────────────────────────────────────┘
         │                    │                    │
         ▼                    ▼                    ▼
┌─────────────┐    ┌─────────────────┐    ┌─────────────────────┐
│  Plugins    │    │  Agents (10个)   │    │  Skills (28个)     │
│  4个插件    │    │  主脑 + 专用Agent│    │  workspace技能     │
└─────────────┘    └─────────────────┘    └─────────────────────┘
```

---

## 二、已安装插件（4个）

| 插件 | 路径 | Slot | 功能 |
|------|------|------|------|
| `lossless-claw-enhanced` | `~/.openclaw/extensions/lossless-claw-enhanced` | **contextEngine** | DAG上下文压缩，SQLite持久化 |
| `memory-lancedb-pro` | `~/.openclaw/extensions/memory-lancedb-pro` | **memory** | 向量检索+BM25混合+CrossEncoder重排 |
| `openclaw-lark` | `~/.openclaw/extensions/openclaw-lark` | — | 飞书全栈集成 |
| `sas-engine` | `~/.openclaw/extensions/sas-engine` | — | SAS准则工具（sas_check_gate等）|

### 2.1 lossless-claw-enhanced
- **用途**: 上下文满了自动摘要，不丢信息
- **配置**: `slots.contextEngine: "lossless-claw"`
- **数据库**: `~/.openclaw/lcm.db` (26MB)
- **命令**: `openclaw sessions list/status` — 已废弃，部分子命令超时
- **文档**: win4r/lossless-claw-enhanced (MIT)

### 2.2 memory-lancedb-pro
- **用途**: 长期记忆向量存储+混合检索
- **Embedding**: Ollama bge-m3 (本地1024维)
- **数据路径**: `~/.openclaw/memory/lancedb-pro/`
- **功能**: smartExtraction / Weibull遗忘 / 多作用域隔离
- **文档**: CortexReach/memory-lancedb-pro (MIT)

### 2.3 openclaw-lark
- **用途**: 飞书消息/日历/表格/文档/多维表格
- **配置**: 已在 bindings 中配置5个Agent对应飞书群

### 2.4 sas-engine
- **用途**: SAS准则执行工具
- **工具**: sas_check_gate / sas_log_transition / sas_watchdog_check / sas_get_task_state

---

## 三、Agent 系统（10个）

| Agent ID | 名称 | 模型 | 飞书群 | Skills | 职责 |
|----------|------|------|--------|--------|------|
| **main** | SC主脑 | MiniMax-M2.7-highspeed | — | — | 统筹协调，CEO模式 |
| **hr** | HR专家 | GLM-5-Turbo | ✅ | — | 招聘/入职/团队管理 |
| **doc-expert** | 文档专家 | GLM-4.7 | ✅ | — | 文档处理/生成 |
| **weather** | 天气 | GLM-4.5-Air | ✅ | — | 天气查询 |
| **tech-news** | 科技新闻 | GLM-4.5-Air | ✅ | — | 新闻收集 |
| **sas-sop-expert** | SAS优化 | MiniMax-M2.7 | ✅ | — | SAS准则每日优化 |
| **sas-default** | SAS执行 | MiniMax-M2.7-highspeed | — | memory工具 | SAS准则执行 |
| **sas-leader** | SAS派发 | MiniMax-M2.7 | — | **harness-leader** | 任务分解+派发 |
| **xiaowen** | AI博士助理 | (继承主脑) | — | — | 博士后工作站辅助 |
| **deepseek** | 编程专家 | DeepSeek Chat | — | — | 编程任务 |

### 3.1 模型配置（4个Provider，18个模型）

| Provider | 模型数 | 主要用途 |
|---------|--------|---------|
| **minimax** | 6 | 主脑/M2.7高速推理 |
| **zai** | 6 | 备用/深度定制OpenClaw |
| **deepseek** | 2 | 编程/代码任务 |
| **siliconflow** | 4 | 免费备用（DeepSeek-V3等）|

---

## 四、Workspace Skills（28个）

### 核心运维类
| Skill | 功能 |
|-------|------|
| `system-healer` | 自愈机制（Ollama/Gateway/端口检查+修复） |
| `workspace-manager` | 工作区审计、优化、维护 |
| `harness-leader` | 多Agent协作编排（sas-leader使用）|
| `sas-default` | SAS准则执行 |
| `sas-task-planner` | 任务全生命周期管理 |
| `task-planner` | 通用任务规划 |
| `self-improving-agent` | 持续改进 |
| `clawteam` | 多Agent协作（Python CLI）|

### 博士工作站类（8个）
| Skill | 功能 |
|-------|------|
| `postdoc-admin` | 行政事务 |
| `postdoc-cnas` | CNAS认证管理 |
| `postdoc-anticheat` | 反蒸馏/安全审计 |
| `postdoc-policy` | 政策情报追踪 |
| `postdoc-recruit` | 人才引进管理 |
| `postdoc-ip` | 知识产权管理 |
| `postdoc-project` | 科研项目管理 |
| `postdoc-director` | 所长事务 |

### 文档处理类（5个）
| Skill | 功能 |
|-------|------|
| `word-docx` | Word文档 |
| `excel-xlsx` | Excel处理 |
| `powerpoint-pptx` | PPT处理 |
| `doc-handler` | Word/PDF/Excel综合 |
| `official-document-template` | 公文排版（GB/T 9704-2012）|

### 设计与爬虫类（4个）
| Skill | 功能 |
|-------|------|
| `frontend-design-3` | 前端界面生成 |
| `diagram-generator` | 图表生成 |
| `playwright-scraper-skill` | 网页爬取 |
| `graphify` | 知识图谱生成 |

### 工具类（6个）
| Skill | 功能 |
|-------|------|
| `memory-lancedb-pro-skill` | 向量记忆管理 |
| `nano-pdf` | PDF编辑 |
| `video-frames` | 视频帧提取 |
| `websearch` | 网页搜索 |
| `snoopyclaw-skills` | SC专属技能 |
| `graphify-out` | 知识图谱输出 |

### OpenClaw 内置 Skills（50+个）
`github` / `gh-issues` / `healthcheck` / `node-connect` / `weather` / `cron` / `feishu-*` / `clawhub` 等

---

## 五、自动化系统

| 系统 | 实现方式 | 触发时间 |
|------|---------|---------|
| **心跳巡检** | HEARTBEAT.md | 每30分钟 |
| **GitHub同步** | `python3 scripts/sas_github_sync.py` | 每日02:00 |
| **会话记忆同步** | `python3 scripts/sync_session_memory.py` | 每日02:00 |
| **SAS-SOP优化** | cron触发sas-sop-expert | 每日 |
| **资讯推送** | cron触发tech-news | 每日 |
| **天气推送** | cron触发weather | 每日 |

---

## 六、网络与监控

| 服务 | 技术栈 | 端口 |
|------|--------|------|
| AI Monitor后端 | FastAPI + SQLite | 8000 |
| AI Monitor前端 | Vue 3 + Tailwind | 3000 |
| Gateway | OpenClaw | 18789 |
| Ollama | bge-m3 embedding | 11434 |
| ClawTeam | tmux/subprocess | — |

---

## 七、外部集成

| 集成 | 状态 | 说明 |
|------|------|------|
| **飞书** | ✅ 已配置 | 5个Agent绑定不同群 |
| **Telegram** | ✅ 集成 | Bot配置 |
| **GitHub** | ✅ CLI已集成 | `gh`命令可用 |
| **YouTube** | ✅ yt-dlp | cookies工具链 |
| **ClawTeam** | ✅ 已安装 | Python CLI |

---

## 八、snoopy-evolver 模块（新集成）

路径：`~/.openclaw/workspace/snoopy-evolver/` | GitHub: `terlivy/SAS.git`

| 模块 | 文件 | 功能 |
|------|------|------|
| **P0 Ops** | `ops/health_check.py` | 6项健康检查矩阵 |
| **P1 基因库** | `evolver/genes/genes.json` | 19条基因，12类别 |
| **P1 选择器** | `evolver/selector.py` | 信号→基因匹配 |
| **P2 审计** | `evolver/events/logger.py` | EvolutionEvent日志 |
| **P3 共享** | `evolver/clawteam_integration.py` | 跨Agent经验共享 |

---

## 九、关键配置文件

| 文件 | 用途 |
|------|------|
| `~/.openclaw/openclaw.json` | Gateway主配置（agents/plugins/models/channels）|
| `~/.openclaw/workspace/SOUL.md` | SC核心身份+CEO模式 |
| `~/.openclaw/workspace/MEMORY.md` | 记忆索引+红线规则 |
| `~/.openclaw/workspace/HEARTBEAT.md` | 心跳巡检规则 |
| `~/.openclaw/workspace/AGENTS.md` | 工作区规范 |
| `~/.openclaw/workspace/USER.md` | 用户信息 |

---

## 十、安全配置（重要！）

```json
// ~/.openclaw/openclaw.json 关键配置

// 派发子Agent权限
"agents": {
  "defaults": {
    "subagents": {
      "allowAgents": ["*"]  // ✅ 已修复，允许派发给任意Agent
    }
  }
}

// 跨Agent消息权限
"tools": {
  "sessions": {
    "visibility": "all"  // ✅ 已修复，允许跨Agent通信
  }
}

// Agent间通信
"tools": {
  "agentToAgent": {
    "enabled": true,
    "allow": ["main", "sas-leader"]
  }
}
```

---

## 十一、架构一致性说明

### 为什么之前回答不一致？
因为没有单一事实来源（SSOT）。从现在起：
- **架构问题** → 以本文档为准
- **配置问题** → 以 `~/.openclaw/openclaw.json` 为准
- **代码问题** → 以实际文件为准

### 如何更新本文档？
每次架构变更（新增插件/Agent/Skill/配置修改），立即更新本文档。

---

*本文档由 SC 主脑生成，最后更新：2026-04-22*
