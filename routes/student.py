"""
学生端路由
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, send_from_directory, jsonify, session
from flask_login import login_required, current_user
from models import db, User, Team, Project, Competition, Track, ProjectTrack, ProjectMember, ReviewStatus, TeamMember, UserRole, Score, ProjectAttachment, Award, ExternalAward
from forms import ProjectForm, ExternalAwardForm
from utils.decorators import student_required
from utils.file_handler import save_uploaded_file, allowed_file
from utils.timezone import beijing_now
from config import Config
from pathlib import Path
from datetime import datetime
import os
import random

student_bp = Blueprint('student', __name__)

@student_bp.route('/dashboard', methods=['GET', 'POST'])
@login_required
@student_required
def dashboard():
    """学生首页 - 显示个人信息和编辑表单"""
    from forms import ProfileForm
    
    form = ProfileForm()
    
    if form.validate_on_submit():
        has_errors = False
        
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
                has_errors = True
            else:
                current_user.email = email_input
        else:
            # 如果用户没有填写邮箱，保持原值不变
            pass
        
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
            form.contact_info.data = current_user.contact_info
            return render_template('student/dashboard.html', form=form)
        
        db.session.commit()
        flash('个人资料更新成功', 'success')
        return redirect(url_for('student.dashboard'))
    
    # 填充表单数据（GET 请求或验证失败时）
    form.real_name.data = current_user.real_name
    form.email.data = ''  # 邮箱不默认填写
    form.contact_info.data = current_user.contact_info
    
    return render_template('student/dashboard.html', form=form)

@student_bp.route('/projects')
@login_required
@student_required
def projects():
    """我的项目页面"""
    # 获取当前用户参与的所有队伍
    user_teams = TeamMember.query.filter_by(user_id=current_user.id).all()
    teams = [tm.team for tm in user_teams]
    
    # 获取通过队伍关联的项目
    projects = []
    for team in teams:
        projects.extend(team.projects.all())
    
    # 获取通过项目成员关联的项目（包括被添加但未确认的项目）
    project_members = ProjectMember.query.filter_by(user_id=current_user.id).all()
    project_member_dict = {}  # 用于存储项目ID到ProjectMember的映射
    for pm in project_members:
        if pm.project not in projects:
            projects.append(pm.project)
        project_member_dict[pm.project_id] = pm
    
    # 去重并排序（按创建时间倒序）
    projects = list(set(projects))
    projects.sort(key=lambda p: p.created_at, reverse=True)
    
    return render_template('student/projects.html', projects=projects, project_member_dict=project_member_dict)

@student_bp.route('/draw_defense_order')
@login_required
@student_required
def draw_defense_order_page():
    """答辩抽签页面"""
    # 获取当前用户作为队长的所有队伍
    user_teams = TeamMember.query.filter_by(user_id=current_user.id, role='leader').all()
    leader_teams = [tm.team for tm in user_teams if tm.team.leader_id == current_user.id]
    
    # 获取这些队伍的所有项目
    projects = []
    for team in leader_teams:
        team_projects = team.projects.all()
        for project in team_projects:
            # 只显示进入决赛的项目
            if project.is_final or project.competition.defense_order_start or project.competition.defense_order_end:
                projects.append(project)
    
    # 为每个项目计算抽签状态
    projects_with_status = []
    now = beijing_now()
    
    for project in projects:
        competition = project.competition
        can_draw = False
        order_status = None
        
        if project.defense_order:
            order_status = '已抽取'
        elif competition.defense_order_start and competition.defense_order_end:
            if now < competition.defense_order_start:
                order_status = '未开始'
            elif now >= competition.defense_order_start and now <= competition.defense_order_end:
                can_draw = True
                order_status = '可抽取'
            else:
                order_status = '已过期'
        elif competition.defense_order_start or competition.defense_order_end:
            # 如果只设置了开始或结束时间之一，也允许抽签
            can_draw = True
            order_status = '可抽取'
        else:
            order_status = '未设置'
        
        projects_with_status.append({
            'project': project,
            'can_draw': can_draw,
            'order_status': order_status
        })
    
    return render_template('student/draw_defense_order.html', projects_with_status=projects_with_status)

@student_bp.route('/view_qq_group')
@login_required
@student_required
def view_qq_group():
    """查看QQ群页面"""
    # 获取当前用户参与的所有项目
    user_teams = TeamMember.query.filter_by(user_id=current_user.id).all()
    user_projects = []
    for tm in user_teams:
        team_projects = tm.team.projects.all()
        user_projects.extend(team_projects)
    
    # 获取这些项目所属的竞赛，并筛选出有QQ群信息的竞赛
    competitions_dict = {}
    for project in user_projects:
        competition = project.competition
        if competition.id not in competitions_dict:
            competitions_dict[competition.id] = competition
    
    # 筛选出有QQ群号或二维码的竞赛
    competitions_with_qq = []
    for competition in competitions_dict.values():
        if competition.qq_group_number or competition.qq_group_qrcode:
            competitions_with_qq.append({
                'competition': competition
            })
    
    return render_template('student/view_qq_group.html', competitions_with_qq=competitions_with_qq)

@student_bp.route('/expert_suggestions')
@login_required
@student_required
def expert_suggestions():
    """专家建议页面"""
    # 获取当前用户参与的所有项目
    user_teams = TeamMember.query.filter_by(user_id=current_user.id).all()
    teams = [tm.team for tm in user_teams]
    
    # 获取通过队伍关联的项目
    projects = []
    for team in teams:
        projects.extend(team.projects.all())
    
    # 获取通过项目成员关联的项目
    project_members = ProjectMember.query.filter_by(user_id=current_user.id).all()
    for pm in project_members:
        if pm.project not in projects:
            projects.append(pm.project)
    
    # 去重
    projects = list(set(projects))
    
    # 为每个项目获取专家评分和建议
    projects_with_suggestions = []
    for project in projects:
        scores = Score.query.filter_by(project_id=project.id).all()
        suggestions = [s.comment for s in scores if s.comment]
        if scores or suggestions:
            projects_with_suggestions.append({
                'project': project,
                'scores': scores,
                'suggestions': suggestions,
                'has_suggestions': len(suggestions) > 0
            })
    
    # 按创建时间倒序排序
    projects_with_suggestions.sort(key=lambda x: x['project'].created_at, reverse=True)
    
    return render_template('student/expert_suggestions.html', projects_with_suggestions=projects_with_suggestions)

@student_bp.route('/project_awards')
@login_required
@student_required
def project_awards():
    """项目奖项页面"""
    # 获取当前用户参与的所有项目
    user_teams = TeamMember.query.filter_by(user_id=current_user.id).all()
    teams = [tm.team for tm in user_teams]
    
    # 获取通过队伍关联的项目
    projects = []
    for team in teams:
        projects.extend(team.projects.all())
    
    # 获取通过项目成员关联的项目
    project_members = ProjectMember.query.filter_by(user_id=current_user.id).all()
    for pm in project_members:
        if pm.project not in projects:
            projects.append(pm.project)
    
    # 去重
    projects = list(set(projects))
    
    # 为每个项目获取奖项信息（包括校赛奖项和外部奖项）
    # 只显示有校赛奖项的项目（校级管理员已设置奖项的项目）
    projects_with_awards = []
    for project in projects:
        awards = Award.query.filter_by(project_id=project.id).all()
        external_awards = ExternalAward.query.filter_by(project_id=project.id).all()
        # 只显示有校赛奖项的项目（即校级管理员已设置奖项的项目）
        if awards:
            projects_with_awards.append({
                'project': project,
                'awards': awards,
                'external_awards': external_awards
            })
    
    # 按创建时间倒序排序
    projects_with_awards.sort(key=lambda x: x['project'].created_at, reverse=True)
    
    return render_template('student/project_awards.html', projects_with_awards=projects_with_awards)

@student_bp.route('/upload_awards')
@login_required
@student_required
def upload_awards():
    """奖项上传页面 - 显示可以上传奖项的项目"""
    # 获取当前用户作为队长的所有项目
    user_teams = TeamMember.query.filter_by(user_id=current_user.id).all()
    teams = [tm.team for tm in user_teams if tm.team.leader_id == current_user.id]
    
    # 获取通过队伍关联的项目
    projects = []
    for team in teams:
        projects.extend(team.projects.all())
    
    # 获取通过项目成员关联的项目（作为队长）
    project_members = ProjectMember.query.filter_by(user_id=current_user.id).all()
    for pm in project_members:
        if pm.project.team.leader_id == current_user.id and pm.project not in projects:
            projects.append(pm.project)
    
    # 去重
    projects = list(set(projects))
    
    # 为每个项目获取外部奖项信息
    projects_with_info = []
    for project in projects:
        external_awards = ExternalAward.query.filter_by(project_id=project.id).all()
        projects_with_info.append({
            'project': project,
            'external_awards': external_awards,
            'has_external_awards': len(external_awards) > 0
        })
    
    # 按创建时间倒序排序
    projects_with_info.sort(key=lambda x: x['project'].created_at, reverse=True)
    
    return render_template('student/upload_awards.html', projects_with_info=projects_with_info)

@student_bp.route('/project/<int:project_id>/upload_external_award', methods=['GET', 'POST'])
@login_required
@student_required
def upload_external_award(project_id):
    """上传省赛/国赛奖状"""
    project = Project.query.get_or_404(project_id)
    
    # 检查用户是否为项目队长
    if project.team.leader_id != current_user.id:
        flash('只有项目队长可以上传省赛/国赛奖状', 'error')
        return redirect(url_for('student.upload_awards'))
    
    # 检查项目是否开放奖项收集
    if not project.allow_award_collection:
        flash('该项目尚未开放奖状上传功能，请联系校级管理员', 'error')
        return redirect(url_for('student.upload_awards'))
    
    form = ExternalAwardForm()
    
    if form.validate_on_submit():
        # 处理文件上传
        certificate_file_path = None
        if form.certificate_file.data:
            file = form.certificate_file.data
            file_info = save_uploaded_file(file, subfolder=f'external_awards/project_{project_id}')
            if file_info:
                certificate_file_path = file_info['file_path']
        
        # 创建外部奖项记录
        external_award = ExternalAward(
            project_id=project_id,
            award_level=form.award_level.data,
            award_name=form.award_name.data,
            award_organization=None,  # 不再使用此字段
            award_date=None,  # 不再使用此字段
            certificate_file=certificate_file_path,
            description=form.description.data or None,
            uploaded_by=current_user.id
        )
        
        db.session.add(external_award)
        db.session.commit()
        
        flash('省赛/国赛奖状上传成功', 'success')
        return redirect(url_for('student.upload_awards'))
    
    # 获取已有的外部奖项
    existing_awards = ExternalAward.query.filter_by(project_id=project_id).all()
    
    return render_template('student/upload_external_award.html', 
                         project=project, 
                         form=form,
                         existing_awards=existing_awards)

@student_bp.route('/external_award/<int:award_id>/delete', methods=['POST'])
@login_required
@student_required
def delete_external_award(award_id):
    """删除省赛/国赛奖状"""
    external_award = ExternalAward.query.get_or_404(award_id)
    project = external_award.project
    
    # 检查用户是否为项目队长
    if project.team.leader_id != current_user.id:
        flash('只有项目队长可以删除省赛/国赛奖状', 'error')
        return redirect(url_for('student.project_awards'))
    
    # 删除文件（如果存在）
    if external_award.certificate_file:
        file_path = os.path.join(Config.UPLOAD_FOLDER, external_award.certificate_file)
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as e:
                print(f"删除文件失败: {e}")
    
    db.session.delete(external_award)
    db.session.commit()
    
    flash('省赛/国赛奖状已删除', 'success')
    return redirect(url_for('student.upload_awards'))

@student_bp.route('/team/create', methods=['GET', 'POST'])
@login_required
@student_required
def create_team():
    """创建队伍"""
    if request.method == 'POST':
        team_name = request.form.get('team_name')
        competition_id = request.form.get('competition_id', type=int)
        
        if not team_name or not competition_id:
            flash('请填写完整信息', 'error')
            return render_template('student/create_team.html', competitions=Competition.query.filter_by(is_active=True).all())
        
        # 检查队伍名是否已存在
        if Team.query.filter_by(name=team_name, competition_id=competition_id).first():
            flash('该竞赛中已存在同名队伍', 'error')
            return render_template('student/create_team.html', competitions=Competition.query.filter_by(is_active=True).all())
        
        # 创建队伍
        team = Team(
            name=team_name,
            leader_id=current_user.id,
            competition_id=competition_id
        )
        db.session.add(team)
        db.session.flush()
        
        # 添加队长为成员
        member = TeamMember(team_id=team.id, user_id=current_user.id, role='leader')
        db.session.add(member)
        db.session.commit()
        
        flash('队伍创建成功', 'success')
        return redirect(url_for('student.dashboard'))
    
    competitions = Competition.query.filter_by(is_active=True).all()
    return render_template('student/create_team.html', competitions=competitions)

@student_bp.route('/project/create', methods=['GET', 'POST'])
@login_required
@student_required
def create_project_select_competition():
    """选择竞赛创建项目"""
    if request.method == 'POST':
        competition_id = request.form.get('competition_id', type=int)
        if not competition_id:
            flash('请选择竞赛', 'error')
            return redirect(url_for('student.create_project_select_competition'))
        
        # 检查用户是否有该竞赛的队伍，如果没有则创建
        competition = Competition.query.get_or_404(competition_id)
        user_teams = TeamMember.query.filter_by(user_id=current_user.id).all()
        leader_teams = [tm.team for tm in user_teams if tm.team.leader_id == current_user.id and tm.team.competition_id == competition_id]
        
        if not leader_teams:
            # 自动创建队伍
            team = Team(
                name=f'{current_user.real_name}的队伍',
                leader_id=current_user.id,
                competition_id=competition_id
            )
            db.session.add(team)
            db.session.flush()
            
            # 添加队长为成员
            member = TeamMember(team_id=team.id, user_id=current_user.id, role='leader')
            db.session.add(member)
            db.session.commit()
            
            team_id = team.id
        else:
            # 使用第一个队伍
            team_id = leader_teams[0].id
        
        # 将竞赛ID和队伍ID存储在session中，不立即创建项目
        from flask import session
        session['pending_competition_id'] = competition_id
        session['pending_team_id'] = team_id
        
        return redirect(url_for('student.create_project_info'))
    
    # GET 请求：显示竞赛选择页面（只显示已发布的竞赛）
    competitions = Competition.query.filter_by(is_active=True, is_published=True).all()
    return render_template('student/select_competition.html', competitions=competitions)

@student_bp.route('/project/info', methods=['GET', 'POST'])
@student_bp.route('/project/<int:project_id>/info', methods=['GET', 'POST'])
@login_required
@student_required
def create_project_info(project_id=None):
    """填写项目信息（第一步）"""
    from flask import session
    
    project = None
    competition = None
    
    # 如果提供了project_id，说明是编辑已有项目
    if project_id:
        project = Project.query.get_or_404(project_id)
        # 检查权限：只有队长可以编辑
        if project.team.leader_id != current_user.id:
            flash('只有队长可以编辑项目', 'error')
            return redirect(url_for('student.view_project', project_id=project_id))
        competition = project.competition
    else:
        # 新项目，从session获取信息
        competition_id = session.get('pending_competition_id')
        team_id = session.get('pending_team_id')
        
        if not competition_id or not team_id:
            flash('请先选择竞赛', 'error')
            return redirect(url_for('student.create_project_select_competition'))
        
        competition = Competition.query.get_or_404(competition_id)
        # 验证队伍属于当前用户
        team = Team.query.get_or_404(team_id)
        if team.leader_id != current_user.id:
            flash('权限错误', 'error')
            return redirect(url_for('student.projects'))
    
    form = ProjectForm()
    
    # 获取竞赛类型
    competition_type = competition.competition_type if competition else None
    
    # 如果是编辑已有项目，填充表单数据（GET请求时）
    if project and request.method == 'GET':
        form.title.data = project.title
        form.description.data = project.description
        form.project_category.data = project.project_category
        form.push_college.data = project.push_college
        form.project_type.data = getattr(project, 'project_type', None)
        form.project_field.data = getattr(project, 'project_field', None)
        form.innovation_points.data = getattr(project, 'innovation_points', None)
        form.development_status.data = getattr(project, 'development_status', None)
        form.awards_patents_papers.data = getattr(project, 'awards_patents_papers', None)
    # POST请求时，Flask-WTF会自动保留表单数据，但如果验证失败且是已有项目，需要确保数据正确
    elif project and request.method == 'POST':
        # 如果表单数据为空（可能是验证失败），从项目对象恢复
        if not form.title.data and project.title:
            form.title.data = project.title
        if not form.description.data and project.description:
            form.description.data = project.description
        if not form.project_category.data and project.project_category:
            form.project_category.data = project.project_category
        if not form.push_college.data and project.push_college:
            form.push_college.data = project.push_college
        if not form.project_type.data and getattr(project, 'project_type', None):
            form.project_type.data = getattr(project, 'project_type', None)
        if not form.project_field.data and getattr(project, 'project_field', None):
            form.project_field.data = getattr(project, 'project_field', None)
        if not form.innovation_points.data and getattr(project, 'innovation_points', None):
            form.innovation_points.data = getattr(project, 'innovation_points', None)
        if not form.development_status.data and getattr(project, 'development_status', None):
            form.development_status.data = getattr(project, 'development_status', None)
        if not form.awards_patents_papers.data and getattr(project, 'awards_patents_papers', None):
            form.awards_patents_papers.data = getattr(project, 'awards_patents_papers', None)
    
    if request.method == 'POST':
        # 根据竞赛类型进行不同的验证
        errors = []
        if not form.title.data or not form.title.data.strip():
            errors.append('项目名称不能为空')
        if not form.description.data or not form.description.data.strip():
            errors.append('项目简介不能为空')
        
        # 根据竞赛类型验证特定字段
        if competition_type == '中国国际大学生创新大赛"青年红色筑梦之旅"赛道':
            if not form.project_category.data or form.project_category.data == '':
                errors.append('请选择项目组别')
            if not form.push_college.data or not form.push_college.data.strip():
                errors.append('作品推送学院不能为空')
            if not form.innovation_points.data or not form.innovation_points.data.strip():
                errors.append('项目创新点不能为空')
            if not form.development_status.data or not form.development_status.data.strip():
                errors.append('项目开发现状不能为空')
            if not form.awards_patents_papers.data or not form.awards_patents_papers.data.strip():
                errors.append('获奖、专利及论文情况不能为空')
        elif competition_type == '"挑战杯"全国大学生课外学术科技作品竞赛':
            if not form.project_type.data or form.project_type.data == '':
                errors.append('请选择作品类别')
            if not form.push_college.data or not form.push_college.data.strip():
                errors.append('作品推送学院不能为空')
            if not form.innovation_points.data or not form.innovation_points.data.strip():
                errors.append('项目创新点不能为空')
            if not form.development_status.data or not form.development_status.data.strip():
                errors.append('项目开发现状不能为空')
            if not form.awards_patents_papers.data or not form.awards_patents_papers.data.strip():
                errors.append('获奖、专利及论文情况不能为空')
        elif competition_type == '"挑战杯"中国大学生创业计划大赛':
            if not form.project_field.data or form.project_field.data == '':
                errors.append('请选择项目领域')
            if not form.push_college.data or not form.push_college.data.strip():
                errors.append('作品推送学院不能为空')
            if not form.innovation_points.data or not form.innovation_points.data.strip():
                errors.append('项目创新点不能为空')
            if not form.development_status.data or not form.development_status.data.strip():
                errors.append('项目开发现状不能为空')
            if not form.awards_patents_papers.data or not form.awards_patents_papers.data.strip():
                errors.append('获奖、专利及论文情况不能为空')
        
        if errors:
            for error in errors:
                flash(error, 'error')
            # 验证失败时，重新填充表单数据，避免用户输入丢失
            if project:
                form.title.data = form.title.data or project.title
                form.description.data = form.description.data or project.description
                form.project_category.data = form.project_category.data or project.project_category
                form.push_college.data = form.push_college.data or project.push_college
                form.project_type.data = form.project_type.data or getattr(project, 'project_type', None)
                form.project_field.data = form.project_field.data or getattr(project, 'project_field', None)
                form.innovation_points.data = form.innovation_points.data or getattr(project, 'innovation_points', None)
                form.development_status.data = form.development_status.data or getattr(project, 'development_status', None)
                form.awards_patents_papers.data = form.awards_patents_papers.data or getattr(project, 'awards_patents_papers', None)
        else:
            # 表单验证通过，处理数据
            if not project:
                # 新项目，创建
                team_id = session.get('pending_team_id')
                competition_id = session.get('pending_competition_id')
                
                project = Project(
                    team_id=team_id,
                    competition_id=competition_id,
                    title=form.title.data.strip(),
                    description=form.description.data.strip(),
                    project_category=form.project_category.data if competition_type == '中国国际大学生创新大赛"青年红色筑梦之旅"赛道' else None,
                    push_college=form.push_college.data.strip() if form.push_college.data else None,
                    status=ReviewStatus.DRAFT
                )
                # 根据竞赛类型设置特定字段
                if competition_type == '中国国际大学生创新大赛"青年红色筑梦之旅"赛道':
                    project.innovation_points = form.innovation_points.data.strip() if form.innovation_points.data else None
                    project.development_status = form.development_status.data.strip() if form.development_status.data else None
                    project.awards_patents_papers = form.awards_patents_papers.data.strip() if form.awards_patents_papers.data else None
                elif competition_type == '"挑战杯"全国大学生课外学术科技作品竞赛':
                    project.project_type = form.project_type.data
                    project.innovation_points = form.innovation_points.data.strip() if form.innovation_points.data else None
                    project.development_status = form.development_status.data.strip() if form.development_status.data else None
                    project.awards_patents_papers = form.awards_patents_papers.data.strip() if form.awards_patents_papers.data else None
                elif competition_type == '"挑战杯"中国大学生创业计划大赛':
                    project.project_field = form.project_field.data
                    project.innovation_points = form.innovation_points.data.strip() if form.innovation_points.data else None
                    project.development_status = form.development_status.data.strip() if form.development_status.data else None
                    project.awards_patents_papers = form.awards_patents_papers.data.strip() if form.awards_patents_papers.data else None
                
                db.session.add(project)
                db.session.flush()
                
                # 清除session中的临时数据
                session.pop('pending_competition_id', None)
                session.pop('pending_team_id', None)
            else:
                # 更新已有项目
                project.title = form.title.data.strip()
                project.description = form.description.data.strip()
                # 根据竞赛类型更新特定字段
                if competition_type == '中国国际大学生创新大赛"青年红色筑梦之旅"赛道':
                    project.project_category = form.project_category.data
                    project.push_college = form.push_college.data.strip() if form.push_college.data else None
                    project.innovation_points = form.innovation_points.data.strip() if form.innovation_points.data else None
                    project.development_status = form.development_status.data.strip() if form.development_status.data else None
                    project.awards_patents_papers = form.awards_patents_papers.data.strip() if form.awards_patents_papers.data else None
                elif competition_type == '"挑战杯"全国大学生课外学术科技作品竞赛':
                    project.project_type = form.project_type.data
                    project.push_college = form.push_college.data.strip() if form.push_college.data else None
                    project.innovation_points = form.innovation_points.data.strip() if form.innovation_points.data else None
                    project.development_status = form.development_status.data.strip() if form.development_status.data else None
                    project.awards_patents_papers = form.awards_patents_papers.data.strip() if form.awards_patents_papers.data else None
                elif competition_type == '"挑战杯"中国大学生创业计划大赛':
                    project.project_field = form.project_field.data
                    project.push_college = form.push_college.data.strip() if form.push_college.data else None
                    project.innovation_points = form.innovation_points.data.strip() if form.innovation_points.data else None
                    project.development_status = form.development_status.data.strip() if form.development_status.data else None
                    project.awards_patents_papers = form.awards_patents_papers.data.strip() if form.awards_patents_papers.data else None
            
            # 处理附件上传（针对"中国国际大学生创新大赛"青年红色筑梦之旅"赛道"、"挑战杯"全国大学生课外学术科技作品竞赛和"挑战杯"中国大学生创业计划大赛）
            if (competition_type == '中国国际大学生创新大赛"青年红色筑梦之旅"赛道' or 
                competition_type == '"挑战杯"全国大学生课外学术科技作品竞赛' or
                competition_type == '"挑战杯"中国大学生创业计划大赛') and 'attachments' in request.files:
                files = request.files.getlist('attachments')
                for file in files:
                    if file and file.filename and allowed_file(file.filename):
                        file_info = save_uploaded_file(file, subfolder=f'project_{project.id}')
                        if file_info:
                            attachment = ProjectAttachment(
                                project_id=project.id,
                                filename=file_info['filename'],
                                original_filename=file_info['original_filename'],
                                file_path=file_info['file_path'],
                                file_size=file_info['file_size'],
                                file_type=file_info['file_type']
                            )
                            db.session.add(attachment)
            
            db.session.commit()
            
            # 检查是否有保存按钮或下一步按钮
            if 'save' in request.form:
                flash('项目信息已保存', 'success')
                return redirect(url_for('student.create_project_info', project_id=project.id))
            elif 'next' in request.form:
                return redirect(url_for('student.create_project_members', project_id=project.id))
    
    # 渲染模板
    from models import COLLEGES
    if project:
        return render_template('student/create_project_info.html', form=form, project=project, competition=project.competition, competition_type=project.competition.competition_type, colleges=COLLEGES)
    else:
        # 新项目，传递competition信息
        return render_template('student/create_project_info.html', form=form, competition=competition, competition_type=competition_type, team_id=session.get('pending_team_id'), colleges=COLLEGES)

@student_bp.route('/project/<int:project_id>/members', methods=['GET', 'POST'])
@login_required
@student_required
def create_project_members(project_id):
    """填写队员和指导老师信息（第三步）"""
    project = Project.query.get_or_404(project_id)
    
    # 检查权限：只有队长可以编辑
    if project.team.leader_id != current_user.id:
        flash('只有队长可以编辑项目', 'error')
        return redirect(url_for('student.view_project', project_id=project_id))
    
    if request.method == 'POST':
        # 更新指导老师信息
        project.instructor_name = request.form.get('instructor_name', '')
        project.instructor_work_id = request.form.get('instructor_work_id', '')
        project.instructor_unit = request.form.get('instructor_unit', '')
        project.instructor_phone = request.form.get('instructor_phone', '')
        
        # 获取所有队员信息（从表单中提取）
        member_orders = []
        for key in request.form.keys():
            if key.startswith('member_name_'):
                order = int(key.split('_')[-1])
                member_orders.append(order)
        
        member_orders.sort()
        
        # 验证所有队员是否已注册
        unregistered_members = []
        members_data = []
        
        for order in member_orders:
            member_name = request.form.get(f'member_name_{order}', '').strip()
            member_work_id = request.form.get(f'member_work_id_{order}', '').strip()
            member_college = request.form.get(f'member_college_{order}', '').strip()
            member_major = request.form.get(f'member_major_{order}', '').strip()
            member_phone = request.form.get(f'member_phone_{order}', '').strip()
            member_email = request.form.get(f'member_email_{order}', '').strip()
            
            if member_name and member_work_id:
                # 尝试通过学工号查找用户
                member_user = User.query.filter_by(work_id=member_work_id).first()
                
                # 如果是队长，使用当前用户
                if member_work_id == current_user.work_id:
                    member_user = current_user
                
                # 检查队员是否已注册（队长除外）
                if not member_user:
                    unregistered_members.append(f"{member_name}（学号：{member_work_id}）")
                
                members_data.append({
                    'order': order,
                    'member_user': member_user,
                    'member_name': member_name,
                    'member_work_id': member_work_id,
                    'member_college': member_college,
                    'member_major': member_major,
                    'member_phone': member_phone,
                    'member_email': member_email
                })
        
        # 如果有未注册的队员，显示错误提示并阻止保存
        if unregistered_members:
            flash(f'以下队员还未注册，请先完成注册后再添加：{", ".join(unregistered_members)}', 'error')
            return redirect(url_for('student.create_project_members', project_id=project_id))
        
        # 删除现有项目成员（除了队长）
        ProjectMember.query.filter_by(project_id=project_id).filter(
            ProjectMember.user_id != project.team.leader_id
        ).delete()
        db.session.flush()  # 确保删除操作立即生效
        
        # 添加项目成员（按顺位）
        for member_data in members_data:
            member_user = member_data['member_user']
            # 队长自动确认
            is_confirmed = (member_user and member_user.id == project.team.leader_id)
            
            # 检查是否已存在（避免重复添加队长）
            existing_pm = ProjectMember.query.filter_by(
                project_id=project.id,
                user_id=member_user.id if member_user else None
            ).first()
            
            if existing_pm:
                # 如果已存在，更新信息
                existing_pm.order = member_data['order']
                existing_pm.member_name = member_data['member_name']
                existing_pm.member_work_id = member_data['member_work_id']
                existing_pm.member_college = member_data['member_college']
                existing_pm.member_major = member_data['member_major']
                existing_pm.member_phone = member_data['member_phone']
                existing_pm.member_email = member_data['member_email']
                if is_confirmed and not existing_pm.is_confirmed:
                    existing_pm.is_confirmed = True
                    existing_pm.confirmed_at = beijing_now()
            else:
                # 如果不存在，创建新记录
                pm = ProjectMember(
                    project_id=project.id,
                    user_id=member_user.id if member_user else None,
                    order=member_data['order'],
                    member_name=member_data['member_name'],
                    member_work_id=member_data['member_work_id'],
                    member_college=member_data['member_college'],
                    member_major=member_data['member_major'],
                    member_phone=member_data['member_phone'],
                    member_email=member_data['member_email'],
                    is_confirmed=is_confirmed
                )
                if is_confirmed:
                    pm.confirmed_at = beijing_now()
                db.session.add(pm)
        
        db.session.commit()
        
        if 'save' in request.form:
            flash('队员信息已保存，已向队员发送邀请', 'success')
        elif 'next' in request.form:
            flash('队员信息已保存，请等待所有队员确认后提交', 'success')
            return redirect(url_for('student.view_project', project_id=project_id))
        
        return redirect(url_for('student.create_project_members', project_id=project_id))
    
    # GET 请求：显示表单
    existing_members = project.project_members.all()
    from models import COLLEGES
    return render_template('student/create_project_members.html', project=project, existing_members=existing_members, colleges=COLLEGES)

@student_bp.route('/project/<int:project_id>/submit', methods=['POST'])
@login_required
@student_required
def submit_project(project_id):
    """提交项目（从草稿变为已提交状态）"""
    project = Project.query.get_or_404(project_id)
    
    # 检查权限：只有队长可以提交
    if project.team.leader_id != current_user.id:
        flash('只有队长可以提交项目', 'error')
        return redirect(url_for('student.view_project', project_id=project_id))
    
    if project.status in [ReviewStatus.DRAFT, ReviewStatus.COLLEGE_REJECTED]:
        # 对于被拒绝的项目，不需要重新确认队员，可以直接重新提交
        # 对于草稿状态的项目，需要检查所有队员是否已确认
        if project.status == ReviewStatus.DRAFT:
            if not project.all_members_confirmed():
                flash('请等待所有队员确认后才能提交', 'error')
                return redirect(url_for('student.view_project', project_id=project_id))
        
        # 如果是从不通过状态重新提交，清除之前的审核意见
        was_rejected = project.status == ReviewStatus.COLLEGE_REJECTED
        project.status = ReviewStatus.SUBMITTED
        if was_rejected:
            project.college_review_comment = None
        db.session.commit()
        flash('项目已提交，等待学院审核', 'success')
    else:
        flash('项目状态不正确', 'error')
    
    return redirect(url_for('student.view_project', project_id=project_id))

@student_bp.route('/project/<int:project_id>')
@login_required
@student_required
def view_project(project_id):
    """查看项目详情"""
    project = Project.query.get_or_404(project_id)
    
    # 检查权限：队伍成员或项目成员都可以查看
    is_team_member = TeamMember.query.filter_by(team_id=project.team_id, user_id=current_user.id).first()
    is_project_member = ProjectMember.query.filter_by(project_id=project_id, user_id=current_user.id).first()
    
    if not is_team_member and not is_project_member:
        flash('您没有权限访问此项目', 'error')
        return redirect(url_for('student.projects'))
    
    # 获取当前用户在项目中的成员信息
    user_project_member = ProjectMember.query.filter_by(project_id=project_id, user_id=current_user.id).first()
    
    # 判断是否是队长（队长可以查看所有成员信息）
    is_leader = project.team.leader_id == current_user.id
    
    # 检查是否可以抽取答辩顺序（只有进入决赛的项目才显示，只有队长可以抽签）
    can_draw_order = False
    order_status = None
    competition = project.competition
    now = beijing_now()
    
    # 只有进入决赛的项目才显示答辩顺序相关信息
    if project.is_final:
        if project.defense_order:
            order_status = '已抽取'
        elif is_leader:  # 只有队长才需要判断抽签状态
            if competition.defense_order_start and competition.defense_order_end:
                # 确保时间比较使用北京时间
                if now < competition.defense_order_start:
                    order_status = '未开始'
                elif now >= competition.defense_order_start and now <= competition.defense_order_end:
                    can_draw_order = True
                    order_status = '可抽取'
                else:
                    order_status = '已过期'
            elif competition.defense_order_start or competition.defense_order_end:
                # 如果只设置了开始或结束时间之一，也允许抽签
                can_draw_order = True
                order_status = '可抽取'
            else:
                order_status = '未设置'
        else:
            # 非队长成员，显示等待状态
            order_status = '等待队长抽取'
    
    return render_template('student/view_project.html', project=project, user_project_member=user_project_member, is_leader=is_leader, can_draw_order=can_draw_order, order_status=order_status)

@student_bp.route('/project/<int:project_id>/delete', methods=['POST'])
@login_required
@student_required
def delete_project(project_id):
    """删除项目（仅队长可删除草稿状态的项目）"""
    try:
        project = Project.query.get_or_404(project_id)
        
        # 检查权限：只有队长可以删除
        if project.team.leader_id != current_user.id:
            flash('只有队长可以删除项目', 'error')
            return redirect(url_for('student.projects'))
        
        # 只能删除草稿状态的项目
        if project.status != ReviewStatus.DRAFT:
            flash('只能删除草稿状态的项目', 'error')
            return redirect(url_for('student.projects'))
        
        # 删除项目（关联数据会通过cascade自动删除）
        project_title = project.title
        db.session.delete(project)
        db.session.commit()
        
        flash(f'项目"{project_title}"已删除', 'success')
    except Exception as e:
        db.session.rollback()
        flash('删除项目时发生错误，请重试', 'error')
        import traceback
        print(f"Delete project error: {traceback.format_exc()}")
    
    return redirect(url_for('student.projects'))

@student_bp.route('/project/<int:project_id>/confirm', methods=['POST'])
@login_required
@student_required
def confirm_project(project_id):
    """队员确认参与项目"""
    project = Project.query.get_or_404(project_id)
    
    # 检查当前用户是否是项目成员
    project_member = ProjectMember.query.filter_by(project_id=project_id, user_id=current_user.id).first()
    if not project_member:
        flash('您不是该项目的成员', 'error')
        return redirect(url_for('student.projects'))
    
    if project_member.is_confirmed:
        flash('您已经确认过此项目', 'info')
    else:
        project_member.is_confirmed = True
        project_member.confirmed_at = beijing_now()
        db.session.commit()
        flash('您已确认参与此项目', 'success')
    
    return redirect(url_for('student.view_project', project_id=project_id))

@student_bp.route('/project/<int:project_id>/draw_defense_order', methods=['POST'])
@login_required
@student_required
def draw_defense_order(project_id):
    """抽取答辩顺序"""
    project = Project.query.get_or_404(project_id)
    
    # 检查权限：只有队长可以抽取
    if project.team.leader_id != current_user.id:
        # 如果是 JSON 请求，返回 JSON 响应
        if request.is_json or request.headers.get('Content-Type') == 'application/json':
            return jsonify({'success': False, 'message': '只有队长可以抽取答辩顺序'}), 403
        flash('只有队长可以抽取答辩顺序', 'error')
        return redirect(url_for('student.view_project', project_id=project_id))
    
    # 检查项目是否进入决赛
    if not project.is_final:
        if request.is_json or request.headers.get('Content-Type') == 'application/json':
            return jsonify({'success': False, 'message': '只有进入决赛的项目才能抽取答辩顺序'}), 400
        flash('只有进入决赛的项目才能抽取答辩顺序', 'error')
        return redirect(url_for('student.view_project', project_id=project_id))
    
    # 检查是否已抽取
    if project.defense_order:
        if request.is_json or request.headers.get('Content-Type') == 'application/json':
            return jsonify({'success': False, 'message': '您已经抽取过答辩顺序', 'defense_order': project.defense_order}), 400
        flash('您已经抽取过答辩顺序', 'error')
        return redirect(url_for('student.view_project', project_id=project_id))
    
    competition = project.competition
    now = beijing_now()
    
    # 检查时间（允许管理员跳过时间检查）
    skip_time_check = False
    if request.is_json:
        skip_time_check = request.json.get('skip_time_check', False) if request.json else False
    elif request.form:
        skip_time_check = request.form.get('skip_time_check', 'false').lower() == 'true'
    
    if not skip_time_check:
        if not competition.defense_order_start or not competition.defense_order_end:
            if request.is_json or request.headers.get('Content-Type') == 'application/json':
                return jsonify({'success': False, 'message': '管理员尚未设置答辩顺序抽取时间'}), 400
            flash('管理员尚未设置答辩顺序抽取时间', 'error')
            return redirect(url_for('student.view_project', project_id=project_id))
        
        if now < competition.defense_order_start:
            if request.is_json or request.headers.get('Content-Type') == 'application/json':
                return jsonify({'success': False, 'message': '答辩顺序抽取尚未开始'}), 400
            flash('答辩顺序抽取尚未开始', 'error')
            return redirect(url_for('student.view_project', project_id=project_id))
        
        if now > competition.defense_order_end:
            if request.is_json or request.headers.get('Content-Type') == 'application/json':
                return jsonify({'success': False, 'message': '答辩顺序抽取时间已过，请联系管理员'}), 400
            flash('答辩顺序抽取时间已过，请联系管理员', 'error')
            return redirect(url_for('student.view_project', project_id=project_id))
    
    # 获取该竞赛所有进入决赛的项目
    all_final_projects = Project.query.filter(
        Project.competition_id == project.competition_id,
        Project.is_final == True
    ).all()
    
    # 获取已抽取的顺序
    taken_orders = set()
    for p in all_final_projects:
        if p.defense_order:
            taken_orders.add(p.defense_order)
    
    # 获取可用的顺序列表
    total_count = len(all_final_projects)
    available_orders = [i for i in range(1, total_count + 1) if i not in taken_orders]
    
    if not available_orders:
        if request.is_json or request.headers.get('Content-Type') == 'application/json':
            return jsonify({'success': False, 'message': '所有答辩顺序已被抽取'}), 400
        flash('所有答辩顺序已被抽取', 'error')
        return redirect(url_for('student.view_project', project_id=project_id))
    
    # 随机抽取一个顺序
    selected_order = random.choice(available_orders)
    
    # 保存结果
    project.defense_order = selected_order
    db.session.commit()
    
    # 如果是 JSON 请求，返回 JSON 响应
    if request.is_json or request.headers.get('Content-Type') == 'application/json':
        return jsonify({
            'success': True,
            'message': f'恭喜！您抽取到第{selected_order}位答辩顺序',
            'defense_order': selected_order
        })
    
    flash(f'恭喜！您抽取到第{selected_order}位答辩顺序', 'success')
    return redirect(url_for('student.view_project', project_id=project_id))

@student_bp.route('/project/<int:project_id>/award/<int:award_id>/view')
@login_required
@student_required
def view_certificate(project_id, award_id):
    """查看项目证书（在线预览）"""
    from flask import send_from_directory, abort, send_file
    import os
    
    project = Project.query.get_or_404(project_id)
    award = Award.query.get_or_404(award_id)
    
    # 检查权限：必须是项目成员
    is_team_member = TeamMember.query.filter_by(team_id=project.team_id, user_id=current_user.id).first()
    is_project_member = ProjectMember.query.filter_by(project_id=project_id, user_id=current_user.id).first()
    
    if not is_team_member and not is_project_member:
        abort(403)
    
    # 检查证书是否存在
    if not award.certificate_path:
        abort(404)
    
    # 构建证书文件路径
    cert_folder = str(Config.CERTIFICATE_FOLDER)
    cert_path = os.path.join(cert_folder, award.certificate_path)
    cert_path = os.path.normpath(cert_path)
    cert_folder = os.path.normpath(cert_folder)
    
    # 安全检查
    if not cert_path.startswith(cert_folder):
        abort(403)
    
    if not os.path.exists(cert_path):
        abort(404)
    
    # 直接使用send_file发送文件，避免路径问题
    return send_file(
        cert_path,
        mimetype='image/png',
        as_attachment=False
    )

@student_bp.route('/project/<int:project_id>/award/<int:award_id>/download')
@login_required
@student_required
def download_certificate(project_id, award_id):
    """下载项目证书（文件名：项目名+奖项名）"""
    from flask import send_from_directory, abort
    import os
    
    project = Project.query.get_or_404(project_id)
    award = Award.query.get_or_404(award_id)
    
    # 检查权限：必须是项目成员
    is_team_member = TeamMember.query.filter_by(team_id=project.team_id, user_id=current_user.id).first()
    is_project_member = ProjectMember.query.filter_by(project_id=project_id, user_id=current_user.id).first()
    
    if not is_team_member and not is_project_member:
        flash('您没有权限下载此证书', 'error')
        abort(403)
    
    # 检查证书是否存在
    if not award.certificate_path:
        flash('证书文件不存在', 'error')
        abort(404)
    
    # 构建证书文件路径
    cert_folder = str(Config.CERTIFICATE_FOLDER)
    cert_path = os.path.join(cert_folder, award.certificate_path)
    cert_path = os.path.normpath(cert_path)
    cert_folder = os.path.normpath(cert_folder)
    
    # 安全检查
    if not cert_path.startswith(cert_folder):
        abort(403)
    
    if not os.path.exists(cert_path):
        abort(404)
    
    # 生成下载文件名：项目名+奖项名
    safe_project_name = "".join(c for c in project.title if c.isalnum() or c in (' ', '-', '_', '，', '。', '、')).strip()
    safe_award_name = "".join(c for c in award.award_name if c.isalnum() or c in (' ', '-', '_', '，', '。', '、')).strip()
    download_filename = f"{safe_project_name}+{safe_award_name}.png"
    download_filename = download_filename.replace(' ', '_')
    
    # send_from_directory需要相对于cert_folder的路径
    relative_path = os.path.relpath(cert_path, cert_folder)
    relative_path = relative_path.replace('\\', '/')
    
    return send_from_directory(
        cert_folder,
        relative_path,
        as_attachment=True,
        download_name=download_filename,
        mimetype='image/png'
    )

@student_bp.route('/project/<int:project_id>/delete_attachment', methods=['POST'])
@login_required
@student_required
def delete_attachment(project_id):
    """删除项目附件"""
    from flask import jsonify
    project = Project.query.get_or_404(project_id)
    
    # 检查权限：只有队长可以删除附件
    if project.team.leader_id != current_user.id:
        return jsonify({'success': False, 'message': '只有队长可以删除附件'}), 403
    
    attachment_id = request.args.get('attachment_id', type=int)
    if not attachment_id:
        return jsonify({'success': False, 'message': '缺少附件ID'}), 400
    
    attachment = ProjectAttachment.query.get_or_404(attachment_id)
    
    # 验证附件属于该项目
    if attachment.project_id != project.id:
        return jsonify({'success': False, 'message': '附件不属于该项目'}), 403
    
    # 删除文件
    file_path = Path(Config.UPLOAD_FOLDER) / attachment.file_path
    if file_path.exists():
        try:
            file_path.unlink()
        except Exception as e:
            return jsonify({'success': False, 'message': f'删除文件失败: {str(e)}'}), 500
    
    # 删除数据库记录
    db.session.delete(attachment)
    db.session.commit()
    
    return jsonify({'success': True, 'message': '附件已删除'})

