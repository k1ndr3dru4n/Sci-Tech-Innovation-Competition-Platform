"""
个人资料路由
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_required, current_user
from models import db, User
from forms import ProfileForm

profile_bp = Blueprint('profile', __name__)

@profile_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """个人资料页面"""
    form = ProfileForm()
    
    if form.validate_on_submit():
        # 更新基本信息
        current_user.real_name = form.real_name.data
        # 邮箱为选填项，如果填写了则验证并更新
        email_input = form.email.data.strip() if form.email.data else ''
        # 如果邮箱值等于学工号，说明是浏览器自动填充的，忽略它
        if email_input and email_input == current_user.work_id:
            email_input = ''
        if email_input:
            # 检查邮箱是否被其他用户使用
            existing_user = User.query.filter(
                User.email == email_input,
                User.id != current_user.id
            ).first()
            if existing_user:
                flash('该邮箱已被其他用户使用', 'error')
                # 重新填充表单，但不填充邮箱
                form.real_name.data = current_user.real_name
                form.email.data = ''  # 设置为空字符串，不填充
                if current_user.work_id:
                    form.college.data = current_user.college
                if current_user.role in ['school_admin', 'judge']:
                    form.unit.data = current_user.unit
                form.contact_info.data = current_user.contact_info
                return render_template('profile/profile.html', form=form)
            current_user.email = email_input
        else:
            # 如果用户没有填写邮箱，保持原值不变（不清空已有邮箱，也不设置为学工号）
            # 不更新邮箱字段
            pass
        
        # 学院字段不可修改（由数据库预设），不更新
        # 如果是校级管理员或专家，可以更新单位
        if current_user.role in ['school_admin', 'judge'] and form.unit.data:
            current_user.unit = form.unit.data.strip() if form.unit.data else None
        
        # 更新联系方式
        current_user.contact_info = form.contact_info.data
        
        # 如果提供了新密码，验证旧密码并更新
        if form.new_password.data:
            if not form.old_password.data:
                flash('请输入当前密码', 'error')
                return render_template('profile/profile.html', form=form)
            
            if not current_user.check_password(form.old_password.data):
                flash('当前密码错误', 'error')
                return render_template('profile/profile.html', form=form)
            
            if form.new_password.data != form.confirm_password.data:
                flash('两次新密码输入不一致', 'error')
                return render_template('profile/profile.html', form=form)
            
            current_user.set_password(form.new_password.data)
        
        db.session.commit()
        flash('个人资料更新成功', 'success')
        # 设置标记，表示刚刚保存成功，邮箱字段应该为空
        session['profile_saved'] = True
        return redirect(url_for('profile.profile'))
    
    # 填充表单数据（GET 请求或验证失败时）
    form.real_name.data = current_user.real_name
    # 邮箱不默认填写，由用户自行输入（即使数据库中有邮箱也不填充）
    # 如果刚刚保存成功，确保邮箱字段为空
    if session.get('profile_saved'):
        form.email.data = ''
        session.pop('profile_saved', None)
    else:
        form.email.data = ''  # 明确设置为空字符串，不填充任何值
    # 学院字段（学生和学院管理员）：只读，由数据库预设
    if current_user.work_id:
        form.college.data = current_user.college
    # 单位字段（校级管理员和专家）
    if current_user.role in ['school_admin', 'judge']:
        form.unit.data = current_user.unit
    form.contact_info.data = current_user.contact_info
    
    return render_template('profile/profile.html', form=form)

