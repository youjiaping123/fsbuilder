# 项目结构说明

## 项目定位

`fs-builder` 是一个面向毕业答辩演示的 Python 项目，用来把自然语言描述的简单机械结构需求转换为可粘贴到 Onshape Feature Studio 的 FeatureScript。项目同时提供命令行入口和本地 Web UI，核心目标是演示“需求分析 -> 结构化 plan -> 确定性脚本生成”的主链路。

当前项目不是完整 CAD 求解器，也不做复杂装配约束求解。它把 LLM 的职责限定在需求分析阶段，后续 plan 校验和 FeatureScript 生成都走本地确定性逻辑。

## 总体运行链路

```text
需求文本
  -> LLM 分析
  -> JSON plan 解析
  -> Pydantic schema 校验
  -> 按零件 shape 渲染 FeatureScript 片段
  -> 合并为完整 FeatureScript
  -> CLI/Web UI 展示，或写入 output/
```

核心数据流如下：

1. 用户通过 CLI 参数、需求文本文件或 Web UI 输入机械结构需求。
2. `analysis` 模块读取 `prompts/analyze.txt`，调用兼容 OpenAI Chat Completions 的接口，要求模型只输出 JSON。
3. `models.py` 使用 Pydantic 将模型输出校验为 `AssemblyPlan`，并检查零件 id、shape 参数、装配关系引用等约束。
4. `generation` 模块根据每个零件的 `shape` 选择本地模板，生成对应 FeatureScript 片段。
5. `generation.merge` 将所有零件片段合并成一个 Onshape feature，并写入或返回给调用方。
6. CLI 和 Web UI 共用应用层能力，但分别负责终端输出和浏览器交互。

如果分析阶段失败，且需求命中内置“冷拉延模具”演示样例，系统会使用 demo fallback 生成一个稳定 plan；其他需求不会静默兜底。

## 运行入口

### CLI

项目在 `pyproject.toml` 中注册命令：

```text
fs-builder = "fs_builder.cli:main"
```

主要子命令：

- `fs-builder analyze`：把需求文本分析成 plan JSON。
- `fs-builder validate-plan`：读取并校验已有 plan 文件。
- `fs-builder generate`：根据已有 plan 生成 FeatureScript。
- `fs-builder build`：执行完整链路；可从需求开始，也可通过 `--plan` 跳过分析。
- `fs-builder serve`：启动本地 Web UI 服务。

典型全流程命令：

```bash
.venv/bin/fs-builder build --input examples/drawing_die.txt
```

### Web UI

Web UI 的推荐启动入口是：

```bash
./scripts/start_webui.sh
```

脚本会进入项目根目录，并执行：

```text
.venv/bin/fs-builder serve --host <HOST> --port <PORT>
```

实际链路为：

```text
scripts/start_webui.sh
  -> fs_builder.cli
  -> fs_builder.webui.server
  -> fs_builder.webui.api.WebUIService
```

浏览器端静态资源位于 `src/fs_builder/webui/static/`。前端通过 `/api/state`、`/api/analyze`、`/api/generate`、`/api/build` 与本地 HTTP 服务通信。

## 后端模块职责

```text
src/fs_builder/
  analysis/       需求分析：调用模型、解析 JSON/SSE、处理 demo fallback
  application/    应用编排：为 CLI 组织 analyze/build/generate 等用例
  generation/     脚本生成：按 shape 渲染 FeatureScript 并合并输出
  io/             文件读写：plan JSON、FeatureScript 产物、资源加载
  prompts/        LLM 分析提示词
  references/     FeatureScript 参考资料
  webui/          本地 HTTP 服务、Web API、静态页面
  cli.py          命令行参数解析与命令分发
  models.py       强类型 plan schema 与校验规则
  settings.py     环境变量、命令行覆盖项和默认路径配置
```

关键模块说明：

- `analysis.provider`：负责向模型发送 Chat Completions 请求，兼容 SDK client、注入 requester 和自定义 `OPENAI_BASE_URL`。
- `analysis.parsing`：负责从普通响应、completion envelope 或 SSE 流中抽取文本，并解析为 JSON。
- `analysis.service`：把模型调用、响应解析、schema 校验和 demo fallback 串成稳定入口。
- `models.py`：定义 `AssemblyPlan`、`PartSpec`、`AssemblyRelation` 等核心数据契约。
- `generation.renderers`：为 `box`、`cylinder`、`hollow_cylinder`、`tapered_cylinder`、`flange` 提供确定性渲染模板。
- `generation.merge`：生成 FeatureScript 文件头、feature 定义、零件分段和错误注释。
- `webui.server`：基于标准库 `http.server` 提供静态资源和 JSON API。
- `webui.api`：复用分析与生成服务，并把结果序列化给前端。

## 数据契约

核心 plan 类型是 `AssemblyPlan`，其顶层结构包含：

- `assembly_name`：装配名称，要求是 snake_case 标识符。
- `description`：装配摘要。
- `global_params`：全局尺寸、单位和坐标原点说明。
- `parts`：零件列表，每个零件由 `PartSpec` 描述。
- `assembly_relations`：装配关系列表，每条关系由 `AssemblyRelation` 描述。

`PartSpec` 的关键字段：

- `id`：唯一零件 id，格式为小写字母开头，只包含小写字母、数字和下划线。
- `shape`：零件形状，必须属于当前支持的 5 种基础形状。
- `material_hint`：材料提示，只允许 `steel`、`cast_iron`、`carbide`、`general`。
- `params`：形状参数，必须与 `shape` 的要求完全一致。
- `position`：零件底部中心位置，使用毫米单位。

当前支持的 shape 和参数：

| shape | 参数 |
| --- | --- |
| `box` | `width_mm`、`depth_mm`、`height_mm` |
| `cylinder` | `diameter_mm`、`height_mm` |
| `hollow_cylinder` | `outer_diameter_mm`、`inner_diameter_mm`、`height_mm` |
| `tapered_cylinder` | `top_diameter_mm`、`bottom_diameter_mm`、`height_mm` |
| `flange` | `flange_diameter_mm`、`flange_height_mm`、`shaft_diameter_mm`、`shaft_height_mm` |

校验规则会拒绝多余字段、缺失参数、非正尺寸、重复零件 id、自引用关系和不存在的关系引用。对空心圆柱，外径必须大于内径；对法兰，法兰直径必须大于轴直径。

## 输出产物

默认输出目录由 `Settings.output_dir` 控制，命令行默认值为 `output/`。

完整构建会产生两类文件：

```text
output/<assembly_name>_plan.json
output/<assembly_name>.fs
```

其中：

- `*_plan.json` 是校验后的结构化 plan，可再次传给 `validate-plan`、`generate` 或 Web UI。
- `.fs` 是合并后的 FeatureScript，可粘贴到 Onshape Feature Studio 使用。

输出文件名会通过 `safe_slug` 清理，避免非法字符或路径越界。写入路径最终会校验在指定输出目录内。

## 配置与环境变量

项目通过 `.env`、系统环境变量和 CLI 参数共同解析配置。`load_project_env()` 会加载最近的 `.env`，但不会覆盖已经存在的环境变量。

常用配置：

- `OPENAI_API_KEY`：分析需求时使用的 API Key。
- `OPENAI_BASE_URL`：可选，自定义兼容 OpenAI 接口的服务地址。
- `OPENAI_TIMEOUT_SECONDS`：分析请求超时时间，默认 30 秒。
- `ANALYZE_MODEL`：分析模型，默认 `gpt-4o`。
- `ANALYZE_MAX_TOKENS`：分析阶段最大输出 token，默认 2048。

生成阶段不调用模型，只依赖已经校验通过的 plan。

## 能力边界

- 当前只支持 `box`、`cylinder`、`hollow_cylinder`、`tapered_cylinder`、`flange` 这 5 种基础形状。
- 不支持复杂曲面、倒角、螺纹、孔阵列等高级 CAD 特征。
- 不做真实装配约束求解，`assembly_relations` 主要作为结构说明和后续扩展数据。
- 未接入 Onshape 在线编译验证闭环，`.fs` 文件生成后需要人工粘贴到 Onshape 验证。
- demo fallback 只服务仓库内置冷拉延模具示例，不作为通用容错策略。
