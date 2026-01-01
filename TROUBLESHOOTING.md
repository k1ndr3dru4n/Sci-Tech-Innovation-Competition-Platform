# 故障排查指南

## 水平导航栏失效问题

### 问题描述
服务器上所有水平导航栏（tab导航）失效，本地正常。

### 原因分析
通常是因为CSS文件没有正确加载，导致 `.tab-nav` 和 `.tab-nav-item` 样式未生效。

### 解决方案

#### 方案1：启用Nginx静态文件服务（推荐）

1. **更新nginx配置**：
```bash
sudo nano /etc/nginx/sites-available/stic
```

2. **确保有以下配置（未被注释）**：
```nginx
location /static {
    alias /var/www/stic/static;
    expires 30d;
    add_header Cache-Control "public, immutable";
    access_log off;
}
```

3. **测试并重启Nginx**：
```bash
sudo nginx -t
sudo systemctl restart nginx
```

#### 方案2：检查静态文件是否存在

```bash
# 检查静态文件目录
ls -la /var/www/stic/static/css/style.css

# 检查文件权限
ls -la /var/www/stic/static/

# 确保www-data用户有读取权限
sudo chown -R www-data:www-data /var/www/stic/static
sudo chmod -R 755 /var/www/stic/static
```

#### 方案3：检查浏览器控制台

1. 在浏览器中打开开发者工具（F12）
2. 查看Console标签，检查是否有CSS文件加载错误
3. 查看Network标签，检查 `/static/css/style.css` 是否返回404或500错误

#### 方案4：清除浏览器缓存

在浏览器中按 `Ctrl+Shift+R` (Windows/Linux) 或 `Cmd+Shift+R` (Mac) 强制刷新页面。

#### 方案5：验证CSS文件内容

```bash
# 在服务器上检查CSS文件是否包含tab-nav样式
grep -n "tab-nav" /var/www/stic/static/css/style.css

# 应该能看到类似以下输出：
# 821:.tab-nav {
# 830:.tab-nav-item {
```

### 完整检查清单

执行以下命令检查所有可能的问题：

```bash
# 1. 检查静态文件是否存在
ls -la /var/www/stic/static/css/style.css

# 2. 检查文件权限
ls -la /var/www/stic/static/

# 3. 检查Nginx配置
sudo nginx -t
cat /etc/nginx/sites-available/stic | grep -A 5 "location /static"

# 4. 检查Nginx错误日志
sudo tail -n 50 /var/log/nginx/stic_error.log

# 5. 测试静态文件访问（应该返回CSS内容）
curl http://localhost/static/css/style.css | head -20

# 6. 如果使用域名，测试：
curl http://your-domain.com/static/css/style.css | head -20
```

### 修复步骤总结

1. **上传最新的nginx.conf到服务器**（已修复静态文件配置）
2. **在服务器上更新Nginx配置**：
   ```bash
   sudo cp /var/www/stic/nginx.conf /etc/nginx/sites-available/stic
   sudo nginx -t
   sudo systemctl restart nginx
   ```
3. **确保静态文件权限正确**：
   ```bash
   sudo chown -R www-data:www-data /var/www/stic/static
   sudo chmod -R 755 /var/www/stic/static
   ```
4. **清除浏览器缓存并刷新页面**

### 其他常见问题

#### 问题：静态文件返回404

**解决**：
- 检查静态文件目录路径是否正确
- 检查Nginx配置中的 `alias` 路径是否正确
- 确保 `/var/www/stic/static` 目录存在且可读

#### 问题：静态文件返回403

**解决**：
- 检查文件权限：`sudo chmod -R 755 /var/www/stic/static`
- 检查目录权限：`sudo chmod 755 /var/www/stic`
- 确保www-data用户有读取权限

#### 问题：CSS文件加载但样式不生效

**解决**：
- 清除浏览器缓存
- 检查CSS文件内容是否完整（可能上传时损坏）
- 检查浏览器控制台是否有CSS解析错误

### 联系支持

如果以上方案都无法解决问题，请提供以下信息：
1. Nginx错误日志：`sudo tail -n 100 /var/log/nginx/stic_error.log`
2. 浏览器控制台错误信息（F12 -> Console）
3. 网络请求详情（F12 -> Network，查看CSS文件的响应）

