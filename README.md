# fs-builder

面向毕设演示的 CLI 工具：把简单机械结构需求先分析成结构化 plan，再生成可粘贴到 Onshape Feature Studio 的 FeatureScript。

当前版本是 **CLI-first 精简版**：

- 保留三段式流程：`analyze -> generate -> merge`
- Web UI、SSE、服务器部署脚本已移除
- Step 2 仍然是 **legacy LLM 生成器**，只是过渡方案
- 后续会替换成你提供资料后的 FeatureScript 模板生成

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
# GENERATE_MODEL=gpt-4o-mini
```

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
3. 调用 legacy 生成器生成各零件代码
4. 合并成 `output/<assembly_name>.fs`

## 项目结构

```text
src/fs_builder/
├── cli.py               # 新的 CLI 子命令入口
├── settings.py          # .env 和运行配置
├── models.py            # 强类型 plan schema
├── analyzer.py          # Step 1: requirement -> plan
├── generator.py         # Step 2: legacy LLM generator
├── merger.py            # Step 3: merge FeatureScript
├── paths.py             # 输出路径 sanitize
├── plan_io.py           # plan 读写
└── prompts/
    ├── analyze.txt
    └── generate_legacy.txt
```

## 设计原则

- AI 先负责把需求变成结构化 plan
- CLI 和 schema 负责尽早拦截错误
- 输出路径不直接信任模型字符串
- 旧的自由生成逻辑先保留，但明确标记为临时实现

## 已知限制

- 当前不是模板生成版，FeatureScript 输出仍然依赖 LLM，稳定性有限
- 还不支持复杂装配约束求解
- 还不支持 Web 演示界面
- 还没有接入 Onshape 编译验证闭环

## 测试

```bash
pytest
```

CI 也会在 GitHub Actions 里跑同样的测试。
