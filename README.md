# fs-builder

面向毕设演示的 CLI 工具：把简单机械结构需求先分析成结构化 plan，再生成可粘贴到 Onshape Feature Studio 的 FeatureScript。

当前版本是 **CLI + Local Web UI 精简版**：

- 保留三段式流程：`analyze -> generate -> merge`
- 提供一个可直接运行的本地 Web UI，服务端仍然复用 Python 主链路
- Step 2 默认改成 **确定性 FeatureScript 模板生成**
- CLI 现在只保留稳定主链路，不再支持 `--legacy`

## 适用范围

当前只面向简单演示模型，plan 只支持这 5 种零件形状：

- `box`
- `cylinder`
- `hollow_cylinder`
- `tapered_cylinder`
- `flange`

如果分析结果出现不支持的 shape，CLI 会直接报错，不会继续硬生成。

## 安装

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e .[dev]
cp .env.example .env
```

`.env` 示例：

```env
OPENAI_API_KEY=sk-...
# OPENAI_BASE_URL=https://api.openai.com/v1
# ANALYZE_MODEL=gpt-4o
# OPENAI_TIMEOUT_SECONDS=30
# ANALYZE_MAX_TOKENS=2048
```

说明：

- `analyze` 和 `build --input ...` 需要 API key，因为要调用分析模型
- `generate --plan ...` 和 `build --plan ...` 默认走模板生成，不需要 API key
- `serve` 命令复用同一套环境变量，本地 Web UI 的 Analyze / Build 也遵循同样规则
- 某些第三方兼容接口对超大 `max_tokens` 不稳定，分析阶段默认使用 `2048`，也支持通过 `ANALYZE_MAX_TOKENS` 调整

## CLI 用法

### 1. 只做需求分析

```bash
fs-builder analyze --input examples/drawing_die.txt --output output/drawing_die_plan.json
```

不加 `--output` 时，会直接把 JSON 打到标准输出。

### 2. 校验已有 plan

```bash
fs-builder validate-plan --plan output/drawing_die_plan.json
```

### 3. 基于已有 plan 生成 FeatureScript

```bash
fs-builder generate --plan output/drawing_die_plan.json
```

默认输出到 `output/<assembly_name>.fs`。

### 4. 走完整流程

```bash
fs-builder build --input examples/drawing_die.txt
```

这会：

1. 调用分析器生成并校验 plan
2. 把 plan 保存到 `output/<assembly_name>_plan.json`
3. 调用模板生成器生成各零件代码
4. 合并成 `output/<assembly_name>.fs`

### 5. 启动本地 Web UI

```bash
fs-builder serve --host 127.0.0.1 --port 8000
```

或者直接使用仓库内脚本：

```bash
./scripts/start_webui.sh
# 自定义端口
PORT=8765 ./scripts/start_webui.sh
```

启动后访问 `http://127.0.0.1:8000`。Web UI 提供：

- Analyze：输入需求并查看结构化 plan
- Generate：在页面里编辑当前 plan JSON 后直接生成 FeatureScript
- Full Build：执行完整链路并把 plan / `.fs` 写入 `output/`

## 项目结构

```text
src/fs_builder/
├── cli.py               # CLI 参数解析与输出
├── settings.py          # 环境变量加载与运行配置
├── models.py            # 强类型 plan schema
├── errors.py            # 项目级异常定义
├── application/         # analyze / generate / build 用例编排
├── analysis/            # provider 调用、输出解析、demo fallback
├── generation/          # 模板渲染、合并与结果模型
├── io/                  # plan/artifact I/O 与资源读取
├── webui/               # 本地 Web UI 服务与静态资源
├── references/
│   └── featurescript_guide.md
└── prompts/
    └── analyze.txt
```

## 设计原则

- AI 先负责把需求变成结构化 plan
- CLI 和 schema 负责尽早拦截错误
- Step 2 默认使用确定性模板，不让 LLM 自由写 FeatureScript
- 输出路径不直接信任模型字符串
- CLI 只负责参数解析和结果输出，不再直接承担业务编排
- 分析/生成/I/O 分层后，测试可以直接覆盖核心逻辑，而不必全部绕过 CLI
- Web UI 不单独复制业务逻辑，而是复用同一套分析与生成服务，避免前后端行为漂移

## FeatureScript 教程

项目内置了一份中文教程，供后续模板开发和调试直接参考：

- `src/fs_builder/references/featurescript_guide.md`

它固定了本项目的写法规范，包括：

- `defineFeature` 的基本结构
- 单位和 `ValueWithUnits`
- `Context` / `Query` / `op*`
- `newSketchOnPlane -> sk* -> skSolve -> op*` 的模板路线
- 当前 5 个 shape 的建模映射

## 已知限制

- 当前模板只覆盖 5 种基础 shape
- 还不支持复杂装配约束求解
- 还不支持孔、倒角、圆角等更复杂特征
- 还没有接入 Onshape 编译验证闭环

## 测试

```bash
ruff check .
ruff format --check .
mypy src
pytest --cov=fs_builder
```

CI 也会在 GitHub Actions 里跑同样的测试。
