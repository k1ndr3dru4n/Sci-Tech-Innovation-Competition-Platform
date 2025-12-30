"""
数据导出工具
"""
from io import BytesIO
from models import Project, Team, User, Score, Award, ReviewStatus

# 延迟导入pandas，避免启动时的NumPy版本冲突
def _import_pandas():
    try:
        import pandas as pd
        return pd
    except ImportError as e:
        raise ImportError("pandas未安装或版本不兼容，无法使用导出功能") from e

def export_projects_to_excel(projects, filename='projects_export.xlsx'):
    """导出项目数据到Excel"""
    pd = _import_pandas()
    data = []
    for project in projects:
        team = project.team
        leader = team.leader
        tracks = ', '.join([pt.track.name for pt in project.tracks])
        members = ', '.join([tm.user.real_name for tm in team.members])
        
        # 计算平均分
        scores = project.scores.all()
        avg_score = sum(s.score_value for s in scores) / len(scores) if scores else None
        
        # 奖项
        awards = ', '.join([a.award_name for a in project.awards])
        
        data.append({
            '项目ID': project.id,
            '项目名称': project.title,
            '队伍名称': team.name,
            '队长': leader.real_name,
            '队长学工号': leader.work_id,
            '学院': leader.college,
            '成员': members,
            '赛道': tracks,
            '指导教师': project.instructor_name,
            '项目描述': project.description,
            '审核状态': project.status,
            '学院审核备注': project.college_review_comment,
            '校级审核备注': project.school_review_comment,
            '答辩顺序': project.defense_order,
            '平均得分': avg_score,
            '奖项': awards,
            '创建时间': project.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            '更新时间': project.updated_at.strftime('%Y-%m-%d %H:%M:%S')
        })
    
    df = pd.DataFrame(data)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='项目数据')
    output.seek(0)
    return output

def export_scores_to_excel(projects, filename='scores_export.xlsx'):
    """导出评分数据到Excel"""
    pd = _import_pandas()
    data = []
    for project in projects:
        scores = project.scores.all()
        for score in scores:
            data.append({
                '项目ID': project.id,
                '项目名称': project.title,
                '队伍名称': project.team.name,
                '评委': score.judge.real_name,
                '总分': score.score_value,
                '创新性得分': score.innovation_score,
                '可行性得分': score.feasibility_score,
                '社会价值得分': score.social_value_score,
                '展示效果得分': score.presentation_score,
                '评语': score.comment,
                '评分时间': score.scored_at.strftime('%Y-%m-%d %H:%M:%S')
            })
    
    df = pd.DataFrame(data)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='评分数据')
    output.seek(0)
    return output

def export_to_csv(data, filename='export.csv'):
    """导出数据到CSV"""
    pd = _import_pandas()
    df = pd.DataFrame(data)
    output = BytesIO()
    df.to_csv(output, index=False, encoding='utf-8-sig')
    output.seek(0)
    return output

def export_detailed_projects_to_excel(projects, filename='detailed_projects_export.xlsx'):
    """导出详细的项目数据到Excel，包含项目信息、成员信息等，整理到一个大Excel中"""
    pd = _import_pandas()
    from models import ProjectMember, ProjectAttachment, Score, Award
    
    # 项目基本信息表
    projects_data = []
    # 成员信息表
    members_data = []
    # 评分信息表
    scores_data = []
    # 奖项信息表
    awards_data = []
    
    for project in projects:
        team = project.team
        leader = team.leader
        
        # 获取竞赛信息
        competition_name = project.competition.name if project.competition else ''
        competition_type = project.competition.competition_type if project.competition else ''
        
        # 计算平均分
        scores = project.scores.all()
        avg_score = sum(s.score_value for s in scores) / len(scores) if scores else None
        score_count = len(scores) if scores else 0
        
        # 获取所有奖项
        awards = project.awards.all()
        award_names = ', '.join([a.award_name for a in awards]) if awards else ''
        
        # 获取附件信息
        attachments = project.attachments.all()
        attachment_names = ', '.join([a.original_filename for a in attachments]) if attachments else ''
        
        # 项目基本信息
        project_row = {
            '项目ID': project.id,
            '项目名称': project.title,
            '竞赛名称': competition_name,
            '竞赛类型': competition_type,
            '队伍名称': team.name,
            '作品推送学院': project.push_college or '',
            '项目组别': project.project_category or '',
            '作品类别': project.project_type or '',
            '项目领域': project.project_field or '',
            '项目描述': project.description or '',
            '项目创新点': project.innovation_points or '',
            '项目开发现状': project.development_status or '',
            '获奖、专利及论文情况': project.awards_patents_papers or '',
            '队长姓名': leader.real_name,
            '队长学工号': leader.work_id,
            '队长学院': leader.college or '',
            '队长联系方式': leader.contact_info or '',
            '队长邮箱': leader.email or '',
            '指导教师姓名': project.instructor_name or '',
            '指导教师学工号': project.instructor_work_id or '',
            '指导教师单位': project.instructor_unit or '',
            '指导教师联系方式': project.instructor_phone or '',
            '审核状态': project.status,
            '学院审核备注': project.college_review_comment or '',
            '校级审核备注': project.school_review_comment or '',
            '答辩顺序': project.defense_order or '',
            '是否进入决赛': '是' if project.is_final else '否',
            '平均得分': round(avg_score, 2) if avg_score else '',
            '评分数量': score_count,
            '奖项': award_names,
            '附件': attachment_names,
            '创建时间': project.created_at.strftime('%Y-%m-%d %H:%M:%S') if project.created_at else '',
            '更新时间': project.updated_at.strftime('%Y-%m-%d %H:%M:%S') if project.updated_at else ''
        }
        projects_data.append(project_row)
        
        # 成员信息（包括队长和项目成员）
        # 先添加队长
        members_data.append({
            '项目ID': project.id,
            '项目名称': project.title,
            '成员姓名': leader.real_name,
            '学工号': leader.work_id,
            '学院': leader.college or '',
            '专业': '',  # User模型中没有major字段
            '联系方式': leader.contact_info or '',
            '邮箱': leader.email or '',
            '角色': '队长',
            '顺位': 1,
            '是否确认': '是',
            '确认时间': ''
        })
        
        # 添加项目成员（按顺位排序）
        project_members = ProjectMember.query.filter_by(project_id=project.id).order_by(ProjectMember.order).all()
        for pm in project_members:
            if pm.user_id:
                # 已注册用户
                user = pm.user
                members_data.append({
                    '项目ID': project.id,
                    '项目名称': project.title,
                    '成员姓名': user.real_name,
                    '学工号': user.work_id,
                    '学院': user.college or '',
                    '专业': pm.member_major or '',  # 使用ProjectMember中的member_major字段
                    '联系方式': user.contact_info or '',
                    '邮箱': user.email or '',
                    '角色': '队员',
                    '顺位': pm.order,
                    '是否确认': '是' if pm.is_confirmed else '否',
                    '确认时间': pm.confirmed_at.strftime('%Y-%m-%d %H:%M:%S') if pm.confirmed_at else ''
                })
            else:
                # 未注册用户（使用项目成员表中的信息）
                members_data.append({
                    '项目ID': project.id,
                    '项目名称': project.title,
                    '成员姓名': pm.member_name or '',
                    '学工号': pm.member_work_id or '',
                    '学院': pm.member_college or '',
                    '专业': pm.member_major or '',
                    '联系方式': pm.member_phone or '',
                    '邮箱': pm.member_email or '',
                    '角色': '队员',
                    '顺位': pm.order,
                    '是否确认': '是' if pm.is_confirmed else '否',
                    '确认时间': pm.confirmed_at.strftime('%Y-%m-%d %H:%M:%S') if pm.confirmed_at else ''
                })
        
        # 评分信息
        for score in scores:
            judge = score.judge
            judge_name = judge.real_name if judge else ''
            judge_unit = judge.unit if judge and hasattr(judge, 'unit') and judge.unit else ''
            scores_data.append({
                '项目ID': project.id,
                '项目名称': project.title,
                '评委姓名': judge_name,
                '评委单位': judge_unit,
                '总分': score.score_value,
                '评语': score.comment or '',
                '评分时间': score.scored_at.strftime('%Y-%m-%d %H:%M:%S') if score.scored_at else ''
            })
        
        # 奖项信息
        for award in awards:
            awards_data.append({
                '项目ID': project.id,
                '项目名称': project.title,
                '奖项名称': award.award_name,
                '设置时间': award.created_at.strftime('%Y-%m-%d %H:%M:%S') if award.created_at else ''
            })
    
    # 创建Excel文件，包含多个工作表
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # 项目基本信息表
        if projects_data:
            df_projects = pd.DataFrame(projects_data)
            df_projects.to_excel(writer, index=False, sheet_name='项目信息')
        
        # 成员信息表
        if members_data:
            df_members = pd.DataFrame(members_data)
            df_members.to_excel(writer, index=False, sheet_name='成员信息')
        
        # 评分信息表
        if scores_data:
            df_scores = pd.DataFrame(scores_data)
            df_scores.to_excel(writer, index=False, sheet_name='评分信息')
        
        # 奖项信息表
        if awards_data:
            df_awards = pd.DataFrame(awards_data)
            df_awards.to_excel(writer, index=False, sheet_name='奖项信息')
    
    output.seek(0)
    return output

