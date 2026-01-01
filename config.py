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
    
    # AI脱敏识别配置
    QWEN_API_KEY = os.environ.get('QWEN_API_KEY') or 'sk-c721f79442294bc88297e5404538571e'  # 千问API密钥
    QWEN_API_BASE_URL = os.environ.get('QWEN_API_BASE_URL') or 'https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation'  # 文本生成API
    QWEN_VL_API_BASE_URL = os.environ.get('QWEN_VL_API_BASE_URL') or 'https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation'  # 视觉模型API
    SENSITIVE_KEYWORDS = ['西南交通大学']  # 敏感关键词列表，可根据需要修改

