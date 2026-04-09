# fs-builder

面向毕设演示的 CLI 工具：把简单机械结构需求先分析成结构化 plan，再生成可粘贴到 Onshape Feature Studio 的 FeatureScript。

当前版本是 **CLI-first 精简版**：

- 保留三段式流程：`analyze -> generate -> merge`
- Web UI、SSE、服务器部署脚本已移除
- Step 2 默认改成 **确定性 FeatureScript 模板生成**
- `--legacy` 只保留为兼容开关，不再是主链路

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
# ANALYZE_MAX_TOKENS=2048
# GENERATE_MODEL=gpt-4o-mini
```

说明：

- `analyze` 和 `build --input ...` 需要 API key，因为要调用分析模型
- `generate --plan ...` 和 `build --plan ...` 默认走模板生成，不需要 API key
- 只有显式加 `--legacy` 时，Step 2 才会重新使用 LLM
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

如果你要回退到旧的 LLM 生成器：

```bash
fs-builder generate --plan output/drawing_die_plan.json --legacy --api-key sk-...
```

### 4. 走完整流程

```bash
fs-builder build --input examples/drawing_die.txt
```

这会：

1. 调用分析器生成并校验 plan
2. 把 plan 保存到 `output/<assembly_name>_plan.json`
3. 调用模板生成器生成各零件代码
4. 合并成 `output/<assembly_name>.fs`

## 项目结构

```text
src/fs_builder/
├── cli.py               # 新的 CLI 子命令入口
├── settings.py          # .env 和运行配置
├── models.py            # 强类型 plan schema
├── analyzer.py          # Step 1: requirement -> plan
├── generator.py         # Step 2: template generator + legacy fallback
├── merger.py            # Step 3: merge FeatureScript
├── paths.py             # 输出路径 sanitize
├── plan_io.py           # plan 读写
├── references/
│   └── featurescript_guide.md
└── prompts/
    ├── analyze.txt
    └── generate_legacy.txt
```

## 设计原则

- AI 先负责把需求变成结构化 plan
- CLI 和 schema 负责尽早拦截错误
- Step 2 默认使用确定性模板，不让 LLM 自由写 FeatureScript
- 输出路径不直接信任模型字符串
- 旧的自由生成逻辑只保留为显式兼容路径

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
pytest
```

CI 也会在 GitHub Actions 里跑同样的测试。
