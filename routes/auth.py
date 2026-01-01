"""
用户认证路由
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_user, logout_user, login_required, current_user
from models import User, UserRole, db
from forms import LoginForm, JudgeLoginForm, RegisterForm, JudgeRegisterForm
from utils.timezone import beijing_now

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
                # 更新最后登录时间
                user.last_login = beijing_now()
                db.session.commit()
                # 自动识别角色（使用数据库中存储的角色）
                login_user(user, remember=form.remember_me.data)
                # 初始化session中的当前角色为主角色
                session['current_role'] = user.role
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
        # 通过用户名查找用户（仅限评委角色）
        user = User.query.filter(
            User.username == form.username.data,
            User.role == UserRole.JUDGE
        ).first()
        
        if user and user.check_password(form.password.data):
            if user.is_active:
                # 更新最后登录时间
                user.last_login = beijing_now()
                db.session.commit()
                login_user(user, remember=form.remember_me.data)
                # 初始化session中的当前角色为主角色
                session['current_role'] = user.role
                next_page = request.args.get('next')
                return redirect(next_page or url_for('dashboard.dashboard'))
            else:
                flash('账户已被禁用，请联系管理员', 'error')
        else:
            flash('用户名或密码错误', 'error')
    
    return render_template('auth/judge_login.html', form=form)

@auth_bp.route('/logout')
@login_required
def logout():
    """用户登出"""
    # 保存用户角色用于跳转
    user_role = current_user.role
    session.pop('current_role', None)
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

@auth_bp.route('/switch_role', methods=['POST'])
@login_required
def switch_role():
    """切换当前角色"""
    role = request.form.get('role')
    
    if not role:
        flash('请选择角色', 'error')
        return redirect(url_for('dashboard.dashboard'))
    
    # 检查用户是否拥有该角色
    if not current_user.has_role(role):
        flash('您没有该角色权限', 'error')
        return redirect(url_for('dashboard.dashboard'))
    
    # 更新session中的当前角色
    session['current_role'] = role
    session.permanent = True  # 确保session被保存
    
    role_names = {
        'student': '学生',
        'college_admin': '学院管理员',
        'school_admin': '校级管理员',
        'judge': '校外评委'
    }
    role_name = role_names.get(role, role)
    
    flash(f'已切换到{role_name}', 'success')
    
    # 根据切换后的角色跳转到对应的dashboard
    if role == UserRole.STUDENT:
        return redirect(url_for('student.dashboard'))
    elif role == UserRole.COLLEGE_ADMIN:
        return redirect(url_for('college_admin.dashboard'))
    elif role == UserRole.SCHOOL_ADMIN:
        return redirect(url_for('school_admin.dashboard'))
    elif role == UserRole.JUDGE:
        return redirect(url_for('judge.dashboard'))
    else:
        return redirect(url_for('dashboard.dashboard'))

