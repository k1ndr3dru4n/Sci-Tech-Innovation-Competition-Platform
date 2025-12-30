#!/bin/bash

###############################################################################
# STIC 项目恢复脚本
# 从备份文件恢复数据
# 使用方法: ./restore.sh backup_20231201_120000.tar.gz
###############################################################################

set -e

# 配置变量
APP_DIR="/opt/stic"
BACKUP_DIR="$APP_DIR/backups"

# 检查参数
if [ -z "$1" ]; then
    echo "错误: 请指定备份文件"
    echo "使用方法: $0 backup_YYYYMMDD_HHMMSS.tar.gz"
    echo ""
    echo "可用备份文件:"
    ls -lh "$BACKUP_DIR"/backup_*.tar.gz 2>/dev/null || echo "  无备份文件"
    exit 1
fi

BACKUP_FILE="$1"
if [[ ! "$BACKUP_FILE" == /* ]]; then
    BACKUP_FILE="$BACKUP_DIR/$BACKUP_FILE"
fi

if [ ! -f "$BACKUP_FILE" ]; then
    echo "错误: 备份文件不存在: $BACKUP_FILE"
    exit 1
fi

echo "========================================="
echo "恢复备份: $BACKUP_FILE"
echo "========================================="

# 确认操作
read -p "警告: 此操作将覆盖现有数据，是否继续？(yes/no): " -r
if [[ ! $REPLY == "yes" ]]; then
    echo "操作已取消"
    exit 0
fi

# 创建临时目录
TEMP_DIR=$(mktemp -d)
trap "rm -rf $TEMP_DIR" EXIT

# 解压备份文件
echo "解压备份文件..."
tar -xzf "$BACKUP_FILE" -C "$TEMP_DIR"
BACKUP_NAME=$(basename "$BACKUP_FILE" .tar.gz)
RESTORE_DIR="$TEMP_DIR/$BACKUP_NAME"

# 恢复数据库
if [ -f "$RESTORE_DIR/competition.db" ]; then
    echo "恢复 SQLite 数据库..."
    systemctl stop stic 2>/dev/null || true
    cp "$RESTORE_DIR/competition.db" "$APP_DIR/competition.db"
    chown stic:stic "$APP_DIR/competition.db"
    echo "✓ 数据库恢复完成"
fi

if [ -f "$RESTORE_DIR/database.dump" ]; then
    echo "恢复 PostgreSQL 数据库..."
    if [ -f "$APP_DIR/.env" ]; then
        source "$APP_DIR/.env"
        if [[ "$DATABASE_URL" == postgresql://* ]]; then
            DB_URL=${DATABASE_URL#postgresql://}
            DB_USER_PASS=${DB_URL%%@*}
            DB_USER=${DB_USER_PASS%%:*}
            DB_PASS=${DB_USER_PASS#*:}
            DB_HOST_DB=${DB_URL#*@}
            DB_HOST=${DB_HOST_DB%%/*}
            DB_NAME=${DB_HOST_DB#*/}
            
            export PGPASSWORD="$DB_PASS"
            pg_restore -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -c "$RESTORE_DIR/database.dump"
            unset PGPASSWORD
            echo "✓ PostgreSQL 数据库恢复完成"
        fi
    fi
fi

# 恢复上传文件
if [ -f "$RESTORE_DIR/uploads.tar.gz" ]; then
    echo "恢复上传文件..."
    systemctl stop stic 2>/dev/null || true
    rm -rf "$APP_DIR/uploads"/*
    tar -xzf "$RESTORE_DIR/uploads.tar.gz" -C "$APP_DIR"
    chown -R stic:stic "$APP_DIR/uploads"
    echo "✓ 上传文件恢复完成"
fi

# 恢复证书
if [ -f "$RESTORE_DIR/certificates.tar.gz" ]; then
    echo "恢复证书文件..."
    systemctl stop stic 2>/dev/null || true
    rm -rf "$APP_DIR/certificates"/*
    tar -xzf "$RESTORE_DIR/certificates.tar.gz" -C "$APP_DIR"
    chown -R stic:stic "$APP_DIR/certificates"
    echo "✓ 证书恢复完成"
fi

# 恢复配置文件（可选）
if [ -f "$RESTORE_DIR/.env" ]; then
    read -p "是否恢复配置文件 .env？(y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        cp "$RESTORE_DIR/.env" "$APP_DIR/.env.backup.$(date +%Y%m%d_%H%M%S)"
        cp "$RESTORE_DIR/.env" "$APP_DIR/.env"
        chown stic:stic "$APP_DIR/.env"
        chmod 600 "$APP_DIR/.env"
        echo "✓ 配置文件恢复完成"
    fi
fi

# 重启服务
echo "重启服务..."
systemctl start stic
sleep 2

if systemctl is-active --quiet stic; then
    echo "✓ 服务启动成功"
else
    echo "✗ 服务启动失败，请检查日志: journalctl -u stic"
fi

echo "========================================="
echo "恢复完成！"
echo "========================================="

