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
    """导出详细的项目数据到Excel，包含项目信息、成员信息等，每个成员一行"""
    pd = _import_pandas()
    from models import ProjectMember, ProjectAttachment, Score, Award, ExternalAward
    
    # 所有项目数据（每个成员一行）
    projects_data = []
    
    for project in projects:
        team = project.team
        leader = team.leader
        
        # 获取竞赛信息
        competition_name = project.competition.name if project.competition else ''
        competition_type = project.competition.competition_type if project.competition else ''
        
        # 获取赛道信息
        tracks = project.tracks.all()
        track_names = ', '.join([pt.track.name for pt in tracks]) if tracks else ''
        
        # 获取所有奖项（校赛奖项）
        awards = project.awards.all()
        award_names = ', '.join([a.award_name for a in awards]) if awards else ''
        
        # 获取省赛/国赛奖状
        external_awards = project.external_awards.all()
        external_award_info = []
        for ext_award in external_awards:
            external_award_info.append(f"{ext_award.award_level}-{ext_award.award_name}")
        external_award_names = ', '.join(external_award_info) if external_award_info else ''
        
        # 获取项目成员信息（包括队长和队员）
        project_members = ProjectMember.query.filter_by(project_id=project.id).order_by(ProjectMember.order).all()
        
        # 基础项目信息（所有成员共享）
        base_project_info = {
            '项目ID': project.id,
            '项目名称': project.title,
            '竞赛名称': competition_name,
            '竞赛类型': competition_type,
            '赛道': track_names,
            '作品推送学院': project.push_college or '',
            '项目组别': project.project_category or '',
            '作品类别': project.project_type or '',
            '项目领域': project.project_field or '',
            '项目描述': project.description or '',
            '项目创新点': project.innovation_points or '',
            '项目开发现状': project.development_status or '',
            '获奖、专利及论文情况': project.awards_patents_papers or '',
            '队长姓名': leader.real_name,
            '队长学工号': leader.work_id or '',
            '队长学院': leader.college or '',
            '队长联系方式': leader.contact_info or '',
            '队长邮箱': leader.email or '',
            '指导教师姓名': project.instructor_name or '',
            '指导教师学工号': project.instructor_work_id or '',
            '指导教师单位': project.instructor_unit or '',
            '指导教师联系方式': project.instructor_phone or '',
            '是否进入决赛': '是' if project.is_final else '否',
            '校赛奖项': award_names,
            '省赛/国赛奖状': external_award_names,
        }
        
        # 先添加队长作为一行
        leader_row = base_project_info.copy()
        leader_row.update({
            '成员姓名': leader.real_name,
            '成员学工号': leader.work_id or '',
            '成员学院': leader.college or '',
            '成员专业': '',
            '成员联系方式': leader.contact_info or '',
            '成员邮箱': leader.email or '',
            '成员角色': '队长',
            '成员顺位': 1
        })
        projects_data.append(leader_row)
        
        # 添加项目成员（按顺位排序，每个成员一行）
        for pm in project_members:
            member_row = base_project_info.copy()
            if pm.user_id:
                # 已注册用户
                user = pm.user
                member_row.update({
                    '成员姓名': user.real_name,
                    '成员学工号': user.work_id or '',
                    '成员学院': user.college or '',
                    '成员专业': pm.member_major or '',
                    '成员联系方式': user.contact_info or '',
                    '成员邮箱': user.email or '',
                    '成员角色': '队员',
                    '成员顺位': pm.order
                })
            else:
                # 未注册用户（使用项目成员表中的信息）
                member_row.update({
                    '成员姓名': pm.member_name or '',
                    '成员学工号': pm.member_work_id or '',
                    '成员学院': pm.member_college or '',
                    '成员专业': pm.member_major or '',
                    '成员联系方式': pm.member_phone or '',
                    '成员邮箱': pm.member_email or '',
                    '成员角色': '队员',
                    '成员顺位': pm.order
                })
            projects_data.append(member_row)
        
        # 如果项目没有成员（只有队长），也要确保至少有一行
        if not project_members:
            # 队长行已经添加，不需要额外处理
            pass
    
    # 创建Excel文件，只有一个工作表
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        if projects_data:
            df_projects = pd.DataFrame(projects_data)
            
            # 删除全为空的列（包括空字符串、None、NaN）
            # 方法：检查每列是否所有值都是空字符串、None或NaN
            cols_to_drop = []
            for col in df_projects.columns:
                # 检查该列的所有值是否都为空（空字符串、None、NaN）
                col_values = df_projects[col]
                # 将所有空值类型统一为None进行比较
                is_all_empty = col_values.replace('', None).isna().all()
                if is_all_empty:
                    cols_to_drop.append(col)
            
            # 删除全为空的列
            if cols_to_drop:
                df_projects = df_projects.drop(columns=cols_to_drop)
            
            # 确保所有NaN值显示为空字符串
            df_projects = df_projects.fillna('')
            
            df_projects.to_excel(writer, index=False, sheet_name='项目数据')
    
    output.seek(0)
    return output

