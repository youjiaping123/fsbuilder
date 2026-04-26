# 答辩演示指南

## 演示目标

本项目的答辩重点不是证明系统已经具备完整 CAD 软件能力，而是展示一条稳定、可解释的 AI 辅助建模链路：

```text
自然语言机械需求
  -> AI 需求分析
  -> 结构化装配方案
  -> FeatureScript 自动生成
  -> Onshape 中生成三维模型
```

演示时建议围绕“成功率、可行性、工程闭环”展开，不要现场扩展复杂需求。

## 推荐演示流程

1. 启动本地 Web UI。

```bash
./scripts/start_webui.sh
```

2. 打开浏览器访问默认地址。

```text
http://127.0.0.1:8000
```

3. 在 Web UI 中选择或输入“冷拉延模具”示例需求。

4. 执行“全流程构建”，观察系统生成：

- plan JSON：结构化装配方案。
- 零件列表：每个零件的形状、尺寸、位置和材料提示。
- FeatureScript：可粘贴到 Onshape Feature Studio 的脚本。

5. 将生成的 `.fs` 内容粘贴到 Onshape Feature Studio，展示模型生成结果。

## 三层备用方案

为了保证答辩现场稳定，建议提前准备三层演示方案。

第一层：完整链路演示。

- 使用 `examples/drawing_die.txt`。
- 从需求文本开始，现场完成分析和生成。

第二层：跳过 AI 分析。

- 如果网络、API Key 或模型接口不稳定，直接加载已有 plan JSON。
- 使用 `fs-builder generate --plan <plan 文件>` 或 Web UI 的“脚本生成”模式。

第三层：完全离线展示。

- 提前准备成功生成的 `.fs` 文件。
- 提前准备 Onshape 模型截图或录屏。
- 现场重点讲解系统设计、数据流和结果。

## 建议准备的材料

- `examples/drawing_die.txt`：固定演示需求。
- `output/cold_drawing_die_plan.json`：已验证的结构化 plan。
- `output/cold_drawing_die.fs`：已生成的 FeatureScript。
- Onshape 成功建模截图。
- 20 到 40 秒的操作录屏。
- `docs/PROJECT_STRUCTURE.md`：项目结构与运行机制说明。

## 答辩表述建议

可以这样介绍系统边界：

> 本系统面向毕业设计演示场景，重点验证自然语言机械需求到结构化 CAD 脚本的可行性。当前版本只支持基础机械零件形状，复杂装配约束求解、在线编译验证和更多 CAD 特征作为后续扩展方向。

可以这样解释技术路线：

> 系统没有直接让 AI 生成完整 CAD 脚本，而是先通过 AI 需求分析模块生成结构化 plan，再由本地确定性模板生成 FeatureScript。这样可以降低模型输出不稳定带来的风险，提高演示成功率。

## 演示注意事项

- 答辩前确认 `.env` 中 API Key 可用。
- 答辩前至少完整跑通一次 Web UI 全流程。
- 不建议现场输入临时复杂需求。
- 不建议现场临时修改代码或依赖。
- 如果 Onshape 打开较慢，优先使用截图或录屏兜底。
