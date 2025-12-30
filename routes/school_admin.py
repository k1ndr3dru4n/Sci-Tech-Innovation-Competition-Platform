"""
校级管理员路由
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file, jsonify
from flask_login import login_required, current_user
from models import db, Project, User, ReviewStatus, JudgeAssignment, Award, Competition, Track, Team, ProjectTrack, UserRole, Score
from datetime import datetime
from forms import FilterForm, AwardForm, ReviewForm, CompetitionForm
from utils.decorators import school_admin_required
from utils.certificate import generate_certificate
from utils.export import export_projects_to_excel, export_scores_to_excel, export_detailed_projects_to_excel
import random

school_admin_bp = Blueprint('school_admin', __name__)

@school_admin_bp.route('/dashboard')
@login_required
@school_admin_required
def dashboard():
    """校级管理员 dashboard - 显示基本信息"""
    return render_template('school_admin/dashboard.html')

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

@school_admin_bp.route('/projects')
@login_required
@school_admin_required
def projects():
    """项目列表（带筛选）"""
    form = FilterForm()
    
    # 基础查询：已通过学院审核的项目（包括学校审核通过和不通过的）
    query = Project.query.filter(
        Project.status.in_([ReviewStatus.COLLEGE_APPROVED, ReviewStatus.FINAL_APPROVED, ReviewStatus.FINAL_REJECTED])
    )
    
    # 筛选条件
    project_name = request.args.get('project_name', '').strip()
    competition_id = request.args.get('competition_id', type=int)
    college = request.args.get('college', '').strip()
    status = request.args.get('status', '')
    
    if project_name:
        query = query.filter(Project.title.contains(project_name))
    
    if competition_id:
        # 根据竞赛ID筛选
        query = query.filter(Project.competition_id == competition_id)
    
    if college:
        # 根据学院筛选
        query = query.join(Team, Project.team_id == Team.id).join(User, Team.leader_id == User.id).filter(User.college.contains(college))
    
    if status:
        query = query.filter(Project.status == status)
    
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
    
    return render_template('school_admin/expert_review.html', projects_with_scores=projects_with_scores, competitions=competitions)

@school_admin_bp.route('/project/<int:project_id>/scores')
@login_required
@school_admin_required
def view_scores(project_id):
    """查看项目评分详情"""
    project = Project.query.get_or_404(project_id)
    
    # 获取所有专家的评分信息
    scores = Score.query.filter_by(project_id=project_id).all()
    
    return render_template('school_admin/view_scores.html', project=project, scores=scores)

@school_admin_bp.route('/teachers')
@login_required
@school_admin_required
def teachers():
    """教师管理页 - 学院管理员信息列表"""
    # 基础查询：所有学院管理员
    query = User.query.filter(User.role == UserRole.COLLEGE_ADMIN)
    
    # 筛选条件
    teacher_name = request.args.get('teacher_name', '').strip()
    work_id = request.args.get('work_id', '').strip()
    college = request.args.get('college', '').strip()
    
    if teacher_name:
        query = query.filter(User.real_name.contains(teacher_name))
    
    if work_id:
        query = query.filter(User.work_id.contains(work_id))
    
    if college:
        query = query.filter(User.college.contains(college))
    
    # 按注册时间倒序排列
    teachers = query.order_by(User.created_at.desc()).all()
    
    return render_template('school_admin/teachers.html', teachers=teachers)

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
        if not judge or judge.role != 'judge':
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
    
    # 获取所有评委
    judges = User.query.filter_by(role='judge', is_active=True).all()
    
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

@school_admin_bp.route('/final/draw_lots', methods=['POST'])
@login_required
@school_admin_required
def draw_lots():
    """决赛抽签（自动决定答辩顺序）- 旧版本，保留兼容性"""
    return draw_lots_final()

@school_admin_bp.route('/final_competition/draw_lots', methods=['POST'])
@login_required
@school_admin_required
def draw_lots_final():
    """为决赛项目随机抽签决定答辩顺序"""
    competition_id = request.form.get('competition_id', type=int)
    
    # 查询进入决赛的项目
    query = Project.query.filter(Project.is_final == True)
    
    if competition_id:
        query = query.filter(Project.competition_id == competition_id)
    
    projects = query.all()
    
    if not projects:
        flash('没有找到进入决赛的项目', 'error')
        return redirect(url_for('school_admin.final_competition', competition_id=competition_id))
    
    # 随机打乱顺序
    project_ids = [p.id for p in projects]
    random.shuffle(project_ids)
    
    # 分配答辩顺序
    for order, project_id in enumerate(project_ids, start=1):
        project = Project.query.get(project_id)
        project.defense_order = order
        db.session.add(project)
    
    db.session.commit()
    flash(f'已为 {len(projects)} 个项目随机分配答辩顺序', 'success')
    return redirect(url_for('school_admin.final_competition', competition_id=competition_id))

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
    status = request.args.get('status', '')
    
    # 基础查询：已通过学院审核的项目
    query = Project.query.filter(
        Project.status.in_([ReviewStatus.COLLEGE_APPROVED, ReviewStatus.FINAL_APPROVED, ReviewStatus.FINAL_REJECTED])
    )
    
    if project_name:
        query = query.filter(Project.title.contains(project_name))
    
    if competition_id:
        query = query.filter(Project.competition_id == competition_id)
    
    if college:
        query = query.join(Team, Project.team_id == Team.id).join(User, Team.leader_id == User.id).filter(User.college.contains(college))
    
    if status:
        query = query.filter(Project.status == status)
    
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
    competitions_list = Competition.query.filter_by(is_active=True).order_by(Competition.year.desc(), Competition.created_at.desc()).all()
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
            final_quota=form.final_quota.data if form.final_quota.data is not None else None,
            is_active=True,
            is_published=form.is_published.data if form.is_published.data else False
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
    form.final_quota.data = competition.final_quota
    form.is_published.data = competition.is_published
    
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
        
        # final_quota 处理：优先从请求参数获取（更可靠）
        final_quota_value = None
        
        # 首先尝试从请求参数获取（直接来自表单提交）
        if 'final_quota' in request.form:
            try:
                final_quota_value = int(request.form.get('final_quota'))
            except (ValueError, TypeError):
                pass
        
        # 如果请求参数中没有，尝试从表单对象获取
        if final_quota_value is None:
            final_quota_value = form.final_quota.data
        
        # 如果表单数据为空字符串或None，设置为None；否则转换为整数
        if final_quota_value is None or final_quota_value == '' or (isinstance(final_quota_value, str) and final_quota_value.strip() == ''):
            competition.final_quota = None
        else:
            try:
                # 确保转换为整数
                competition.final_quota = int(final_quota_value)
            except (ValueError, TypeError) as e:
                flash(f'决赛名额格式错误：{str(e)}', 'error')
                competition.final_quota = None
        
        competition.is_published = form.is_published.data if form.is_published.data else False
        db.session.commit()
        
        # 重新查询以确保获取最新值
        db.session.expire_all()
        updated_competition = Competition.query.get(competition_id)
        
        # 显示保存的值
        saved_quota = updated_competition.final_quota if updated_competition.final_quota is not None else '未设置'
        flash(f'竞赛"{competition.name}"更新成功，决赛名额已设置为：{saved_quota}', 'success')
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
    competition = Competition.query.get_or_404(competition_id)
    
    # 切换发布状态
    competition.is_published = not competition.is_published
    db.session.commit()
    
    status = '已发布' if competition.is_published else '已取消发布'
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

@school_admin_bp.route('/awards')
@login_required
@school_admin_required
def awards():
    """奖项收集/发布管理页"""
    # 获取所有竞赛
    competitions = Competition.query.filter_by(is_active=True).all()
    
    # 筛选条件
    competition_id = request.args.get('competition_id', type=int)
    
    # 查询进入决赛的项目
    query = Project.query.filter(Project.is_final == True)
    
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
    
    return render_template('school_admin/awards.html', 
                         projects_with_awards=projects_with_awards,
                         competitions=competitions,
                         selected_competition_id=competition_id)

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

