# 快速部署指南

## 5 分钟快速部署

### 步骤 1: 上传代码到服务器

```bash
# 在本地执行（将代码上传到服务器）
scp -r /path/to/STIC/* user@your-server-ip:/tmp/stic/
```

或者使用 Git：

```bash
# 在服务器上执行
cd /tmp
git clone <your-repo-url> stic
```

### 步骤 2: 运行部署脚本

```bash
# SSH 登录服务器
ssh user@your-server-ip

# 进入项目目录
cd /tmp/stic

# 给脚本执行权限
chmod +x deploy.sh

# 运行部署脚本（需要 root 权限）
sudo bash deploy.sh
```

### 步骤 3: 按提示输入配置

脚本会询问：
1. **应用域名**：如果有域名输入域名，没有则留空（使用 IP 访问）
2. **数据库类型**：输入 `sqlite`（默认）或 `postgresql`
3. **数据库密码**：如果选择 PostgreSQL，输入密码或留空自动生成

### 步骤 4: 等待部署完成

脚本会自动：
- 安装所有依赖
- 创建应用用户和目录
- 配置数据库
- 设置 Python 环境
- 配置 Web 服务器
- 启动服务

### 步骤 5: 访问应用

部署完成后，访问：
- **有域名**：`http://your-domain.com`
- **无域名**：`http://your-server-ip`

### 步骤 6: 配置 SSL（可选，推荐）

如果有域名，配置 HTTPS：

```bash
sudo apt-get install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

## 部署后必做事项

### 1. 修改默认密码

登录系统后，立即修改所有测试账户的默认密码（默认密码：`swjtu12345`）

### 2. 检查服务状态

```bash
# 检查应用服务
sudo systemctl status stic

# 检查 Nginx
sudo systemctl status nginx
```

### 3. 查看日志（如有问题）

```bash
# 应用日志
sudo journalctl -u stic -f

# Nginx 日志
sudo tail -f /opt/stic/logs/nginx_error.log
```

## 常用命令

```bash
# 启动服务
sudo systemctl start stic

# 停止服务
sudo systemctl stop stic

# 重启服务
sudo systemctl restart stic

# 查看服务状态
sudo systemctl status stic

# 查看实时日志
sudo journalctl -u stic -f

# 手动备份
sudo -u stic /opt/stic/backup.sh
```

## 故障排查

### 无法访问网站

1. 检查服务是否运行：
```bash
sudo systemctl status stic
sudo systemctl status nginx
```

2. 检查防火墙：
```bash
sudo ufw status
```

3. 检查端口：
```bash
sudo netstat -tlnp | grep 8000
```

### 服务启动失败

查看详细错误：
```bash
sudo journalctl -u stic -n 50
```

### 数据库错误

检查数据库文件权限：
```bash
ls -la /opt/stic/competition.db
sudo chown stic:stic /opt/stic/competition.db
```

## 完整文档

更多详细信息请参考：
- **DEPLOY.md** - 完整部署文档
- **README.md** - 部署文件说明

