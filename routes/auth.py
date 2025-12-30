"""
用户认证路由
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from models import User, UserRole, db
from forms import LoginForm, JudgeLoginForm, RegisterForm, JudgeRegisterForm

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """校内用户登录（学工号登录）"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.dashboard'))
    
    form = LoginForm()
    if form.validate_on_submit():
        # 通过学工号查找用户
        user = User.query.filter_by(work_id=form.work_id.data).first()
        if user and user.check_password(form.password.data):
            if user.is_active:
                # 自动识别角色（使用数据库中存储的角色）
                login_user(user, remember=form.remember_me.data)
                next_page = request.args.get('next')
                return redirect(next_page or url_for('dashboard.dashboard'))
            else:
                flash('账户已被禁用，请联系管理员', 'error')
        else:
            flash('学工号或密码错误', 'error')
    
    return render_template('auth/login.html', form=form)

@auth_bp.route('/judge/login', methods=['GET', 'POST'])
def judge_login():
    """校外专家登录"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.dashboard'))
    
    form = JudgeLoginForm()
    if form.validate_on_submit():
        # 通过用户名或邮箱查找用户（仅限评委角色）
        user = User.query.filter(
            (User.username == form.username.data) | (User.email == form.username.data),
            User.role == UserRole.JUDGE
        ).first()
        
        if user and user.check_password(form.password.data):
            if user.is_active:
                login_user(user, remember=form.remember_me.data)
                next_page = request.args.get('next')
                return redirect(next_page or url_for('dashboard.dashboard'))
            else:
                flash('账户已被禁用，请联系管理员', 'error')
        else:
            flash('用户名/邮箱或密码错误', 'error')
    
    return render_template('auth/judge_login.html', form=form)

@auth_bp.route('/logout')
@login_required
def logout():
    """用户登出"""
    # 保存用户角色用于跳转
    user_role = current_user.role
    logout_user()
    flash('您已成功登出', 'info')
    # 根据用户角色跳转到对应的登录页面
    if user_role == UserRole.JUDGE:
        return redirect(url_for('auth.judge_login'))
    return redirect(url_for('auth.login'))

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """校内用户注册（已禁用）"""
    flash('注册功能已禁用，请联系管理员创建账户', 'error')
    return redirect(url_for('auth.login'))

@auth_bp.route('/judge/register', methods=['GET', 'POST'])
def judge_register():
    """校外专家注册（已禁用）"""
    flash('注册功能已禁用，请联系管理员创建账户', 'error')
    return redirect(url_for('auth.judge_login'))

