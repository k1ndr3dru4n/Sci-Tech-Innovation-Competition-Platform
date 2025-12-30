#!/bin/bash

###############################################################################
# STIC 项目自动部署脚本
# 适用于 Ubuntu 22.04 UEFI 服务器
# 使用方法: sudo bash deploy.sh
###############################################################################

set -e  # 遇到错误立即退出

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 配置变量（可根据实际情况修改）
APP_NAME="stic"
APP_USER="stic"
APP_DIR="/opt/stic"
APP_DOMAIN=""  # 留空则不配置域名，使用IP访问
DB_TYPE="sqlite"  # sqlite 或 postgresql
DB_NAME="stic_db"
DB_USER="stic_user"
DB_PASSWORD=""  # 如果使用 PostgreSQL，需要设置密码
GUNICORN_WORKERS=4
GUNICORN_PORT=8000

# 打印带颜色的消息
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查是否为 root 用户
check_root() {
    if [ "$EUID" -ne 0 ]; then 
        print_error "请使用 sudo 运行此脚本"
        exit 1
    fi
}

# 更新系统
update_system() {
    print_info "更新系统包..."
    apt-get update
    apt-get upgrade -y
    apt-get install -y curl wget git build-essential
}

# 安装 Python 和 pip
install_python() {
    print_info "安装 Python 3 和 pip..."
    apt-get install -y python3 python3-pip python3-venv python3-dev
    
    # 安装 PostgreSQL 开发库（如果使用 PostgreSQL）
    if [ "$DB_TYPE" = "postgresql" ]; then
        apt-get install -y libpq-dev postgresql postgresql-contrib
    fi
}

# 创建应用用户
create_app_user() {
    print_info "创建应用用户: $APP_USER"
    if id "$APP_USER" &>/dev/null; then
        print_warn "用户 $APP_USER 已存在，跳过创建"
    else
        useradd -r -s /bin/bash -d "$APP_DIR" -m "$APP_USER"
        print_info "用户 $APP_USER 创建成功"
    fi
}

# 创建应用目录
create_app_directories() {
    print_info "创建应用目录..."
    mkdir -p "$APP_DIR"
    mkdir -p "$APP_DIR/uploads"
    mkdir -p "$APP_DIR/certificates"
    mkdir -p "$APP_DIR/logs"
    mkdir -p "$APP_DIR/backups"
    
    # 设置权限
    chown -R "$APP_USER:$APP_USER" "$APP_DIR"
    chmod 755 "$APP_DIR"
    chmod 755 "$APP_DIR/uploads"
    chmod 755 "$APP_DIR/certificates"
}

# 配置 PostgreSQL 数据库
setup_postgresql() {
    if [ "$DB_TYPE" != "postgresql" ]; then
        return
    fi
    
    print_info "配置 PostgreSQL 数据库..."
    
    # 生成随机密码（如果未设置）
    if [ -z "$DB_PASSWORD" ]; then
        DB_PASSWORD=$(openssl rand -base64 32)
        print_warn "数据库密码已自动生成: $DB_PASSWORD"
        print_warn "请保存此密码到安全位置！"
    fi
    
    # 切换到 postgres 用户执行数据库命令
    sudo -u postgres psql <<EOF
-- 创建数据库
CREATE DATABASE $DB_NAME;

-- 创建用户
CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';

-- 授权
GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;
ALTER USER $DB_USER CREATEDB;

-- 退出
\q
EOF
    
    print_info "PostgreSQL 数据库配置完成"
    print_info "数据库名: $DB_NAME"
    print_info "数据库用户: $DB_USER"
}

# 部署应用代码
deploy_application() {
    print_info "部署应用代码..."
    
    # 检查是否已有代码
    if [ -f "$APP_DIR/app.py" ]; then
        print_warn "检测到已有代码"
        read -p "是否备份现有代码？(y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            BACKUP_NAME="old_$(date +%Y%m%d_%H%M%S)"
            mkdir -p "$APP_DIR/backups/$BACKUP_NAME"
            # 备份代码文件（排除 venv, logs, backups 等目录）
            find "$APP_DIR" -maxdepth 1 -type f -exec cp {} "$APP_DIR/backups/$BACKUP_NAME/" \; 2>/dev/null || true
            find "$APP_DIR" -maxdepth 1 -type d \( -name "routes" -o -name "templates" -o -name "static" -o -name "utils" \) -exec cp -r {} "$APP_DIR/backups/$BACKUP_NAME/" \; 2>/dev/null || true
            print_info "代码已备份到 $APP_DIR/backups/$BACKUP_NAME"
        fi
    else
        # 提示用户上传代码
        print_warn "未检测到应用代码"
        print_warn "请将项目代码复制到 $APP_DIR 目录"
        print_warn "可以使用以下命令："
        print_warn "  scp -r /path/to/STIC/* $APP_USER@服务器IP:$APP_DIR/"
        print_warn "或者使用 git clone（如果有仓库）"
        
        read -p "代码已上传？(y/n): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_error "请先上传代码后再运行此脚本"
            exit 1
        fi
        
        # 验证关键文件是否存在
        if [ ! -f "$APP_DIR/app.py" ]; then
            print_error "未找到 app.py 文件，请确认代码已正确上传"
            exit 1
        fi
    fi
    
    # 设置代码目录权限
    chown -R "$APP_USER:$APP_USER" "$APP_DIR"
    print_info "代码部署完成"
}

# 创建 Python 虚拟环境
setup_venv() {
    print_info "创建 Python 虚拟环境..."
    
    sudo -u "$APP_USER" bash <<EOF
cd "$APP_DIR"
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
EOF
    
    print_info "虚拟环境创建完成"
}

# 配置环境变量
setup_env() {
    print_info "配置环境变量..."
    
    # 生成 SECRET_KEY
    SECRET_KEY=$(openssl rand -hex 32)
    
    # 构建数据库 URI
    if [ "$DB_TYPE" = "postgresql" ]; then
        DATABASE_URL="postgresql://$DB_USER:$DB_PASSWORD@localhost/$DB_NAME"
    else
        DATABASE_URL="sqlite:///$APP_DIR/competition.db"
    fi
    
    # 创建 .env 文件
    cat > "$APP_DIR/.env" <<EOF
# Flask 配置
SECRET_KEY=$SECRET_KEY
FLASK_ENV=production
FLASK_APP=app.py

# 数据库配置
DATABASE_URL=$DATABASE_URL

# 应用配置
UPLOAD_FOLDER=$APP_DIR/uploads
CERTIFICATE_FOLDER=$APP_DIR/certificates
EOF
    
    chown "$APP_USER:$APP_USER" "$APP_DIR/.env"
    chmod 600 "$APP_DIR/.env"
    
    print_info "环境变量配置完成"
}

# 初始化数据库
init_database() {
    print_info "初始化数据库..."
    
    sudo -u "$APP_USER" bash <<EOF
cd "$APP_DIR"
source venv/bin/activate
export \$(cat .env | xargs)
python init_db.py
EOF
    
    print_info "数据库初始化完成"
}

# 配置 Gunicorn
setup_gunicorn() {
    print_info "配置 Gunicorn..."
    
    # 创建 Gunicorn 配置文件
    cat > "$APP_DIR/gunicorn_config.py" <<EOF
# Gunicorn 配置文件
import multiprocessing
import os

# 服务器 socket
bind = "127.0.0.1:$GUNICORN_PORT"
backlog = 2048

# 工作进程
workers = $GUNICORN_WORKERS
worker_class = "sync"
worker_connections = 1000
timeout = 30
keepalive = 2

# 日志
accesslog = "$APP_DIR/logs/gunicorn_access.log"
errorlog = "$APP_DIR/logs/gunicorn_error.log"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'

# 进程命名
proc_name = "$APP_NAME"

# 服务器机制
daemon = False
pidfile = "$APP_DIR/gunicorn.pid"
umask = 0
user = "$APP_USER"
group = "$APP_USER"
tmp_upload_dir = None

# SSL (如果需要)
# keyfile = None
# certfile = None
EOF
    
    chown "$APP_USER:$APP_USER" "$APP_DIR/gunicorn_config.py"
    
    print_info "Gunicorn 配置完成"
}

# 创建 systemd 服务
create_systemd_service() {
    print_info "创建 systemd 服务..."
    
    cat > "/etc/systemd/system/$APP_NAME.service" <<EOF
[Unit]
Description=STIC Gunicorn daemon
After=network.target

[Service]
User=$APP_USER
Group=$APP_USER
WorkingDirectory=$APP_DIR
Environment="PATH=$APP_DIR/venv/bin"
EnvironmentFile=$APP_DIR/.env
ExecStart=$APP_DIR/venv/bin/gunicorn \\
    --config $APP_DIR/gunicorn_config.py \\
    app:app

Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF
    
    systemctl daemon-reload
    systemctl enable "$APP_NAME"
    
    print_info "Systemd 服务创建完成"
}

# 配置 Nginx
setup_nginx() {
    print_info "安装和配置 Nginx..."
    
    apt-get install -y nginx
    
    # 创建 Nginx 配置文件
    cat > "/etc/nginx/sites-available/$APP_NAME" <<EOF
# STIC 应用 Nginx 配置
server {
    listen 80;
    server_name ${APP_DOMAIN:-_};
    
    client_max_body_size 16M;
    
    # 访问日志
    access_log $APP_DIR/logs/nginx_access.log;
    error_log $APP_DIR/logs/nginx_error.log;
    
    # 静态文件
    location /static/ {
        alias $APP_DIR/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
    
    # 上传文件
    location /uploads/ {
        alias $APP_DIR/uploads/;
        expires 7d;
        add_header Cache-Control "public";
    }
    
    # 证书文件
    location /certificates/ {
        alias $APP_DIR/certificates/;
        expires 7d;
        add_header Cache-Control "public";
    }
    
    # 代理到 Gunicorn
    location / {
        proxy_pass http://127.0.0.1:$GUNICORN_PORT;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_redirect off;
        
        # WebSocket 支持（如果需要）
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
EOF
    
    # 启用站点
    ln -sf "/etc/nginx/sites-available/$APP_NAME" "/etc/nginx/sites-enabled/$APP_NAME"
    
    # 删除默认站点
    rm -f /etc/nginx/sites-enabled/default
    
    # 测试 Nginx 配置
    nginx -t
    
    print_info "Nginx 配置完成"
}

# 配置防火墙
setup_firewall() {
    print_info "配置防火墙..."
    
    if command -v ufw &> /dev/null; then
        ufw allow 22/tcp
        ufw allow 80/tcp
        ufw allow 443/tcp
        ufw --force enable
        print_info "UFW 防火墙已配置"
    else
        print_warn "未检测到 UFW，请手动配置防火墙"
    fi
}

# 启动服务
start_services() {
    print_info "启动服务..."
    
    systemctl start "$APP_NAME"
    systemctl restart nginx
    
    # 检查服务状态
    sleep 2
    if systemctl is-active --quiet "$APP_NAME"; then
        print_info "应用服务启动成功"
    else
        print_error "应用服务启动失败，请检查日志: journalctl -u $APP_NAME"
    fi
    
    if systemctl is-active --quiet nginx; then
        print_info "Nginx 启动成功"
    else
        print_error "Nginx 启动失败，请检查日志: journalctl -u nginx"
    fi
}

# 配置 SSL 证书（可选）
setup_ssl() {
    if [ -z "$APP_DOMAIN" ]; then
        print_warn "未设置域名，跳过 SSL 配置"
        return
    fi
    
    print_info "配置 SSL 证书..."
    print_warn "SSL 证书配置需要手动完成，请运行："
    print_warn "  sudo apt-get install certbot python3-certbot-nginx"
    print_warn "  sudo certbot --nginx -d $APP_DOMAIN"
}

# 创建备份脚本
create_backup_script() {
    print_info "创建备份脚本..."
    
    cat > "$APP_DIR/backup.sh" <<'BACKUP_EOF'
#!/bin/bash
# 备份脚本

APP_DIR="/opt/stic"
BACKUP_DIR="$APP_DIR/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="backup_$DATE"

mkdir -p "$BACKUP_DIR/$BACKUP_NAME"

# 备份数据库
if [ -f "$APP_DIR/competition.db" ]; then
    cp "$APP_DIR/competition.db" "$BACKUP_DIR/$BACKUP_NAME/competition.db"
    echo "数据库备份完成"
fi

# 备份上传文件
if [ -d "$APP_DIR/uploads" ]; then
    tar -czf "$BACKUP_DIR/$BACKUP_NAME/uploads.tar.gz" -C "$APP_DIR" uploads
    echo "上传文件备份完成"
fi

# 备份证书
if [ -d "$APP_DIR/certificates" ]; then
    tar -czf "$BACKUP_DIR/$BACKUP_NAME/certificates.tar.gz" -C "$APP_DIR" certificates
    echo "证书备份完成"
fi

# 备份配置文件
cp "$APP_DIR/.env" "$BACKUP_DIR/$BACKUP_NAME/.env" 2>/dev/null || true

echo "备份完成: $BACKUP_DIR/$BACKUP_NAME"

# 删除 30 天前的备份
find "$BACKUP_DIR" -name "backup_*" -type d -mtime +30 -exec rm -rf {} \;
echo "已清理 30 天前的备份"
BACKUP_EOF
    
    chmod +x "$APP_DIR/backup.sh"
    chown "$APP_USER:$APP_USER" "$APP_DIR/backup.sh"
    
    # 添加到 crontab（每天凌晨 2 点备份）
    (crontab -u "$APP_USER" -l 2>/dev/null; echo "0 2 * * * $APP_DIR/backup.sh") | crontab -u "$APP_USER" -
    
    print_info "备份脚本创建完成，已设置每天自动备份"
}

# 主函数
main() {
    print_info "========================================="
    print_info "STIC 项目自动部署脚本"
    print_info "========================================="
    
    check_root
    
    # 询问配置
    echo
    read -p "应用域名（留空使用IP访问）: " APP_DOMAIN
    read -p "数据库类型 (sqlite/postgresql) [默认: sqlite]: " DB_TYPE_INPUT
    DB_TYPE=${DB_TYPE_INPUT:-sqlite}
    
    if [ "$DB_TYPE" = "postgresql" ]; then
        read -p "PostgreSQL 数据库密码（留空自动生成）: " DB_PASSWORD_INPUT
        DB_PASSWORD=${DB_PASSWORD_INPUT:-}
    fi
    
    echo
    print_info "开始部署..."
    
    update_system
    install_python
    create_app_user
    create_app_directories
    setup_postgresql
    deploy_application
    setup_venv
    setup_env
    init_database
    setup_gunicorn
    create_systemd_service
    setup_nginx
    setup_firewall
    create_backup_script
    start_services
    setup_ssl
    
    print_info "========================================="
    print_info "部署完成！"
    print_info "========================================="
    print_info "应用目录: $APP_DIR"
    print_info "应用用户: $APP_USER"
    if [ "$DB_TYPE" = "postgresql" ] && [ -n "$DB_PASSWORD" ]; then
        print_info "数据库密码: $DB_PASSWORD"
    fi
    print_info "服务管理命令:"
    print_info "  启动: sudo systemctl start $APP_NAME"
    print_info "  停止: sudo systemctl stop $APP_NAME"
    print_info "  重启: sudo systemctl restart $APP_NAME"
    print_info "  状态: sudo systemctl status $APP_NAME"
    print_info "  日志: sudo journalctl -u $APP_NAME -f"
    print_info ""
    print_info "访问地址:"
    if [ -n "$APP_DOMAIN" ]; then
        print_info "  http://$APP_DOMAIN"
    else
        print_info "  http://$(hostname -I | awk '{print $1}')"
    fi
    print_info ""
    print_warn "请确保已修改默认密码！"
}

# 运行主函数
main

