"""
校外评委路由
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models import db, Project, JudgeAssignment, Score
from forms import ScoreForm
from utils.decorators import judge_required

judge_bp = Blueprint('judge', __name__)

@judge_bp.route('/dashboard', methods=['GET', 'POST'])
@login_required
@judge_required
def dashboard():
    """评委首页 - 显示基本信息和编辑表单"""
    from forms import ProfileForm
    from models import User
    
    form = ProfileForm()
    
    if form.validate_on_submit():
        has_errors = False
        
        # 更新基本信息
        current_user.real_name = form.real_name.data
        # 邮箱为选填项，如果填写了则验证并更新
        email_input = form.email.data.strip() if form.email.data else ''
        # 如果邮箱值等于用户名，说明是浏览器自动填充的，忽略它
        if email_input and email_input == current_user.username:
            email_input = ''
        if email_input:
            # 检查邮箱是否被其他用户使用
            existing_user = User.query.filter(
                User.email == email_input,
                User.id != current_user.id
            ).first()
            if existing_user:
                flash('该邮箱已被其他用户使用', 'error')
                has_errors = True
            else:
                current_user.email = email_input
        else:
            # 如果用户没有填写邮箱，保持原值不变
            pass
        
        # 更新单位
        if form.unit.data:
            current_user.unit = form.unit.data.strip() if form.unit.data else None
        
        # 更新联系方式
        current_user.contact_info = form.contact_info.data
        
        # 如果提供了新密码，验证旧密码并更新
        if form.new_password.data:
            if not form.old_password.data:
                flash('请输入当前密码', 'error')
                has_errors = True
            elif not current_user.check_password(form.old_password.data):
                flash('当前密码错误', 'error')
                has_errors = True
            elif form.new_password.data != form.confirm_password.data:
                flash('两次新密码输入不一致', 'error')
                has_errors = True
            else:
                current_user.set_password(form.new_password.data)
        
        if has_errors:
            # 如果有错误，重新填充表单数据并渲染模板
            form.real_name.data = current_user.real_name
            form.email.data = ''
            if current_user.role in ['school_admin', 'judge']:
                form.unit.data = current_user.unit
            form.contact_info.data = current_user.contact_info
            return render_template('judge/dashboard.html', form=form)
        
        db.session.commit()
        flash('个人资料更新成功', 'success')
        return redirect(url_for('judge.dashboard'))
    
    # 填充表单数据（GET 请求或验证失败时）
    form.real_name.data = current_user.real_name
    form.email.data = ''  # 邮箱不默认填写
    if current_user.role in ['school_admin', 'judge']:
        form.unit.data = current_user.unit
    form.contact_info.data = current_user.contact_info
    
    return render_template('judge/dashboard.html', form=form)

@judge_bp.route('/projects')
@login_required
@judge_required
def projects():
    """评审项目列表"""
    # 获取分配给当前评委的所有项目
    assignments = JudgeAssignment.query.filter_by(
        judge_id=current_user.id,
        is_active=True
    ).all()
    
    projects = [assignment.project for assignment in assignments]
    
    return render_template('judge/projects.html', projects=projects)

@judge_bp.route('/project/<int:project_id>')
@login_required
@judge_required
def view_project(project_id):
    """查看项目详情（浏览全部材料）"""
    project = Project.query.get_or_404(project_id)
    
    # 检查权限：只能查看分配给自己的项目
    assignment = JudgeAssignment.query.filter_by(
        judge_id=current_user.id,
        project_id=project_id,
        is_active=True
    ).first()
    
    if not assignment:
        flash('您没有权限查看此项目', 'error')
        return redirect(url_for('judge.projects'))
    
    # 获取已评分信息
    existing_score = Score.query.filter_by(
        project_id=project_id,
        judge_id=current_user.id
    ).first()
    
    return render_template('judge/view_project.html', project=project, existing_score=existing_score)

@judge_bp.route('/project/<int:project_id>/score', methods=['GET', 'POST'])
@login_required
@judge_required
def score_project(project_id):
    """在线打分"""
    project = Project.query.get_or_404(project_id)
    
    # 检查权限
    assignment = JudgeAssignment.query.filter_by(
        judge_id=current_user.id,
        project_id=project_id,
        is_active=True
    ).first()
    
    if not assignment:
        flash('您没有权限为此项目打分', 'error')
        return redirect(url_for('judge.projects'))
    
    form = ScoreForm()
    
    if form.validate_on_submit():
        # 检查是否已评分
        existing_score = Score.query.filter_by(
            project_id=project_id,
            judge_id=current_user.id
        ).first()
        
        if existing_score:
            # 更新评分
            existing_score.score_value = form.score_value.data
            existing_score.comment = form.comment.data
            flash('评分已更新', 'success')
        else:
            # 创建新评分
            score = Score(
                project_id=project_id,
                judge_id=current_user.id,
                score_value=form.score_value.data,
                comment=form.comment.data
            )
            db.session.add(score)
            flash('评分提交成功', 'success')
        
        db.session.commit()
        return redirect(url_for('judge.view_project', project_id=project_id))
    
    # 如果是GET请求，加载已有评分
    existing_score = Score.query.filter_by(
        project_id=project_id,
        judge_id=current_user.id
    ).first()
    
    if existing_score:
        form.score_value.data = existing_score.score_value
        form.comment.data = existing_score.comment
    
    return render_template('judge/score_project.html', project=project, form=form)

@judge_bp.route('/project/<int:project_id>/score_ajax', methods=['POST'])
@login_required
@judge_required
def score_project_ajax():
    """AJAX驱动的实时打分接口"""
    project = Project.query.get_or_404(project_id)
    
    # 检查权限
    assignment = JudgeAssignment.query.filter_by(
        judge_id=current_user.id,
        project_id=project_id,
        is_active=True
    ).first()
    
    if not assignment:
        return jsonify({'error': '没有权限'}), 403
    
    data = request.get_json()
    
    # 检查是否已评分
    existing_score = Score.query.filter_by(
        project_id=project_id,
        judge_id=current_user.id
    ).first()
    
    if existing_score:
        existing_score.score_value = data.get('score_value')
        existing_score.comment = data.get('comment', '')
    else:
        score = Score(
            project_id=project_id,
            judge_id=current_user.id,
            score_value=data.get('score_value'),
            comment=data.get('comment', '')
        )
        db.session.add(score)
    
    db.session.commit()
    return jsonify({'success': True, 'message': '评分已保存'})

