# 部署文档

本文档说明如何将STIC项目部署到Ubuntu服务器。

## 一、部署位置

推荐部署路径：`/var/www/stic`

目录结构：
```
/var/www/stic/
├── app.py                 # 主应用文件
├── config.py             # 配置文件
├── models.py             # 数据库模型
├── requirements.txt      # Python依赖
├── venv/                 # Python虚拟环境
├── competition.db        # SQLite数据库文件
├── uploads/              # 上传文件目录
├── certificates/         # 证书文件目录
├── logs/                 # 日志目录
├── backup/               # 备份目录
├── routes/               # 路由模块
├── templates/            # 模板文件
├── static/               # 静态文件
└── utils/                # 工具模块
```

## 二、首次部署流程

### 1. 服务器准备

#### 1.1 更新系统
```bash
sudo apt update
sudo apt upgrade -y
```

#### 1.2 安装必要的软件
```bash
# 安装Python 3.8+和pip
sudo apt install -y python3 python3-pip python3-venv

# 安装Nginx（反向代理）
sudo apt install -y nginx

# 安装Git（如果使用Git部署）
sudo apt install -y git

# 安装其他工具
sudo apt install -y curl wget vim
```

#### 1.3 创建应用用户（可选，推荐使用www-data）
```bash
# 使用系统默认的www-data用户，无需创建
# 如果需要创建新用户：
# sudo useradd -r -s /bin/bash -m -d /var/www/stic stic
```

### 2. 上传项目文件

#### 方法一：使用SCP上传（推荐）
在本地Windows/Mac机器上执行：
```bash
# 压缩项目（排除不必要的文件）
tar --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='venv' \
    --exclude='.git' \
    --exclude='competition.db' \
    --exclude='uploads' \
    --exclude='certificates' \
    -czf stic.tar.gz .

# 上传到服务器
scp stic.tar.gz user@your-server-ip:/tmp/

# SSH登录服务器
ssh user@your-server-ip
```

#### 方法二：使用Git（如果项目在Git仓库）
```bash
# 在服务器上克隆
sudo git clone <your-repo-url> /var/www/stic
sudo git checkout <branch-name>
```

### 3. 部署脚本初始化

```bash
# 解压文件（如果使用方法一）
cd /tmp
tar -xzf stic.tar.gz -C /var/www/stic

# 设置权限
sudo chown -R www-data:www-data /var/www/stic
sudo chmod +x /var/www/stic/deploy.sh

# 运行初始化脚本
cd /var/www/stic
sudo ./deploy.sh init
```

### 4. 配置环境变量

创建环境变量文件 `.env`（如果需要）：
```bash
sudo nano /var/www/stic/.env
```

添加以下内容（根据实际情况修改）：
```bash
# 生产环境密钥（务必修改！）
SECRET_KEY=your-super-secret-key-here-change-this

# 数据库配置（如果使用SQLite，可留空使用默认配置）
# DATABASE_URL=sqlite:///var/www/stic/competition.db

# AI配置（可选）
QWEN_API_KEY=your-api-key-here
```

### 5. 初始化数据库

```bash
cd /var/www/stic
source venv/bin/activate
python init_db.py
python migrate_db.py  # 如果需要迁移
deactivate
```

### 6. 创建systemd服务

```bash
# 复制服务文件
sudo cp /var/www/stic/stic.service /etc/systemd/system/

# 修改服务文件中的路径（如果需要）
sudo nano /etc/systemd/system/stic.service

# 重新加载systemd配置
sudo systemctl daemon-reload

# 启用服务（开机自启）
sudo systemctl enable stic.service

# 启动服务
sudo systemctl start stic.service

# 检查服务状态
sudo systemctl status stic.service

# 查看日志
sudo journalctl -u stic.service -f
```

### 7. 配置Nginx

```bash
# 复制Nginx配置
sudo cp /var/www/stic/nginx.conf /etc/nginx/sites-available/stic

# 编辑配置文件，修改server_name
sudo nano /etc/nginx/sites-available/stic
# 将 your-domain.com 替换为实际域名或IP

# 创建符号链接启用配置
sudo ln -s /etc/nginx/sites-available/stic /etc/nginx/sites-enabled/

# 删除默认配置（可选）
sudo rm /etc/nginx/sites-enabled/default

# 测试Nginx配置
sudo nginx -t

# 重启Nginx
sudo systemctl restart nginx

# 检查Nginx状态
sudo systemctl status nginx
```

### 8. 配置防火墙

```bash
# 允许HTTP和HTTPS流量
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# 如果使用SSH，确保允许SSH
sudo ufw allow 22/tcp

# 启用防火墙
sudo ufw enable

# 查看防火墙状态
sudo ufw status
```

### 9. 配置SSL证书（可选，推荐）

使用Let's Encrypt免费SSL证书：

```bash
# 安装Certbot
sudo apt install -y certbot python3-certbot-nginx

# 获取证书（替换your-domain.com和your-email@example.com）
sudo certbot --nginx -d your-domain.com -d www.your-domain.com --email your-email@example.com --agree-tos --non-interactive

# 自动续期
sudo certbot renew --dry-run
```

## 三、更新代码流程

### 方法一：使用部署脚本（推荐）

```bash
# SSH登录服务器
ssh user@your-server-ip

# 进入项目目录
cd /var/www/stic

# 运行更新脚本
sudo ./deploy.sh update
```

### 方法二：手动更新

#### 1. 备份数据

```bash
cd /var/www/stic
sudo mkdir -p backup/$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="backup/$(date +%Y%m%d_%H%M%S)"

# 备份数据库
sudo cp competition.db ${BACKUP_DIR}/

# 备份上传文件
sudo cp -r uploads ${BACKUP_DIR}/

# 备份证书
sudo cp -r certificates ${BACKUP_DIR}/
```

#### 2. 更新代码

**如果使用Git：**
```bash
cd /var/www/stic
sudo git pull origin main  # 或你的分支名
```

**如果使用文件上传：**
```bash
# 在本地压缩新代码
tar --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='venv' \
    --exclude='.git' \
    --exclude='competition.db' \
    --exclude='uploads' \
    --exclude='certificates' \
    -czf stic-update.tar.gz .

# 上传到服务器
scp stic-update.tar.gz user@your-server-ip:/tmp/

# 在服务器上解压
ssh user@your-server-ip
cd /var/www/stic
sudo tar -xzf /tmp/stic-update.tar.gz
```

#### 3. 更新依赖和数据库

```bash
cd /var/www/stic
source venv/bin/activate

# 更新Python依赖
pip install --upgrade pip
pip install -r requirements.txt

# 运行数据库迁移（如果需要）
python migrate_db.py

deactivate
```

#### 4. 重启服务

```bash
sudo systemctl restart stic.service
sudo systemctl status stic.service
```

#### 5. 检查服务

```bash
# 查看服务日志
sudo journalctl -u stic.service -n 50

# 查看应用日志
tail -f /var/www/stic/logs/error.log

# 测试访问
curl http://localhost:8000
```

## 四、常用运维命令

### 服务管理

```bash
# 启动服务
sudo systemctl start stic.service

# 停止服务
sudo systemctl stop stic.service

# 重启服务
sudo systemctl restart stic.service

# 查看服务状态
sudo systemctl status stic.service

# 查看服务日志
sudo journalctl -u stic.service -f

# 禁用开机自启
sudo systemctl disable stic.service

# 启用开机自启
sudo systemctl enable stic.service
```

### 日志查看

```bash
# 应用日志
tail -f /var/www/stic/logs/error.log
tail -f /var/www/stic/logs/access.log

# Nginx日志
tail -f /var/log/nginx/stic_error.log
tail -f /var/log/nginx/stic_access.log

# Systemd日志
sudo journalctl -u stic.service -n 100
```

### 数据库备份

```bash
# 手动备份数据库
cd /var/www/stic
sudo cp competition.db backup/competition_$(date +%Y%m%d_%H%M%S).db

# 定期备份（添加到crontab）
sudo crontab -e
# 添加以下行（每天凌晨2点备份）
0 2 * * * cp /var/www/stic/competition.db /var/www/stic/backup/competition_$(date +\%Y\%m\%d).db
```

### 性能监控

```bash
# 查看进程
ps aux | grep gunicorn

# 查看端口占用
sudo netstat -tlnp | grep 8000

# 查看系统资源
htop
# 或
top
```

## 五、故障排查

### 服务无法启动

1. 检查服务状态：
```bash
sudo systemctl status stic.service
```

2. 查看详细日志：
```bash
sudo journalctl -u stic.service -n 100
```

3. 手动测试启动：
```bash
cd /var/www/stic
source venv/bin/activate
gunicorn --bind 127.0.0.1:8000 app:app
```

### 502 Bad Gateway

1. 检查Gunicorn服务是否运行：
```bash
sudo systemctl status stic.service
curl http://localhost:8000
```

2. 检查Nginx配置：
```bash
sudo nginx -t
```

3. 查看Nginx错误日志：
```bash
sudo tail -f /var/log/nginx/stic_error.log
```

### 数据库错误

1. 检查数据库文件权限：
```bash
ls -la /var/www/stic/competition.db
sudo chown www-data:www-data /var/www/stic/competition.db
```

2. 运行数据库迁移：
```bash
cd /var/www/stic
source venv/bin/activate
python migrate_db.py
```

### 文件上传错误

1. 检查上传目录权限：
```bash
ls -la /var/www/stic/uploads
sudo chown -R www-data:www-data /var/www/stic/uploads
sudo chmod -R 775 /var/www/stic/uploads
```

## 六、安全建议

1. **修改默认密钥**：在生产环境中务必修改 `SECRET_KEY`
2. **使用HTTPS**：配置SSL证书启用HTTPS
3. **定期备份**：设置自动备份数据库和上传文件
4. **更新系统**：定期更新系统和依赖包
5. **防火墙配置**：只开放必要的端口
6. **限制SSH访问**：使用密钥认证，禁用密码登录
7. **监控日志**：定期检查日志文件，发现异常及时处理

## 七、性能优化

1. **增加Gunicorn工作进程**：根据CPU核心数调整workers数量
2. **启用Nginx缓存**：对静态文件启用缓存
3. **数据库优化**：如果数据量大，考虑迁移到PostgreSQL
4. **CDN**：对静态资源使用CDN加速

## 八、联系方式

如有问题，请联系系统管理员。

