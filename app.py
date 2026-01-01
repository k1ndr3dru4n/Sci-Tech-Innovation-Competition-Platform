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

# 配置时区为北京时间（UTC+8）
import os
os.environ['TZ'] = 'Asia/Shanghai'

# 添加Jinja2过滤器：格式化时间为北京时间
@app.template_filter('beijing_time')
def beijing_time_filter(dt, format_str='%Y-%m-%d %H:%M'):
    """将UTC时间转换为北京时间并格式化"""
    if dt is None:
        return None
    from utils.timezone import utc_to_beijing
    from datetime import timezone
    # 如果时间没有时区信息，假设是UTC时间
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    beijing_dt = utc_to_beijing(dt)
    return beijing_dt.strftime(format_str)

# 添加Jinja2过滤器：格式化时间为北京时间
from datetime import datetime, timezone
@app.template_filter('beijing_time')
def beijing_time_filter(dt, format_str='%Y-%m-%d %H:%M'):
    """将UTC时间转换为北京时间并格式化"""
    if dt is None:
        return None
    from utils.timezone import utc_to_beijing
    # 如果时间没有时区信息，假设是UTC时间
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    beijing_dt = utc_to_beijing(dt)
    return beijing_dt.strftime(format_str)

# 初始化扩展
from models import db
db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = 'auth.login'
login_manager.login_message = '请先登录以访问此页面'

# 导入模型（需要在db初始化后）
from models import User, Team, Project, Competition, Track, Score, Award, ExternalAward

# 注册蓝图
from routes.auth import auth_bp
from routes.dashboard import dashboard_bp
from routes.student import student_bp
from routes.college_admin import college_admin_bp
from routes.school_admin import school_admin_bp
from routes.judge import judge_bp

app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(dashboard_bp)
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
    from models import ProjectAttachment
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
    
    # 如果文件不存在，尝试查找对应的附件记录以获取正确的文件路径和类型
    if not os.path.exists(file_path):
        # 尝试从数据库查找附件记录
        # 将filename转换为可能的路径格式进行匹配
        search_path = filename.replace('\\', '/').replace('/', os.sep)
        attachment = ProjectAttachment.query.filter(
            (ProjectAttachment.file_path == filename) |
            (ProjectAttachment.file_path == filename.replace('/', '\\')) |
            (ProjectAttachment.file_path == filename.replace('\\', '/'))
        ).first()
        
        if attachment:
            # 使用数据库中的路径重新构建文件路径
            db_path = attachment.file_path.replace('/', os.sep).replace('\\', os.sep)
            file_path = os.path.join(upload_folder, db_path)
            file_path = os.path.normpath(file_path)
            
            # 如果文件仍然不存在，尝试添加扩展名
            if not os.path.exists(file_path) and attachment.file_type:
                # 尝试添加扩展名
                file_path_with_ext = file_path + '.' + attachment.file_type
                if os.path.exists(file_path_with_ext):
                    file_path = file_path_with_ext
    
    # 安全检查：确保文件路径在upload文件夹内（防止路径遍历攻击）
    if not file_path.startswith(upload_folder):
        from flask import abort
        abort(403)  # 禁止访问
    
    if not os.path.exists(file_path):
        from flask import abort
        abort(404)
    
    # 如果请求参数中有download，则强制下载
    as_attachment = request.args.get('download', 'false').lower() == 'true'
    
    # 首先尝试从数据库获取附件信息以确定文件类型
    search_path = filename.replace('\\', '/').replace('/', os.sep)
    attachment = ProjectAttachment.query.filter(
        (ProjectAttachment.file_path == filename) |
        (ProjectAttachment.file_path == filename.replace('/', '\\')) |
        (ProjectAttachment.file_path == filename.replace('\\', '/'))
    ).first()
    
    # 确定文件类型
    file_type = None
    if attachment:
        # 优先使用 file_type，如果为空则从 original_filename 推断
        file_type = attachment.file_type
        if not file_type and attachment.original_filename:
            # 从 original_filename 提取扩展名
            if '.' in attachment.original_filename:
                file_type = attachment.original_filename.rsplit('.', 1)[1].lower()
            else:
                # 如果 original_filename 本身就是类型名（如 'png'）
                file_type = attachment.original_filename.lower()
    
    # 如果仍然无法确定，尝试从文件路径推断
    if not file_type:
        file_ext = os.path.splitext(file_path)[1].lower()
        if file_ext:
            file_type = file_ext[1:].lower()  # 去掉点号
    
    # 获取文件MIME类型
    file_type_map = {
        'pdf': 'application/pdf',
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg',
        'png': 'image/png',
        'gif': 'image/gif',
        'doc': 'application/msword',
        'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'zip': 'application/zip',
        'rar': 'application/x-rar-compressed'
    }
    
    if file_type and file_type.lower() in file_type_map:
        mimetype = file_type_map[file_type.lower()]
    else:
        # 尝试使用 mimetypes 模块推断
        mimetype, _ = mimetypes.guess_type(file_path)
        if mimetype is None:
            mimetype = 'application/octet-stream'
    
    # 对于图片和PDF，如果不强制下载，确保浏览器能够预览
    # 注意：即使文件名没有扩展名，也要根据 file_type 设置正确的 MIME 类型
    if not as_attachment:
        if file_type and file_type.lower() in ['jpg', 'jpeg', 'png', 'gif', 'pdf']:
            # 确保使用正确的MIME类型
            if file_type.lower() == 'jpg' or file_type.lower() == 'jpeg':
                mimetype = 'image/jpeg'
            elif file_type.lower() == 'png':
                mimetype = 'image/png'
            elif file_type.lower() == 'gif':
                mimetype = 'image/gif'
            elif file_type.lower() == 'pdf':
                mimetype = 'application/pdf'
    
    # send_from_directory需要相对于upload_folder的路径
    # 使用os.path.relpath获取相对路径，然后转换为正斜杠用于URL
    relative_filename = os.path.relpath(file_path, upload_folder)
    # 确保使用正斜杠（URL标准）
    relative_filename = relative_filename.replace('\\', '/')
    
    # 创建响应
    # 对于图片文件，如果文件名没有扩展名，需要确保浏览器能识别
    # 先设置正确的响应头，再发送文件
    if not as_attachment and file_type and file_type.lower() in ['jpg', 'jpeg', 'png', 'gif', 'pdf']:
        # 确保使用正确的MIME类型
        if file_type.lower() == 'jpg' or file_type.lower() == 'jpeg':
            mimetype = 'image/jpeg'
        elif file_type.lower() == 'png':
            mimetype = 'image/png'
        elif file_type.lower() == 'gif':
            mimetype = 'image/gif'
        elif file_type.lower() == 'pdf':
            mimetype = 'application/pdf'
    
    # 如果下载文件且文件名没有扩展名，需要添加扩展名
    download_filename = None
    if as_attachment:
        # 确保 file_type 已正确识别
        if not file_type and attachment:
            if attachment.file_type:
                file_type = attachment.file_type
            elif attachment.original_filename:
                if '.' in attachment.original_filename:
                    file_type = attachment.original_filename.rsplit('.', 1)[1].lower()
                else:
                    # 如果 original_filename 本身就是类型名（如 'png'）
                    file_type = attachment.original_filename.lower()
        
        # 检查文件名是否有扩展名
        base_filename = os.path.basename(relative_filename)
        if '.' not in base_filename and file_type:
            # 如果文件名没有扩展名，添加扩展名
            if attachment and attachment.original_filename and '.' in attachment.original_filename:
                # 使用原始文件名（带扩展名）
                download_filename = attachment.original_filename
            else:
                # 使用文件类型作为扩展名
                download_filename = base_filename + '.' + file_type.lower()
    
    # 对于图片文件预览，不要使用 download_name，避免浏览器下载
    if not as_attachment and file_type and file_type.lower() in ['jpg', 'jpeg', 'png', 'gif']:
        response = send_from_directory(
            upload_folder, 
            relative_filename, 
            as_attachment=False,
            mimetype=mimetype
        )
    else:
        response = send_from_directory(
            upload_folder, 
            relative_filename, 
            as_attachment=as_attachment,
            mimetype=mimetype,
            download_name=download_filename
        )
    
    # 对于图片和PDF文件，确保浏览器能够预览而不是下载
    # 重要：即使文件名没有扩展名，也要根据 file_type 强制设置正确的响应头
    if not as_attachment:
        # 确保 file_type 已正确识别（可能在响应创建时丢失）
        if not file_type and attachment:
            if attachment.file_type:
                file_type = attachment.file_type
            elif attachment.original_filename:
                if '.' in attachment.original_filename:
                    file_type = attachment.original_filename.rsplit('.', 1)[1].lower()
                else:
                    # 如果 original_filename 本身就是类型名（如 'png'）
                    file_type = attachment.original_filename.lower()
        
        if file_type and file_type.lower() in ['jpg', 'jpeg', 'png', 'gif', 'pdf']:
            # 强制设置 Content-Disposition 为 inline，覆盖任何可能的 attachment 设置
            # 对于图片，必须明确设置为 inline，否则浏览器可能下载而不是预览
            if file_type.lower() in ['jpg', 'jpeg', 'png', 'gif']:
                response.headers['Content-Disposition'] = 'inline'
                # 确保 MIME 类型正确（覆盖 send_from_directory 可能设置的错误类型）
                if file_type.lower() == 'jpg' or file_type.lower() == 'jpeg':
                    response.headers['Content-Type'] = 'image/jpeg'
                elif file_type.lower() == 'png':
                    response.headers['Content-Type'] = 'image/png'
                elif file_type.lower() == 'gif':
                    response.headers['Content-Type'] = 'image/gif'
                # 移除可能存在的 filename 参数，避免浏览器下载
                if 'filename=' in response.headers.get('Content-Disposition', ''):
                    response.headers['Content-Disposition'] = 'inline'
            elif file_type.lower() == 'pdf':
                response.headers['Content-Disposition'] = 'inline'
                response.headers['Content-Type'] = 'application/pdf'
    
    return response

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)

