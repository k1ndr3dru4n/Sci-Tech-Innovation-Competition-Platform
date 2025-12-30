#!/bin/bash

###############################################################################
# PostgreSQL 数据库初始化脚本
# 用于从 SQLite 迁移到 PostgreSQL
# 使用方法: sudo -u postgres bash init_postgresql.sh
###############################################################################

set -e

# 配置变量
DB_NAME="stic_db"
DB_USER="stic_user"
DB_PASSWORD=""

# 生成随机密码（如果未提供）
if [ -z "$DB_PASSWORD" ]; then
    DB_PASSWORD=$(openssl rand -base64 32)
    echo "生成的数据库密码: $DB_PASSWORD"
    echo "请保存此密码到 .env 文件中！"
fi

echo "========================================="
echo "初始化 PostgreSQL 数据库"
echo "========================================="

# 创建数据库
echo "创建数据库: $DB_NAME"
psql <<EOF
-- 如果数据库已存在，先删除
DROP DATABASE IF EXISTS $DB_NAME;

-- 创建数据库
CREATE DATABASE $DB_NAME;

-- 创建用户（如果不存在）
DO \$\$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_user WHERE usename = '$DB_USER') THEN
        CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';
    ELSE
        ALTER USER $DB_USER WITH PASSWORD '$DB_PASSWORD';
    END IF;
END
\$\$;

-- 授权
GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;
ALTER USER $DB_USER CREATEDB;

-- 连接到新数据库并授权
\c $DB_NAME
GRANT ALL ON SCHEMA public TO $DB_USER;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO $DB_USER;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO $DB_USER;

\q
EOF

echo "✓ 数据库创建完成"
echo ""
echo "数据库信息:"
echo "  数据库名: $DB_NAME"
echo "  用户名: $DB_USER"
echo "  密码: $DB_PASSWORD"
echo ""
echo "请在 .env 文件中设置:"
echo "  DATABASE_URL=postgresql://$DB_USER:$DB_PASSWORD@localhost/$DB_NAME"
echo ""

