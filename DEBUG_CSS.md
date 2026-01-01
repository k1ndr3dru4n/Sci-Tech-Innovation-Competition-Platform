# 导航栏样式问题排查

## 问题
静态文件可以正常加载（200 OK），但水平导航栏样式未生效，只显示超链接。

## 可能的原因

### 1. 浏览器缓存问题（最常见）

**解决方案：**
- 强制刷新：按 `Ctrl+Shift+R` (Windows/Linux) 或 `Cmd+Shift+R` (Mac)
- 或者在开发者工具中：
  1. 打开开发者工具 (F12)
  2. 右键点击刷新按钮
  3. 选择"清空缓存并硬性重新加载"

### 2. 检查CSS文件内容

在服务器上验证CSS文件中是否包含 `.tab-nav` 样式：

```bash
# 检查CSS文件中是否有tab-nav样式
grep -n "\.tab-nav" /var/www/stic/static/css/style.css

# 应该看到类似输出：
# 821:.tab-nav {
# 830:.tab-nav-item {
```

如果没有输出，说明CSS文件可能不完整，需要重新上传。

### 3. 检查浏览器控制台

1. 打开浏览器开发者工具 (F12)
2. 查看 Console 标签，检查是否有CSS加载错误
3. 查看 Network 标签：
   - 找到 `style.css` 文件
   - 确认返回状态是 200
   - 点击查看 Response，确认CSS内容完整

### 4. 检查CSS选择器优先级

在浏览器中：
1. 打开开发者工具 (F12)
2. 选择 Elements/Inspector 标签
3. 找到导航栏元素（`.tab-nav` 或 `.tab-nav-item`）
4. 查看右侧 Styles 面板，检查：
   - `.tab-nav` 样式是否被应用
   - 是否有其他样式覆盖了它（显示为删除线）
   - Computed 标签中显示的实际样式值

### 5. 验证CSS文件完整性

```bash
# 在服务器上检查CSS文件大小
ls -lh /var/www/stic/static/css/style.css

# 查看文件末尾，确认文件完整
tail -20 /var/www/stic/static/css/style.css

# 检查文件是否有tab-nav相关样式
grep -A 30 "\.tab-nav" /var/www/stic/static/css/style.css
```

### 6. 检查HTML中是否正确引用了CSS

在浏览器中查看页面源代码（右键 -> 查看页面源代码），确认：
```html
<link rel="stylesheet" href="/static/css/style.css">
```

或者使用开发者工具查看：
1. F12 -> Network 标签
2. 刷新页面
3. 查找 `style.css`
4. 确认URL是 `/static/css/style.css`

## 快速修复步骤

### 步骤1：清除浏览器缓存
- 使用 `Ctrl+Shift+R` 强制刷新

### 步骤2：检查开发者工具
- 打开F12，查看Console和Network标签
- 确认没有错误信息

### 步骤3：验证CSS内容
在服务器上运行：
```bash
grep -A 30 "\.tab-nav" /var/www/stic/static/css/style.css
```

如果看到样式定义，说明CSS文件正常。

### 步骤4：如果CSS文件不完整
需要重新上传完整的 `static/css/style.css` 文件。

## 临时验证方法

在浏览器控制台中执行（F12 -> Console）：

```javascript
// 检查CSS文件是否加载
console.log(document.styleSheets);

// 手动检查tab-nav样式
const style = getComputedStyle(document.querySelector('.tab-nav'));
console.log('tab-nav display:', style.display);
console.log('tab-nav background:', style.backgroundColor);
```

## 如果仍然无效

请提供以下信息：
1. 浏览器控制台的错误信息（如果有）
2. 在Elements面板中选中导航栏元素，查看Computed样式
3. `grep -A 30 "\.tab-nav" /var/www/stic/static/css/style.css` 的输出结果

