# system-AI-Toolbox 系统介绍（交接文档）

> 一套「AI Agent 平台 + 智能工作流编排 + 无人值守定时智能体 + 24+ 工具 + 自训练模型」的一体化生产力工具箱。
> 本文档面向后续维护者，覆盖系统全貌、核心子系统、算法与模型、目录结构与扩展方式。

---

## 1. 系统概览

系统的核心不是单个工具，而是一套「**自然语言 → 自动编排工具流水线**」的 Agent 机制：

1. 用户对 AI 助手说一句话（如「记录会议、生成纪要约张三」）
2. 系统用本地模型/规则快速判断意图（0 次 LLM 调用优先）
3. 命中则直接执行；否则由「大脑 LLM」编排成工作流（DAG）
4. 工作流引擎按依赖拓扑执行多个工具
5. 执行后反思（规则校验 + LLM 修复）→ 输出 → 记忆

同时支持**定时智能体（cron）**：把已保存的工作流挂到调度器上，无人值守自动执行（如「每周一 9 点调研竞品动态并发邮件」）。

### 技术栈

| 层 | 技术 |
|---|---|
| 前端 | React 19 + TypeScript + Ant Design 6 + Vite |
| 后端 | FastAPI + SQLAlchemy + SQLite + APScheduler |
| 深度学习 | PyTorch + HuggingFace Transformers（DistilBERT，Apple MPS 加速） |
| 经典 ML | scikit-learn（KNN / RF / 决策树 / GBDT / SVM / KMeans / 回归） |
| 向量检索 | FAISS + sentence-transformers（BGE-large-zh） |
| LLM | DeepSeek（OpenAI 兼容接口，可换成任意兼容后端） |

---

## 2. 系统架构

```
┌──────────────────────────────────────────────────────────┐
│ 前端 React（40+ 工具页面 · 深色科技风 · 气泡网格主页）       │
├──────────────────────────────────────────────────────────┤
│ 33 个 Router（工具 API + Agent API + Robot API）           │
├──────────────────────────────────────────────────────────┤
│ AgentLoop 编排层（感知→规划→执行→反思→输出→记忆）           │
│   ├ 意图路由 intent_router（0 LLM 快路径）                 │
│   ├ 技能注册表 skill_registry（文件夹式技能包）             │
│   ├ 计划缓存 plan_cache（FAISS 向量复用历史方案）           │
│   ├ 记忆 memory_service（会话/实体/计划三层）               │
│   └ 反思 reflector（规则校验 + LLM 修复）                  │
├──────────────────────────────────────────────────────────┤
│ 工作流引擎 workflow_engine（DAG 拓扑执行 + 节点执行器）      │
│ 工具注册表 tools_registry（43 个工具的 schema 声明）        │
├──────────────────────────────────────────────────────────┤
│ 服务层 services（LLM 网关 · 本地模型 · 嵌入 · 音频）        │
└──────────────────────────────────────────────────────────┘
```

**后端工具层是「三层共存」结构**：

| 层 | 文件 | 职责 |
|---|---|---|
| 独立 REST 层 | 27 个 router（`/api/<tool>`） | 每个工具一个可被前端直调的 APIRouter |
| 注册表+执行器层 | `tools_registry.py` + `workflow_engine.EXECUTORS` | 把工具抽象成可被 AI 编排的「节点」 |
| 编排入口层 | `agent.py` / `workflow.py` / `skills.py` / `robot.py` / `ai.py` | 自然语言 → 选工具/串工具 → 执行 |

---

## 3. Tool 工具系统（核心之一）

### 3.1 统一抽象

每个工具用一段**纯数据**声明（`tools_registry.py` 的 `TOOLS` 列表）：

```
{ id, name, description, icon, color,
  inputs, outputs, output_labels,
  category (input/process/output), config_schema }
```

同时有一个**执行器映射** `EXECUTORS: dict[str, Callable]`，`tool_id → 执行函数(inputs)->dict`。

**注册一个新工具的约定 = 在 `TOOLS` 加一条描述 + 在 `EXECUTORS` 加一个同名函数**（`tool_id` 对齐）。工作流规划器、Skill 建边、Agent 大脑提示词三处都消费 `TOOLS` 这份元数据。

### 3.2 工具清单（共 43 个，分三类）

- **📥 输入采集**：会议记录（双设备录音→转写）、图片分析、PDF 工具（提取/合并/拆分）、网页抓取、文件转换、RAG 知识库上传
- **⚙️ AI 处理**：文档摘要、思维导图、待办提取、翻译/润色、文档对比、任务规划、信息提取、数据分析（LLM 生成 pandas 代码）、智能表格、知识库问答、情感分析、深度调研
- **📤 生成输出**：邮件/公文、PPT（大纲/PPTX/HTML）、周报、图表生成、二维码、待办 CRUD
- **🧮 零 LLM 代码工具**（`services/toolkit/code_tools.py`）：计算器（AST 白名单安全 eval）、日期计算、单位换算、字数统计、JSON 格式化
- **🌐 外部数据工具**（`services/toolkit/external_api.py`）：天气（open-meteo 免 key）、汇率（open.er-api 免 key）、股价（需 key）
- **🤖 ML 工具**：7 个 sklearn 模型 + 1 个 FCN 模型（见第 6 节）

---

## 4. Workflow 工作流引擎（核心之二）

文件：`routers/workflow_engine.py`（无 router，纯执行引擎）。

### 4.1 数据结构

一个工作流 plan = `{ title, description, nodes[], edges[], input, reply, questions[] }`：

- **node**：`{ id, tool, label, config? }`，`tool` 必须是注册表里的 tool_id
- **edge**：`{ from, to, fromOutput? }`，`fromOutput` 指定上游哪个输出字段传给下游；不写则按回退链自动找 text

### 4.2 执行模型（DAG 拓扑排序 + 线程池并发）

1. 计算每个节点的入度，构建邻接表
2. 入度=0 的节点进入就绪队列，`ThreadPoolExecutor(max_workers=4)` 并发执行
3. `_resolve_inputs` 按边串联数据：用户输入 → 节点 config → 上游输出（优先 `fromOutput`，否则整包兜底）→ 回退链补 text
4. 单节点失败即中断，标记 `error`

### 4.3 AI 规划

`plan_workflow(text)` 用 `PLANNER_SYSTEM_PROMPT` 让 LLM 根据工具清单把自然语言编排成 JSON plan，校验每个 node.tool 合法。`plan_workflow_cached` 优先查计划缓存（0 LLM）再回退 LLM。

### 4.4 前端可视化

`modules/workflow/WorkflowPage.tsx`（约 1150 行，全项目最复杂）—— **DAG 画布完全手写**，未用 react-flow 等库：节点是绝对定位的 antd Card，连线是 SVG 覆盖层（三次贝塞尔 + 箭头），自实现拓扑分层布局算法 `workflowLayout.ts`。

---

## 5. Scheduled Agent 定时智能体（核心之三，cron）

文件：`routers/robot.py`。

把**已保存的工作流**挂到 APScheduler 的 `CronTrigger` 上，无人值守自动执行：

- **调度类型**：daily / weekly / monthly（`_schedule_robot` 解析 time/weekday/month_day）
- **模板变量**：`{今天}{昨天}{上周一}{本周日}{本月一号}{现在时间}` 等中文占位符替换
- **执行**：每个 job 调 `run_workflow(plan, {"text": 模板输入})`，写执行历史（保留 20 条）
- **持久化**：`data/robots.json`，启动时自动恢复调度

示例（`data/robots.json`）：「每周一 9:00 调研 AI 手语模型竞品动态 → 生成报告 → 发邮件给刘浩」。

---

## 6. Skill 技能系统（核心之四）

文件：`services/skill_registry.py` + `routers/skills.py`。

**「文件夹即真相源」**：每个技能 = `backend/skills/<id>/{skill.json, prompt.md, plan.json}` 三件套。

| 类型 | 定义 | 命中行为 |
|---|---|---|
| **流程型**（workflow） | 有 `plan.json` 含节点 | 直接执行默认流程，0 LLM |
| **知识型**（knowledge） | 只有 `prompt.md` 方法论 | 把方法论注入大脑 prompt，由大脑自定工具 |

匹配通道（无嵌入模型也能用）：
1. 名称/别名/触发词精确匹配（0 LLM）
2. 描述向量相似（FAISS，cos ≥ 0.72）
3. 都未命中 → 交给大脑 LLM（`kind="skill"`）

内置 6 个技能：深度调研、文档解读、会议纪要、会议转 PPT、专业写作（知识型）、周报。用户可从前端可视化创建自定义技能（`create_skill` 自动按工具输入输出串联边）。

---

## 7. AI Agent 循环（大脑）

文件：`services/agent_loop.py`。6 阶段流水线，设计哲学是「**只有大脑是大模型，其余都是代码**」，用 `LLMBudget` 严格限制编排层 LLM 调用次数（默认 3 次）。

```
感知 → 规划 → 执行 → 反思 → 输出 → 记忆
```

**规划是分层决策的**（从 0 LLM 到 1 次 LLM）：

| 优先级 | 机制 | LLM 成本 |
|---|---|---|
| a | 计划缓存精确匹配（MD5） | 0 |
| b | 技能匹配（名称/别名/向量） | 0 |
| c | 计划缓存向量相似（FAISS） | 0 |
| d | 大脑 LLM 判断 `kind`（chat/single_tool/skill/workflow） | 1 |

**反思**（`services/reflector.py`）：先跑规则校验（0 LLM，检查 tool_error/empty_output/json_malformed/truncated_output 等 9 类规则），只有格式类错误才允许 LLM 修复一次，修不好就降级输出成功部分。

### 意图路由（快路径）

`services/intent_router.py` — `/api/agent/chat` 入口先走 0 LLM 快路径：

```
关键词正则直达（17 类工具）→ 问候语识别 → 技能精确命中 → multi-tool 模型把关 → 单意图本地模型+正则
```

只有快路径全 miss 时才启动 AgentLoop 后台循环。

---

## 8. 算法与模型（重点）

### 8.1 本地深度学习模型（PyTorch + DistilBERT，Apple MPS 加速）

| 模型 | 架构 | 类别 | 训练脚本 | 推理服务 |
|---|---|---|---|---|
| **意图分类器** | DistilBERT-multilingual | 35 类（工具标签 + chat） | `train_intent_classifier.py` | `intent_classifier_service.py` |
| **多步骤检测器** | DistilBERT-multilingual | 2 类（single/multi） | `train_multitool_classifier.py` | `multitool_classifier_service.py` |
| **情感分类器** | DistilBERT-multilingual | 3 类（正/负/中） | `train_sentiment_classifier.py` | `sentiment_analyzer.py`(router) |

- 保存为 `safetensors` + `labels.txt`（类别自动从 labels.txt 读，加新工具只需重训练不用改代码）
- 训练脚本在根目录，数据在 CSV，`80/20` 分层切分，MPS 优先

### 8.2 FCN 离职风险预测（新增，本次交接）

| 项 | 值 |
|---|---|
| 算法 | 全连接神经网络 FCN（14 → 64 → 32 → 1），Sigmoid 输出离职概率 |
| 输入特征 | 9 个：工龄/薪资/最近加薪幅度/绩效/加班时长/距上次晋升月数/部门(类别 one-hot)/年龄/考勤异常 |
| 训练数据 | `attrition_data_v2.csv`（3000 条合成，注入非线性交互离职规律） |
| 输出 | 0~1 离职概率 + 风险等级（低 <0.3 / 中 0.3~0.7 / 高 >0.7） |
| 业务用途 | HR 仪表盘打风险分，提前介入留人 |
| 效果 | test AUC 0.73（优于 SVM 基线 0.72 和线性 0.70） |
| 文件 | `train_attrition_fcn.py`（训练）+ `generate_attrition_v2_data.py`（造数）+ `models/attrition_fcn/model.pt`（模型）+ `attrition_service.py`（推理） |

> 该工具此前用 SVM（`train_attrition_classifier.py`，仍保留但服务已切换到 FCN）。

### 8.3 经典 ML 模型（scikit-learn，joblib 保存）

| 模型 | 算法 | 用途 | 特征 |
|---|---|---|---|
| 水果识别 | **KNN**（k 网格选优 + StandardScaler） | 4 类水果 | mass/width/height/color_score |
| 垃圾邮件检测 | **RandomForest**（100 树，balanced） | ham/spam | 手工特征 34 项 + 垃圾关键词计数 |
| 任务优先级 | **DecisionTree**（max_depth=5） | 高/中/低，可解释 if-then | deadline/impact/leader_followup/workload |
| 延期风险 | **GradientBoosting**（100 树） | 高/中/低 | 进度/人手/需求变更/加班/依赖/临时需求 |
| 离职风险（旧） | **SVM**（RBF，balanced） | 离职/留任 | 6 特征（已被 FCN 替代） |
| 异常员工识别 | **KMeans**（k=3 无监督 + PCA 可视化） | 离群检测 | 绩效/加班/工龄/薪资 |
| 股票预测 | **LinearRegression + LogisticRegression** | 次日收盘价/涨跌 | OHLCV + daily_return |

> 注：延期风险用 GradientBoosting 而非 XGBoost，因为 XGBoost 与 PyTorch 在 macOS 上 OpenMP 库冲突会段错误。

### 8.4 LLM 网关

`services/llm_service.py` — 统一入口，OpenAI 兼容 / Anthropic 双后端自动切换（DeepSeek 默认走 OpenAI 兼容），按 `task_type` 路由模型，流式/非流式，错误统一转 `LLMError`。

### 8.5 RAG 与向量检索

- **嵌入模型**：`BAAI/bge-large-zh-v1.5`（共享加载，1.3GB）
- **RAG 知识库**：`embedding_service.py`（默认索引）+ `rag_qa.py`（文档切片入库 + top_k 检索问答）
- **计划缓存**：`plan_cache.py`（独立 FAISS 索引，MD5 精确短路 + 向量相似 cos≥0.90，LRU 淘汰）

### 8.6 会议录制子系统（独立 CLI）

`worker-toolbox/meeting_recorder/` — 双轨录音（BlackHole 系统轨 + 麦克风轨）→ faster-whisper 转写 → pyannote 说话人分离 → LLM 结构化纪要。利用物理声道分离降低 diarization 难度。

---

## 9. 目录结构

```
system-AI-Toolbox/
├── models/                          # 训练好的模型
│   ├── intent_classifier/           # DistilBERT 35 类（safetensors）
│   ├── multitool_classifier/        # DistilBERT 2 类
│   ├── sentiment_classifier/        # DistilBERT 3 类
│   ├── attrition_fcn/               # FCN 离职风险（model.pt）
│   └── */model.joblib               # 7 个 sklearn 模型
├── train_*.py                       # 训练脚本（根目录）
├── *_data.csv                       # 训练数据
├── generate_attrition_v2_data.py    # FCN 造数脚本
└── worker-toolbox/
    ├── backend/
    │   ├── routers/                 # 33 个 API 路由（含 workflow_engine/tools_registry）
    │   ├── services/                # 模型推理、LLM、Agent、记忆、嵌入等
    │   ├── skills/                  # 技能包（文件夹即真相源）
    │   ├── main.py                  # FastAPI 入口
    │   └── config.py                # 全局配置（env 覆盖）
    ├── frontend/src/
    │   ├── modules/                 # 40+ 工具页面
    │   ├── pages/                   # Home + ToolLayout
    │   ├── shared/                  # AiChat/CommandPalette/AgentStepsTimeline 等
    │   └── services/                # http.ts + llmService.ts
    └── meeting_recorder/            # 会议录制 CLI 子系统
```

---

## 10. 启动与运行

```bash
# 后端（端口 8000）
cd worker-toolbox && bash run_backend.sh   # 需 .env 配置 OPENAI_API_KEY

# 前端（端口 5173）
cd worker-toolbox/frontend && npm run dev
```

> 注意：后端热重载默认关闭（macOS 上 `--reload` 会死锁），改 `.py` 后需手动重启。前端 Vite 天然热更新。

---

## 11. 如何扩展

- **加一个工具**：`TOOLS` 加 schema + `EXECUTORS` 加执行函数 + 前端 `modules/` 加页面
- **加一个技能**：前端可视化创建，或在 `skills/<id>/` 放 skill.json + prompt.md + plan.json
- **加一个 ML 模型**：写 `train_*.py` → 存到 `models/<name>/` → 写 `services/<name>_service.py` → 注册进 `core_tools.py` + `TOOLS` + `EXECUTORS`

---

## 12. 关键设计决策与注意事项

1. **成本分层**：缓存/技能/正则/本地模型层层拦截，LLM 只在最后兜底，`LLMBudget` 硬限编排层调用次数。
2. **两套平行实现**：独立 router 与 workflow 执行器逻辑有重复（页面直调 vs 工作流编排是两条路径），加工具需维护两处。
3. **已知死代码**：`zustand` 依赖未使用；`useStream.ts`（SSE）和 `shared/hooks.ts` 写了但未接线。
4. **图片分析是「伪视觉」**：只传图片元信息不传像素。
5. **安全**：计算器用 AST 白名单；`data_analysis`/`spreadsheet`/`chart_generator` 是「LLM 生成代码→exec」模式，需注意执行环境沙箱。
6. **小 bug**：`robot.py` 的 `toggle_robot` 函数未加路由装饰器，toggle 功能未暴露成 API。

---

*最后更新：2026-08-18（FCN 离职风险预测接入）*
