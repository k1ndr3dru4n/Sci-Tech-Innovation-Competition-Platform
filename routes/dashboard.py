"""
通用dashboard路由
"""
from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user
from models import UserRole

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/dashboard')
@login_required
def dashboard():
    """根据用户角色跳转到对应的dashboard"""
    role = current_user.role
    
    if role == UserRole.STUDENT:
        return redirect(url_for('student.dashboard'))
    elif role == UserRole.COLLEGE_ADMIN:
        return redirect(url_for('college_admin.dashboard'))
    elif role == UserRole.SCHOOL_ADMIN:
        return redirect(url_for('school_admin.dashboard'))
    elif role == UserRole.JUDGE:
        return redirect(url_for('judge.dashboard'))
    else:
        return redirect(url_for('auth.login'))

