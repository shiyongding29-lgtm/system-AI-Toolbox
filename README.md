# system-AI-Toolbox 智能工具箱

一个集成 **39 个 AI 工具** + 智能工作流编排 + 无人值守定时智能体（Agentic Automation）+ **自训练模型**的 AI Agent 平台。

## ✨ 核心特性

| 功能 | 说明 |
|---|---|
| 🤖 **AI Assistant** | 42 类意图识别，自动判断单工具 / 多步骤任务，LLM 提取结构化数值参数 |
| 🔀 **智能工作流** | 自然语言自动生成工作流，DAG 画布拖拽编排，支持串联 ML 工具 |
| ⏰ **Scheduled Agent** | 无人值守定时智能体：按 cron 调度自动执行 AI 工作流 |
| 🧠 **自训练模型** | 3 个 DistilBERT + 1 个 FCN 神经网络 + 7 个 sklearn 模型，全部本地推理 |
| 🧩 **技能系统** | 文件夹式技能包（方法论 + 默认流程），可视化自定义扩展 |
| 🎨 **科技风 UI** | 深色/浅色双主题，Apple Watch 气泡网格 |

---

## 🧠 AI 模型

### 模型 1：意图分类器（Intent Classifier）

| 项目 | 值 |
|---|---|
| 架构 | `DistilBERT-base-multilingual-cased` |
| 类别数 | **42 类**（工具标签 + chat，含 7 个 ML 工具） |
| 训练数据 | 853 条标注样本 |
| 训练脚本 | `train_intent_classifier.py` |
| 权重文件 | `models/intent_classifier/` |

**作用**：判断用户想用哪个工具（meeting / translation / calculator / attrition_risk / ...）。

### 模型 2：多步骤检测器（Multi-Tool Detector）

| 项目 | 值 |
|---|---|
| 架构 | `DistilBERT-base-multilingual-cased` |
| 类别数 | 2 类（`single_tool` / `multi_tool`） |
| 训练脚本 | `train_multitool_classifier.py` |

**作用**：判断用户请求是单步骤还是需要多个工具协同。

### 模型 3：情感分类器（Sentiment Classifier）

| 项目 | 值 |
|---|---|
| 架构 | `DistilBERT-base-multilingual-cased` |
| 类别数 | 3 类（`positive` / `negative` / `neutral`） |
| 训练脚本 | `train_sentiment_classifier.py` |

### 模型 4：FCN 离职风险预测（全连接神经网络）

| 项目 | 值 |
|---|---|
| 架构 | 全连接 `14 → 64 → 32 → 1`，Sigmoid 输出离职概率 |
| 输入特征 | 9 个（工龄/薪资/加薪幅度/绩效/加班/晋升间隔/部门/年龄/考勤异常） |
| 输出 | 0~1 离职概率 + 风险等级（低/中/高） |
| 训练脚本 | `train_attrition_fcn.py` + `generate_attrition_v2_data.py` |
| 效果 | test AUC 0.73（优于 SVM 基线） |

### 模型 5：7 个经典 ML 模型（scikit-learn）

| 模型 | 算法 | 用途 |
|---|---|---|
| 水果识别 | KNN | 4 类水果 |
| 垃圾邮件检测 | RandomForest | ham/spam |
| 任务优先级 | DecisionTree | 可解释 if-then 规则 |
| 延期风险 | GradientBoosting | 高/中/低 |
| 离职风险（旧） | SVM | 已被 FCN 替代 |
| 异常员工识别 | KMeans + PCA | 无监督离群检测 |
| 股票预测 | LinearRegression + LogisticRegression | 次日收盘价/涨跌 |

### 模型 6：DeepSeek LLM（云端）

| 项目 | 值 |
|---|---|
| 模型 | `deepseek-chat` |
| 用途 | 大脑决策、数值参数提取、工作流自动生成 |
| 配置 | `worker-toolbox/.env` |

> 本地模型默认从 `<repo>/models/` 自动加载；如需自定义位置，设置环境变量 `MODELS_DIR`。

---

## 🔄 AI Assistant 推理流程

```
用户输入
    ↓
① 关键词正则直达（0 LLM：计算器/天气/汇率/日期…）
    ↓ 未命中
② Multi-Tool 模型（判断几个工具）
    ├─ multi_tool ≥ 70% → LLM 生成工作流
    └─ single_tool → 意图分类模型（42 类）
                        ├─ ML 工具 → 大脑 LLM 提取数值参数 → 执行
                        ├─ 普通工具 → 正则提取参数 → 跳转
                        └─ 低信心 → LLM 兜底
```

**ML 工具调用**：对「预测离职风险，工龄 5 年，月薪一万二，绩效 4 分」这类请求，大脑 LLM 自动从自然语言提取结构化数值（中文数字/单位自动转换），缺参数时反问补充。

---

## 📦 39 个工具

| 分类 | 工具 |
|---|---|
| 📥 输入采集 | Meeting Notes、Image Analyzer、PDF Toolkit、File Converter、Web Scraper、User Input、Multi-Source |
| ⚙️ AI 处理 | Doc Summary、Mind Map、Todo Extract、Translation、Data Analysis、Task Planning、Doc Compare、Spreadsheet、Knowledge Q&A、Table Generator、Sentiment Analyzer、Info Extraction |
| 📤 生成输出 | Add Todo、Email & Docs、PPT/HTML、Deep Research、Weekly Report、Chart Generator、QR Generator |
| 🧮 零 LLM 工具 | Calculator、Date Calc、Unit Converter、Word Count、JSON Formatter |
| 🌐 外部数据 | Weather、Exchange Rate、Stock Quote |
| 🤖 ML 工具 | Fruit Classifier、Spam Detector、Task Priority、Delay Risk、Attrition Risk（FCN）、Anomaly Detection、Stock Predictor |

---

## 🏗️ 技术栈

| 层 | 技术 |
|---|---|
| 前端 | React 19 + TypeScript + Ant Design 6 + Vite |
| 后端 | FastAPI + SQLAlchemy + APScheduler |
| 深度学习 | PyTorch + HuggingFace Transformers + DistilBERT |
| 经典 ML | scikit-learn（KNN / RF / 决策树 / GBDT / SVM / KMeans / 回归） |
| 向量检索 | FAISS + sentence-transformers |
| 训练加速 | Apple MPS GPU |
| 数据库 | SQLite |

---

## 📁 目录结构

```
system-AI-Toolbox/
├── models/                        # 训练好的模型
│   ├── intent_classifier/          # 意图分类（42 类）
│   ├── multitool_classifier/       # 多步骤检测（2 类）
│   ├── sentiment_classifier/       # 情感分类（3 类）
│   ├── attrition_fcn/              # FCN 离职风险（model.pt）
│   └── */model.joblib              # 7 个 sklearn 模型
├── train_intent_classifier.py      # 意图分类训练脚本
├── train_multitool_classifier.py   # 多步骤检测训练脚本
├── train_sentiment_classifier.py   # 情感分类训练脚本
├── train_attrition_fcn.py          # FCN 离职风险训练脚本
├── generate_attrition_v2_data.py   # FCN 造数脚本
├── add_ml_training_data.py         # 意图训练集扩充脚本
├── training_data.csv               # 意图分类训练数据（42 类）
└── worker-toolbox/
    ├── backend/
    │   ├── routers/                # 33 个 API 路由
    │   ├── services/               # 模型推理、LLM、Agent、记忆、嵌入
    │   ├── skills/                 # 技能包（文件夹即真相源）
    │   └── main.py                 # FastAPI 入口
    ├── frontend/
    │   └── src/modules/            # 40+ 工具页面模块
    └── run_backend.sh              # 后端启动脚本
```

---

## 🚀 快速开始

### 1. 安装依赖

```bash
# 后端
pip install -r worker-toolbox/backend/requirements.txt

# 前端
cd worker-toolbox/frontend && npm install
```

### 2. 配置 API Key

```bash
cd worker-toolbox
cp .env.example .env  # 填入 OPENAI_API_KEY（默认走 DeepSeek）
```

### 3. 启动

```bash
# 后端（端口 8000）
cd worker-toolbox && bash run_backend.sh

# 前端（端口 5173）
cd worker-toolbox/frontend && npm run dev
```

---

## 🧪 重新训练模型

```bash
# 意图分类模型（42 类）
python3 train_intent_classifier.py

# 多步骤检测模型
python3 train_multitool_classifier.py

# 情感分类模型
python3 train_sentiment_classifier.py

# FCN 离职风险模型（先生成数据再训练）
python3 generate_attrition_v2_data.py
python3 train_attrition_fcn.py
```

训练数据在 CSV 文件中，每行格式：`文本,标签`。添加新工具：用 `add_ml_training_data.py` 补意图样本 → 重训意图分类器 → 重启后端自动加载。

---

## 📚 更多文档

- [SYSTEM_OVERVIEW.md](SYSTEM_OVERVIEW.md) — 完整系统介绍（架构/算法/扩展指南）
- [系统介绍.docx](系统介绍.docx) — 面试版 Word 文档

## 📄 License

MIT
