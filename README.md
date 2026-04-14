# fs-builder

面向毕业答辩演示的最小项目：把简单机械结构需求分析成结构化 plan，再生成可粘贴到 Onshape Feature Studio 的 FeatureScript。

当前仓库只保留演示所需主链路：

- 命令行入口 `fs-builder`
- 本地 Web UI
- 一个样例需求 `examples/drawing_die.txt`
- 一键启动脚本 `scripts/start_webui.sh`

## 适用范围

当前只支持 5 种基础零件形状：

- `box`
- `cylinder`
- `hollow_cylinder`
- `tapered_cylinder`
- `flange`

如果分析结果出现不支持的 shape，系统会直接报错，不继续生成。

## 安装

如果项目里还没有虚拟环境：

```bash
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -e .
cp .env.example .env
```

如果已经有 `.venv`，通常只需要确认 `.env` 可用即可。

## 启动 Web UI

最方便的方式：

```bash
./scripts/start_webui.sh
```

自定义端口：

```bash
PORT=8765 ./scripts/start_webui.sh
```

启动后访问 `http://127.0.0.1:8000` 或你指定的端口。

## CLI 示例

完整构建：

```bash
.venv/bin/fs-builder build --input examples/drawing_die.txt
```

只启动服务：

```bash
.venv/bin/fs-builder serve --host 127.0.0.1 --port 8000
```

## 当前目录结构

```text
src/                核心源码
examples/           演示样例输入
scripts/            启动脚本
.env.example        环境变量示例
pyproject.toml      项目配置
README.md           说明文档
```

## 已知限制

- 当前模板只覆盖 5 种基础 shape
- 还不支持复杂装配约束求解
- 还没有接入 Onshape 在线编译验证闭环
