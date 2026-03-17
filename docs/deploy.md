# 服务器部署教程

本文档介绍如何将 fs-builder 部署到 Ubuntu 服务器。

---

## 准备工作

- Ubuntu 20.04 / 22.04 / 24.04 服务器
- root 或 sudo 权限
- 已安装 Git（可选，也可以直接上传文件）

---

## 方式一：一键部署脚本（推荐）

### 1. 上传代码到服务器

**如果已推送到 GitHub：**

```bash
# 在服务器上执行
git clone https://github.com/你的用户名/fs-builder.git /tmp/fs-builder
```

**如果没有 GitHub，用 scp 上传：**

```bash
# 在本地执行（Mac/Linux）
scp -r /Users/roe/Documents/AICAD 用户名@服务器IP:/tmp/fs-builder
```

### 2. 执行一键部署

```bash
# 在服务器上执行
cd /tmp/fs-builder
sudo bash deploy/setup.sh
```

如果有域名：

```bash
sudo bash deploy/setup.sh --domain your.domain.com
```

脚本会自动完成：
- 安装 Python、nginx
- 创建虚拟环境、安装依赖
- 配置 systemd 服务（开机自启）
- 配置 nginx 反向代理

### 3. 填写 API Key

```bash
sudo nano /opt/fs-builder/.env
```

填写内容：

```env
OPENAI_API_KEY=你的API密钥
OPENAI_BASE_URL=https://你的中转API地址/v1
ANALYZE_MODEL=gpt-4o
GENERATE_MODEL=gpt-4o-mini
```

保存后重启服务：

```bash
sudo systemctl restart fs-builder
```

### 4. 访问

打开浏览器访问 `http://服务器IP`，API Key 字段会显示 **✓ from .env**，直接点击生成即可。

---

## 方式二：手动部署

如果你想了解每一步的细节，或脚本遇到问题，可以手动执行。

### 1. 安装系统依赖

```bash
sudo apt-get update
sudo apt-get install -y python3 python3-pip python3-venv nginx
```

### 2. 部署代码

```bash
sudo mkdir -p /opt/fs-builder
sudo rsync -a /tmp/fs-builder/ /opt/fs-builder/
```

### 3. 创建虚拟环境

```bash
cd /opt/fs-builder
sudo python3 -m venv .venv
sudo .venv/bin/pip install --upgrade pip
sudo .venv/bin/pip install .
```

### 4. 配置环境变量

```bash
sudo cp /opt/fs-builder/.env.example /opt/fs-builder/.env
sudo nano /opt/fs-builder/.env
```

### 5. 配置 systemd 服务

```bash
sudo cp /opt/fs-builder/deploy/fs-builder.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable fs-builder
sudo systemctl start fs-builder
```

### 6. 配置 nginx

```bash
sudo cp /opt/fs-builder/deploy/fs-builder.nginx /etc/nginx/sites-available/fs-builder
sudo ln -s /etc/nginx/sites-available/fs-builder /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx
```

---

## 更新代码

每次修改代码后，在服务器上执行：

```bash
sudo bash /opt/fs-builder/deploy/update.sh
```

如果是手动上传文件，先用 scp 上传，再执行 update.sh。

---

## 常用运维命令

```bash
# 查看实时日志
sudo journalctl -u fs-builder -f

# 查看最近 50 行日志
sudo journalctl -u fs-builder -n 50

# 重启服务
sudo systemctl restart fs-builder

# 停止服务
sudo systemctl stop fs-builder

# 查看服务状态
sudo systemctl status fs-builder

# 测试 nginx 配置
sudo nginx -t

# 重载 nginx（不中断现有连接）
sudo systemctl reload nginx
```

---

## 可选：配置 HTTPS

如果有域名，可以用 Certbot 免费申请 SSL 证书：

```bash
sudo apt-get install -y certbot python3-certbot-nginx
sudo certbot --nginx -d your.domain.com
```

Certbot 会自动修改 nginx 配置并设置自动续期。

---

## 故障排查

**服务起不来？**

```bash
sudo journalctl -u fs-builder -n 50
```

常见原因：
- `.env` 文件不存在或 API Key 为空
- Python 依赖未安装
- 端口 8000 被占用：`sudo lsof -i :8000`

**nginx 502 错误？**

说明 fs-builder 服务没有在运行：

```bash
sudo systemctl status fs-builder
sudo systemctl start fs-builder
```

**SSE 不流式输出？**

确认 nginx 配置中有以下两行：

```nginx
proxy_buffering off;
proxy_cache     off;
```
