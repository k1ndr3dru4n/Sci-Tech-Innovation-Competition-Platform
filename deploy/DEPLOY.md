# STIC 项目部署文档

本文档说明如何在 Ubuntu 22.04 UEFI 服务器上部署 STIC 项目。

## 目录

- [快速部署](#快速部署)
- [手动部署](#手动部署)
- [配置说明](#配置说明)
- [服务管理](#服务管理)
- [备份与恢复](#备份与恢复)
- [故障排查](#故障排查)

## 快速部署

### 1. 准备工作

确保您有：
- Ubuntu 22.04 服务器（root 或 sudo 权限）
- 服务器 IP 地址或域名
- 项目代码文件

### 2. 上传项目文件

将项目文件上传到服务器：

```bash
# 方法1: 使用 SCP
scp -r /path/to/STIC/* user@server-ip:/tmp/stic/

# 方法2: 使用 Git（如果有仓库）
git clone <repository-url> /tmp/stic
```

### 3. 运行部署脚本

```bash
# 进入项目目录
cd /tmp/stic

# 给脚本执行权限
chmod +x deploy.sh

# 运行部署脚本
sudo bash deploy.sh
```

部署脚本会：
- 自动安装依赖
- 创建应用用户和目录
- 配置数据库（SQLite 或 PostgreSQL）
- 设置 Python 虚拟环境
- 配置 Gunicorn 和 Nginx
- 启动服务

### 4. 配置域名（可选）

如果有域名，编辑 Nginx 配置：

```bash
sudo nano /etc/nginx/sites-available/stic
```

将 `server_name _;` 改为 `server_name your-domain.com;`

然后配置 SSL 证书：

```bash
sudo apt-get install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

## 手动部署

如果自动部署脚本不适用，可以按照以下步骤手动部署。

### 1. 系统准备

```bash
# 更新系统
sudo apt-get update
sudo apt-get upgrade -y

# 安装基础工具
sudo apt-get install -y curl wget git build-essential python3 python3-pip python3-venv python3-dev nginx
```

### 2. 创建应用用户

```bash
sudo useradd -r -s /bin/bash -d /opt/stic -m stic
```

### 3. 部署代码

```bash
# 创建应用目录
sudo mkdir -p /opt/stic
sudo chown stic:stic /opt/stic

# 复制代码（以您的方式上传代码到服务器）
# 然后设置权限
sudo chown -R stic:stic /opt/stic
```

### 4. 配置 Python 环境

```bash
# 切换到应用用户
sudo -u stic bash

# 进入应用目录
cd /opt/stic

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install --upgrade pip
pip install -r requirements.txt

# 退出虚拟环境
deactivate
exit
```

### 5. 配置环境变量

```bash
# 生成 SECRET_KEY
SECRET_KEY=$(openssl rand -hex 32)

# 创建 .env 文件
sudo -u stic cat > /opt/stic/.env <<EOF
SECRET_KEY=$SECRET_KEY
FLASK_ENV=production
FLASK_APP=app.py
DATABASE_URL=sqlite:////opt/stic/competition.db
UPLOAD_FOLDER=/opt/stic/uploads
CERTIFICATE_FOLDER=/opt/stic/certificates
EOF

# 设置权限
sudo chmod 600 /opt/stic/.env
```

### 6. 初始化数据库

```bash
sudo -u stic bash -c "cd /opt/stic && source venv/bin/activate && export \$(cat .env | xargs) && python init_db.py"
```

### 7. 配置 Gunicorn

复制 `deploy/gunicorn_config.py` 到 `/opt/stic/gunicorn_config.py`

### 8. 创建 Systemd 服务

复制 `deploy/stic.service` 到 `/etc/systemd/system/stic.service`

```bash
sudo systemctl daemon-reload
sudo systemctl enable stic
sudo systemctl start stic
```

### 9. 配置 Nginx

复制 `deploy/nginx.conf` 到 `/etc/nginx/sites-available/stic`

```bash
sudo ln -s /etc/nginx/sites-available/stic /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx
```

### 10. 配置防火墙

```bash
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw --force enable
```

## 配置说明

### 数据库选择

#### SQLite（默认，适合小规模）

无需额外配置，数据库文件位于 `/opt/stic/competition.db`

#### PostgreSQL（推荐生产环境）

1. 安装 PostgreSQL：

```bash
sudo apt-get install postgresql postgresql-contrib libpq-dev
```

2. 初始化数据库：

```bash
sudo -u postgres bash deploy/init_postgresql.sh
```

3. 修改 `.env` 文件：

```bash
DATABASE_URL=postgresql://stic_user:your_password@localhost/stic_db
```

4. 重新初始化数据库：

```bash
sudo -u stic bash -c "cd /opt/stic && source venv/bin/activate && export \$(cat .env | xargs) && python init_db.py"
```

### 目录结构

```
/opt/stic/
├── app.py                 # 应用主文件
├── config.py              # 配置文件
├── models.py              # 数据模型
├── .env                   # 环境变量（敏感信息）
├── gunicorn_config.py     # Gunicorn 配置
├── venv/                  # Python 虚拟环境
├── uploads/               # 上传文件目录
├── certificates/          # 证书目录
├── logs/                  # 日志目录
│   ├── gunicorn_access.log
│   ├── gunicorn_error.log
│   ├── nginx_access.log
│   └── nginx_error.log
└── backups/               # 备份目录
```

### 环境变量说明

| 变量名 | 说明 | 必需 |
|--------|------|------|
| `SECRET_KEY` | Flask 密钥，用于加密 session | 是 |
| `FLASK_ENV` | 环境模式（production/development） | 是 |
| `DATABASE_URL` | 数据库连接字符串 | 是 |
| `UPLOAD_FOLDER` | 上传文件目录 | 是 |
| `CERTIFICATE_FOLDER` | 证书目录 | 是 |

## 服务管理

### 查看服务状态

```bash
# 查看应用服务状态
sudo systemctl status stic

# 查看 Nginx 状态
sudo systemctl status nginx
```

### 启动/停止/重启服务

```bash
# 应用服务
sudo systemctl start stic
sudo systemctl stop stic
sudo systemctl restart stic

# Nginx
sudo systemctl restart nginx
```

### 查看日志

```bash
# 应用日志
sudo journalctl -u stic -f

# Gunicorn 日志
sudo tail -f /opt/stic/logs/gunicorn_error.log
sudo tail -f /opt/stic/logs/gunicorn_access.log

# Nginx 日志
sudo tail -f /opt/stic/logs/nginx_error.log
sudo tail -f /opt/stic/logs/nginx_access.log
```

### 更新代码

```bash
# 1. 停止服务
sudo systemctl stop stic

# 2. 备份当前代码
sudo -u stic cp -r /opt/stic /opt/stic.backup.$(date +%Y%m%d)

# 3. 更新代码（根据您的部署方式）
# git pull 或 scp 上传新文件

# 4. 更新依赖（如果有新依赖）
sudo -u stic bash -c "cd /opt/stic && source venv/bin/activate && pip install -r requirements.txt"

# 5. 运行数据库迁移（如果有）
# sudo -u stic bash -c "cd /opt/stic && source venv/bin/activate && python migrate_db.py"

# 6. 重启服务
sudo systemctl start stic
```

## 备份与恢复

### 自动备份

备份脚本已配置为每天凌晨 2 点自动运行。也可以手动执行：

```bash
sudo -u stic /opt/stic/backup.sh
```

### 手动备份

```bash
# 复制备份脚本
sudo cp deploy/backup.sh /opt/stic/backup.sh
sudo chmod +x /opt/stic/backup.sh
sudo chown stic:stic /opt/stic/backup.sh

# 执行备份
sudo -u stic /opt/stic/backup.sh
```

### 恢复备份

```bash
# 复制恢复脚本
sudo cp deploy/restore.sh /opt/stic/restore.sh
sudo chmod +x /opt/stic/restore.sh

# 查看可用备份
ls -lh /opt/stic/backups/

# 恢复备份
sudo /opt/stic/restore.sh backup_20231201_120000.tar.gz
```

## 故障排查

### 服务无法启动

1. 检查服务状态：

```bash
sudo systemctl status stic
```

2. 查看详细日志：

```bash
sudo journalctl -u stic -n 50
```

3. 检查配置文件：

```bash
# 检查 .env 文件
sudo cat /opt/stic/.env

# 检查 Gunicorn 配置
sudo cat /opt/stic/gunicorn_config.py
```

### 数据库连接失败

1. 检查数据库服务（PostgreSQL）：

```bash
sudo systemctl status postgresql
```

2. 测试数据库连接：

```bash
sudo -u stic bash -c "cd /opt/stic && source venv/bin/activate && python -c \"from app import app; from models import db; app.app_context().push(); db.engine.connect()\""
```

### Nginx 502 错误

1. 检查 Gunicorn 是否运行：

```bash
sudo systemctl status stic
ps aux | grep gunicorn
```

2. 检查端口是否监听：

```bash
sudo netstat -tlnp | grep 8000
```

3. 检查 Nginx 配置：

```bash
sudo nginx -t
```

### 文件上传失败

1. 检查目录权限：

```bash
ls -la /opt/stic/uploads
```

2. 检查 Nginx 配置中的 `client_max_body_size`

3. 检查应用配置中的 `MAX_CONTENT_LENGTH`

### 性能优化

1. 调整 Gunicorn 工作进程数：

编辑 `/opt/stic/gunicorn_config.py`，修改 `workers` 参数

2. 启用 Nginx 缓存：

在 Nginx 配置中添加缓存设置

3. 使用 PostgreSQL 替代 SQLite（生产环境推荐）

## 安全建议

1. **修改默认密码**：初始化后立即修改所有测试账户密码

2. **使用强 SECRET_KEY**：确保 `.env` 文件中的 `SECRET_KEY` 足够强

3. **配置 SSL**：生产环境必须使用 HTTPS

4. **定期备份**：确保备份脚本正常运行

5. **更新系统**：定期更新系统和依赖包

6. **限制访问**：配置防火墙，只开放必要端口

7. **文件权限**：确保敏感文件权限正确（`.env` 应为 600）

## 联系支持

如遇到问题，请检查：
1. 日志文件
2. 服务状态
3. 配置文件
4. 系统资源（磁盘空间、内存）

---

**注意**：首次部署后，请务必修改所有测试账户的默认密码！

