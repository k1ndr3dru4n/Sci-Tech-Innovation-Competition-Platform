"""
应用配置文件
"""
import os
from pathlib import Path

basedir = Path(__file__).parent.absolute()

class Config:
    """应用配置类"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        f'sqlite:///{basedir}/competition.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # 文件上传配置
    UPLOAD_FOLDER = basedir / 'uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png', 'zip', 'rar'}
    
    # 证书生成配置
    CERTIFICATE_FOLDER = basedir / 'certificates'
    
    # 分页配置
    POSTS_PER_PAGE = 20

