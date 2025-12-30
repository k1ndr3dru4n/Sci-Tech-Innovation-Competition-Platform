#!/bin/bash

###############################################################################
# STIC 项目备份脚本
# 自动备份数据库、上传文件和证书
# 使用方法: ./backup.sh
# 建议添加到 crontab: 0 2 * * * /opt/stic/backup.sh
###############################################################################

set -e

# 配置变量
APP_DIR="/opt/stic"
BACKUP_DIR="$APP_DIR/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="backup_$DATE"
BACKUP_PATH="$BACKUP_DIR/$BACKUP_NAME"

# 创建备份目录
mkdir -p "$BACKUP_PATH"

echo "========================================="
echo "开始备份: $BACKUP_NAME"
echo "========================================="

# 备份 SQLite 数据库
if [ -f "$APP_DIR/competition.db" ]; then
    echo "备份 SQLite 数据库..."
    cp "$APP_DIR/competition.db" "$BACKUP_PATH/competition.db"
    echo "✓ 数据库备份完成"
fi

# 备份 PostgreSQL 数据库（如果使用）
if command -v pg_dump &> /dev/null; then
    # 从 .env 文件读取数据库配置
    if [ -f "$APP_DIR/.env" ]; then
        source "$APP_DIR/.env"
        if [[ "$DATABASE_URL" == postgresql://* ]]; then
            echo "备份 PostgreSQL 数据库..."
            # 解析 DATABASE_URL
            DB_URL=${DATABASE_URL#postgresql://}
            DB_USER_PASS=${DB_URL%%@*}
            DB_USER=${DB_USER_PASS%%:*}
            DB_PASS=${DB_USER_PASS#*:}
            DB_HOST_DB=${DB_URL#*@}
            DB_HOST=${DB_HOST_DB%%/*}
            DB_NAME=${DB_HOST_DB#*/}
            
            export PGPASSWORD="$DB_PASS"
            pg_dump -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -F c -f "$BACKUP_PATH/database.dump"
            unset PGPASSWORD
            echo "✓ PostgreSQL 数据库备份完成"
        fi
    fi
fi

# 备份上传文件
if [ -d "$APP_DIR/uploads" ] && [ "$(ls -A $APP_DIR/uploads)" ]; then
    echo "备份上传文件..."
    tar -czf "$BACKUP_PATH/uploads.tar.gz" -C "$APP_DIR" uploads
    echo "✓ 上传文件备份完成 ($(du -h $BACKUP_PATH/uploads.tar.gz | cut -f1))"
fi

# 备份证书
if [ -d "$APP_DIR/certificates" ] && [ "$(ls -A $APP_DIR/certificates)" ]; then
    echo "备份证书文件..."
    tar -czf "$BACKUP_PATH/certificates.tar.gz" -C "$APP_DIR" certificates
    echo "✓ 证书备份完成 ($(du -h $BACKUP_PATH/certificates.tar.gz | cut -f1))"
fi

# 备份配置文件
if [ -f "$APP_DIR/.env" ]; then
    echo "备份配置文件..."
    cp "$APP_DIR/.env" "$BACKUP_PATH/.env"
    echo "✓ 配置文件备份完成"
fi

# 创建备份信息文件
cat > "$BACKUP_PATH/backup_info.txt" <<EOF
备份时间: $(date)
备份名称: $BACKUP_NAME
应用目录: $APP_DIR
EOF

# 压缩整个备份目录
echo "压缩备份文件..."
cd "$BACKUP_DIR"
tar -czf "${BACKUP_NAME}.tar.gz" "$BACKUP_NAME"
rm -rf "$BACKUP_NAME"
echo "✓ 备份压缩完成: ${BACKUP_NAME}.tar.gz ($(du -h ${BACKUP_NAME}.tar.gz | cut -f1))"

# 删除 30 天前的备份
echo "清理旧备份..."
find "$BACKUP_DIR" -name "backup_*.tar.gz" -type f -mtime +30 -delete
echo "✓ 已清理 30 天前的备份"

echo "========================================="
echo "备份完成！"
echo "备份文件: $BACKUP_DIR/${BACKUP_NAME}.tar.gz"
echo "========================================="

