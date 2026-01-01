# 快速部署指南

## 部署位置

**推荐路径：** `/var/www/stic`

## 首次部署步骤

### 1. 在服务器上准备环境

```bash
# SSH登录服务器
ssh user@your-server-ip

# 更新系统
sudo apt update && sudo apt upgrade -y

# 安装必要软件
sudo apt install -y python3 python3-pip python3-venv nginx git
```

### 2. 上传项目文件到服务器

**在本地Windows/Mac机器上：**

```bash
# 方法1：使用SCP上传（推荐）
# 先压缩项目（排除不必要的文件）
tar --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='venv' \
    --exclude='.git' \
    --exclude='competition.db' \
    --exclude='uploads' \
    --exclude='certificates' \
    --exclude='*.log' \
    -czf stic.tar.gz .

# 上传到服务器
scp stic.tar.gz user@your-server-ip:/tmp/

# 方法2：使用Git（如果项目在Git仓库）
# 在服务器上执行：
sudo git clone <your-repo-url> /var/www/stic
```

### 3. 在服务器上部署

```bash
# SSH登录服务器
ssh user@your-server-ip

# 解压文件（如果使用方法1）
sudo mkdir -p /var/www/stic
sudo tar -xzf /tmp/stic.tar.gz -C /var/www/stic

# 设置权限
sudo chown -R www-data:www-data /var/www/stic
sudo chmod +x /var/www/stic/deploy.sh

# 运行初始化脚本
cd /var/www/stic
sudo ./deploy.sh init
```

### 4. 配置环境变量

```bash
sudo nano /var/www/stic/.env
```

添加：
```
SECRET_KEY=your-super-secret-key-change-this
```

### 5. 初始化数据库

```bash
cd /var/www/stic
source venv/bin/activate
python init_db.py
python migrate_db.py
deactivate
```

### 6. 设置systemd服务

```bash
sudo cp /var/www/stic/stic.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable stic.service
sudo systemctl start stic.service
sudo systemctl status stic.service
```

### 7. 配置Nginx

```bash
# 编辑nginx.conf，修改server_name
sudo nano /var/www/stic/nginx.conf
# 将 your-domain.com 改为实际域名或IP

# 复制配置
sudo cp /var/www/stic/nginx.conf /etc/nginx/sites-available/stic
sudo ln -s /etc/nginx/sites-available/stic /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default

# 测试并重启
sudo nginx -t
sudo systemctl restart nginx
```

### 8. 配置防火墙

```bash
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 22/tcp
sudo ufw enable
```

## 更新代码步骤

### 方法一：使用部署脚本（推荐）

```bash
# SSH登录服务器
ssh user@your-server-ip

# 进入项目目录
cd /var/www/stic

# 先上传新代码文件（使用SCP或Git）
# 然后运行更新脚本
sudo ./deploy.sh update
```

### 方法二：手动更新

1. **上传新代码到服务器**（使用SCP或Git）

2. **在服务器上执行：**

```bash
cd /var/www/stic

# 备份数据
sudo mkdir -p backup/$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="backup/$(date +%Y%m%d_%H%M%S)"
sudo cp competition.db ${BACKUP_DIR}/
sudo cp -r uploads ${BACKUP_DIR}/
sudo cp -r certificates ${BACKUP_DIR}/

# 如果使用Git，拉取代码
sudo git pull origin main

# 更新依赖
source venv/bin/activate
pip install -r requirements.txt

# 运行数据库迁移
python migrate_db.py

deactivate

# 重启服务
sudo systemctl restart stic.service
sudo systemctl status stic.service
```

## 需要上传的文件清单

必须上传的文件：
- ✅ `app.py`
- ✅ `config.py`
- ✅ `models.py`
- ✅ `forms.py`
- ✅ `init_db.py`
- ✅ `migrate_db.py`
- ✅ `requirements.txt`
- ✅ `routes/` 目录（所有Python文件）
- ✅ `templates/` 目录（所有HTML文件）
- ✅ `static/` 目录（所有CSS/JS文件）
- ✅ `utils/` 目录（所有Python文件）
- ✅ `deploy.sh`
- ✅ `stic.service`
- ✅ `nginx.conf`
- ✅ `DEPLOY.md`
- ✅ `.gitignore`

不需要上传的文件：
- ❌ `venv/` （在服务器上重新创建）
- ❌ `__pycache__/` 
- ❌ `*.pyc`
- ❌ `competition.db` （在服务器上初始化）
- ❌ `uploads/` （在服务器上创建空目录）
- ❌ `certificates/` （在服务器上创建空目录）
- ❌ `*.log`

## 常用命令

```bash
# 查看服务状态
sudo systemctl status stic.service

# 查看日志
sudo journalctl -u stic.service -f

# 重启服务
sudo systemctl restart stic.service

# 查看应用日志
tail -f /var/www/stic/logs/error.log

# 测试应用
curl http://localhost:8000
```

## 故障排查

如果服务无法启动：
1. 检查日志：`sudo journalctl -u stic.service -n 50`
2. 检查权限：`ls -la /var/www/stic`
3. 手动测试：`cd /var/www/stic && source venv/bin/activate && gunicorn --bind 127.0.0.1:8000 app:app`

如果502错误：
1. 检查Gunicorn是否运行：`curl http://localhost:8000`
2. 检查Nginx日志：`sudo tail -f /var/log/nginx/stic_error.log`

详细说明请参考 `DEPLOY.md`

