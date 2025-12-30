"""
学生端路由
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, send_from_directory, jsonify, session
from flask_login import login_required, current_user
from models import db, User, Team, Project, Competition, Track, ProjectTrack, ProjectMember, ReviewStatus, TeamMember, UserRole, Score, ProjectAttachment, Award
from forms import ProjectForm
from utils.decorators import student_required
from utils.file_handler import save_uploaded_file, allowed_file
from config import Config
from pathlib import Path
from datetime import datetime
import os

student_bp = Blueprint('student', __name__)

@student_bp.route('/dashboard')
@login_required
@student_required
def dashboard():
    """学生首页 - 显示个人信息"""
    return render_template('student/dashboard.html')

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
    
    # 如果是编辑已有项目，填充表单数据
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
                if competition_type == '"挑战杯"全国大学生课外学术科技作品竞赛':
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
            
            # 处理附件上传（仅针对"中国国际大学生创新大赛"青年红色筑梦之旅"赛道"）
            if competition_type == '中国国际大学生创新大赛"青年红色筑梦之旅"赛道' and 'attachments' in request.files:
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
                    existing_pm.confirmed_at = datetime.utcnow()
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
                    pm.confirmed_at = datetime.utcnow()
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
        # 检查所有队员是否已确认
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
    
    # 获取所有专家的评分信息
    scores = Score.query.filter_by(project_id=project_id).all()
    
    # 获取项目奖项
    awards = Award.query.filter_by(project_id=project_id).all()
    
    return render_template('student/view_project.html', project=project, user_project_member=user_project_member, is_leader=is_leader, scores=scores, awards=awards)

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
        from datetime import datetime
        project_member.is_confirmed = True
        project_member.confirmed_at = datetime.utcnow()
        db.session.commit()
        flash('您已确认参与此项目', 'success')
    
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

