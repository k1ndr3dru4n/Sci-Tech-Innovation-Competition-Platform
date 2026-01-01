"""
学院管理员路由
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, send_from_directory, abort, send_file
from flask_login import login_required, current_user
from models import db, Project, ReviewStatus, User, Team, Track, ProjectTrack, UserRole, Score, Award, ExternalAward
from forms import ReviewForm, FilterForm
from utils.decorators import college_admin_required
from utils.export import export_detailed_projects_to_excel
from config import Config
from datetime import datetime
import os

college_admin_bp = Blueprint('college_admin', __name__)

@college_admin_bp.route('/project/<int:project_id>/award/<int:award_id>/view')
@login_required
@college_admin_required
def view_certificate(project_id, award_id):
    """查看项目证书（在线预览）"""
    from flask import send_file
    project = Project.query.get_or_404(project_id)
    award = Award.query.get_or_404(award_id)
    
    # 检查权限：只能查看推送到本学院的项目证书
    if project.push_college != current_user.college:
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

@college_admin_bp.route('/project/<int:project_id>/award/<int:award_id>/download')
@login_required
@college_admin_required
def download_certificate(project_id, award_id):
    """下载项目证书（文件名：项目名+奖项名）"""
    project = Project.query.get_or_404(project_id)
    award = Award.query.get_or_404(award_id)
    
    # 检查权限：只能下载推送到本学院的项目证书
    if project.push_college != current_user.college:
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

@college_admin_bp.route('/dashboard', methods=['GET', 'POST'])
@login_required
@college_admin_required
def dashboard():
    """学院管理员 dashboard - 显示基本信息和编辑表单"""
    from forms import ProfileForm
    from models import User
    
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
            return render_template('college_admin/dashboard.html', form=form)
        
        db.session.commit()
        flash('个人资料更新成功', 'success')
        return redirect(url_for('college_admin.dashboard'))
    
    # 填充表单数据（GET 请求或验证失败时）
    form.real_name.data = current_user.real_name
    form.email.data = ''  # 邮箱不默认填写
    form.contact_info.data = current_user.contact_info
    
    return render_template('college_admin/dashboard.html', form=form)

@college_admin_bp.route('/review')
@login_required
@college_admin_required
def review():
    """审核管理页 - 待审核项目列表（只显示待审核的项目）"""
    # 获取当前管理员所在学院
    college = current_user.college
    if not college:
        flash('您的账户未设置学院信息，请联系管理员', 'error')
        return render_template('college_admin/review.html', projects=[], college=college)
    
    # 根据项目的 push_college 字段筛选，这是"作品推送学院"
    # 只显示待审核的项目（submitted状态）和被打回的项目（college_rejected，可以重新审核）
    projects = Project.query.filter(
        Project.push_college == college,
        Project.status.in_([ReviewStatus.SUBMITTED, ReviewStatus.COLLEGE_REJECTED])
    ).order_by(Project.created_at.desc()).all()
    
    return render_template('college_admin/review.html', projects=projects, college=college)

@college_admin_bp.route('/projects')
@login_required
@college_admin_required
def projects():
    """项目列表（带筛选）- 只显示已通过学院审核的项目"""
    college = current_user.college
    form = FilterForm()
    
    # 基础查询：根据项目的 push_college 字段筛选本学院的项目
    # 只显示已通过学院审核的项目（college_approved 及之后的状态）
    query = Project.query.filter(
        Project.push_college == college,
        Project.status.in_([ReviewStatus.COLLEGE_APPROVED, ReviewStatus.FINAL_APPROVED, ReviewStatus.FINAL_REJECTED])
    )
    
    # 筛选条件
    project_name = request.args.get('project_name', '').strip()
    track_id = request.args.get('track_id', type=int)
    status = request.args.get('status', '')
    
    if project_name:
        query = query.filter(Project.title.contains(project_name))
    
    if track_id and track_id > 0:
        query = query.join(ProjectTrack).join(Track).filter(Track.id == track_id)
    
    if status:
        query = query.filter(Project.status == status)
    
    projects = query.order_by(Project.created_at.desc()).all()
    
    # 获取所有竞赛和赛道用于筛选下拉框
    from models import Competition
    competitions = Competition.query.filter_by(is_active=True).all()
    
    return render_template('college_admin/projects.html', projects=projects, form=form, competitions=competitions)

@college_admin_bp.route('/project/<int:project_id>/review', methods=['GET', 'POST'])
@login_required
@college_admin_required
def review_project(project_id):
    """审核项目"""
    project = Project.query.get_or_404(project_id)
    
    # 检查权限：只能审核推送到本学院的项目
    if project.push_college != current_user.college:
        flash('您没有权限审核此项目', 'error')
        return redirect(url_for('college_admin.review'))
    
    form = ReviewForm()
    
    if form.validate_on_submit():
        action = form.action.data
        comment = form.comment.data
        
        if action == 'approve':
            project.status = ReviewStatus.COLLEGE_APPROVED
            flash('项目已通过', 'success')
        elif action == 'reject':
            # 不通过时，项目状态设为学院审核不通过，允许重新编辑
            project.status = ReviewStatus.COLLEGE_REJECTED
            # 项目未通过学院审核时，队员不需要重新确认
            flash('项目未通过，学生需要根据反馈修改后重新提交', 'info')
        
        project.college_review_comment = comment
        db.session.commit()
        
        return redirect(url_for('college_admin.review'))
    
    # 获取所有专家的评分信息
    scores = Score.query.filter_by(project_id=project_id).all()
    
    # 获取项目奖项
    awards = Award.query.filter_by(project_id=project_id).all()
    
    return render_template('college_admin/review_project.html', project=project, form=form, scores=scores, awards=awards)

@college_admin_bp.route('/award_statistics')
@login_required
@college_admin_required
def award_statistics():
    """奖项统计页面 - 显示该学院所有项目的奖项（包括校赛奖项和省赛/国赛奖状）"""
    college = current_user.college
    
    # 获取该学院的所有项目（根据 push_college 字段）
    projects = Project.query.filter_by(push_college=college).all()
    
    # 为每个项目获取奖项信息（包括校赛奖项和省赛/国赛奖状）
    projects_with_awards = []
    for project in projects:
        awards = Award.query.filter_by(project_id=project.id).all()
        external_awards = ExternalAward.query.filter_by(project_id=project.id).all()
        
        # 如果有任何奖项（校赛或省赛/国赛），就添加到列表中
        if awards or external_awards:
            projects_with_awards.append({
                'project': project,
                'awards': awards,
                'external_awards': external_awards
            })
    
    # 按创建时间倒序排序
    projects_with_awards.sort(key=lambda x: x['project'].created_at, reverse=True)
    
    # 统计信息
    total_projects = len(projects)
    projects_with_award_count = len(projects_with_awards)
    total_awards = sum(len(item['awards']) + len(item['external_awards']) for item in projects_with_awards)
    
    return render_template('college_admin/award_statistics.html', 
                         projects_with_awards=projects_with_awards,
                         college=college,
                         total_projects=total_projects,
                         projects_with_award_count=projects_with_award_count,
                         total_awards=total_awards)

@college_admin_bp.route('/students')
@login_required
@college_admin_required
def students():
    """学生信息列表（带筛选）"""
    college = current_user.college
    
    # 基础查询：本学院的学生
    query = User.query.filter(
        User.college == college,
        User.role == UserRole.STUDENT
    )
    
    # 筛选条件
    student_name = request.args.get('student_name', '').strip()
    work_id = request.args.get('work_id', '').strip()
    
    if student_name:
        query = query.filter(User.real_name.contains(student_name))
    
    if work_id:
        query = query.filter(User.work_id.contains(work_id))
    
    # 按注册时间倒序排列
    students = query.order_by(User.created_at.desc()).all()
    
    return render_template('college_admin/students.html', students=students, college=college)

@college_admin_bp.route('/export/projects')
@login_required
@college_admin_required
def export_projects():
    """导出项目数据（包含完整的项目、成员信息）"""
    college = current_user.college
    if not college:
        flash('您的账户未设置学院信息，请联系管理员', 'error')
        return redirect(url_for('college_admin.projects'))
    
    # 获取筛选条件
    project_name = request.args.get('project_name', '').strip()
    track_id = request.args.get('track_id', type=int)
    status = request.args.get('status', '')
    
    # 基础查询：根据项目的 push_college 字段筛选本学院的项目
    # 只显示已通过学院审核的项目（college_approved 及之后的状态）
    query = Project.query.filter(
        Project.push_college == college,
        Project.status.in_([ReviewStatus.COLLEGE_APPROVED, ReviewStatus.FINAL_APPROVED, ReviewStatus.FINAL_REJECTED])
    )
    
    # 应用筛选条件
    if project_name:
        query = query.filter(Project.title.contains(project_name))
    
    if track_id and track_id > 0:
        query = query.join(ProjectTrack).join(Track).filter(Track.id == track_id)
    
    if status:
        query = query.filter(Project.status == status)
    
    projects = query.order_by(Project.created_at.desc()).all()
    
    if not projects:
        flash('没有可导出的项目数据', 'info')
        return redirect(url_for('college_admin.projects'))
    
    try:
        output = export_detailed_projects_to_excel(projects)
        filename = f'{college}_项目数据导出_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        flash(f'导出失败：{str(e)}', 'error')
        return redirect(url_for('college_admin.projects'))

