# 部署文件说明

本目录包含 STIC 项目的所有部署相关文件。

## 文件列表

### 核心部署文件

- **deploy.sh** - 自动部署脚本（一键部署）
- **DEPLOY.md** - 详细部署文档

### 配置文件

- **nginx.conf** - Nginx 反向代理配置
- **stic.service** - Systemd 服务单元文件
- **gunicorn_config.py** - Gunicorn 应用服务器配置
- **env.template** - 环境变量配置模板

### 数据库脚本

- **init_postgresql.sh** - PostgreSQL 数据库初始化脚本

### 备份脚本

- **backup.sh** - 自动备份脚本
- **restore.sh** - 备份恢复脚本

## 快速开始

### 方法1: 使用自动部署脚本（推荐）

```bash
# 1. 上传项目代码到服务器
# 2. 进入项目目录
cd /path/to/STIC

# 3. 运行部署脚本
sudo bash deploy.sh
```

### 方法2: 手动部署

参考 `DEPLOY.md` 文档中的手动部署步骤。

## 文件使用说明

### 1. deploy.sh

主部署脚本，自动化整个部署过程。

**使用方法：**
```bash
sudo bash deploy.sh
```

脚本会提示输入：
- 应用域名（可选）
- 数据库类型（sqlite/postgresql）
- 数据库密码（如果使用 PostgreSQL）

### 2. nginx.conf

Nginx 配置文件，需要复制到 `/etc/nginx/sites-available/stic`

**使用方法：**
```bash
sudo cp deploy/nginx.conf /etc/nginx/sites-available/stic
sudo ln -s /etc/nginx/sites-available/stic /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

**注意：** 需要修改 `server_name` 为您的域名，或使用 `_` 表示所有域名。

### 3. stic.service

Systemd 服务文件，用于管理 Gunicorn 进程。

**使用方法：**
```bash
sudo cp deploy/stic.service /etc/systemd/system/stic.service
sudo systemctl daemon-reload
sudo systemctl enable stic
sudo systemctl start stic
```

### 4. gunicorn_config.py

Gunicorn 配置文件，定义工作进程数、日志等。

**使用方法：**
```bash
sudo cp deploy/gunicorn_config.py /opt/stic/gunicorn_config.py
sudo chown stic:stic /opt/stic/gunicorn_config.py
```

### 5. env.template

环境变量模板，需要复制为 `.env` 并修改。

**使用方法：**
```bash
sudo cp deploy/env.template /opt/stic/.env
sudo nano /opt/stic/.env  # 编辑配置
sudo chown stic:stic /opt/stic/.env
sudo chmod 600 /opt/stic/.env
```

### 6. init_postgresql.sh

PostgreSQL 数据库初始化脚本。

**使用方法：**
```bash
sudo -u postgres bash deploy/init_postgresql.sh
```

### 7. backup.sh

自动备份脚本，备份数据库和文件。

**使用方法：**
```bash
# 复制到应用目录
sudo cp deploy/backup.sh /opt/stic/backup.sh
sudo chmod +x /opt/stic/backup.sh
sudo chown stic:stic /opt/stic/backup.sh

# 手动执行
sudo -u stic /opt/stic/backup.sh

# 或添加到 crontab（每天凌晨2点）
(crontab -u stic -l 2>/dev/null; echo "0 2 * * * /opt/stic/backup.sh") | crontab -u stic -
```

### 8. restore.sh

备份恢复脚本。

**使用方法：**
```bash
# 复制到应用目录
sudo cp deploy/restore.sh /opt/stic/restore.sh
sudo chmod +x /opt/stic/restore.sh

# 查看可用备份
ls -lh /opt/stic/backups/

# 恢复备份
sudo /opt/stic/restore.sh backup_20231201_120000.tar.gz
```

## 部署后检查清单

- [ ] 服务正常运行：`sudo systemctl status stic`
- [ ] Nginx 正常运行：`sudo systemctl status nginx`
- [ ] 可以访问网站
- [ ] 日志文件正常生成
- [ ] 文件上传功能正常
- [ ] 数据库连接正常
- [ ] 备份脚本已配置
- [ ] 已修改默认密码
- [ ] SSL 证书已配置（生产环境）

## 常见问题

### 权限问题

确保所有文件的所有者是 `stic` 用户：

```bash
sudo chown -R stic:stic /opt/stic
```

### 端口冲突

如果 8000 端口被占用，修改：
- `gunicorn_config.py` 中的 `bind` 参数
- `nginx.conf` 中的 `proxy_pass` 地址

### 数据库迁移

从 SQLite 迁移到 PostgreSQL：

1. 运行 `init_postgresql.sh` 创建数据库
2. 修改 `.env` 中的 `DATABASE_URL`
3. 重新运行 `init_db.py`

## 技术支持

遇到问题请查看：
1. `DEPLOY.md` 中的故障排查部分
2. 服务日志：`sudo journalctl -u stic -f`
3. Nginx 日志：`sudo tail -f /opt/stic/logs/nginx_error.log`

