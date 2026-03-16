<div align="center">

<h1>⚙️ fs-builder</h1>

<p>
  <a href="README.en.md">English</a>
</p>

<p>
  <img src="https://img.shields.io/badge/Python-3.9+-3776AB?style=flat-square&logo=python&logoColor=white"/>
  <img src="https://img.shields.io/badge/FastAPI-0.100+-009688?style=flat-square&logo=fastapi&logoColor=white"/>
  <img src="https://img.shields.io/badge/Onshape-FeatureScript-FF6B35?style=flat-square"/>
  <img src="https://img.shields.io/badge/license-MIT-green?style=flat-square"/>
</p>

<p><strong>自然语言 → Onshape FeatureScript 生成器</strong></p>

</div>

---

## 项目简介

用中文（或英文）描述你的机械装配体，fs-builder 通过 AI 自动生成可直接粘贴到 [Onshape Feature Studio](https://www.onshape.com/en/features/featurescript) 的 `.fs` 文件。

整个流程分为三步：

| 步骤 | 模块 | 说明 |
|------|------|------|
| **1. 分析** | `analyzer.py` | AI 将自然语言需求转换为结构化 JSON 设计方案 |
| **2. 生成** | `generator.py` | AI 并发为每个零件生成 FeatureScript 代码 |
| **3. 合并** | `merger.py` | 确定性地将所有零件代码合并为一个完整 `.fs` 文件 |

## 快速开始

### Web UI（推荐）

```bash
cp .env.example .env   # 填写你的 API Key
./start.sh             # 启动服务器并自动打开浏览器
```

在网页中输入需求，点击 **Generate FeatureScript** 即可。

### 命令行

```bash
# 直接输入需求
python main.py "设计一套冷拔模具，外径 50mm，包含凸模、凹模和压边圈"

# 从文件读取
python main.py --input examples/drawing_die.txt

# 跳过分析步骤，复用已有 JSON 方案
python main.py --plan output/my_assembly_plan.json
```

## 安装

**环境要求：** Python ≥ 3.9，OpenAI 兼容的 API Key

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install .
```

复制 `.env.example` 为 `.env` 并填写配置：

```env
OPENAI_API_KEY=sk-...

# 以下为可选项
# OPENAI_BASE_URL=https://api.openai.com/v1
# ANALYZE_MODEL=gpt-4o
# GENERATE_MODEL=gpt-4o-mini
```

> 配置 `.env` 后，Web UI 和 CLI 均会自动读取，无需每次手动填写。

## 项目结构

```
fs-builder/
├── app.py              # FastAPI 服务器（SSE 实时流式输出）
├── main.py             # 命令行入口
├── analyzer.py         # Step 1 — 需求 → JSON 设计方案
├── generator.py        # Step 2 — 并发生成各零件 FeatureScript
├── merger.py           # Step 3 — 合并为完整 .fs 文件
├── prompts/
│   ├── analyze.txt     # 分析步骤的系统提示词
│   └── generate.txt    # 生成步骤的系统提示词
├── examples/
│   └── drawing_die.txt # 示例需求（冷拉延模具）
├── static/
│   └── index.html      # Web UI
├── output/             # 生成的 .fs 文件（已加入 .gitignore）
└── .env.example
```

## 架构

```
用户需求（自然语言）
        │
        ▼
  ┌───────────┐  AI (gpt-4o)   ┌──────────────────────┐
  │ 分析器    │ ─────────────▶ │  JSON 设计方案        │
  └───────────┘                │  零件列表 + 位置坐标   │
                               └──────────┬───────────┘
                                          │
                                          ▼
                          ┌──────────────────────────────┐
                          │  生成器（并发）               │  AI (gpt-4o-mini)
                          │  每个零件独立调用 API          │ ──────────────▶
                          └──────────────┬───────────────┘
                                          │
                                          ▼
                          ┌──────────────────────────────┐
                          │  合并器（确定性）              │
                          │  每个零件包裹在 {} 作用域内    │
                          │  添加 FeatureScript 文件头    │
                          └──────────────┬───────────────┘
                                          │
                                          ▼
                             output/<assembly_name>.fs
```

JSON 设计方案是步骤 1 和步骤 2 之间的契约，保存在 `output/<name>_plan.json`，可复用以跳过分析步骤重新生成。

## 命令行参数

```
python main.py [需求文本 | --input 文件路径]
               [--output 文件路径]      输出 .fs 文件路径（默认：output/<name>.fs）
               [--plan 文件路径]        跳过步骤 1，加载已有 JSON 方案
               [--dry-run]             仅执行步骤 1，打印方案后退出
               [--api-key KEY]         覆盖 OPENAI_API_KEY 环境变量
               [--base-url URL]        OpenAI 兼容的 API 地址
               [--analyze-model M]     步骤 1 使用的模型（默认：gpt-4o）
               [--generate-model M]    步骤 2 使用的模型（默认：gpt-4o-mini）
               [--concurrency N]       最大并发 API 调用数（默认：8）
```

## 使用生成的文件

1. 打开 [Onshape](https://cad.onshape.com)，新建文档
2. 从底部标签栏打开 **Feature Studio**
3. 将 `.fs` 文件内容粘贴进去
4. 点击 **Compile** — 自定义特征即出现在 Part Studio 中
