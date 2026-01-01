#!/bin/bash
# 自动部署脚本 - 用于Ubuntu服务器
# 使用方法: ./deploy.sh [init|update]

set -e  # 遇到错误立即退出

# 配置变量
APP_NAME="stic"
APP_USER="www-data"
APP_DIR="/var/www/${APP_NAME}"
VENV_DIR="${APP_DIR}/venv"
SERVICE_NAME="${APP_NAME}.service"
REPO_URL=""  # 如果使用Git，填写仓库URL
BRANCH="main"  # Git分支名

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查是否为root用户
check_root() {
    if [ "$EUID" -ne 0 ]; then 
        log_error "请使用root权限运行此脚本"
        exit 1
    fi
}

# 初始化部署
init_deploy() {
    log_info "开始初始化部署..."
    
    # 创建应用目录
    log_info "创建应用目录: ${APP_DIR}"
    mkdir -p ${APP_DIR}
    mkdir -p ${APP_DIR}/logs
    mkdir -p ${APP_DIR}/uploads
    mkdir -p ${APP_DIR}/certificates
    mkdir -p ${APP_DIR}/backup
    
    # 设置权限
    chown -R ${APP_USER}:${APP_USER} ${APP_DIR}
    chmod -R 755 ${APP_DIR}
    chmod -R 775 ${APP_DIR}/uploads
    chmod -R 775 ${APP_DIR}/certificates
    chmod -R 775 ${APP_DIR}/logs
    
    # 创建虚拟环境
    log_info "创建Python虚拟环境..."
    if [ ! -d "${VENV_DIR}" ]; then
        python3 -m venv ${VENV_DIR}
    fi
    
    # 激活虚拟环境并安装依赖
    log_info "安装Python依赖..."
    source ${VENV_DIR}/bin/activate
    pip install --upgrade pip
    pip install -r ${APP_DIR}/requirements.txt
    
    # 如果使用Git，克隆代码
    if [ -n "${REPO_URL}" ]; then
        log_info "从Git仓库克隆代码..."
        if [ ! -d "${APP_DIR}/.git" ]; then
            git clone -b ${BRANCH} ${REPO_URL} ${APP_DIR}/temp_clone
            cp -r ${APP_DIR}/temp_clone/. ${APP_DIR}/
            rm -rf ${APP_DIR}/temp_clone
        fi
    fi
    
    log_info "初始化部署完成！"
    log_warn "请执行以下步骤："
    log_warn "1. 将项目文件复制到 ${APP_DIR}"
    log_warn "2. 配置环境变量（创建 .env 文件）"
    log_warn "3. 运行 'python init_db.py' 初始化数据库"
    log_warn "4. 运行 'python migrate_db.py' 迁移数据库（如需要）"
    log_warn "5. 运行 './deploy.sh update' 完成部署"
}

# 更新部署
update_deploy() {
    log_info "开始更新部署..."
    
    # 检查应用目录是否存在
    if [ ! -d "${APP_DIR}" ]; then
        log_error "应用目录不存在，请先运行 './deploy.sh init' 初始化"
        exit 1
    fi
    
    # 备份数据库和上传文件
    log_info "备份数据..."
    BACKUP_DIR="${APP_DIR}/backup/$(date +%Y%m%d_%H%M%S)"
    mkdir -p ${BACKUP_DIR}
    
    if [ -f "${APP_DIR}/competition.db" ]; then
        cp ${APP_DIR}/competition.db ${BACKUP_DIR}/competition.db
        log_info "数据库已备份到 ${BACKUP_DIR}/competition.db"
    fi
    
    if [ -d "${APP_DIR}/uploads" ] && [ "$(ls -A ${APP_DIR}/uploads)" ]; then
        cp -r ${APP_DIR}/uploads ${BACKUP_DIR}/uploads
        log_info "上传文件已备份到 ${BACKUP_DIR}/uploads"
    fi
    
    if [ -d "${APP_DIR}/certificates" ] && [ "$(ls -A ${APP_DIR}/certificates)" ]; then
        cp -r ${APP_DIR}/certificates ${BACKUP_DIR}/certificates
        log_info "证书文件已备份到 ${BACKUP_DIR}/certificates"
    fi
    
    # 如果使用Git，拉取最新代码
    if [ -d "${APP_DIR}/.git" ]; then
        log_info "从Git仓库拉取最新代码..."
        cd ${APP_DIR}
        git pull origin ${BRANCH}
    fi
    
    # 更新虚拟环境依赖
    log_info "更新Python依赖..."
    source ${VENV_DIR}/bin/activate
    pip install --upgrade pip
    pip install -r ${APP_DIR}/requirements.txt
    
    # 运行数据库迁移（如果需要）
    if [ -f "${APP_DIR}/migrate_db.py" ]; then
        log_info "运行数据库迁移..."
        cd ${APP_DIR}
        python migrate_db.py || log_warn "数据库迁移失败或不需要迁移"
    fi
    
    # 重启服务
    log_info "重启服务..."
    systemctl restart ${SERVICE_NAME} || log_warn "服务重启失败，请手动检查"
    
    # 检查服务状态
    sleep 2
    if systemctl is-active --quiet ${SERVICE_NAME}; then
        log_info "服务运行正常"
    else
        log_error "服务启动失败，请检查日志: journalctl -u ${SERVICE_NAME} -n 50"
    fi
    
    log_info "更新部署完成！"
}

# 主函数
main() {
    check_root
    
    case "${1:-update}" in
        init)
            init_deploy
            ;;
        update)
            update_deploy
            ;;
        *)
            echo "使用方法: $0 [init|update]"
            echo "  init   - 初始化部署（首次部署）"
            echo "  update - 更新部署（更新代码）"
            exit 1
            ;;
    esac
}

main "$@"

