"""
权限装饰器
"""
from functools import wraps
from flask import abort, current_app, redirect, url_for, flash
from flask_login import current_user
from models import UserRole

def role_required(*roles):
    """要求特定角色的装饰器"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)
            if current_user.role not in roles:
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def student_required(f):
    """要求学生角色"""
    return role_required(UserRole.STUDENT)(f)

def college_admin_required(f):
    """要求学院管理员角色，并确保已设置学院"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            abort(401)
        if current_user.role != UserRole.COLLEGE_ADMIN:
            abort(403)
        # 确保学院管理员已设置学院
        if not current_user.college:
            flash('您的账户未设置所属学院，请先完善个人资料', 'error')
            return redirect(url_for('profile.profile'))
        return f(*args, **kwargs)
    return decorated_function

def school_admin_required(f):
    """要求校级管理员角色"""
    return role_required(UserRole.SCHOOL_ADMIN)(f)

def judge_required(f):
    """要求评委角色"""
    return role_required(UserRole.JUDGE)(f)

