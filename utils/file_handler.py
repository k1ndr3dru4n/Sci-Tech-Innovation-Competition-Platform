"""
文件处理工具
"""
import os
from werkzeug.utils import secure_filename
from config import Config
from pathlib import Path

def allowed_file(filename):
    """检查文件扩展名是否允许"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS

def save_uploaded_file(file, subfolder=''):
    """保存上传的文件"""
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        # 生成唯一文件名
        from datetime import datetime
        import uuid
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_id = str(uuid.uuid4())[:8]
        name, ext = os.path.splitext(filename)
        unique_filename = f"{timestamp}_{unique_id}{ext}"
        
        # 创建目录
        upload_dir = Path(Config.UPLOAD_FOLDER) / subfolder
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        # 保存文件
        file_path = upload_dir / unique_filename
        file.save(str(file_path))
        
        return {
            'filename': unique_filename,
            'original_filename': filename,
            'file_path': str(file_path.relative_to(Config.UPLOAD_FOLDER)),
            'file_size': os.path.getsize(file_path),
            'file_type': ext[1:].lower()
        }
    return None

def get_file_preview_url(file_path, file_type):
    """获取文件预览URL"""
    # 对于图片，直接返回URL
    if file_type.lower() in ['jpg', 'jpeg', 'png', 'gif']:
        return f'/uploads/{file_path}'
    # 对于PDF，可以使用浏览器内置预览
    elif file_type.lower() == 'pdf':
        return f'/uploads/{file_path}'
    # 其他文件类型可能需要特殊处理
    else:
        return None

