# 大学科创竞赛校级管理平台

一个基于 Flask 的 Web 应用，用于支持中国国际大学生创新大赛"青年红色筑梦之旅"赛道、"挑战杯"全国大学生课外学术科技作品竞赛、"挑战杯"中国大学生创业计划大赛的校内组织流程。

## ✨ 功能特性

- 🎯 **多角色用户系统** - 支持学生、学院管理员、校级管理员、校外评委四种角色，支持多角色分配和切换
- 📝 **项目全流程管理** - 从项目创建、队员确认、多级审核到最终评审的完整流程
- 🏆 **竞赛管理** - 竞赛创建、发布、报名时间设置、决赛名额管理
- 👨‍⚖️ **评审系统** - 评委分配、在线多维度打分、评分统计
- 🎲 **答辩抽签** - 学生自主抽取答辩顺序，管理员可管理
- 🏅 **奖项管理** - 校赛奖项自动生成证书，支持外部奖项上传
- 🤖 **AI敏感信息检测** - 基于千问API自动检测项目附件中的敏感信息
- 📊 **考核系统** - 年度考核数据统计、自动算分、数据导出
- 📤 **数据导出** - 支持项目、评分、考核数据一键导出为Excel
- 🔐 **权限控制** - 基于角色的访问控制（RBAC），数据隔离
- 📁 **文件管理** - 支持多种格式文件上传、在线预览、下载
- ⏰ **时区支持** - 自动使用北京时间（UTC+8）

## 🛠️ 技术栈

- **后端**: Python 3.8+, Flask 3.0
- **数据库**: SQLite（可切换为 PostgreSQL/MySQL）
- **ORM**: SQLAlchemy
- **前端**: HTML5, CSS3, JavaScript (原生), AG Grid
- **其他工具**: 
  - Pillow (图像处理)
  - pandas (数据处理)
  - openpyxl (Excel 导出)
  - PyPDF2 (PDF文本提取)
  - python-docx (Word文档处理)
  - requests (HTTP请求，用于AI API)
  - gunicorn (生产环境WSGI服务器)

## 🚀 快速开始

### 安装

```bash
# 克隆项目
git clone <repository-url>
cd Sci-Tech-Innovation-Competition-Platform

# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 初始化数据库
python init_db.py

# 运行应用
python app.py
```

应用将在 `http://127.0.0.1:5000` 启动。

### 测试账户

初始化脚本已创建以下测试账户（初始密码均为 `swjtu12345`）：

| 角色 | 登录方式 | 账号 | 说明 |
|------|---------|------|------|
| 学生 | 学工号 | 2023115871 | 所属学院：利兹学院 |
| 学院管理员 | 学工号 | T2023115871 | 利兹学院管理员 |
| 校级管理员 | 学工号 | A2023115871 | 单位：教务处 |
| 校外专家 | 用户名/邮箱 | J2023115871 或 judge@example.com | 单位：外部评审机构 |

**登录入口**：
- 校内用户：`/auth/login`（使用学工号登录）
- 校外专家：`/auth/judge/login`（使用用户名或邮箱登录）

## 📖 使用说明

### 学生端

- 创建队伍和项目，填写项目信息
- 添加队员和指导老师，上传项目附件
- 等待队员确认后提交项目
- 查看专家建议、奖项、下载证书
- 上传外部奖项（省赛、国赛）
- 抽取答辩顺序（决赛项目）

### 学院管理员

- 审核本院项目（通过/不通过）
- 查看项目列表和学生信息
- 查看奖项统计
- 导出项目数据

### 校级管理员

- 审核项目、分配评委
- 管理竞赛（创建、编辑、发布）
- 管理决赛和答辩顺序
- 设置奖项、生成证书
- 用户和角色管理
- AI敏感信息检测
- 考核系统管理
- 数据导出

### 校外评委

- 查看分配的项目
- 浏览项目材料和附件
- 在线打分（多维度评分）
- 填写评语和建议

## ⚙️ 配置

### 环境变量

创建 `.env` 文件（可选）：

```env
# Flask 密钥（生产环境必须修改）
SECRET_KEY=your-secret-key-here

# 数据库连接（可选，默认使用 SQLite）
DATABASE_URL=sqlite:///competition.db

# AI 敏感信息检测（可选）
QWEN_API_KEY=your-api-key-here
```

### AI敏感信息检测配置

在 `config.py` 中配置：

```python
QWEN_API_KEY = 'your-api-key'
SENSITIVE_KEYWORDS = ['西南交通大学']  # 敏感关键词列表
```

### 文件上传配置

在 `config.py` 中配置：

```python
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png', 'zip', 'rar'}
```

## 📁 项目结构

```
Sci-Tech-Innovation-Competition-Platform/
├── app.py                      # Flask 应用主文件
├── config.py                   # 配置文件
├── models.py                   # 数据库模型
├── forms.py                    # 表单定义
├── requirements.txt            # Python 依赖
├── init_db.py                  # 数据库初始化脚本
├── migrate_db.py               # 数据库迁移脚本
├── routes/                     # 路由模块
│   ├── auth.py                 # 认证路由
│   ├── student.py              # 学生端路由
│   ├── college_admin.py        # 学院管理员路由
│   ├── school_admin.py         # 校级管理员路由
│   └── judge.py                # 评委路由
├── templates/                  # HTML 模板
├── static/                     # 静态文件
├── utils/                      # 工具模块
│   ├── decorators.py           # 权限装饰器
│   ├── certificate.py         # 证书生成
│   ├── export.py               # 数据导出
│   ├── file_handler.py        # 文件处理
│   ├── ai_sensitive_detection.py  # AI敏感信息检测
│   └── timezone.py             # 时区处理
├── uploads/                    # 上传文件目录
├── certificates/               # 证书目录
└── deploy.sh                   # 部署脚本
```

## 🚢 部署

### 开发环境

直接运行 `python app.py` 即可。

### 生产环境

系统支持部署到 Ubuntu 服务器，使用 Gunicorn + Nginx 架构。

详细部署文档：
- 📘 [快速部署指南](QUICK_START.md)
- 📗 [完整部署文档](DEPLOY.md)
- 📙 [故障排查](TROUBLESHOOTING.md)

主要步骤：

1. 上传项目到服务器（推荐路径：`/var/www/stic`）
2. 创建虚拟环境并安装依赖
3. 配置环境变量
4. 初始化数据库
5. 配置 systemd 服务
6. 配置 Nginx 反向代理

## 🔧 开发

### 数据库关系

```
User (用户)
  ├── TeamMember (多对多: 学生-队伍)
  ├── ProjectMember (多对多: 学生-项目)
  ├── JudgeAssignment (多对多: 评委-项目)
  └── UserRoleAssignment (多对多: 用户-角色)

Project (项目)
  ├── ProjectTrack (多对多: 项目-赛道)
  ├── ProjectAttachment (项目附件)
  ├── Score (评分)
  ├── Award (校赛奖项)
  └── ExternalAward (外部奖项)

Competition (竞赛)
  ├── Track (赛道)
  └── Project (项目)
```

### 审核状态流转

```
草稿 (DRAFT) 
  → 已提交 (SUBMITTED) 
  → 学院已通过 (COLLEGE_APPROVED) 
  → 最终通过 (FINAL_APPROVED)
```

### 扩展开发

- **添加新角色**: 在 `models.py` 的 `UserRole` 类中添加，创建对应的路由和模板
- **添加新字段**: 修改模型，运行 `migrate_db.py` 进行数据库迁移
- **自定义证书模板**: 修改 `utils/certificate.py` 中的 `generate_certificate` 函数
- **配置AI检测**: 在 `config.py` 中修改 `SENSITIVE_KEYWORDS` 和 API 配置

## 📄 许可证

本项目仅供学习和研究使用。

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

---

如有问题，请查看 [故障排查文档](TROUBLESHOOTING.md) 或提交 Issue。
