"""
校级管理员路由
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file, jsonify
from flask_login import login_required, current_user
from models import db, Project, User, ReviewStatus, JudgeAssignment, Award, ExternalAward, Competition, Track, Team, ProjectTrack, UserRole, Score, UserRoleAssignment, AssessmentConfig
from datetime import datetime
from forms import FilterForm, AwardForm, ReviewForm, CompetitionForm, UserEditForm, UserCreateForm, QQGroupForm, DefenseOrderTimeForm, FinalQuotaForm, ExternalAwardForm, AssessmentConfigForm
from utils.decorators import school_admin_required
from utils.certificate import generate_certificate
from utils.export import export_projects_to_excel, export_scores_to_excel, export_detailed_projects_to_excel
from utils.file_handler import save_uploaded_file
from utils.timezone import beijing_now
from config import Config
import random

school_admin_bp = Blueprint('school_admin', __name__)

@school_admin_bp.route('/dashboard', methods=['GET', 'POST'])
@login_required
@school_admin_required
def dashboard():
    """校级管理员 dashboard - 显示基本信息和编辑表单"""
    from forms import ProfileForm
    
    form = ProfileForm()
    
    if form.validate_on_submit():
        has_errors = False
        
        # 更新基本信息
        current_user.real_name = form.real_name.data
        # 邮箱为选填项，如果填写了则验证并更新
        email_input = form.email.data.strip() if form.email.data else ''
        # 如果邮箱值等于学工号，说明是浏览器自动填充的，忽略它
        if email_input and email_input == (current_user.work_id or current_user.username):
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
            return render_template('school_admin/dashboard.html', form=form)
        
        db.session.commit()
        flash('个人资料更新成功', 'success')
        return redirect(url_for('school_admin.dashboard'))
    
    # 填充表单数据（GET 请求或验证失败时）
    form.real_name.data = current_user.real_name
    form.email.data = ''  # 邮箱不默认填写
    if current_user.role in ['school_admin', 'judge']:
        form.unit.data = current_user.unit
    form.contact_info.data = current_user.contact_info
    
    return render_template('school_admin/dashboard.html', form=form)

@school_admin_bp.route('/review')
@login_required
@school_admin_required
def review():
    """审核管理页 - 已通过学院审核的项目列表"""
    # 获取所有已通过学院审核的项目
    projects = Project.query.filter(
        Project.status == ReviewStatus.COLLEGE_APPROVED
    ).all()
    
    return render_template('school_admin/review.html', projects=projects)

@school_admin_bp.route('/project/<int:project_id>/review', methods=['GET', 'POST'])
@login_required
@school_admin_required
def review_project(project_id):
    """审核项目"""
    project = Project.query.get_or_404(project_id)
    
    # 只能审核已通过学院审核的项目
    if project.status != ReviewStatus.COLLEGE_APPROVED:
        flash('该项目不在待审核状态', 'error')
        return redirect(url_for('school_admin.review'))
    
    form = ReviewForm()
    
    if form.validate_on_submit():
        action = form.action.data
        comment = form.comment.data
        
        if action == 'approve':
            project.status = ReviewStatus.FINAL_APPROVED
            flash('项目已通过学校审核', 'success')
        elif action == 'reject':
            project.status = ReviewStatus.FINAL_REJECTED
            flash('项目未通过学校审核', 'info')
        
        # 保存审核意见
        project.school_review_comment = comment
        db.session.commit()
        
        return redirect(url_for('school_admin.review'))
    
    # 获取所有专家的评分信息
    scores = Score.query.filter_by(project_id=project_id).all()
    
    return render_template('school_admin/review_project.html', project=project, form=form, scores=scores)

@school_admin_bp.route('/project/<int:project_id>/sensitive_detection')
@login_required
@school_admin_required
def sensitive_detection(project_id):
    """脱敏识别页面"""
    project = Project.query.get_or_404(project_id)
    
    # 获取项目附件
    attachments = project.attachments.all()
    
    # 存储识别结果
    detection_results = []
    
    # 如果没有附件，直接返回
    if not attachments:
        return render_template('school_admin/sensitive_detection.html', 
                             project=project, 
                             detection_results=[])
    
    # 对每个附件进行识别
    from utils.ai_sensitive_detection import SensitiveDetector
    from config import Config
    import os
    
    detector = SensitiveDetector()
    
    for attachment in attachments:
        # 构建完整文件路径
        file_path = os.path.join(Config.UPLOAD_FOLDER, attachment.file_path.replace('/', os.sep).replace('\\', os.sep))
        file_path = os.path.normpath(file_path)
        
        if os.path.exists(file_path):
            # 进行识别
            result = detector.detect_attachment(file_path, attachment.file_type or '')
            
            detection_results.append({
                'attachment': attachment,
                'has_sensitive': result.get('has_sensitive', False),
                'detected_keywords': result.get('detected_keywords', []),
                'details': result.get('details', ''),
                'error': result.get('error')
            })
        else:
            detection_results.append({
                'attachment': attachment,
                'has_sensitive': False,
                'detected_keywords': [],
                'details': '文件不存在',
                'error': '文件不存在'
            })
    
    return render_template('school_admin/sensitive_detection.html', 
                         project=project, 
                         detection_results=detection_results,
                         sensitive_keywords=Config.SENSITIVE_KEYWORDS)

@school_admin_bp.route('/projects')
@login_required
@school_admin_required
def projects():
    """项目列表（带筛选）"""
    form = FilterForm()
    
    # 基础查询：只显示学校已通过的项目
    query = Project.query.filter(
        Project.status == ReviewStatus.FINAL_APPROVED
    )
    
    # 筛选条件
    project_name = request.args.get('project_name', '').strip()
    competition_id = request.args.get('competition_id', type=int)
    college = request.args.get('college', '').strip()
    
    if project_name:
        query = query.filter(Project.title.contains(project_name))
    
    if competition_id:
        # 根据竞赛ID筛选
        query = query.filter(Project.competition_id == competition_id)
    
    if college:
        # 根据学院筛选
        query = query.join(Team, Project.team_id == Team.id).join(User, Team.leader_id == User.id).filter(User.college.contains(college))
    
    # 使用 distinct() 避免重复结果（当有多个 join 时）
    projects = query.distinct().all()
    
    # 获取所有竞赛用于筛选下拉框（不再需要赛道）
    competitions = Competition.query.filter_by(is_active=True).all()
    
    return render_template('school_admin/projects.html', projects=projects, form=form, competitions=competitions)

@school_admin_bp.route('/expert_review')
@login_required
@school_admin_required
def expert_review():
    """专家评审页 - 已通过学校审核的项目列表"""
    # 获取所有已通过学校审核的项目
    query = Project.query.filter(
        Project.status == ReviewStatus.FINAL_APPROVED
    )
    
    # 筛选条件
    project_name = request.args.get('project_name', '').strip()
    competition_id = request.args.get('competition_id', type=int)
    college = request.args.get('college', '').strip()
    
    if project_name:
        query = query.filter(Project.title.contains(project_name))
    
    if competition_id:
        query = query.filter(Project.competition_id == competition_id)
    
    if college:
        query = query.join(Team, Project.team_id == Team.id).join(User, Team.leader_id == User.id).filter(User.college.contains(college))
    
    projects = query.distinct().all()
    
    # 获取所有竞赛用于筛选下拉框
    competitions = Competition.query.filter_by(is_active=True).all()
    
    # 为每个项目获取评分信息
    projects_with_scores = []
    for project in projects:
        scores = Score.query.filter_by(project_id=project.id).all()
        projects_with_scores.append({
            'project': project,
            'scores': scores,
            'score_count': len(scores),
            'avg_score': sum(s.score_value for s in scores) / len(scores) if scores else None
        })
    
    return render_template('school_admin/expert_review.html', 
                         projects_with_scores=projects_with_scores, 
                         competitions=competitions)

@school_admin_bp.route('/project/<int:project_id>/scores')
@login_required
@school_admin_required
def view_scores(project_id):
    """查看项目评分详情"""
    project = Project.query.get_or_404(project_id)
    
    # 获取所有专家的评分信息
    scores = Score.query.filter_by(project_id=project_id).all()
    
    return render_template('school_admin/view_scores.html', project=project, scores=scores)

@school_admin_bp.route('/project/<int:project_id>/assign_judge', methods=['GET', 'POST'])
@login_required
@school_admin_required
def assign_judge(project_id):
    """分配评委"""
    project = Project.query.get_or_404(project_id)
    
    if request.method == 'POST':
        judge_id = request.form.get('judge_id', type=int)
        
        if not judge_id:
            flash('请选择评委', 'error')
            return redirect(url_for('school_admin.assign_judge', project_id=project_id))
        
        judge = User.query.get(judge_id)
        if not judge or not judge.has_role('judge'):
            flash('无效的评委', 'error')
            return redirect(url_for('school_admin.assign_judge', project_id=project_id))
        
        # 检查是否已分配
        existing = JudgeAssignment.query.filter_by(
            judge_id=judge_id,
            project_id=project_id
        ).first()
        
        if existing:
            flash('该评委已分配到此项目', 'error')
        else:
            assignment = JudgeAssignment(
                judge_id=judge_id,
                project_id=project_id
            )
            db.session.add(assignment)
            db.session.commit()
            flash('评委分配成功', 'success')
        
        # 返回时保留 next 参数
        next_page = request.args.get('next')
        if next_page:
            return redirect(next_page)
        return redirect(url_for('school_admin.assign_judge', project_id=project_id, next=next_page))
    
    # 获取所有评委（包括主角色为judge的用户，以及通过额外角色拥有judge身份的用户）
    from models import UserRoleAssignment
    # 主角色为judge的用户
    primary_judges = User.query.filter_by(role='judge', is_active=True).all()
    # 通过额外角色拥有judge身份的用户
    additional_judge_ids = [ur.user_id for ur in UserRoleAssignment.query.filter_by(role='judge').all()]
    additional_judges = User.query.filter(User.id.in_(additional_judge_ids), User.is_active == True).all() if additional_judge_ids else []
    # 合并并去重
    all_judge_ids = set([j.id for j in primary_judges] + [j.id for j in additional_judges])
    judges = User.query.filter(User.id.in_(all_judge_ids), User.is_active == True).all()
    
    # 获取已分配的评委
    assigned_judges = [ja.judge for ja in project.judge_assignments.filter_by(is_active=True).all()]
    
    # 确定返回页面：优先使用 next 参数，否则根据 referrer 判断
    next_page = request.args.get('next')
    if not next_page:
        referrer = request.referrer
        if referrer and 'projects' in referrer:
            next_page = url_for('school_admin.projects')
        else:
            next_page = url_for('school_admin.review')
    
    return render_template('school_admin/assign_judge.html', project=project, judges=judges, assigned_judges=assigned_judges, next_page=next_page)


@school_admin_bp.route('/project/<int:project_id>/award', methods=['GET', 'POST'])
@login_required
@school_admin_required
def set_award(project_id):
    """设置奖项"""
    project = Project.query.get_or_404(project_id)
    form = AwardForm()
    
    if form.validate_on_submit():
        award_name = form.award_name.data
        
        # 生成证书
        certificate_path = generate_certificate(
            team_name=project.team.name,
            award_name=award_name,
            competition_name=project.competition.name,
            year=project.competition.year
        )
        
        # 创建奖项记录
        award = Award(
            project_id=project_id,
            award_name=award_name,
            certificate_path=certificate_path
        )
        db.session.add(award)
        db.session.commit()
        
        flash(f'奖项设置成功，证书已生成：{project.team.name}_{award_name}', 'success')
        return redirect(url_for('school_admin.dashboard'))
    
    return render_template('school_admin/set_award.html', project=project, form=form)

@school_admin_bp.route('/export/projects')
@login_required
@school_admin_required
def export_projects():
    """导出项目数据（包含完整的项目、成员信息）"""
    # 获取筛选条件
    project_name = request.args.get('project_name', '').strip()
    competition_id = request.args.get('competition_id', type=int)
    college = request.args.get('college', '').strip()
    
    # 基础查询：只显示学校已通过的项目
    query = Project.query.filter(
        Project.status == ReviewStatus.FINAL_APPROVED
    )
    
    if project_name:
        query = query.filter(Project.title.contains(project_name))
    
    if competition_id:
        query = query.filter(Project.competition_id == competition_id)
    
    if college:
        query = query.join(Team, Project.team_id == Team.id).join(User, Team.leader_id == User.id).filter(User.college.contains(college))
    
    projects = query.distinct().all()
    
    if not projects:
        flash('没有可导出的项目数据', 'info')
        return redirect(url_for('school_admin.projects'))
    
    try:
        output = export_detailed_projects_to_excel(projects)
        from datetime import datetime
        filename = f'全校项目数据导出_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        flash(f'导出失败：{str(e)}', 'error')
        return redirect(url_for('school_admin.projects'))

@school_admin_bp.route('/export/scores')
@login_required
@school_admin_required
def export_scores():
    """导出评分数据"""
    projects = Project.query.all()
    output = export_scores_to_excel(projects)
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name='scores_export.xlsx'
    )

@school_admin_bp.route('/competitions')
@login_required
@school_admin_required
def competitions():
    """竞赛管理"""
    # 基础查询：所有活跃的竞赛
    query = Competition.query.filter_by(is_active=True)
    
    # 搜索条件
    search_name = request.args.get('search_name', '').strip()
    
    if search_name:
        query = query.filter(Competition.name.contains(search_name))
    
    competitions_list = query.order_by(Competition.year.desc(), Competition.created_at.desc()).all()
    return render_template('school_admin/competitions.html', competitions=competitions_list)

@school_admin_bp.route('/competition/create', methods=['GET', 'POST'])
@login_required
@school_admin_required
def create_competition():
    """创建竞赛"""
    form = CompetitionForm()
    
    if form.validate_on_submit():
        competition = Competition(
            name=form.name.data,
            year=form.year.data,
            competition_type=form.competition_type.data if form.competition_type.data else None,
            description=form.description.data if form.description.data else None,
            registration_start=form.registration_start.data if form.registration_start.data else None,
            registration_end=form.registration_end.data if form.registration_end.data else None,
            is_active=True,
            is_published=False
        )
        db.session.add(competition)
        db.session.commit()
        flash(f'竞赛"{competition.name}"创建成功', 'success')
        return redirect(url_for('school_admin.competitions'))
    
    return render_template('school_admin/create_competition.html', form=form)

@school_admin_bp.route('/competition/<int:competition_id>/edit', methods=['GET', 'POST'])
@login_required
@school_admin_required
def edit_competition(competition_id):
    """编辑竞赛"""
    competition = Competition.query.get_or_404(competition_id)
    form = CompetitionForm()
    
    # 填充表单数据
    form.name.data = competition.name
    form.year.data = competition.year
    form.competition_type.data = competition.competition_type
    form.description.data = competition.description
    
    # 设置日期时间字段 - DateTimeLocalField 期望 datetime 对象
    if competition.registration_start:
        if isinstance(competition.registration_start, datetime):
            form.registration_start.data = competition.registration_start
        else:
            # 如果是字符串，尝试解析为 datetime 对象
            try:
                form.registration_start.data = datetime.strptime(str(competition.registration_start), '%Y-%m-%dT%H:%M')
            except (ValueError, TypeError):
                # 如果解析失败，尝试其他格式
                try:
                    form.registration_start.data = datetime.strptime(str(competition.registration_start), '%Y-%m-%d %H:%M:%S')
                except (ValueError, TypeError):
                    form.registration_start.data = None
    if competition.registration_end:
        if isinstance(competition.registration_end, datetime):
            form.registration_end.data = competition.registration_end
        else:
            # 如果是字符串，尝试解析为 datetime 对象
            try:
                form.registration_end.data = datetime.strptime(str(competition.registration_end), '%Y-%m-%dT%H:%M')
            except (ValueError, TypeError):
                # 如果解析失败，尝试其他格式
                try:
                    form.registration_end.data = datetime.strptime(str(competition.registration_end), '%Y-%m-%d %H:%M:%S')
                except (ValueError, TypeError):
                    form.registration_end.data = None
    
    if form.validate_on_submit():
        competition.name = form.name.data
        competition.year = form.year.data
        competition.competition_type = form.competition_type.data if form.competition_type.data else None
        competition.description = form.description.data if form.description.data else None
        competition.registration_start = form.registration_start.data if form.registration_start.data else None
        competition.registration_end = form.registration_end.data if form.registration_end.data else None
        
        db.session.commit()
        flash(f'竞赛"{competition.name}"更新成功', 'success')
        return redirect(url_for('school_admin.competitions'))
    else:
        # 如果表单验证失败，显示错误信息
        if request.method == 'POST':
            flash('表单验证失败，请检查输入', 'error')
            for field, errors in form.errors.items():
                for error in errors:
                    flash(f'{getattr(form, field).label.text}: {error}', 'error')
        # 如果表单验证失败，显示错误信息
        if request.method == 'POST':
            flash('表单验证失败，请检查输入', 'error')
            for field, errors in form.errors.items():
                for error in errors:
                    flash(f'{getattr(form, field).label.text}: {error}', 'error')
    
    return render_template('school_admin/edit_competition.html', form=form, competition=competition)

@school_admin_bp.route('/competition/<int:competition_id>/toggle_publish', methods=['POST'])
@login_required
@school_admin_required
def toggle_publish_competition(competition_id):
    """发布/取消发布竞赛"""
    from flask import jsonify
    competition = Competition.query.get_or_404(competition_id)
    
    # 切换发布状态
    competition.is_published = not competition.is_published
    db.session.commit()
    
    status = '已发布' if competition.is_published else '已取消发布'
    
    # 如果是AJAX请求，返回JSON响应
    if request.headers.get('Content-Type') == 'application/json' or request.is_json:
        return jsonify({
            'success': True,
            'is_published': competition.is_published,
            'message': f'竞赛"{competition.name}"{status}'
        })
    
    # 否则重定向（兼容旧代码）
    flash(f'竞赛"{competition.name}"{status}', 'success')
    return redirect(url_for('school_admin.competitions'))

@school_admin_bp.route('/competition/<int:competition_id>/delete', methods=['POST'])
@login_required
@school_admin_required
def delete_competition(competition_id):
    """删除竞赛"""
    competition = Competition.query.get_or_404(competition_id)
    
    # 检查是否有项目关联
    project_count = Project.query.filter_by(competition_id=competition_id).count()
    if project_count > 0:
        flash(f'无法删除竞赛"{competition.name}"，该竞赛下已有 {project_count} 个项目', 'error')
        return redirect(url_for('school_admin.competitions'))
    
    competition_name = competition.name
    # 删除关联的赛道
    Track.query.filter_by(competition_id=competition_id).delete()
    # 删除竞赛
    db.session.delete(competition)
    db.session.commit()
    
    flash(f'竞赛"{competition_name}"已删除', 'success')
    return redirect(url_for('school_admin.competitions'))

@school_admin_bp.route('/final_competition')
@login_required
@school_admin_required
def final_competition():
    """校赛决赛管理页"""
    # 获取所有竞赛
    competitions = Competition.query.filter_by(is_active=True).all()
    
    # 筛选条件
    competition_id = request.args.get('competition_id', type=int)
    
    # 查询已通过学校审核且有评分的项目
    query = Project.query.filter(
        Project.status == ReviewStatus.FINAL_APPROVED
    ).join(Competition)
    
    if competition_id:
        query = query.filter(Project.competition_id == competition_id)
    
    projects = query.all()
    
    # 按竞赛分组处理项目
    competition_projects = {}
    for project in projects:
        comp_id = project.competition_id
        if comp_id not in competition_projects:
            competition_projects[comp_id] = []
        
        scores = Score.query.filter_by(project_id=project.id).all()
        if scores:
            avg_score = sum(s.score_value for s in scores) / len(scores)
            competition_projects[comp_id].append({
                'project': project,
                'avg_score': avg_score,
                'score_count': len(scores)
            })
    
    # 为每个竞赛的项目按平均分降序排序，并确定进入决赛的项目
    all_final_projects = []
    all_non_final_projects = []
    
    for comp_id, projects_list in competition_projects.items():
        competition = Competition.query.get(comp_id)
        # 按平均分降序排序
        projects_list.sort(key=lambda x: x['avg_score'], reverse=True)
        
        # 根据竞赛的决赛名额确定哪些项目进入决赛
        for idx, item in enumerate(projects_list, start=1):
            project = item['project']
            if competition.final_quota and idx <= competition.final_quota:
                project.is_final = True
                all_final_projects.append(item)
            else:
                project.is_final = False
                all_non_final_projects.append(item)
    
    db.session.commit()
    
    # 校赛决赛不按评分排序，按项目ID或创建时间排序（保持稳定顺序）
    all_final_projects.sort(key=lambda x: x['project'].id)
    all_non_final_projects.sort(key=lambda x: x['avg_score'], reverse=True)  # 未进入决赛的仍按评分排序显示
    
    return render_template('school_admin/final_competition.html', 
                         final_projects=all_final_projects, 
                         non_final_projects=all_non_final_projects,
                         competitions=competitions,
                         selected_competition_id=competition_id)

@school_admin_bp.route('/defense_order')
@login_required
@school_admin_required
def defense_order():
    """答辩顺序管理页"""
    # 获取所有竞赛
    competitions = Competition.query.filter_by(is_active=True).all()
    
    # 筛选条件
    competition_id = request.args.get('competition_id', type=int)
    
    # 查询进入决赛的项目（只查询设置了决赛名额的竞赛）
    query = Project.query.filter(
        Project.is_final == True
    ).join(Competition).filter(
        Competition.final_quota.isnot(None),
        Competition.final_quota > 0
    )
    
    if competition_id:
        query = query.filter(Project.competition_id == competition_id)
    
    projects = query.all()
    
    # 处理每个项目的抽取状态
    final_projects = []
    for project in projects:
        competition = project.competition
        now = beijing_now()
        
        # 检查是否需要自动分配（超过截止时间且未抽取）
        if (competition.defense_order_end and 
            now > competition.defense_order_end and 
            project.defense_order is None):
            # 自动分配：获取该竞赛所有已抽取的顺序
            existing_orders = set()
            other_projects = Project.query.filter(
                Project.competition_id == project.competition_id,
                Project.is_final == True,
                Project.defense_order.isnot(None)
            ).all()
            for p in other_projects:
                if p.defense_order:
                    existing_orders.add(p.defense_order)
            
            # 获取所有进入决赛的项目数量
            all_final = Project.query.filter(
                Project.competition_id == project.competition_id,
                Project.is_final == True
            ).count()
            
            # 找到第一个未使用的顺序
            for order in range(1, all_final + 1):
                if order not in existing_orders:
                    project.defense_order = order
                    db.session.commit()
                    break
        
        final_projects.append({'project': project})
    
    # 按答辩顺序排序，未抽取的排在后面
    final_projects.sort(key=lambda x: (x['project'].defense_order is None, x['project'].defense_order or 999999))
    
    return render_template('school_admin/defense_order.html', 
                         final_projects=final_projects,
                         competitions=competitions,
                         selected_competition_id=competition_id)

@school_admin_bp.route('/defense_order/update', methods=['POST'])
@login_required
@school_admin_required
def update_defense_order():
    """更新答辩顺序"""
    data = request.get_json()
    project_id = data.get('project_id')
    defense_order = data.get('defense_order')
    
    if not project_id:
        return jsonify({'success': False, 'message': '缺少项目ID'}), 400
    
    project = Project.query.get_or_404(project_id)
    
    # 检查项目是否进入决赛
    if not project.is_final:
        return jsonify({'success': False, 'message': '该项目未进入决赛'}), 400
    
    # 如果设置了顺序，检查是否与其他项目冲突，如果有则交换位置
    if defense_order:
        defense_order = int(defense_order)
        if defense_order < 1:
            return jsonify({'success': False, 'message': '答辩顺序必须大于0'}), 400
        
        # 保存当前项目的原顺序
        old_order = project.defense_order
        
        # 如果新顺序已被其他项目使用，则交换位置
        existing = Project.query.filter(
            Project.competition_id == project.competition_id,
            Project.is_final == True,
            Project.defense_order == defense_order,
            Project.id != project_id
        ).first()
        
        if existing:
            # 交换位置：将B调整到A的原位置
            existing.defense_order = old_order
        
        # 将当前项目调整到新位置
        project.defense_order = defense_order
    else:
        project.defense_order = None
    
    db.session.commit()
    
    return jsonify({'success': True, 'message': '答辩顺序已更新'})

@school_admin_bp.route('/qq_group', methods=['GET', 'POST'])
@login_required
@school_admin_required
def qq_group():
    """QQ群管理页"""
    from pathlib import Path
    import os
    
    # 获取所有竞赛
    competitions = Competition.query.filter_by(is_active=True).all()
    
    # 筛选条件
    competition_id = request.args.get('competition_id', type=int)
    
    form = QQGroupForm()
    form.competition_id.choices = [(0, '请选择竞赛')] + [(c.id, c.name) for c in competitions]
    
    if request.method == 'POST':
        competition_id = request.form.get('competition_id', type=int)
        if competition_id:
            competition = Competition.query.get_or_404(competition_id)
            
            # 更新QQ群号
            qq_group_number = request.form.get('qq_group_number', '').strip()
            competition.qq_group_number = qq_group_number if qq_group_number else None
            
            # 处理二维码上传
            if 'qq_group_qrcode' in request.files:
                file = request.files['qq_group_qrcode']
                if file and file.filename:
                    # 只允许图片格式
                    allowed_extensions = {'jpg', 'jpeg', 'png', 'gif'}
                    if '.' in file.filename and file.filename.rsplit('.', 1)[1].lower() in allowed_extensions:
                        # 删除旧的二维码（如果存在）
                        if competition.qq_group_qrcode:
                            old_path = Path(Config.UPLOAD_FOLDER) / competition.qq_group_qrcode
                            if old_path.exists():
                                try:
                                    old_path.unlink()
                                except:
                                    pass
                        
                        # 保存新二维码
                        file_info = save_uploaded_file(file, subfolder='qq_group_qrcodes')
                        if file_info:
                            competition.qq_group_qrcode = file_info['file_path']
            
            db.session.commit()
            flash(f'QQ群信息已更新', 'success')
            return redirect(url_for('school_admin.qq_group', competition_id=competition_id))
        else:
            flash('请选择竞赛', 'error')
    
    # GET请求或表单验证失败，显示表单
    selected_competition = None
    if competition_id:
        selected_competition = Competition.query.get(competition_id)
        if selected_competition:
            form.competition_id.data = competition_id
            form.qq_group_number.data = selected_competition.qq_group_number
    
    return render_template('school_admin/qq_group.html',
                         form=form,
                         competitions=competitions,
                         selected_competition=selected_competition,
                         selected_competition_id=competition_id)

@school_admin_bp.route('/defense_order_time', methods=['GET', 'POST'])
@login_required
@school_admin_required
def defense_order_time():
    """答辩顺序抽取时间设置页"""
    # 获取所有竞赛
    competitions = Competition.query.filter_by(is_active=True).all()
    
    # 筛选条件
    competition_id = request.args.get('competition_id', type=int) or (request.form.get('competition_id', type=int) if request.method == 'POST' else None)
    
    # 处理表单提交
    if request.method == 'POST' and competition_id:
        competition = Competition.query.get_or_404(competition_id)
        
        # 获取时间数据
        defense_order_start_str = request.form.get('defense_order_start', '').strip()
        defense_order_end_str = request.form.get('defense_order_end', '').strip()
        
        if defense_order_start_str:
            try:
                competition.defense_order_start = datetime.strptime(defense_order_start_str, '%Y-%m-%dT%H:%M')
            except ValueError:
                flash('开始时间格式错误', 'error')
                return redirect(url_for('school_admin.defense_order_time', competition_id=competition_id))
        else:
            competition.defense_order_start = None
        
        if defense_order_end_str:
            try:
                competition.defense_order_end = datetime.strptime(defense_order_end_str, '%Y-%m-%dT%H:%M')
            except ValueError:
                flash('结束时间格式错误', 'error')
                return redirect(url_for('school_admin.defense_order_time', competition_id=competition_id))
        else:
            competition.defense_order_end = None
        
        db.session.commit()
        flash(f'答辩顺序抽取时间已更新', 'success')
        return redirect(url_for('school_admin.defense_order_time', competition_id=competition_id))
    
    # 处理表单初始化
    time_form = DefenseOrderTimeForm()
    time_form.competition_id.choices = [(0, '请选择竞赛')] + [(c.id, c.name) for c in competitions]
    
    selected_competition = None
    if competition_id:
        selected_competition = Competition.query.get(competition_id)
        if selected_competition:
            time_form.competition_id.data = competition_id
            if selected_competition.defense_order_start:
                if isinstance(selected_competition.defense_order_start, datetime):
                    time_form.defense_order_start.data = selected_competition.defense_order_start
                else:
                    try:
                        time_form.defense_order_start.data = datetime.strptime(str(selected_competition.defense_order_start), '%Y-%m-%dT%H:%M')
                    except (ValueError, TypeError):
                        try:
                            time_form.defense_order_start.data = datetime.strptime(str(selected_competition.defense_order_start), '%Y-%m-%d %H:%M:%S')
                        except (ValueError, TypeError):
                            time_form.defense_order_start.data = None
            if selected_competition.defense_order_end:
                if isinstance(selected_competition.defense_order_end, datetime):
                    time_form.defense_order_end.data = selected_competition.defense_order_end
                else:
                    try:
                        time_form.defense_order_end.data = datetime.strptime(str(selected_competition.defense_order_end), '%Y-%m-%dT%H:%M')
                    except (ValueError, TypeError):
                        try:
                            time_form.defense_order_end.data = datetime.strptime(str(selected_competition.defense_order_end), '%Y-%m-%d %H:%M:%S')
                        except (ValueError, TypeError):
                            time_form.defense_order_end.data = None
    
    return render_template('school_admin/defense_order_time.html',
                         time_form=time_form,
                         competitions=competitions,
                         selected_competition_id=competition_id)

def update_final_projects_by_quota(competition_id):
    """
    根据决赛名额自动更新项目的is_final状态
    根据专家评审的平均分排名，将前N名项目设置为进入决赛
    
    Args:
        competition_id: 竞赛ID
    """
    from models import Score
    
    competition = Competition.query.get_or_404(competition_id)
    
    # 获取该竞赛所有已通过学校审核的项目
    projects = Project.query.filter(
        Project.competition_id == competition_id,
        Project.status == ReviewStatus.FINAL_APPROVED
    ).all()
    
    # 计算每个项目的平均分，并过滤掉没有评分的项目
    projects_with_scores = []
    for project in projects:
        scores = Score.query.filter_by(project_id=project.id).all()
        if scores:  # 只处理有评分的项目
            avg_score = sum(s.score_value for s in scores) / len(scores)
            projects_with_scores.append({
                'project': project,
                'avg_score': avg_score
            })
    
    # 按平均分降序排序
    projects_with_scores.sort(key=lambda x: x['avg_score'], reverse=True)
    
    # 根据决赛名额设置is_final
    if competition.final_quota and competition.final_quota > 0:
        # 如果设置了名额，将前N名设为进入决赛
        for idx, item in enumerate(projects_with_scores, start=1):
            if idx <= competition.final_quota:
                item['project'].is_final = True
            else:
                item['project'].is_final = False
    else:
        # 如果没有设置名额，将所有项目设为不进入决赛
        for item in projects_with_scores:
            item['project'].is_final = False
    
    # 对于没有评分的项目，也设为不进入决赛
    projects_without_scores = [p for p in projects if not any(ps['project'].id == p.id for ps in projects_with_scores)]
    for project in projects_without_scores:
        project.is_final = False
    
    db.session.commit()

@school_admin_bp.route('/final_quota', methods=['GET', 'POST'])
@login_required
@school_admin_required
def final_quota():
    """决赛名额设置页"""
    # 获取所有竞赛
    competitions = Competition.query.filter_by(is_active=True).all()
    
    # 筛选条件
    competition_id = request.args.get('competition_id', type=int) or (request.form.get('competition_id', type=int) if request.method == 'POST' else None)
    
    # 处理表单提交
    if request.method == 'POST' and competition_id:
        competition = Competition.query.get_or_404(competition_id)
        
        # 获取决赛名额
        final_quota_value = request.form.get('final_quota', '').strip()
        
        if final_quota_value:
            try:
                competition.final_quota = int(final_quota_value)
                if competition.final_quota < 1:
                    flash('决赛名额必须大于0', 'error')
                    return redirect(url_for('school_admin.final_quota', competition_id=competition_id))
            except ValueError:
                flash('决赛名额格式错误', 'error')
                return redirect(url_for('school_admin.final_quota', competition_id=competition_id))
        else:
            competition.final_quota = None
        
        db.session.commit()
        
        # 根据决赛名额自动更新项目的is_final状态
        update_final_projects_by_quota(competition_id)
        
        flash(f'决赛名额已设置为：{competition.final_quota if competition.final_quota else "未设置"}，已根据专家评审评分自动更新进入决赛的项目', 'success')
        return redirect(url_for('school_admin.final_quota', competition_id=competition_id))
    
    # 处理表单初始化
    quota_form = FinalQuotaForm()
    quota_form.competition_id.choices = [(0, '请选择竞赛')] + [(c.id, c.name) for c in competitions]
    
    # 如果选择了竞赛，填充表单数据
    if competition_id:
        selected_competition = Competition.query.get(competition_id)
        if selected_competition:
            quota_form.competition_id.data = competition_id
            quota_form.final_quota.data = selected_competition.final_quota
    
    return render_template('school_admin/final_quota.html',
                         quota_form=quota_form,
                         competitions=competitions,
                         selected_competition_id=competition_id)

@school_admin_bp.route('/awards')
@login_required
@school_admin_required
def awards():
    """奖项收集/发布管理页 - 重定向到奖项发布"""
    return redirect(url_for('school_admin.award_publish'))

@school_admin_bp.route('/award_publish')
@login_required
@school_admin_required
def award_publish():
    """奖项发布管理页（校赛证书发布）"""
    # 获取所有竞赛
    competitions = Competition.query.filter_by(is_active=True).all()
    
    # 筛选条件
    competition_id = request.args.get('competition_id', type=int)
    
    # 查询进入决赛的项目（只查询设置了决赛名额的竞赛）
    query = Project.query.filter(
        Project.is_final == True
    ).join(Competition).filter(
        Competition.final_quota.isnot(None),
        Competition.final_quota > 0
    )
    
    if competition_id:
        query = query.filter(Project.competition_id == competition_id)
    
    projects = query.all()
    
    # 为每个项目获取奖项信息
    projects_with_awards = []
    for project in projects:
        awards = Award.query.filter_by(project_id=project.id).all()
        projects_with_awards.append({
            'project': project,
            'awards': awards,
            'has_award': len(awards) > 0
        })
    
    return render_template('school_admin/award_publish.html', 
                         projects_with_awards=projects_with_awards,
                         competitions=competitions,
                         selected_competition_id=competition_id)

@school_admin_bp.route('/award_collection')
@login_required
@school_admin_required
def award_collection():
    """奖项收集管理页（指定项目开放上传）"""
    # 获取所有竞赛
    competitions = Competition.query.filter_by(is_active=True).all()
    
    # 筛选条件
    competition_id = request.args.get('competition_id', type=int)
    project_name = request.args.get('project_name', '').strip()
    
    # 查询所有已通过学校审核的项目
    query = Project.query.filter(Project.status.in_([ReviewStatus.FINAL_APPROVED]))
    
    if competition_id:
        query = query.filter(Project.competition_id == competition_id)
    
    if project_name:
        query = query.filter(Project.title.contains(project_name))
    
    projects = query.order_by(Project.created_at.desc()).all()
    
    # 为每个项目获取外部奖项信息
    projects_with_info = []
    for project in projects:
        external_awards = ExternalAward.query.filter_by(project_id=project.id).all()
        projects_with_info.append({
            'project': project,
            'external_awards': external_awards,
            'has_external_awards': len(external_awards) > 0
        })
    
    return render_template('school_admin/award_collection.html',
                         projects_with_info=projects_with_info,
                         competitions=competitions,
                         selected_competition_id=competition_id,
                         project_name=project_name)

@school_admin_bp.route('/project/<int:project_id>/toggle_award_collection', methods=['POST'])
@login_required
@school_admin_required
def toggle_award_collection(project_id):
    """切换项目是否开放奖项收集"""
    project = Project.query.get_or_404(project_id)
    
    # 切换状态
    project.allow_award_collection = not project.allow_award_collection
    db.session.commit()
    
    status_text = '已开放' if project.allow_award_collection else '已关闭'
    flash(f'项目"{project.title}"的奖项收集功能已{status_text}', 'success')
    
    return redirect(url_for('school_admin.award_collection'))

@school_admin_bp.route('/project/<int:project_id>/set_award', methods=['GET', 'POST'])
@login_required
@school_admin_required
def set_award_for_final(project_id):
    """为决赛项目设置奖项"""
    project = Project.query.get_or_404(project_id)
    
    if not project.is_final:
        flash('只有进入决赛的项目才能设置奖项', 'error')
        return redirect(url_for('school_admin.awards'))
    
    form = AwardForm()
    
    if form.validate_on_submit():
        award_name = form.award_name.data
        
        # 检查是否已有奖项
        existing_award = Award.query.filter_by(project_id=project_id).first()
        if existing_award:
            # 更新奖项
            existing_award.award_name = award_name
            # 重新生成证书
            certificate_path = generate_certificate(
                team_name=project.team.name,
                award_name=award_name,
                competition_name=project.competition.name,
                year=project.competition.year
            )
            existing_award.certificate_path = certificate_path
            flash('奖项已更新，证书已重新生成', 'success')
        else:
            # 创建新奖项
            certificate_path = generate_certificate(
                team_name=project.team.name,
                award_name=award_name,
                competition_name=project.competition.name,
                year=project.competition.year
            )
            award = Award(
                project_id=project_id,
                award_name=award_name,
                certificate_path=certificate_path
            )
            db.session.add(award)
            flash('奖项设置成功，证书已生成', 'success')
        
        db.session.commit()
        return redirect(url_for('school_admin.awards', competition_id=project.competition_id))
    
    # 加载已有奖项
    existing_award = Award.query.filter_by(project_id=project_id).first()
    if existing_award:
        form.award_name.data = existing_award.award_name
    
    return render_template('school_admin/set_award.html', project=project, form=form)

@school_admin_bp.route('/users')
@login_required
@school_admin_required
def users():
    """用户管理页 - 显示所有用户"""
    # 基础查询：所有用户
    query = User.query
    
    # 筛选条件
    user_name = request.args.get('user_name', '').strip()
    work_id = request.args.get('work_id', '').strip()
    role = request.args.get('role', '').strip()
    college = request.args.get('college', '').strip()
    
    if user_name:
        query = query.filter(User.real_name.contains(user_name))
    
    if work_id:
        query = query.filter(User.work_id.contains(work_id))
    
    if role:
        query = query.filter(User.role == role)
    
    if college:
        query = query.filter(User.college.contains(college))
    
    # 按注册时间倒序排列
    users_list = query.order_by(User.created_at.desc()).all()
    
    return render_template('school_admin/users.html', users=users_list)

@school_admin_bp.route('/user/create', methods=['GET', 'POST'])
@login_required
@school_admin_required
def create_user():
    """创建新用户"""
    form = UserCreateForm()
    
    if form.validate_on_submit():
        # 验证必填字段根据角色
        role = form.role.data
        work_id = form.work_id.data.strip() if form.work_id.data else None
        username = form.username.data.strip() if form.username.data else None
        email = form.email.data.strip() if form.email.data else None
        
        # 根据角色验证必填字段
        if role in ['student', 'college_admin']:
            if not work_id:
                flash('学生和学院管理员必须填写学工号', 'error')
                return render_template('school_admin/create_user.html', form=form)
        elif role == 'judge':
            if not username:
                flash('校外评委必须填写用户名', 'error')
                return render_template('school_admin/create_user.html', form=form)
        
        # 检查学工号是否已存在
        if work_id:
            existing_user = User.query.filter_by(work_id=work_id).first()
            if existing_user:
                flash('该学工号已被使用', 'error')
                return render_template('school_admin/create_user.html', form=form)
        
        # 检查用户名是否已存在
        if username:
            existing_user = User.query.filter_by(username=username).first()
            if existing_user:
                flash('该用户名已被使用', 'error')
                return render_template('school_admin/create_user.html', form=form)
        
        # 检查邮箱是否已存在
        if email:
            existing_user = User.query.filter_by(email=email).first()
            if existing_user:
                flash('该邮箱已被使用', 'error')
                return render_template('school_admin/create_user.html', form=form)
        
        # 创建新用户
        user = User(
            real_name=form.real_name.data.strip(),
            work_id=work_id,
            username=username,
            email=email,
            college=form.college.data if form.college.data else None,
            unit=form.unit.data.strip() if form.unit.data else None,
            contact_info=form.contact_info.data.strip() if form.contact_info.data else None,
            role=role,
            is_active=form.is_active.data if form.is_active.data is not None else True
        )
        user.set_password(form.password.data)
        
        db.session.add(user)
        db.session.commit()
        flash(f'用户"{user.real_name}"创建成功', 'success')
        return redirect(url_for('school_admin.users'))
    
    return render_template('school_admin/create_user.html', form=form)

@school_admin_bp.route('/user/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@school_admin_required
def edit_user(user_id):
    """编辑用户信息"""
    user = User.query.get_or_404(user_id)
    form = UserEditForm()
    
    # 填充表单数据
    if request.method == 'GET':
        form.real_name.data = user.real_name
        form.work_id.data = user.work_id
        form.username.data = user.username
        form.email.data = user.email
        form.college.data = user.college
        form.unit.data = user.unit
        form.contact_info.data = user.contact_info
        form.role.data = user.role
        form.is_active.data = user.is_active
    
    if form.validate_on_submit():
        # 更新用户信息
        user.real_name = form.real_name.data.strip()
        user.work_id = form.work_id.data.strip() if form.work_id.data else None
        user.username = form.username.data.strip() if form.username.data else None
        user.email = form.email.data.strip() if form.email.data else None
        user.college = form.college.data if form.college.data else None
        user.unit = form.unit.data.strip() if form.unit.data else None
        user.contact_info = form.contact_info.data.strip() if form.contact_info.data else None
        user.role = form.role.data
        user.is_active = form.is_active.data if form.is_active.data is not None else True
        
        # 如果提供了新密码，则更新密码
        if form.new_password.data:
            user.set_password(form.new_password.data)
        
        db.session.commit()
        flash(f'用户"{user.real_name}"信息已更新', 'success')
        return redirect(url_for('school_admin.users'))
    
    return render_template('school_admin/edit_user.html', user=user, form=form)

@school_admin_bp.route('/user/reset_password', methods=['POST'])
@login_required
@school_admin_required
def reset_user_password():
    """重置用户密码为默认密码"""
    data = request.get_json()
    user_id = data.get('user_id')
    
    if not user_id:
        return jsonify({'success': False, 'message': '缺少用户ID'}), 400
    
    user = User.query.get_or_404(user_id)
    
    # 重置为默认密码
    default_password = 'swjtu12345'
    user.set_password(default_password)
    db.session.commit()
    
    return jsonify({'success': True, 'message': '密码已重置'})

@school_admin_bp.route('/user/change_password', methods=['POST'])
@login_required
@school_admin_required
def change_user_password():
    """修改用户密码"""
    data = request.get_json()
    user_id = data.get('user_id')
    new_password = data.get('new_password')
    
    if not user_id or not new_password:
        return jsonify({'success': False, 'message': '缺少必要参数'}), 400
    
    if len(new_password) < 6:
        return jsonify({'success': False, 'message': '密码长度至少为6位'}), 400
    
    user = User.query.get_or_404(user_id)
    user.set_password(new_password)
    db.session.commit()
    
    return jsonify({'success': True, 'message': '密码修改成功'})

@school_admin_bp.route('/user/delete', methods=['POST'])
@login_required
@school_admin_required
def delete_user():
    """删除用户"""
    data = request.get_json()
    user_id = data.get('user_id')
    
    if not user_id:
        return jsonify({'success': False, 'message': '缺少用户ID'}), 400
    
    user = User.query.get_or_404(user_id)
    
    # 不能删除自己
    if user.id == current_user.id:
        return jsonify({'success': False, 'message': '不能删除自己的账户'}), 400
    
    # 检查用户是否有关联数据
    # 检查是否有队伍（作为队长）
    team_count = Team.query.filter_by(leader_id=user_id).count()
    if team_count > 0:
        return jsonify({'success': False, 'message': f'无法删除用户，该用户是 {team_count} 个队伍的队长'}), 400
    
    # 检查是否有队伍成员关系
    from models import TeamMember
    team_member_count = TeamMember.query.filter_by(user_id=user_id).count()
    if team_member_count > 0:
        return jsonify({'success': False, 'message': f'无法删除用户，该用户是 {team_member_count} 个队伍的成员'}), 400
    
    # 检查是否有项目成员关系
    from models import ProjectMember
    project_member_count = ProjectMember.query.filter_by(user_id=user_id).count()
    if project_member_count > 0:
        return jsonify({'success': False, 'message': f'无法删除用户，该用户参与了 {project_member_count} 个项目'}), 400
    
    # 检查是否有评委分配
    judge_assignment_count = JudgeAssignment.query.filter_by(judge_id=user_id).count()
    if judge_assignment_count > 0:
        return jsonify({'success': False, 'message': f'无法删除用户，该用户被分配了 {judge_assignment_count} 个评审任务'}), 400
    
    # 删除用户
    user_name = user.real_name
    db.session.delete(user)
    db.session.commit()
    
    return jsonify({'success': True, 'message': f'用户"{user_name}"已删除'})

@school_admin_bp.route('/roles')
@login_required
@school_admin_required
def roles():
    """角色管理列表页 - 显示所有用户及其角色"""
    # 基础查询：所有用户
    query = User.query
    
    # 筛选条件
    user_name = request.args.get('user_name', '').strip()
    work_id = request.args.get('work_id', '').strip()
    role = request.args.get('role', '').strip()
    college = request.args.get('college', '').strip()
    
    if user_name:
        query = query.filter(User.real_name.contains(user_name))
    
    if work_id:
        query = query.filter(User.work_id.contains(work_id))
    
    if role:
        query = query.filter(User.role == role)
    
    if college:
        query = query.filter(User.college.contains(college))
    
    # 按注册时间倒序排列
    users_list = query.order_by(User.created_at.desc()).all()
    
    return render_template('school_admin/roles.html', users=users_list)

@school_admin_bp.route('/user/<int:user_id>/roles/manage', methods=['GET'])
@login_required
@school_admin_required
def manage_user_roles(user_id):
    """角色管理页面（单个用户）"""
    user = User.query.get_or_404(user_id)
    all_roles = [
        ('student', '学生'),
        ('college_admin', '学院管理员'),
        ('school_admin', '校级管理员'),
        ('judge', '校外评委')
    ]
    
    # 获取用户的额外角色
    additional_roles = [ur.role for ur in user.additional_roles.all()]
    
    return render_template('school_admin/manage_roles.html', user=user, all_roles=all_roles, additional_roles=additional_roles)

@school_admin_bp.route('/user/<int:user_id>/roles/add', methods=['POST'])
@login_required
@school_admin_required
def add_user_role(user_id):
    """为用户添加角色"""
    user = User.query.get_or_404(user_id)
    data = request.get_json()
    role = data.get('role')
    
    if not role:
        return jsonify({'success': False, 'message': '缺少角色参数'}), 400
    
    # 检查角色是否有效
    valid_roles = ['student', 'college_admin', 'school_admin', 'judge']
    if role not in valid_roles:
        return jsonify({'success': False, 'message': '无效的角色'}), 400
    
    # 不能添加主角色作为额外角色
    if role == user.role:
        return jsonify({'success': False, 'message': '不能添加与主角色相同的角色'}), 400
    
    # 检查角色是否已存在
    existing_role = user.additional_roles.filter_by(role=role).first()
    if existing_role:
        return jsonify({'success': False, 'message': '该角色已存在'}), 400
    
    # 添加角色
    user_role = UserRoleAssignment(user_id=user_id, role=role)
    db.session.add(user_role)
    db.session.commit()
    
    role_names = {
        'student': '学生',
        'college_admin': '学院管理员',
        'school_admin': '校级管理员',
        'judge': '校外评委'
    }
    
    return jsonify({'success': True, 'message': f'已添加角色：{role_names.get(role, role)}'})

@school_admin_bp.route('/user/<int:user_id>/roles/remove', methods=['POST'])
@login_required
@school_admin_required
def remove_user_role(user_id):
    """移除用户的角色"""
    user = User.query.get_or_404(user_id)
    data = request.get_json()
    role = data.get('role')
    
    if not role:
        return jsonify({'success': False, 'message': '缺少角色参数'}), 400
    
    # 不能删除主角色
    if role == user.role:
        return jsonify({'success': False, 'message': '不能删除主角色，请先修改用户的主角色'}), 400
    
    # 查找并删除角色
    user_role = user.additional_roles.filter_by(role=role).first()
    if not user_role:
        return jsonify({'success': False, 'message': '该角色不存在'}), 400
    
    db.session.delete(user_role)
    db.session.commit()
    
    role_names = {
        'student': '学生',
        'college_admin': '学院管理员',
        'school_admin': '校级管理员',
        'judge': '校外评委'
    }
    
    return jsonify({'success': True, 'message': f'已移除角色：{role_names.get(role, role)}'})

@school_admin_bp.route('/assessment')
@login_required
@school_admin_required
def assessment():
    """考核模块主页 - 科创竞赛参与与获奖数据"""
    from models import COLLEGES
    from datetime import datetime
    
    # 获取年度筛选参数（默认为当前年份）
    selected_year = request.args.get('year', type=int)
    if not selected_year:
        selected_year = datetime.now().year
    
    # 获取所有可用年份（从竞赛中提取）
    available_years = db.session.query(Competition.year).distinct().order_by(Competition.year.desc()).all()
    available_years = [y[0] for y in available_years if y[0]]
    
    # 挑战杯系列赛事类型
    challenge_cup_types = [
        '"挑战杯"全国大学生课外学术科技作品竞赛',
        '"挑战杯"中国大学生创业计划大赛'
    ]
    
    # 获取指定年度的挑战杯系列竞赛（同一类型只取先创建的）
    challenge_cup_competitions = []
    for comp_type in challenge_cup_types:
        comp = Competition.query.filter(
            Competition.competition_type == comp_type,
            Competition.is_active == True,
            Competition.year == selected_year
        ).order_by(Competition.created_at.asc()).first()  # 取最先创建的
        if comp:
            challenge_cup_competitions.append(comp)
    
    # 按学院统计数据
    college_stats = {}
    
    for college in COLLEGES:
        # 初始化统计数据
        stats = {
            'college': college,
            # 挑战杯主赛道
            'challenge_cup': {
                'registration_count': 0,  # 报名数
                'school_awards': {
                    'gold': 0,  # 校级金奖（一等奖/特等奖）
                    'silver': 0,  # 校级银奖（二等奖）
                    'bronze': 0,  # 校级铜奖（三等奖）
                },
                'provincial_awards': {
                    'gold': 0,  # 省级金奖（一等奖/特等奖）
                    'silver': 0,  # 省级银奖（二等奖）
                    'bronze': 0,  # 省级铜奖（三等奖）
                },
                'national_awards': {
                    'gold': 0,  # 国家级金奖（所有奖项都算，加满3分）
                    'silver': 0,  # 国家级银奖（所有奖项都算，加满3分）
                    'bronze': 0,  # 国家级铜奖（所有奖项都算，加满3分）
                },
                'total_awards': 0,  # 获奖总数
                'special_notes': '',  # 特殊情况备注
            },
            # 配套活动
            'challenge_cup_activities': {
                'registration_count': 0,
                'national_awards': {
                    'gold': 0,
                    'silver': 0,
                    'bronze': 0
                },
                'notes': ''  # 配套活动备注（暂时保留，但表格中不再显示）
            },
            # 红旅赛道
            'red_travel': {
                'registration_count': 0,
                'school_awards': {
                    'gold': 0,  # 校级金奖（一等奖/特等奖）
                    'silver': 0,  # 校级银奖（二等奖）
                    'bronze': 0,  # 校级铜奖（三等奖）
                },
                'provincial_awards': {
                    'gold': 0,  # 省级金奖
                    'silver': 0,  # 省级银奖
                    'bronze': 0,  # 省级铜奖
                },
                'national_awards': {
                    'gold': 0,  # 国家级金奖（所有奖项都算，加满3分）
                    'silver': 0,  # 国家级银奖（所有奖项都算，加满3分）
                    'bronze': 0,  # 国家级铜奖（所有奖项都算，加满3分）
                },
                'total_awards': 0,  # 获奖总数
                'special_notes': ''  # 特殊情况备注
            }
        }
        
        # 统计挑战杯主赛道数据
        for comp in challenge_cup_competitions:
            # 查询该学院在该竞赛中的项目（已通过学校审核）
            projects = Project.query.filter(
                Project.competition_id == comp.id,
                Project.push_college == college,
                Project.status == ReviewStatus.FINAL_APPROVED
            ).all()
            
            stats['challenge_cup']['registration_count'] += len(projects)
            
            # 统计每个项目的奖项
            for project in projects:
                # 统计校赛奖项（Award表）- 统一识别为金奖/银奖/铜奖
                awards = Award.query.filter_by(project_id=project.id).all()
                for award in awards:
                    award_name = award.award_name
                    # 兼容"一等奖/特等奖"和"金奖"，统一识别为金奖
                    if '金奖' in award_name or '一等奖' in award_name or '特等奖' in award_name:
                        stats['challenge_cup']['school_awards']['gold'] += 1
                        stats['challenge_cup']['total_awards'] += 1
                    # 兼容"二等奖"和"银奖"，统一识别为银奖
                    elif '银奖' in award_name or '二等奖' in award_name:
                        stats['challenge_cup']['school_awards']['silver'] += 1
                        stats['challenge_cup']['total_awards'] += 1
                    # 兼容"三等奖"和"铜奖"，统一识别为铜奖
                    elif '铜奖' in award_name or '三等奖' in award_name:
                        stats['challenge_cup']['school_awards']['bronze'] += 1
                        stats['challenge_cup']['total_awards'] += 1
                
                # 统计外部奖项（ExternalAward表）- 统一识别为金奖/银奖/铜奖
                external_awards = ExternalAward.query.filter_by(project_id=project.id).all()
                for ext_award in external_awards:
                    if ext_award.award_level == '省赛':
                        award_name = ext_award.award_name
                        # 兼容"一等奖/特等奖"和"金奖"，统一识别为金奖
                        if '金奖' in award_name or '一等奖' in award_name or '特等奖' in award_name:
                            stats['challenge_cup']['provincial_awards']['gold'] += 1
                            stats['challenge_cup']['total_awards'] += 1
                        # 兼容"二等奖"和"银奖"，统一识别为银奖
                        elif '银奖' in award_name or '二等奖' in award_name:
                            stats['challenge_cup']['provincial_awards']['silver'] += 1
                            stats['challenge_cup']['total_awards'] += 1
                        # 兼容"三等奖"和"铜奖"，统一识别为铜奖
                        elif '铜奖' in award_name or '三等奖' in award_name:
                            stats['challenge_cup']['provincial_awards']['bronze'] += 1
                            stats['challenge_cup']['total_awards'] += 1
                    elif ext_award.award_level == '国赛':
                        award_name = ext_award.award_name
                        # 国赛所有奖项都统计（无论金银铜，计分时都加满3分）
                        if '金奖' in award_name or '一等奖' in award_name or '特等奖' in award_name:
                            stats['challenge_cup']['national_awards']['gold'] += 1
                            stats['challenge_cup']['total_awards'] += 1
                        elif '银奖' in award_name or '二等奖' in award_name:
                            stats['challenge_cup']['national_awards']['silver'] += 1
                            stats['challenge_cup']['total_awards'] += 1
                        elif '铜奖' in award_name or '三等奖' in award_name:
                            stats['challenge_cup']['national_awards']['bronze'] += 1
                            stats['challenge_cup']['total_awards'] += 1
        
        # 统计红旅赛道数据（指定年度，只取先创建的）
        red_travel_comp = Competition.query.filter(
            Competition.competition_type == '中国国际大学生创新大赛"青年红色筑梦之旅"赛道',
            Competition.is_active == True,
            Competition.year == selected_year
        ).order_by(Competition.created_at.asc()).first()  # 取最先创建的
        red_travel_competitions = [red_travel_comp] if red_travel_comp else []
        
        for comp in red_travel_competitions:
            projects = Project.query.filter(
                Project.competition_id == comp.id,
                Project.push_college == college,
                Project.status == ReviewStatus.FINAL_APPROVED
            ).all()
            
            stats['red_travel']['registration_count'] += len(projects)
            
            # 统计每个项目的奖项
            for project in projects:
                # 统计校赛奖项 - 统一识别为金奖/银奖/铜奖
                awards = Award.query.filter_by(project_id=project.id).all()
                for award in awards:
                    award_name = award.award_name
                    # 兼容"一等奖/特等奖"和"金奖"，统一识别为金奖
                    if '金奖' in award_name or '一等奖' in award_name or '特等奖' in award_name:
                        stats['red_travel']['school_awards']['gold'] += 1
                        stats['red_travel']['total_awards'] += 1
                    # 兼容"二等奖"和"银奖"，统一识别为银奖
                    elif '银奖' in award_name or '二等奖' in award_name:
                        stats['red_travel']['school_awards']['silver'] += 1
                        stats['red_travel']['total_awards'] += 1
                    # 兼容"三等奖"和"铜奖"，统一识别为铜奖
                    elif '铜奖' in award_name or '三等奖' in award_name:
                        stats['red_travel']['school_awards']['bronze'] += 1
                        stats['red_travel']['total_awards'] += 1
                
                # 统计外部奖项
                external_awards = ExternalAward.query.filter_by(project_id=project.id).all()
                for ext_award in external_awards:
                    if ext_award.award_level == '省赛':
                        award_name = ext_award.award_name
                        if '金奖' in award_name or '一等奖' in award_name or '特等奖' in award_name:
                            stats['red_travel']['provincial_awards']['gold'] += 1
                            stats['red_travel']['total_awards'] += 1
                        elif '银奖' in award_name or '二等奖' in award_name:
                            stats['red_travel']['provincial_awards']['silver'] += 1
                            stats['red_travel']['total_awards'] += 1
                        elif '铜奖' in award_name or '三等奖' in award_name:
                            stats['red_travel']['provincial_awards']['bronze'] += 1
                            stats['red_travel']['total_awards'] += 1
                    elif ext_award.award_level == '国赛':
                        award_name = ext_award.award_name
                        if '金奖' in award_name or '一等奖' in award_name or '特等奖' in award_name:
                            stats['red_travel']['national_awards']['gold'] += 1
                            stats['red_travel']['total_awards'] += 1
                        elif '银奖' in award_name or '二等奖' in award_name:
                            stats['red_travel']['national_awards']['silver'] += 1
                            stats['red_travel']['total_awards'] += 1
                        elif '铜奖' in award_name or '三等奖' in award_name:
                            stats['red_travel']['national_awards']['bronze'] += 1
                            stats['red_travel']['total_awards'] += 1
        
        # 获取配置数据（任务要求、特殊情况备注、配套活动、可编辑的统计数据）- 按学院获取
        config = AssessmentConfig.query.filter_by(year=selected_year, college=college).first()
        if config:
            # 任务要求
            stats['challenge_cup']['requirement'] = config.challenge_cup_requirement if config.challenge_cup_requirement else None
            stats['red_travel']['requirement'] = config.red_travel_requirement if config.red_travel_requirement else None
            # 特殊情况备注
            stats['challenge_cup']['special_notes'] = config.challenge_cup_special_notes or '' if config.challenge_cup_special_notes else ''
            stats['red_travel']['special_notes'] = config.red_travel_special_notes or '' if config.red_travel_special_notes else ''
            # 配套活动数据（从JSON解析，如果challenge_cup_activities是JSON格式）
            # 暂时保留notes字段的兼容性，后续可以改为存储JSON
            stats['challenge_cup_activities']['notes'] = config.challenge_cup_activities or '' if config.challenge_cup_activities else ''
            
            # 从配置中获取可编辑的统计数据
            # 挑战杯主赛道
            if config.challenge_cup_main_registration is not None:
                stats['challenge_cup']['registration_count'] = config.challenge_cup_main_registration
            if config.challenge_cup_main_school_gold is not None:
                stats['challenge_cup']['school_awards']['gold'] = config.challenge_cup_main_school_gold
            if config.challenge_cup_main_school_silver is not None:
                stats['challenge_cup']['school_awards']['silver'] = config.challenge_cup_main_school_silver
            if config.challenge_cup_main_school_bronze is not None:
                stats['challenge_cup']['school_awards']['bronze'] = config.challenge_cup_main_school_bronze
            if config.challenge_cup_main_provincial_gold is not None:
                stats['challenge_cup']['provincial_awards']['gold'] = config.challenge_cup_main_provincial_gold
            if config.challenge_cup_main_provincial_silver is not None:
                stats['challenge_cup']['provincial_awards']['silver'] = config.challenge_cup_main_provincial_silver
            if config.challenge_cup_main_provincial_bronze is not None:
                stats['challenge_cup']['provincial_awards']['bronze'] = config.challenge_cup_main_provincial_bronze
            if config.challenge_cup_main_national_gold is not None:
                stats['challenge_cup']['national_awards']['gold'] = config.challenge_cup_main_national_gold
            if config.challenge_cup_main_national_silver is not None:
                stats['challenge_cup']['national_awards']['silver'] = config.challenge_cup_main_national_silver
            if config.challenge_cup_main_national_bronze is not None:
                stats['challenge_cup']['national_awards']['bronze'] = config.challenge_cup_main_national_bronze
            if config.challenge_cup_main_total_awards is not None:
                stats['challenge_cup']['total_awards'] = config.challenge_cup_main_total_awards
            
            # 挑战杯配套活动
            if config.challenge_cup_activities_registration is not None:
                stats['challenge_cup_activities']['registration_count'] = config.challenge_cup_activities_registration
            if config.challenge_cup_activities_national_gold is not None:
                stats['challenge_cup_activities']['national_awards']['gold'] = config.challenge_cup_activities_national_gold
            if config.challenge_cup_activities_national_silver is not None:
                stats['challenge_cup_activities']['national_awards']['silver'] = config.challenge_cup_activities_national_silver
            if config.challenge_cup_activities_national_bronze is not None:
                stats['challenge_cup_activities']['national_awards']['bronze'] = config.challenge_cup_activities_national_bronze
            
            # 红旅赛道
            if config.red_travel_registration is not None:
                stats['red_travel']['registration_count'] = config.red_travel_registration
            if config.red_travel_school_gold is not None:
                stats['red_travel']['school_awards']['gold'] = config.red_travel_school_gold
            if config.red_travel_school_silver is not None:
                stats['red_travel']['school_awards']['silver'] = config.red_travel_school_silver
            if config.red_travel_school_bronze is not None:
                stats['red_travel']['school_awards']['bronze'] = config.red_travel_school_bronze
            if config.red_travel_provincial_gold is not None:
                stats['red_travel']['provincial_awards']['gold'] = config.red_travel_provincial_gold
            if config.red_travel_provincial_silver is not None:
                stats['red_travel']['provincial_awards']['silver'] = config.red_travel_provincial_silver
            if config.red_travel_provincial_bronze is not None:
                stats['red_travel']['provincial_awards']['bronze'] = config.red_travel_provincial_bronze
            if config.red_travel_national_gold is not None:
                stats['red_travel']['national_awards']['gold'] = config.red_travel_national_gold
            if config.red_travel_national_silver is not None:
                stats['red_travel']['national_awards']['silver'] = config.red_travel_national_silver
            if config.red_travel_national_bronze is not None:
                stats['red_travel']['national_awards']['bronze'] = config.red_travel_national_bronze
            if config.red_travel_total_awards is not None:
                stats['red_travel']['total_awards'] = config.red_travel_total_awards
        else:
            stats['challenge_cup']['requirement'] = None
            stats['red_travel']['requirement'] = None
            stats['challenge_cup']['special_notes'] = ''
            stats['red_travel']['special_notes'] = ''
            stats['challenge_cup_activities']['notes'] = ''
        
        college_stats[college] = stats
    
    return render_template('school_admin/assessment_data_aggrid.html', 
                         colleges=COLLEGES,
                         college_stats=college_stats,
                         selected_year=selected_year,
                         available_years=available_years)

@school_admin_bp.route('/assessment/aggrid')
@login_required
@school_admin_required
def assessment_aggrid():
    """考核模块主页 - AG Grid 版本（重定向到 /assessment）"""
    year = request.args.get('year')
    if year:
        return redirect(url_for('school_admin.assessment', year=year))
    else:
        return redirect(url_for('school_admin.assessment'))

@school_admin_bp.route('/assessment/score')
@login_required
@school_admin_required
def assessment_score():
    """年度考核分数统计"""
    from models import COLLEGES
    from datetime import datetime
    
    # 获取年度筛选参数（默认为当前年份）
    selected_year = request.args.get('year', type=int)
    if not selected_year:
        selected_year = datetime.now().year
    
    # 获取所有可用年份（从竞赛中提取）
    available_years = db.session.query(Competition.year).distinct().order_by(Competition.year.desc()).all()
    available_years = [y[0] for y in available_years if y[0]]
    
    # 重新计算统计数据（与assessment()函数相同的逻辑）
    challenge_cup_types = [
        '"挑战杯"全国大学生课外学术科技作品竞赛',
        '"挑战杯"中国大学生创业计划大赛'
    ]
    
    # 获取指定年度的挑战杯系列竞赛（同一类型只取先创建的）
    challenge_cup_competitions = []
    for comp_type in challenge_cup_types:
        comp = Competition.query.filter(
            Competition.competition_type == comp_type,
            Competition.is_active == True,
            Competition.year == selected_year
        ).order_by(Competition.created_at.asc()).first()  # 取最先创建的
        if comp:
            challenge_cup_competitions.append(comp)
    
    # 获取红旅竞赛（只取先创建的）
    red_travel_comp = Competition.query.filter(
        Competition.competition_type == '中国国际大学生创新大赛"青年红色筑梦之旅"赛道',
        Competition.is_active == True,
        Competition.year == selected_year
    ).order_by(Competition.created_at.asc()).first()  # 取最先创建的
    red_travel_competitions = [red_travel_comp] if red_travel_comp else []
    
    # 按学院统计分数
    college_scores = {}
    
    for college in COLLEGES:
        # 初始化分数统计
        score_data = {
            'college': college,
            'red_travel_participation': 0,  # 红旅参与（申报队伍数）
            'red_travel_award': 0,  # 红旅获奖（最高奖项分数）
            'challenge_cup_participation': 0,  # 挑战杯参与（报名数）
            'challenge_cup_award': 0,  # 挑战杯获奖（最高奖项分数）
            'total_score': 0,  # 总分
            'score_details': {
                'red_travel_participation': {'score': 0, 'note': ''},
                'red_travel_award': {'score': 0, 'note': ''},
                'challenge_cup_participation': {'score': 0, 'note': ''},
                'challenge_cup_award': {'score': 0, 'note': ''}
            }
        }
        
        # 统计红旅数据
        red_travel_projects = []
        if red_travel_comp:
            projects = Project.query.filter(
                Project.competition_id == red_travel_comp.id,
                Project.push_college == college,
                Project.status == ReviewStatus.FINAL_APPROVED
            ).all()
            red_travel_projects.extend(projects)
        
        score_data['red_travel_participation'] = len(red_travel_projects)
        # 红旅参与分数计算（2分满分，实际申报/要求申报*2分，上限2分，缺项为空）
        actual_count = len(red_travel_projects)
        # 按学院获取任务要求
        college_config = AssessmentConfig.query.filter_by(year=selected_year, college=college).first()
        target_count = college_config.red_travel_requirement if college_config and college_config.red_travel_requirement else None
        
        if target_count is None or target_count == 0:
            # 缺项：任务要求未设置，分数为空
            score_data['score_details']['red_travel_participation']['score'] = None
            score_data['score_details']['red_travel_participation']['note'] = f'申报队伍数：{actual_count}（任务要求未设置）'
        else:
            # 实际申报/要求申报*2分，上限2分
            calculated_score = min(2.0, (actual_count / target_count) * 2.0)
            score_data['score_details']['red_travel_participation']['score'] = calculated_score
            score_data['score_details']['red_travel_participation']['note'] = f'申报队伍数：{actual_count}，任务要求：{target_count}'
        
        # 红旅获奖分数计算（3分满分，取最高奖项）
        max_red_travel_score = 0
        for project in red_travel_projects:
            # 检查校赛奖项 - 统一识别为金奖/银奖/铜奖
            awards = Award.query.filter_by(project_id=project.id).all()
            for award in awards:
                award_name = award.award_name
                # 校赛：金奖=1分，银奖=0.6分，铜奖=0.3分（特等奖按金奖算）
                if '金奖' in award_name or '一等奖' in award_name or '特等奖' in award_name:
                    max_red_travel_score = max(max_red_travel_score, 1.0)
                elif '银奖' in award_name or '二等奖' in award_name:
                    max_red_travel_score = max(max_red_travel_score, 0.6)
                elif '铜奖' in award_name or '三等奖' in award_name:
                    max_red_travel_score = max(max_red_travel_score, 0.3)
            
            # 检查外部奖项
            external_awards = ExternalAward.query.filter_by(project_id=project.id).all()
            for ext_award in external_awards:
                award_name = ext_award.award_name
                if ext_award.award_level == '省赛':
                    # 省赛：金奖=3分，银奖=2分，铜奖=1分
                    if '金奖' in award_name or '一等奖' in award_name or '特等奖' in award_name:
                        max_red_travel_score = max(max_red_travel_score, 3.0)
                    elif '银奖' in award_name or '二等奖' in award_name:
                        max_red_travel_score = max(max_red_travel_score, 2.0)
                    elif '铜奖' in award_name or '三等奖' in award_name:
                        max_red_travel_score = max(max_red_travel_score, 1.0)
                elif ext_award.award_level == '国赛':
                    # 国赛：无论金银铜都加满（3分）
                    if '金奖' in award_name or '银奖' in award_name or '铜奖' in award_name or '一等奖' in award_name or '二等奖' in award_name or '三等奖' in award_name or '特等奖' in award_name:
                        max_red_travel_score = max(max_red_travel_score, 3.0)
        
        score_data['red_travel_award'] = max_red_travel_score
        score_data['score_details']['red_travel_award']['score'] = min(3.0, max_red_travel_score)
        if max_red_travel_score == 0:
            score_data['score_details']['red_travel_award']['note'] = '无获奖'
        else:
            score_data['score_details']['red_travel_award']['note'] = f'最高奖项得分：{max_red_travel_score}分'
        
        # 统计挑战杯数据
        challenge_cup_projects = []
        for comp in challenge_cup_competitions:
            projects = Project.query.filter(
                Project.competition_id == comp.id,
                Project.push_college == college,
                Project.status == ReviewStatus.FINAL_APPROVED
            ).all()
            challenge_cup_projects.extend(projects)
        
        score_data['challenge_cup_participation'] = len(challenge_cup_projects)
        # 挑战杯参与分数计算（2分满分，实际申报/要求申报*2分，上限2分，缺项为空）
        actual_count = len(challenge_cup_projects)
        # 按学院获取任务要求
        college_config = AssessmentConfig.query.filter_by(year=selected_year, college=college).first()
        target_count = college_config.challenge_cup_requirement if college_config and college_config.challenge_cup_requirement else None
        
        if target_count is None or target_count == 0:
            # 缺项：任务要求未设置，分数为空
            score_data['score_details']['challenge_cup_participation']['score'] = None
            score_data['score_details']['challenge_cup_participation']['note'] = f'报名数：{actual_count}（任务要求未设置）'
        else:
            # 实际申报/要求申报*2分，上限2分
            calculated_score = min(2.0, (actual_count / target_count) * 2.0)
            score_data['score_details']['challenge_cup_participation']['score'] = calculated_score
            score_data['score_details']['challenge_cup_participation']['note'] = f'报名数：{actual_count}，任务要求：{target_count}'
        
        # 挑战杯获奖分数计算（3分满分，取最高奖项）
        max_challenge_cup_score = 0
        for project in challenge_cup_projects:
            # 检查校赛奖项 - 统一识别为金奖/银奖/铜奖
            awards = Award.query.filter_by(project_id=project.id).all()
            for award in awards:
                award_name = award.award_name
                # 校赛：金奖=1分，银奖=0.6分，铜奖=0.3分（特等奖按金奖算）
                if '金奖' in award_name or '一等奖' in award_name or '特等奖' in award_name:
                    max_challenge_cup_score = max(max_challenge_cup_score, 1.0)
                elif '银奖' in award_name or '二等奖' in award_name:
                    max_challenge_cup_score = max(max_challenge_cup_score, 0.6)
                elif '铜奖' in award_name or '三等奖' in award_name:
                    max_challenge_cup_score = max(max_challenge_cup_score, 0.3)
            
            # 检查外部奖项
            external_awards = ExternalAward.query.filter_by(project_id=project.id).all()
            for ext_award in external_awards:
                award_name = ext_award.award_name
                if ext_award.award_level == '省赛':
                    # 省赛：金奖=3分，银奖=2分，铜奖=1分（特等奖按金奖算）
                    if '金奖' in award_name or '一等奖' in award_name or '特等奖' in award_name:
                        max_challenge_cup_score = max(max_challenge_cup_score, 3.0)
                    elif '银奖' in award_name or '二等奖' in award_name:
                        max_challenge_cup_score = max(max_challenge_cup_score, 2.0)
                    elif '铜奖' in award_name or '三等奖' in award_name:
                        max_challenge_cup_score = max(max_challenge_cup_score, 1.0)
                elif ext_award.award_level == '国赛':
                    # 国赛：无论金银铜都加满（3分）
                    if '金奖' in award_name or '银奖' in award_name or '铜奖' in award_name or '一等奖' in award_name or '二等奖' in award_name or '三等奖' in award_name or '特等奖' in award_name:
                        max_challenge_cup_score = max(max_challenge_cup_score, 3.0)
        
        score_data['challenge_cup_award'] = max_challenge_cup_score
        score_data['score_details']['challenge_cup_award']['score'] = min(3.0, max_challenge_cup_score)
        if max_challenge_cup_score == 0:
            score_data['score_details']['challenge_cup_award']['note'] = '无获奖'
        else:
            score_data['score_details']['challenge_cup_award']['note'] = f'最高奖项得分：{max_challenge_cup_score}分'
        
        # 计算总分（如果某项为空则不计入）
        total_score = 0
        if score_data['score_details']['red_travel_participation']['score'] is not None:
            total_score += score_data['score_details']['red_travel_participation']['score']
        total_score += score_data['score_details']['red_travel_award']['score']
        if score_data['score_details']['challenge_cup_participation']['score'] is not None:
            total_score += score_data['score_details']['challenge_cup_participation']['score']
        total_score += score_data['score_details']['challenge_cup_award']['score']
        score_data['total_score'] = total_score
        
        college_scores[college] = score_data
    
    return render_template('school_admin/assessment_score.html', 
                         colleges=COLLEGES,
                         college_scores=college_scores,
                         selected_year=selected_year,
                         available_years=available_years)

@school_admin_bp.route('/assessment/score/aggrid')
@login_required
@school_admin_required
def assessment_score_aggrid():
    """年度考核分数统计 - AG Grid 版本"""
    # 复用 assessment_score() 的数据准备逻辑
    from models import COLLEGES
    from datetime import datetime
    
    selected_year = request.args.get('year', type=int)
    if not selected_year:
        selected_year = datetime.now().year
    
    available_years = db.session.query(Competition.year).distinct().order_by(Competition.year.desc()).all()
    available_years = [y[0] for y in available_years if y[0]]
    
    # 重新计算统计数据（与assessment_score()函数相同的逻辑）
    challenge_cup_types = [
        '"挑战杯"全国大学生课外学术科技作品竞赛',
        '"挑战杯"中国大学生创业计划大赛'
    ]
    
    challenge_cup_competitions = []
    for comp_type in challenge_cup_types:
        comp = Competition.query.filter(
            Competition.competition_type == comp_type,
            Competition.is_active == True,
            Competition.year == selected_year
        ).order_by(Competition.created_at.asc()).first()
        if comp:
            challenge_cup_competitions.append(comp)
    
    red_travel_comp = Competition.query.filter(
        Competition.competition_type == '中国国际大学生创新大赛"青年红色筑梦之旅"赛道',
        Competition.is_active == True,
        Competition.year == selected_year
    ).order_by(Competition.created_at.asc()).first()
    
    college_scores = {}
    
    for college in COLLEGES:
        score_data = {
            'college': college,
            'red_travel_participation': 0,
            'red_travel_award': 0,
            'challenge_cup_participation': 0,
            'challenge_cup_award': 0,
            'total_score': 0,
            'score_details': {
                'red_travel_participation': {'score': 0, 'note': ''},
                'red_travel_award': {'score': 0, 'note': ''},
                'challenge_cup_participation': {'score': 0, 'note': ''},
                'challenge_cup_award': {'score': 0, 'note': ''}
            }
        }
        
        red_travel_projects = []
        if red_travel_comp:
            projects = Project.query.filter(
                Project.competition_id == red_travel_comp.id,
                Project.push_college == college,
                Project.status == ReviewStatus.FINAL_APPROVED
            ).all()
            red_travel_projects.extend(projects)
        
        score_data['red_travel_participation'] = len(red_travel_projects)
        actual_count = len(red_travel_projects)
        college_config = AssessmentConfig.query.filter_by(year=selected_year, college=college).first()
        target_count = college_config.red_travel_requirement if college_config and college_config.red_travel_requirement else None
        
        # 优先使用保存的分数，否则使用计算值
        if college_config and college_config.red_travel_participation_score is not None:
            score_data['score_details']['red_travel_participation']['score'] = college_config.red_travel_participation_score
        elif target_count is None or target_count == 0:
            score_data['score_details']['red_travel_participation']['score'] = None
            score_data['score_details']['red_travel_participation']['note'] = f'申报队伍数：{actual_count}（任务要求未设置）'
        else:
            calculated_score = min(2.0, (actual_count / target_count) * 2.0)
            score_data['score_details']['red_travel_participation']['score'] = calculated_score
            score_data['score_details']['red_travel_participation']['note'] = f'申报队伍数：{actual_count}，任务要求：{target_count}'
        
        max_red_travel_score = 0
        for project in red_travel_projects:
            awards = Award.query.filter_by(project_id=project.id).all()
            for award in awards:
                award_name = award.award_name
                if '金奖' in award_name or '一等奖' in award_name or '特等奖' in award_name:
                    max_red_travel_score = max(max_red_travel_score, 1.0)
                elif '银奖' in award_name or '二等奖' in award_name:
                    max_red_travel_score = max(max_red_travel_score, 0.6)
                elif '铜奖' in award_name or '三等奖' in award_name:
                    max_red_travel_score = max(max_red_travel_score, 0.3)
            
            external_awards = ExternalAward.query.filter_by(project_id=project.id).all()
            for ext_award in external_awards:
                award_name = ext_award.award_name
                if ext_award.award_level == '省赛':
                    if '金奖' in award_name or '一等奖' in award_name or '特等奖' in award_name:
                        max_red_travel_score = max(max_red_travel_score, 3.0)
                    elif '银奖' in award_name or '二等奖' in award_name:
                        max_red_travel_score = max(max_red_travel_score, 2.0)
                    elif '铜奖' in award_name or '三等奖' in award_name:
                        max_red_travel_score = max(max_red_travel_score, 1.0)
                elif ext_award.award_level == '国赛':
                    max_red_travel_score = max(max_red_travel_score, 3.0)
        
        score_data['red_travel_award'] = max_red_travel_score
        # 优先使用保存的分数，否则使用计算值
        if college_config and college_config.red_travel_award_score is not None:
            score_data['score_details']['red_travel_award']['score'] = college_config.red_travel_award_score
        else:
            score_data['score_details']['red_travel_award']['score'] = min(3.0, max_red_travel_score)
        if max_red_travel_score == 0:
            score_data['score_details']['red_travel_award']['note'] = '无获奖'
        else:
            score_data['score_details']['red_travel_award']['note'] = f'最高奖项得分：{max_red_travel_score}分'
        
        challenge_cup_projects = []
        for comp in challenge_cup_competitions:
            projects = Project.query.filter(
                Project.competition_id == comp.id,
                Project.push_college == college,
                Project.status == ReviewStatus.FINAL_APPROVED
            ).all()
            challenge_cup_projects.extend(projects)
        
        score_data['challenge_cup_participation'] = len(challenge_cup_projects)
        actual_count = len(challenge_cup_projects)
        target_count = college_config.challenge_cup_requirement if college_config and college_config.challenge_cup_requirement else None
        
        # 优先使用保存的分数，否则使用计算值
        if college_config and college_config.challenge_cup_participation_score is not None:
            score_data['score_details']['challenge_cup_participation']['score'] = college_config.challenge_cup_participation_score
        elif target_count is None or target_count == 0:
            score_data['score_details']['challenge_cup_participation']['score'] = None
            score_data['score_details']['challenge_cup_participation']['note'] = f'报名数：{actual_count}（任务要求未设置）'
        else:
            calculated_score = min(2.0, (actual_count / target_count) * 2.0)
            score_data['score_details']['challenge_cup_participation']['score'] = calculated_score
            score_data['score_details']['challenge_cup_participation']['note'] = f'报名数：{actual_count}，任务要求：{target_count}'
        
        max_challenge_cup_score = 0
        for project in challenge_cup_projects:
            awards = Award.query.filter_by(project_id=project.id).all()
            for award in awards:
                award_name = award.award_name
                if '金奖' in award_name or '一等奖' in award_name or '特等奖' in award_name:
                    max_challenge_cup_score = max(max_challenge_cup_score, 1.0)
                elif '银奖' in award_name or '二等奖' in award_name:
                    max_challenge_cup_score = max(max_challenge_cup_score, 0.6)
                elif '铜奖' in award_name or '三等奖' in award_name:
                    max_challenge_cup_score = max(max_challenge_cup_score, 0.3)
            
            external_awards = ExternalAward.query.filter_by(project_id=project.id).all()
            for ext_award in external_awards:
                award_name = ext_award.award_name
                if ext_award.award_level == '省赛':
                    if '金奖' in award_name or '一等奖' in award_name or '特等奖' in award_name:
                        max_challenge_cup_score = max(max_challenge_cup_score, 3.0)
                    elif '银奖' in award_name or '二等奖' in award_name:
                        max_challenge_cup_score = max(max_challenge_cup_score, 2.0)
                    elif '铜奖' in award_name or '三等奖' in award_name:
                        max_challenge_cup_score = max(max_challenge_cup_score, 1.0)
                elif ext_award.award_level == '国赛':
                    max_challenge_cup_score = max(max_challenge_cup_score, 3.0)
        
        score_data['challenge_cup_award'] = max_challenge_cup_score
        # 优先使用保存的分数，否则使用计算值
        if college_config and college_config.challenge_cup_award_score is not None:
            score_data['score_details']['challenge_cup_award']['score'] = college_config.challenge_cup_award_score
        else:
            score_data['score_details']['challenge_cup_award']['score'] = min(3.0, max_challenge_cup_score)
        if max_challenge_cup_score == 0:
            score_data['score_details']['challenge_cup_award']['note'] = '无获奖'
        else:
            score_data['score_details']['challenge_cup_award']['note'] = f'最高奖项得分：{max_challenge_cup_score}分'
        
        total_score = 0
        if score_data['score_details']['red_travel_participation']['score'] is not None:
            total_score += score_data['score_details']['red_travel_participation']['score']
        total_score += score_data['score_details']['red_travel_award']['score']
        if score_data['score_details']['challenge_cup_participation']['score'] is not None:
            total_score += score_data['score_details']['challenge_cup_participation']['score']
        total_score += score_data['score_details']['challenge_cup_award']['score']
        score_data['total_score'] = total_score
        
        college_scores[college] = score_data
    
    return render_template('school_admin/assessment_score_aggrid.html', 
                         colleges=COLLEGES,
                         college_scores=college_scores,
                         selected_year=selected_year,
                         available_years=available_years)

@school_admin_bp.route('/assessment/config/save', methods=['POST'])
@login_required
@school_admin_required
def save_assessment_config():
    """保存考核配置（按学院保存，AJAX接口）"""
    try:
        from datetime import datetime
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'message': '请求数据为空'}), 400
        
        selected_year = data.get('year')
        if not selected_year:
            selected_year = datetime.now().year
        
        college = data.get('college')
        if not college:
            return jsonify({'success': False, 'message': '学院参数缺失'}), 400
        
        field_type = data.get('field_type')  # 'requirement_challenge_cup', 'requirement_red_travel', 'special_notes_challenge_cup', 'special_notes_red_travel', 'activities_challenge_cup'
        value = data.get('value', '')
        # 如果是字符串，则strip；如果是数字，则转换为字符串
        if isinstance(value, str):
            value = value.strip()
        elif value is None:
            value = ''
        else:
            # 如果是数字，转换为字符串
            value = str(value)
        
        # 处理数字字段：空字符串或非数字字符串 -> None，有效数字字符串 -> int
        def parse_int_value(v):
            if not v or not v.strip():
                return None
            try:
                return int(float(v))  # 支持 '5.0' 这样的字符串
            except (ValueError, TypeError):
                return None
        
        # 获取或创建配置记录
        config = AssessmentConfig.query.filter_by(year=selected_year, college=college).first()
        if not config:
            config = AssessmentConfig(year=selected_year, college=college)
            db.session.add(config)
        
        # 根据字段类型更新相应的字段
        if field_type == 'requirement_challenge_cup':
            config.challenge_cup_requirement = parse_int_value(value)
        elif field_type == 'requirement_red_travel':
            config.red_travel_requirement = parse_int_value(value)
        elif field_type == 'special_notes_challenge_cup':
            config.challenge_cup_special_notes = value if value else None
        elif field_type == 'special_notes_red_travel':
            config.red_travel_special_notes = value if value else None
        elif field_type == 'activities_challenge_cup':
            config.challenge_cup_activities = value if value else None
        else:
            return jsonify({'success': False, 'message': '无效的字段类型'}), 400
        
        db.session.commit()
        return jsonify({'success': True, 'message': '保存成功'})
    except Exception as e:
        db.session.rollback()
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': '保存失败: ' + str(e)}), 500

@school_admin_bp.route('/assessment/data/save', methods=['POST'])
@login_required
@school_admin_required
def save_assessment_data():
    """保存考核数据（按学院保存，AJAX接口）"""
    try:
        from datetime import datetime
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'message': '请求数据为空'}), 400
        
        selected_year = data.get('year')
        if not selected_year:
            selected_year = datetime.now().year
        
        college = data.get('college')
        if not college:
            return jsonify({'success': False, 'message': '学院参数缺失'}), 400
        
        field_type = data.get('field_type')
        value = data.get('value', '')
        # 如果是字符串，则strip；如果是数字，则转换为字符串
        if isinstance(value, str):
            value = value.strip()
        elif value is None:
            value = ''
        else:
            # 如果是数字，转换为字符串（包括0）
            value = str(value)
        
        # 处理数字字段：空字符串或非数字字符串 -> None，有效数字字符串 -> int
        def parse_int_value(v):
            if not v or not v.strip():
                return None
            try:
                return int(float(v))  # 支持 '5.0' 这样的字符串
            except (ValueError, TypeError):
                return None
        
        # 获取或创建配置记录
        config = AssessmentConfig.query.filter_by(year=selected_year, college=college).first()
        if not config:
            config = AssessmentConfig(year=selected_year, college=college)
            db.session.add(config)
        
        # 根据字段类型更新相应的字段
        # 挑战杯主赛道
        if field_type == 'registration_count_challenge_cup':
            config.challenge_cup_main_registration = parse_int_value(value)
        elif field_type == 'school_gold_challenge_cup':
            config.challenge_cup_main_school_gold = parse_int_value(value)
        elif field_type == 'school_silver_challenge_cup':
            config.challenge_cup_main_school_silver = parse_int_value(value)
        elif field_type == 'school_bronze_challenge_cup':
            config.challenge_cup_main_school_bronze = parse_int_value(value)
        elif field_type == 'provincial_gold_challenge_cup':
            config.challenge_cup_main_provincial_gold = parse_int_value(value)
        elif field_type == 'provincial_silver_challenge_cup':
            config.challenge_cup_main_provincial_silver = parse_int_value(value)
        elif field_type == 'provincial_bronze_challenge_cup':
            config.challenge_cup_main_provincial_bronze = parse_int_value(value)
        elif field_type == 'national_gold_challenge_cup':
            config.challenge_cup_main_national_gold = parse_int_value(value)
        elif field_type == 'national_silver_challenge_cup':
            config.challenge_cup_main_national_silver = parse_int_value(value)
        elif field_type == 'national_bronze_challenge_cup':
            config.challenge_cup_main_national_bronze = parse_int_value(value)
        elif field_type == 'total_awards_challenge_cup':
            config.challenge_cup_main_total_awards = parse_int_value(value)
        # 挑战杯配套活动
        elif field_type == 'activities_registration_challenge_cup':
            config.challenge_cup_activities_registration = parse_int_value(value)
        elif field_type == 'activities_national_gold':
            config.challenge_cup_activities_national_gold = parse_int_value(value)
        elif field_type == 'activities_national_silver':
            config.challenge_cup_activities_national_silver = parse_int_value(value)
        elif field_type == 'activities_national_bronze':
            config.challenge_cup_activities_national_bronze = parse_int_value(value)
        # 红旅赛道
        elif field_type == 'registration_count_red_travel':
            config.red_travel_registration = parse_int_value(value)
        elif field_type == 'school_gold_red_travel':
            config.red_travel_school_gold = parse_int_value(value)
        elif field_type == 'school_silver_red_travel':
            config.red_travel_school_silver = parse_int_value(value)
        elif field_type == 'school_bronze_red_travel':
            config.red_travel_school_bronze = parse_int_value(value)
        elif field_type == 'provincial_gold_red_travel':
            config.red_travel_provincial_gold = parse_int_value(value)
        elif field_type == 'provincial_silver_red_travel':
            config.red_travel_provincial_silver = parse_int_value(value)
        elif field_type == 'provincial_bronze_red_travel':
            config.red_travel_provincial_bronze = parse_int_value(value)
        elif field_type == 'national_gold_red_travel':
            config.red_travel_national_gold = parse_int_value(value)
        elif field_type == 'national_silver_red_travel':
            config.red_travel_national_silver = parse_int_value(value)
        elif field_type == 'national_bronze_red_travel':
            config.red_travel_national_bronze = parse_int_value(value)
        elif field_type == 'total_awards_red_travel':
            config.red_travel_total_awards = parse_int_value(value)
        else:
            return jsonify({'success': False, 'message': '无效的字段类型: ' + str(field_type)}), 400
        
        db.session.commit()
        return jsonify({'success': True, 'message': '保存成功'})
    except Exception as e:
        db.session.rollback()
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': '保存失败: ' + str(e)}), 500

@school_admin_bp.route('/assessment/score/save', methods=['POST'])
@login_required
@school_admin_required
def save_assessment_score():
    """保存考核分数（按学院保存，AJAX接口）"""
    try:
        from datetime import datetime
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'message': '请求数据为空'}), 400
        
        selected_year = data.get('year')
        if not selected_year:
            selected_year = datetime.now().year
        
        college = data.get('college')
        if not college:
            return jsonify({'success': False, 'message': '学院参数缺失'}), 400
        
        field_type = data.get('field_type')
        value = data.get('value')
        
        # 处理分数字段：如果是null/undefined/空字符串，则设为None；否则转换为float
        def parse_float_value(v):
            if v is None:
                return None
            # 如果是字符串，检查是否为空
            if isinstance(v, str):
                v = v.strip()
                if v == '' or v == 'null' or v == 'undefined':
                    return None
            # 如果是数字，直接转换
            try:
                return float(v)
            except (ValueError, TypeError):
                return None
        
        # 获取或创建配置记录
        config = AssessmentConfig.query.filter_by(year=selected_year, college=college).first()
        if not config:
            config = AssessmentConfig(year=selected_year, college=college)
            db.session.add(config)
        
        # 根据字段类型更新相应的字段
        if field_type == 'red_travel_participation_score':
            config.red_travel_participation_score = parse_float_value(value)
        elif field_type == 'red_travel_award_score':
            config.red_travel_award_score = parse_float_value(value)
        elif field_type == 'challenge_cup_participation_score':
            config.challenge_cup_participation_score = parse_float_value(value)
        elif field_type == 'challenge_cup_award_score':
            config.challenge_cup_award_score = parse_float_value(value)
        else:
            return jsonify({'success': False, 'message': '无效的字段类型: ' + str(field_type)}), 400
        
        db.session.commit()
        return jsonify({'success': True, 'message': '保存成功'})
    except Exception as e:
        db.session.rollback()
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': '保存失败: ' + str(e)}), 500

@school_admin_bp.route('/assessment/export')
@login_required
@school_admin_required
def export_assessment():
    """导出考核数据到Excel（2个sheet：情况统计、算分）"""
    from datetime import datetime
    from io import BytesIO
    import pandas as pd
    from models import COLLEGES
    
    selected_year = request.args.get('year', type=int)
    if not selected_year:
        selected_year = datetime.now().year
    
    # 挑战杯系列赛事类型
    challenge_cup_types = [
        '"挑战杯"全国大学生课外学术科技作品竞赛',
        '"挑战杯"中国大学生创业计划大赛'
    ]
    
    # 获取指定年度的挑战杯系列竞赛（同一类型只取先创建的）
    challenge_cup_competitions = []
    for comp_type in challenge_cup_types:
        comp = Competition.query.filter(
            Competition.competition_type == comp_type,
            Competition.is_active == True,
            Competition.year == selected_year
        ).order_by(Competition.created_at.asc()).first()
        if comp:
            challenge_cup_competitions.append(comp)
    
    # 获取红旅竞赛（只取先创建的）
    red_travel_comp = Competition.query.filter(
        Competition.competition_type == '中国国际大学生创新大赛"青年红色筑梦之旅"赛道',
        Competition.is_active == True,
        Competition.year == selected_year
    ).order_by(Competition.created_at.asc()).first()
    
    # Sheet 1: 情况统计
    data_stats = []
    for college in COLLEGES:
        # 统计挑战杯数据
        challenge_cup_count = 0
        challenge_cup_school_gold = 0
        challenge_cup_school_silver = 0
        challenge_cup_school_bronze = 0
        challenge_cup_provincial_gold = 0
        challenge_cup_provincial_silver = 0
        challenge_cup_provincial_bronze = 0
        challenge_cup_national_gold = 0
        challenge_cup_national_silver = 0
        challenge_cup_national_bronze = 0
        
        for comp in challenge_cup_competitions:
            projects = Project.query.filter(
                Project.competition_id == comp.id,
                Project.push_college == college,
                Project.status == ReviewStatus.FINAL_APPROVED
            ).all()
            challenge_cup_count += len(projects)
            
            for project in projects:
                awards = Award.query.filter_by(project_id=project.id).all()
                for award in awards:
                    award_name = award.award_name
                    if '金奖' in award_name or '一等奖' in award_name or '特等奖' in award_name:
                        challenge_cup_school_gold += 1
                    elif '银奖' in award_name or '二等奖' in award_name:
                        challenge_cup_school_silver += 1
                    elif '铜奖' in award_name or '三等奖' in award_name:
                        challenge_cup_school_bronze += 1
                
                external_awards = ExternalAward.query.filter_by(project_id=project.id).all()
                for ext_award in external_awards:
                    award_name = ext_award.award_name
                    if ext_award.award_level == '省赛':
                        if '金奖' in award_name or '一等奖' in award_name or '特等奖' in award_name:
                            challenge_cup_provincial_gold += 1
                        elif '银奖' in award_name or '二等奖' in award_name:
                            challenge_cup_provincial_silver += 1
                        elif '铜奖' in award_name or '三等奖' in award_name:
                            challenge_cup_provincial_bronze += 1
                    elif ext_award.award_level == '国赛':
                        if '金奖' in award_name or '一等奖' in award_name or '特等奖' in award_name:
                            challenge_cup_national_gold += 1
                        elif '银奖' in award_name or '二等奖' in award_name:
                            challenge_cup_national_silver += 1
                        elif '铜奖' in award_name or '三等奖' in award_name:
                            challenge_cup_national_bronze += 1
        
        # 统计红旅数据
        red_travel_count = 0
        red_travel_school_gold = 0
        red_travel_school_silver = 0
        red_travel_school_bronze = 0
        red_travel_provincial_gold = 0
        red_travel_provincial_silver = 0
        red_travel_provincial_bronze = 0
        red_travel_national_gold = 0
        red_travel_national_silver = 0
        red_travel_national_bronze = 0
        red_travel_total = 0
        
        if red_travel_comp:
            projects = Project.query.filter(
                Project.competition_id == red_travel_comp.id,
                Project.push_college == college,
                Project.status == ReviewStatus.FINAL_APPROVED
            ).all()
            red_travel_count = len(projects)
            
            for project in projects:
                awards = Award.query.filter_by(project_id=project.id).all()
                for award in awards:
                    award_name = award.award_name
                    if '金奖' in award_name or '一等奖' in award_name or '特等奖' in award_name:
                        red_travel_school_gold += 1
                        red_travel_total += 1
                    elif '银奖' in award_name or '二等奖' in award_name:
                        red_travel_school_silver += 1
                        red_travel_total += 1
                    elif '铜奖' in award_name or '三等奖' in award_name:
                        red_travel_school_bronze += 1
                        red_travel_total += 1
                
                external_awards = ExternalAward.query.filter_by(project_id=project.id).all()
                for ext_award in external_awards:
                    award_name = ext_award.award_name
                    if ext_award.award_level == '省赛':
                        if '金奖' in award_name or '一等奖' in award_name or '特等奖' in award_name:
                            red_travel_provincial_gold += 1
                            red_travel_total += 1
                        elif '银奖' in award_name or '二等奖' in award_name:
                            red_travel_provincial_silver += 1
                            red_travel_total += 1
                        elif '铜奖' in award_name or '三等奖' in award_name:
                            red_travel_provincial_bronze += 1
                            red_travel_total += 1
                    elif ext_award.award_level == '国赛':
                        if '金奖' in award_name or '一等奖' in award_name or '特等奖' in award_name:
                            red_travel_national_gold += 1
                            red_travel_total += 1
                        elif '银奖' in award_name or '二等奖' in award_name:
                            red_travel_national_silver += 1
                            red_travel_total += 1
                        elif '铜奖' in award_name or '三等奖' in award_name:
                            red_travel_national_bronze += 1
                            red_travel_total += 1
        
        # 获取配置数据（按学院）
        college_config = AssessmentConfig.query.filter_by(year=selected_year, college=college).first()
        challenge_cup_requirement = college_config.challenge_cup_requirement if college_config else None
        challenge_cup_special_notes = college_config.challenge_cup_special_notes if college_config else ''
        red_travel_requirement = college_config.red_travel_requirement if college_config else None
        red_travel_special_notes = college_config.red_travel_special_notes if college_config else ''
        
        # 计算挑战杯获奖总数
        challenge_cup_total = challenge_cup_school_gold + challenge_cup_school_silver + challenge_cup_school_bronze + \
                              challenge_cup_provincial_gold + challenge_cup_provincial_silver + challenge_cup_provincial_bronze + \
                              challenge_cup_national_gold + challenge_cup_national_silver + challenge_cup_national_bronze
        
        # 配套活动数据（从challenge_cup_activities字段解析JSON，如果存在）
        import json
        activities_registration = 0
        activities_national_gold = 0
        activities_national_silver = 0
        activities_national_bronze = 0
        if college_config and college_config.challenge_cup_activities:
            try:
                activities_data = json.loads(college_config.challenge_cup_activities)
                activities_registration = activities_data.get('registration_count', 0)
                national_awards = activities_data.get('national_awards', {})
                activities_national_gold = national_awards.get('gold', 0)
                activities_national_silver = national_awards.get('silver', 0)
                activities_national_bronze = national_awards.get('bronze', 0)
            except (json.JSONDecodeError, TypeError, AttributeError):
                # 如果不是JSON格式，忽略
                pass
        
        data_stats.append({
            '序号': len(data_stats) + 1,
            '学院': college,
            # 挑战杯主赛道
            '挑战杯任务要求': challenge_cup_requirement if challenge_cup_requirement else '',
            '挑战杯报名数': challenge_cup_count,
            '挑战杯校赛金奖': challenge_cup_school_gold,
            '挑战杯校赛银奖': challenge_cup_school_silver,
            '挑战杯校赛铜奖': challenge_cup_school_bronze,
            '挑战杯省赛金奖': challenge_cup_provincial_gold,
            '挑战杯省赛银奖': challenge_cup_provincial_silver,
            '挑战杯省赛铜奖': challenge_cup_provincial_bronze,
            '挑战杯国赛金奖': challenge_cup_national_gold,
            '挑战杯国赛银奖': challenge_cup_national_silver,
            '挑战杯国赛铜奖': challenge_cup_national_bronze,
            '挑战杯获奖总数': challenge_cup_total,
            '挑战杯特殊情况备注': challenge_cup_special_notes,
            # 配套活动
            '配套活动报名数': activities_registration,
            '配套活动国赛金奖': activities_national_gold,
            '配套活动国赛银奖': activities_national_silver,
            '配套活动国赛铜奖': activities_national_bronze,
            # 红旅赛道
            '红旅任务要求': red_travel_requirement if red_travel_requirement else '',
            '红旅报名数': red_travel_count,
            '红旅校赛金奖': red_travel_school_gold,
            '红旅校赛银奖': red_travel_school_silver,
            '红旅校赛铜奖': red_travel_school_bronze,
            '红旅省赛金奖': red_travel_provincial_gold,
            '红旅省赛银奖': red_travel_provincial_silver,
            '红旅省赛铜奖': red_travel_provincial_bronze,
            '红旅国赛金奖': red_travel_national_gold,
            '红旅国赛银奖': red_travel_national_silver,
            '红旅国赛铜奖': red_travel_national_bronze,
            '红旅获奖总数': red_travel_total,
            '红旅特殊情况备注': red_travel_special_notes,
        })
    
    # Sheet 2: 算分（复用assessment_score的逻辑）
    score_stats = []
    for college in COLLEGES:
        # 重新计算分数（简化版，复用assessment_score的逻辑）
        red_travel_projects = []
        if red_travel_comp:
            projects = Project.query.filter(
                Project.competition_id == red_travel_comp.id,
                Project.push_college == college,
                Project.status == ReviewStatus.FINAL_APPROVED
            ).all()
            red_travel_projects.extend(projects)
        
        challenge_cup_projects = []
        for comp in challenge_cup_competitions:
            projects = Project.query.filter(
                Project.competition_id == comp.id,
                Project.push_college == college,
                Project.status == ReviewStatus.FINAL_APPROVED
            ).all()
            challenge_cup_projects.extend(projects)
        
        # 计算参与分数（按学院获取任务要求）
        college_config = AssessmentConfig.query.filter_by(year=selected_year, college=college).first()
        red_travel_actual = len(red_travel_projects)
        red_travel_target = college_config.red_travel_requirement if college_config and college_config.red_travel_requirement else None
        red_travel_participation_score = None if red_travel_target is None or red_travel_target == 0 else min(2.0, (red_travel_actual / red_travel_target) * 2.0)
        
        challenge_cup_actual = len(challenge_cup_projects)
        challenge_cup_target = college_config.challenge_cup_requirement if college_config and college_config.challenge_cup_requirement else None
        challenge_cup_participation_score = None if challenge_cup_target is None or challenge_cup_target == 0 else min(2.0, (challenge_cup_actual / challenge_cup_target) * 2.0)
        
        # 计算获奖分数（简化版，只计算最高奖项）
        max_red_travel_score = 0
        for project in red_travel_projects:
            awards = Award.query.filter_by(project_id=project.id).all()
            for award in awards:
                award_name = award.award_name
                if '金奖' in award_name or '一等奖' in award_name or '特等奖' in award_name:
                    max_red_travel_score = max(max_red_travel_score, 1.0)
                elif '银奖' in award_name or '二等奖' in award_name:
                    max_red_travel_score = max(max_red_travel_score, 0.6)
                elif '铜奖' in award_name or '三等奖' in award_name:
                    max_red_travel_score = max(max_red_travel_score, 0.3)
            
            external_awards = ExternalAward.query.filter_by(project_id=project.id).all()
            for ext_award in external_awards:
                award_name = ext_award.award_name
                if ext_award.award_level == '省赛':
                    if '金奖' in award_name or '一等奖' in award_name or '特等奖' in award_name:
                        max_red_travel_score = max(max_red_travel_score, 3.0)
                    elif '银奖' in award_name or '二等奖' in award_name:
                        max_red_travel_score = max(max_red_travel_score, 2.0)
                    elif '铜奖' in award_name or '三等奖' in award_name:
                        max_red_travel_score = max(max_red_travel_score, 1.0)
                elif ext_award.award_level == '国赛':
                    max_red_travel_score = max(max_red_travel_score, 3.0)
        
        max_challenge_cup_score = 0
        for project in challenge_cup_projects:
            awards = Award.query.filter_by(project_id=project.id).all()
            for award in awards:
                award_name = award.award_name
                if '金奖' in award_name or '一等奖' in award_name or '特等奖' in award_name:
                    max_challenge_cup_score = max(max_challenge_cup_score, 1.0)
                elif '银奖' in award_name or '二等奖' in award_name:
                    max_challenge_cup_score = max(max_challenge_cup_score, 0.6)
                elif '铜奖' in award_name or '三等奖' in award_name:
                    max_challenge_cup_score = max(max_challenge_cup_score, 0.3)
            
            external_awards = ExternalAward.query.filter_by(project_id=project.id).all()
            for ext_award in external_awards:
                award_name = ext_award.award_name
                if ext_award.award_level == '省赛':
                    if '金奖' in award_name or '一等奖' in award_name or '特等奖' in award_name:
                        max_challenge_cup_score = max(max_challenge_cup_score, 3.0)
                    elif '银奖' in award_name or '二等奖' in award_name:
                        max_challenge_cup_score = max(max_challenge_cup_score, 2.0)
                    elif '铜奖' in award_name or '三等奖' in award_name:
                        max_challenge_cup_score = max(max_challenge_cup_score, 1.0)
                elif ext_award.award_level == '国赛':
                    max_challenge_cup_score = max(max_challenge_cup_score, 3.0)
        
        red_travel_award_score = min(3.0, max_red_travel_score)
        challenge_cup_award_score = min(3.0, max_challenge_cup_score)
        
        total_score = 0
        if red_travel_participation_score is not None:
            total_score += red_travel_participation_score
        total_score += red_travel_award_score
        if challenge_cup_participation_score is not None:
            total_score += challenge_cup_participation_score
        total_score += challenge_cup_award_score
        
        score_stats.append({
            '序号': len(score_stats) + 1,
            '学院': college,
            '红旅参与得分': red_travel_participation_score if red_travel_participation_score is not None else '',
            '红旅获奖得分': red_travel_award_score,
            '挑战杯参与得分': challenge_cup_participation_score if challenge_cup_participation_score is not None else '',
            '挑战杯获奖得分': challenge_cup_award_score,
            '总分': total_score,
        })
    
    # 创建Excel文件
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        if data_stats:
            df_data = pd.DataFrame(data_stats)
            df_data.to_excel(writer, index=False, sheet_name='情况统计')
        
        if score_stats:
            df_score = pd.DataFrame(score_stats)
            df_score.to_excel(writer, index=False, sheet_name='算分')
    
    output.seek(0)
    
    filename = f'考核数据_{selected_year}年度.xlsx'
    return send_file(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                     as_attachment=True, download_name=filename)

