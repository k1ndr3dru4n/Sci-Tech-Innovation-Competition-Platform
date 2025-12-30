"""
大学科创竞赛校级管理平台
支持中国国际大学生创新大赛"青年红色筑梦之旅"赛道、
"挑战杯"全国大学生课外学术科技作品竞赛、
"挑战杯"中国大学生创业计划大赛
"""
from flask import Flask, redirect, url_for
from flask_login import current_user, login_required
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from config import Config

# 初始化Flask应用
app = Flask(__name__)
app.config.from_object(Config)

# 初始化扩展
from models import db
db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = 'auth.login'
login_manager.login_message = '请先登录以访问此页面'

# 导入模型（需要在db初始化后）
from models import User, Team, Project, Competition, Track, Score, Award

# 注册蓝图
from routes.auth import auth_bp
from routes.dashboard import dashboard_bp
from routes.profile import profile_bp
from routes.student import student_bp
from routes.college_admin import college_admin_bp
from routes.school_admin import school_admin_bp
from routes.judge import judge_bp

app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(dashboard_bp)
app.register_blueprint(profile_bp)
app.register_blueprint(student_bp, url_prefix='/student')
app.register_blueprint(college_admin_bp, url_prefix='/college_admin')
app.register_blueprint(school_admin_bp, url_prefix='/school_admin')
app.register_blueprint(judge_bp, url_prefix='/judge')

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.dashboard'))
    return redirect(url_for('auth.login'))

@app.route('/uploads/<path:filename>')
@login_required
def uploaded_file(filename):
    """提供上传文件的访问和下载，支持在线预览"""
    from flask import send_from_directory, request, Response
    from config import Config
    from pathlib import Path
    import os
    import mimetypes
    
    # 将Path对象转换为字符串
    upload_folder = str(Config.UPLOAD_FOLDER)
    
    # 将URL中的正斜杠转换为系统路径分隔符（Windows使用反斜杠）
    # filename可能包含子目录，如 "project_1/file.pdf" 或 "project_1\file.pdf"
    filename_normalized = filename.replace('/', os.sep).replace('\\', os.sep)
    
    # 构建完整文件路径
    file_path = os.path.join(upload_folder, filename_normalized)
    file_path = os.path.normpath(file_path)
    upload_folder = os.path.normpath(upload_folder)
    
    # 安全检查：确保文件路径在upload文件夹内（防止路径遍历攻击）
    if not file_path.startswith(upload_folder):
        from flask import abort
        abort(403)  # 禁止访问
    
    if not os.path.exists(file_path):
        from flask import abort
        abort(404)
    
    # 如果请求参数中有download，则强制下载
    as_attachment = request.args.get('download', 'false').lower() == 'true'
    
    # 获取文件MIME类型
    mimetype, _ = mimetypes.guess_type(file_path)
    if mimetype is None:
        mimetype = 'application/octet-stream'
    
    # 对于PDF和图片，如果不强制下载，则设置正确的MIME类型以便浏览器预览
    if not as_attachment:
        file_ext = os.path.splitext(filename)[1].lower()
        if file_ext == '.pdf':
            mimetype = 'application/pdf'
        elif file_ext in ['.jpg', '.jpeg']:
            mimetype = 'image/jpeg'
        elif file_ext == '.png':
            mimetype = 'image/png'
        elif file_ext == '.gif':
            mimetype = 'image/gif'
    
    # send_from_directory需要相对于upload_folder的路径
    # 使用os.path.relpath获取相对路径，然后转换为正斜杠用于URL
    relative_filename = os.path.relpath(file_path, upload_folder)
    # 确保使用正斜杠（URL标准）
    relative_filename = relative_filename.replace('\\', '/')
    
    return send_from_directory(
        upload_folder, 
        relative_filename, 
        as_attachment=as_attachment,
        mimetype=mimetype
    )

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)

