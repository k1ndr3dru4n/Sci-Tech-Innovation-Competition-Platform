# 文件复制位置说明

## 📋 复制步骤

### 方法 1: 临时目录（推荐）

**第一步：将整个项目复制到服务器的临时目录**

```bash
# 在本地执行（Windows PowerShell 或 CMD）
scp -r C:\Users\22058\Desktop\STIC\* user@服务器IP:/tmp/stic/

# 或者使用 SFTP 工具（如 WinSCP、FileZilla）
# 将整个 STIC 文件夹内容上传到服务器的 /tmp/stic/ 目录
```

**第二步：SSH 登录服务器并运行部署脚本**

```bash
# SSH 登录
ssh user@服务器IP

# 进入临时目录
cd /tmp/stic

# 给脚本执行权限
chmod +x deploy.sh

# 运行部署脚本
sudo bash deploy.sh
```

**说明：**
- 临时位置：`/tmp/stic/`（可以任意选择，如 `/home/user/stic`）
- 最终位置：脚本会自动将代码部署到 `/opt/stic/`
- 部署完成后，可以删除临时目录

### 方法 2: 直接复制到最终目录（不推荐）

如果您想直接复制到最终位置：

```bash
# 在本地执行
scp -r C:\Users\22058\Desktop\STIC\* user@服务器IP:/opt/stic/
```

**注意：**
- 需要先创建目录：`sudo mkdir -p /opt/stic`
- 需要设置权限：`sudo chown -R user:user /opt/stic`
- 部署脚本会检测已有代码并询问是否备份

## 📁 需要复制的文件

确保以下内容都复制到服务器：

```
STIC/
├── app.py                    # ✅ 必需
├── config.py                 # ✅ 必需
├── models.py                 # ✅ 必需
├── forms.py                  # ✅ 必需
├── requirements.txt          # ✅ 必需
├── init_db.py                # ✅ 必需
├── migrate_db.py             # ✅ 必需（如果有）
├── routes/                   # ✅ 必需（整个目录）
│   ├── __init__.py
│   ├── auth.py
│   ├── dashboard.py
│   ├── profile.py
│   ├── student.py
│   ├── college_admin.py
│   ├── school_admin.py
│   └── judge.py
├── templates/                # ✅ 必需（整个目录）
├── static/                   # ✅ 必需（整个目录）
├── utils/                    # ✅ 必需（整个目录）
├── deploy/                   # ✅ 必需（整个目录，包含部署脚本）
│   ├── deploy.sh
│   ├── nginx.conf
│   ├── stic.service
│   ├── gunicorn_config.py
│   ├── backup.sh
│   ├── restore.sh
│   └── ...
└── uploads/                  # ⚠️ 可选（如果有现有数据）
```

## 🔍 验证文件是否完整

在服务器上检查：

```bash
# 进入项目目录
cd /tmp/stic  # 或您选择的目录

# 检查关键文件
ls -la app.py
ls -la requirements.txt
ls -la deploy/deploy.sh

# 检查目录结构
ls -d routes/ templates/ static/ utils/ deploy/
```

## 📝 完整操作示例

### Windows 用户（使用 PowerShell）

```powershell
# 1. 使用 SCP 上传（需要安装 OpenSSH 客户端）
scp -r C:\Users\22058\Desktop\STIC\* user@192.168.1.100:/tmp/stic/

# 2. SSH 登录服务器
ssh user@192.168.1.100

# 3. 在服务器上执行
cd /tmp/stic
chmod +x deploy.sh
sudo bash deploy.sh
```

### Windows 用户（使用 WinSCP）

1. 打开 WinSCP，连接到服务器
2. 左侧：选择 `C:\Users\22058\Desktop\STIC`
3. 右侧：进入 `/tmp` 目录，创建 `stic` 文件夹
4. 选中左侧所有文件和文件夹，拖拽到右侧 `/tmp/stic/`
5. 使用 PuTTY 或 WinSCP 的终端功能，SSH 登录服务器
6. 执行部署命令

### Linux/Mac 用户

```bash
# 1. 上传文件
scp -r /path/to/STIC/* user@服务器IP:/tmp/stic/

# 2. SSH 登录
ssh user@服务器IP

# 3. 部署
cd /tmp/stic
chmod +x deploy.sh
sudo bash deploy.sh
```

## ⚠️ 重要提示

1. **必须包含 deploy 目录**：部署脚本在项目根目录下
2. **不要复制虚拟环境**：如果有 `venv/` 或 `__pycache__/` 目录，可以排除
3. **数据库文件可选**：`competition.db` 可以不上传，部署脚本会重新初始化
4. **上传文件可选**：`uploads/` 和 `certificates/` 目录可以不上传，部署脚本会创建

## 🎯 部署后的目录结构

部署完成后，应用将安装在：

```
/opt/stic/                    # 应用根目录
├── app.py
├── config.py
├── models.py
├── ...
├── .env                      # 环境变量（部署脚本自动创建）
├── gunicorn_config.py        # Gunicorn 配置（从 deploy/ 复制）
├── venv/                     # Python 虚拟环境（部署脚本创建）
├── competition.db            # 数据库文件（部署脚本创建）
├── uploads/                  # 上传文件目录
├── certificates/             # 证书目录
├── logs/                    # 日志目录
│   ├── gunicorn_access.log
│   ├── gunicorn_error.log
│   ├── nginx_access.log
│   └── nginx_error.log
└── backups/                 # 备份目录
```

## ❓ 常见问题

### Q: 可以只复制部分文件吗？
A: 不行，必须复制完整的项目结构，包括所有 Python 文件、模板、静态文件等。

### Q: deploy.sh 必须在项目根目录吗？
A: 是的，`deploy.sh` 应该在项目根目录，与 `app.py` 同级。

### Q: 上传后需要修改权限吗？
A: 不需要，部署脚本会自动处理所有权限设置。

### Q: 可以使用 Git 吗？
A: 可以！如果有 Git 仓库，可以在服务器上直接 clone：
```bash
cd /tmp
git clone <your-repo-url> stic
cd stic
sudo bash deploy.sh
```

### Q: 文件太大上传慢怎么办？
A: 可以排除不必要的文件：
- `__pycache__/` 目录
- `venv/` 目录（如果有）
- `.git/` 目录（如果使用 Git）
- 现有的 `uploads/` 和 `certificates/`（可选）

## 📞 需要帮助？

如果遇到问题：
1. 检查文件是否完整上传
2. 检查文件权限
3. 查看部署脚本的输出信息
4. 参考 `DEPLOY.md` 中的故障排查部分

