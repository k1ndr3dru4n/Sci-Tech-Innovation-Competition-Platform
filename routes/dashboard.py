"""
通用dashboard路由
"""
from flask import Blueprint, render_template, redirect, url_for, session
from flask_login import login_required, current_user
from models import UserRole
from utils.decorators import get_current_role

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/dashboard')
@login_required
def dashboard():
    """根据用户角色跳转到对应的dashboard"""
    current_role = get_current_role()
    
    if current_role == UserRole.STUDENT:
        return redirect(url_for('student.dashboard'))
    elif current_role == UserRole.COLLEGE_ADMIN:
        return redirect(url_for('college_admin.dashboard'))
    elif current_role == UserRole.SCHOOL_ADMIN:
        return redirect(url_for('school_admin.dashboard'))
    elif current_role == UserRole.JUDGE:
        return redirect(url_for('judge.dashboard'))
    else:
        return redirect(url_for('auth.login'))

