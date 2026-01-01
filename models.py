"""
数据库模型定义
包含多对多关系：队伍-赛道、学生-队伍、评委-项目
"""
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from utils.timezone import beijing_now

# db 将在 app.py 中初始化并导入
db = SQLAlchemy()

# 用户角色枚举
class UserRole:
    STUDENT = 'student'
    COLLEGE_ADMIN = 'college_admin'
    SCHOOL_ADMIN = 'school_admin'
    JUDGE = 'judge'

# 学院列表
COLLEGES = [
    '土木工程学院',
    '机械工程学院',
    '电气工程学院',
    '信息科学与技术学院',
    '计算机与人工智能学院',
    '集成电路科学与工程学院',
    '经济管理学院',
    '外国语学院',
    '交通运输与物流学院',
    '材料科学与工程学院',
    '地球科学与工程学院',
    '环境科学与工程学院',
    '建筑学院',
    '设计艺术学院',
    '物理科学与技术学院',
    '人文学院',
    '公共管理学院',
    '医学院',
    '生命科学与工程学院',
    '化学学院',
    '力学与航空航天学院',
    '数学学院',
    '马克思主义学院',
    '心理研究与咨询中心',
    '轨道交通运载系统全国重点实验室',
    '利兹学院',
    '茅以升学院',
    '智慧城市与交通学院',
    '轨道交通国家实验室',
    '天佑铁道学院',
    '国家卓越工程师学院',
    '继续教育学院',
    '宜宾研究院',
    '唐山研究院',
    '信息化研究院',
    '智能控制与仿真工程研究中心',
    '智能检测研究院',
    '人工智能研究院',
    '网络空间安全研究院',
    '国际老龄科学研究院',
    '前沿科学研究院',
    '未来技术研究院',
    '创新创业学院'
]

# 审核状态枚举
class ReviewStatus:
    DRAFT = 'draft'  # 草稿
    SUBMITTED = 'submitted'  # 已提交
    COLLEGE_APPROVED = 'college_approved'  # 学院审核通过
    COLLEGE_REJECTED = 'college_rejected'  # 学院审核打回
    FINAL_APPROVED = 'final_approved'  # 校级审核通过
    FINAL_REJECTED = 'final_rejected'  # 校级审核打回

# 用户模型
class User(UserMixin, db.Model):
    """用户模型"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=True, index=True)  # 校外专家使用（用户名）
    email = db.Column(db.String(120), unique=True, nullable=True, index=True)  # 校外专家使用（邮箱）
    password_hash = db.Column(db.String(255), nullable=False)
    real_name = db.Column(db.String(80), nullable=False)
    work_id = db.Column(db.String(20), unique=True, nullable=True, index=True)  # 学工号（校内用户使用）
    college = db.Column(db.String(100), nullable=True)  # 学院（学生和学院管理员使用，不可修改）
    unit = db.Column(db.String(100), nullable=True)  # 单位（校级管理员和专家使用）
    contact_info = db.Column(db.String(20), nullable=True)  # 联系方式
    role = db.Column(db.String(20), nullable=False, default=UserRole.STUDENT)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=beijing_now)
    last_login = db.Column(db.DateTime, nullable=True)  # 最后登录时间（北京时间）
    
    # 关系
    teams = db.relationship('TeamMember', back_populates='user', lazy='dynamic')
    judge_assignments = db.relationship('JudgeAssignment', back_populates='judge', lazy='dynamic')
    additional_roles = db.relationship('UserRoleAssignment', back_populates='user', cascade='all, delete-orphan', lazy='dynamic')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def has_role(self, role):
        """检查用户是否拥有指定角色（包括主角色和额外角色）"""
        if self.role == role:
            return True
        return self.additional_roles.filter_by(role=role).first() is not None
    
    def get_all_roles(self):
        """获取用户的所有角色（包括主角色和额外角色）"""
        roles = [self.role]
        roles.extend([ur.role for ur in self.additional_roles.all()])
        return list(set(roles))  # 去重
    
    def __repr__(self):
        return f'<User {self.username}>'

# 用户额外角色关联表（多对多：用户-角色）
class UserRoleAssignment(db.Model):
    """用户额外角色关联表（除了主角色role字段外的额外角色）"""
    __tablename__ = 'user_roles'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 角色名称
    created_at = db.Column(db.DateTime, default=beijing_now)
    
    # 关系
    user = db.relationship('User', back_populates='additional_roles')
    
    __table_args__ = (db.UniqueConstraint('user_id', 'role', name='unique_user_role'),)
    
    def __repr__(self):
        return f'<UserRoleAssignment {self.user_id}-{self.role}>'

# 竞赛模型
class Competition(db.Model):
    """竞赛模型"""
    __tablename__ = 'competitions'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    competition_type = db.Column(db.String(100), nullable=True)  # 竞赛类型：用于匹配对应的报名流程
    description = db.Column(db.Text)
    registration_start = db.Column(db.DateTime)
    registration_end = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)
    is_published = db.Column(db.Boolean, default=False)  # 是否已发布（只有已发布的竞赛学生才能看到）
    final_quota = db.Column(db.Integer, nullable=True)  # 决赛名额（排名前几可以进入决赛）
    defense_order_start = db.Column(db.DateTime, nullable=True)  # 答辩顺序抽取开始时间
    defense_order_end = db.Column(db.DateTime, nullable=True)  # 答辩顺序抽取结束时间
    qq_group_number = db.Column(db.String(50), nullable=True)  # QQ群号
    qq_group_qrcode = db.Column(db.String(500), nullable=True)  # QQ群二维码图片路径
    created_at = db.Column(db.DateTime, default=beijing_now)
    
    # 关系
    tracks = db.relationship('Track', back_populates='competition', lazy='dynamic')
    projects = db.relationship('Project', back_populates='competition', lazy='dynamic')
    
    def __repr__(self):
        return f'<Competition {self.name} {self.year}>'

# 赛道模型
class Track(db.Model):
    """赛道模型"""
    __tablename__ = 'tracks'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    competition_id = db.Column(db.Integer, db.ForeignKey('competitions.id'), nullable=False)
    description = db.Column(db.Text)
    
    # 关系
    competition = db.relationship('Competition', back_populates='tracks')
    projects = db.relationship('ProjectTrack', back_populates='track', lazy='dynamic')
    
    def __repr__(self):
        return f'<Track {self.name}>'

# 队伍模型
class Team(db.Model):
    """队伍模型"""
    __tablename__ = 'teams'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False, index=True)
    leader_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    competition_id = db.Column(db.Integer, db.ForeignKey('competitions.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=beijing_now)
    
    # 关系
    leader = db.relationship('User', foreign_keys=[leader_id])
    competition = db.relationship('Competition')
    members = db.relationship('TeamMember', back_populates='team', lazy='dynamic', cascade='all, delete-orphan')
    projects = db.relationship('Project', back_populates='team', lazy='dynamic')
    
    def __repr__(self):
        return f'<Team {self.name}>'

# 队伍成员关联表（多对多：学生-队伍）
class TeamMember(db.Model):
    """队伍成员关联表"""
    __tablename__ = 'team_members'
    
    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    role = db.Column(db.String(20), default='member')  # leader, member
    joined_at = db.Column(db.DateTime, default=beijing_now)
    
    # 关系
    team = db.relationship('Team', back_populates='members')
    user = db.relationship('User', back_populates='teams')
    
    __table_args__ = (db.UniqueConstraint('team_id', 'user_id', name='unique_team_member'),)
    
    def __repr__(self):
        return f'<TeamMember {self.team_id}-{self.user_id}>'

# 项目模型
class Project(db.Model):
    """项目模型"""
    __tablename__ = 'projects'
    
    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False)
    competition_id = db.Column(db.Integer, db.ForeignKey('competitions.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False, index=True)
    description = db.Column(db.Text)
    project_category = db.Column(db.String(20), nullable=True)  # 项目组别：公益组、创意组、创业组（中国国际大学生创新大赛"青年红色筑梦之旅"赛道）
    project_type = db.Column(db.String(100), nullable=True)  # 作品类别（"挑战杯"全国大学生课外学术科技作品竞赛）
    project_field = db.Column(db.String(100), nullable=True)  # 项目领域（"挑战杯"中国大学生创业计划大赛）
    push_college = db.Column(db.String(100), nullable=True)  # 作品推送学院
    innovation_points = db.Column(db.Text, nullable=True)  # 项目创新点（适用于所有三个竞赛类型）
    development_status = db.Column(db.Text, nullable=True)  # 项目开发现状（适用于所有三个竞赛类型）
    awards_patents_papers = db.Column(db.Text, nullable=True)  # 获奖、专利及论文情况（适用于所有三个竞赛类型）
    instructor_name = db.Column(db.String(100))  # 指导教师姓名
    instructor_work_id = db.Column(db.String(20), nullable=True)  # 指导老师学工号
    instructor_unit = db.Column(db.String(100), nullable=True)  # 指导老师单位
    instructor_phone = db.Column(db.String(20), nullable=True)  # 指导老师联系方式
    status = db.Column(db.String(20), default=ReviewStatus.DRAFT, index=True)
    is_final = db.Column(db.Boolean, default=False)  # 是否进入校赛决赛
    allow_award_collection = db.Column(db.Boolean, default=False)  # 是否开放奖项收集（允许学生上传省赛、国赛奖状）
    college_review_comment = db.Column(db.Text)  # 学院审核备注
    school_review_comment = db.Column(db.Text)  # 校级审核备注
    defense_order = db.Column(db.Integer, nullable=True)  # 答辩顺序（抽签结果）
    created_at = db.Column(db.DateTime, default=beijing_now)
    updated_at = db.Column(db.DateTime, default=beijing_now, onupdate=beijing_now)
    
    # 关系
    team = db.relationship('Team', back_populates='projects')
    competition = db.relationship('Competition', back_populates='projects')
    tracks = db.relationship('ProjectTrack', back_populates='project', lazy='dynamic', cascade='all, delete-orphan')
    attachments = db.relationship('ProjectAttachment', back_populates='project', lazy='dynamic', cascade='all, delete-orphan')
    judge_assignments = db.relationship('JudgeAssignment', back_populates='project', lazy='dynamic', cascade='all, delete-orphan')
    scores = db.relationship('Score', back_populates='project', lazy='dynamic', cascade='all, delete-orphan')
    awards = db.relationship('Award', back_populates='project', lazy='dynamic', cascade='all, delete-orphan')
    external_awards = db.relationship('ExternalAward', back_populates='project', lazy='dynamic', cascade='all, delete-orphan')
    project_members = db.relationship('ProjectMember', back_populates='project', lazy='dynamic', cascade='all, delete-orphan', order_by='ProjectMember.order')
    
    def all_members_confirmed(self):
        """检查所有成员是否已确认"""
        members = self.project_members.all()
        if not members:
            return False
        return all(member.is_confirmed for member in members)
    
    def __repr__(self):
        return f'<Project {self.title}>'

# 项目成员表（项目-成员，包含确认状态和顺位）
class ProjectMember(db.Model):
    """项目成员表"""
    __tablename__ = 'project_members'
    
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # 可为空，因为可能是外部成员
    order = db.Column(db.Integer, nullable=False)  # 顺位（1, 2, 3...）
    # 队员详细信息（如果user_id为空，则使用这些字段）
    member_name = db.Column(db.String(80), nullable=True)  # 姓名
    member_work_id = db.Column(db.String(20), nullable=True)  # 学号
    member_college = db.Column(db.String(100), nullable=True)  # 学院
    member_major = db.Column(db.String(100), nullable=True)  # 专业
    member_phone = db.Column(db.String(20), nullable=True)  # 联系方式
    member_email = db.Column(db.String(120), nullable=True)  # 电子邮箱
    is_confirmed = db.Column(db.Boolean, default=False)  # 是否已确认
    confirmed_at = db.Column(db.DateTime, nullable=True)  # 确认时间
    created_at = db.Column(db.DateTime, default=beijing_now)
    
    # 关系
    project = db.relationship('Project', back_populates='project_members')
    user = db.relationship('User')
    
    __table_args__ = (db.UniqueConstraint('project_id', 'user_id', name='unique_project_member'),)
    
    def __repr__(self):
        return f'<ProjectMember {self.project_id}-{self.user_id} (order: {self.order}, confirmed: {self.is_confirmed})>'

# 项目-赛道关联表（多对多：项目-赛道）
class ProjectTrack(db.Model):
    """项目-赛道关联表"""
    __tablename__ = 'project_tracks'
    
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    track_id = db.Column(db.Integer, db.ForeignKey('tracks.id'), nullable=False)
    
    # 关系
    project = db.relationship('Project', back_populates='tracks')
    track = db.relationship('Track', back_populates='projects')
    
    __table_args__ = (db.UniqueConstraint('project_id', 'track_id', name='unique_project_track'),)
    
    def __repr__(self):
        return f'<ProjectTrack {self.project_id}-{self.track_id}>'

# 项目附件模型
class ProjectAttachment(db.Model):
    """项目附件模型"""
    __tablename__ = 'project_attachments'
    
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.Integer)  # 文件大小（字节）
    file_type = db.Column(db.String(50))  # 文件类型
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # 关系
    project = db.relationship('Project', back_populates='attachments')
    
    def __repr__(self):
        return f'<ProjectAttachment {self.original_filename}>'

# 评委分配关联表（多对多：评委-项目）
class JudgeAssignment(db.Model):
    """评委分配关联表"""
    __tablename__ = 'judge_assignments'
    
    id = db.Column(db.Integer, primary_key=True)
    judge_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    assigned_at = db.Column(db.DateTime, default=beijing_now)
    is_active = db.Column(db.Boolean, default=True)
    
    # 关系
    judge = db.relationship('User', back_populates='judge_assignments')
    project = db.relationship('Project', back_populates='judge_assignments')
    
    __table_args__ = (db.UniqueConstraint('judge_id', 'project_id', name='unique_judge_assignment'),)
    
    def __repr__(self):
        return f'<JudgeAssignment {self.judge_id}-{self.project_id}>'

# 评分模型
class Score(db.Model):
    """评分模型"""
    __tablename__ = 'scores'
    
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    judge_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    score_value = db.Column(db.Float, nullable=False)  # 总分
    innovation_score = db.Column(db.Float)  # 创新性得分
    feasibility_score = db.Column(db.Float)  # 可行性得分
    social_value_score = db.Column(db.Float)  # 社会价值得分
    presentation_score = db.Column(db.Float)  # 展示效果得分
    comment = db.Column(db.Text)  # 评语
    scored_at = db.Column(db.DateTime, default=beijing_now)
    updated_at = db.Column(db.DateTime, default=beijing_now, onupdate=beijing_now)
    
    # 关系
    project = db.relationship('Project', back_populates='scores')
    judge = db.relationship('User')
    
    __table_args__ = (db.UniqueConstraint('project_id', 'judge_id', name='unique_project_judge_score'),)
    
    def __repr__(self):
        return f'<Score {self.project_id}-{self.judge_id}: {self.score_value}>'

# 奖项模型（校赛证书）
class Award(db.Model):
    """奖项模型（校赛证书）"""
    __tablename__ = 'awards'
    
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    award_name = db.Column(db.String(100), nullable=False)  # 奖项名称（如：一等奖、二等奖）
    certificate_path = db.Column(db.String(500))  # 证书文件路径
    created_at = db.Column(db.DateTime, default=beijing_now)
    
    # 关系
    project = db.relationship('Project', back_populates='awards')
    
    def __repr__(self):
        return f'<Award {self.award_name} for Project {self.project_id}>'

# 外部奖项模型（省赛、国赛奖状，由学生上传）
class ExternalAward(db.Model):
    """外部奖项模型（省赛、国赛奖状）"""
    __tablename__ = 'external_awards'
    
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    award_level = db.Column(db.String(50), nullable=False)  # 奖项级别：省赛、国赛
    award_name = db.Column(db.String(100), nullable=False)  # 奖项名称（如：一等奖、二等奖、三等奖）
    award_organization = db.Column(db.String(200), nullable=True)  # 颁奖机构
    award_date = db.Column(db.Date, nullable=True)  # 获奖日期
    certificate_file = db.Column(db.String(500), nullable=True)  # 奖状文件路径
    description = db.Column(db.Text, nullable=True)  # 其他说明
    uploaded_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)  # 上传者（队长）
    created_at = db.Column(db.DateTime, default=beijing_now)
    updated_at = db.Column(db.DateTime, default=beijing_now, onupdate=beijing_now)
    
    # 关系
    project = db.relationship('Project', back_populates='external_awards')
    uploader = db.relationship('User')
    
    def __repr__(self):
        return f'<ExternalAward {self.award_level}-{self.award_name} for Project {self.project_id}>'

# 考核配置模型（存储任务要求、配套活动、特殊情况备注等）
class AssessmentConfig(db.Model):
    """考核配置模型，用于存储年度任务要求和手动输入的奖项数据"""
    __tablename__ = 'assessment_config'
    
    id = db.Column(db.Integer, primary_key=True)
    year = db.Column(db.Integer, nullable=False)  # 年度
    college = db.Column(db.String(100), nullable=False)  # 学院
    
    # 任务要求
    red_travel_requirement = db.Column(db.Integer, nullable=True)  # 红旅任务要求数
    challenge_cup_requirement = db.Column(db.Integer, nullable=True)  # 挑战杯任务要求数
    
    # 手动输入数据（现在用于存储配套活动和特殊情况备注，以及可编辑的统计数据）
    challenge_cup_activities = db.Column(db.Text, nullable=True)  # 挑战杯配套活动（JSON格式存储，现在用于存储配套活动备注）
    challenge_cup_special_notes = db.Column(db.Text, nullable=True)  # 挑战杯特殊情况备注
    red_travel_special_notes = db.Column(db.Text, nullable=True)  # 红旅特殊情况备注
    
    # 新增字段用于存储可编辑的统计数据
    # 挑战杯主赛道
    challenge_cup_main_registration = db.Column(db.Integer, nullable=True)
    challenge_cup_main_school_gold = db.Column(db.Integer, nullable=True)
    challenge_cup_main_school_silver = db.Column(db.Integer, nullable=True)
    challenge_cup_main_school_bronze = db.Column(db.Integer, nullable=True)
    challenge_cup_main_provincial_gold = db.Column(db.Integer, nullable=True)
    challenge_cup_main_provincial_silver = db.Column(db.Integer, nullable=True)
    challenge_cup_main_provincial_bronze = db.Column(db.Integer, nullable=True)
    challenge_cup_main_national_gold = db.Column(db.Integer, nullable=True)
    challenge_cup_main_national_silver = db.Column(db.Integer, nullable=True)
    challenge_cup_main_national_bronze = db.Column(db.Integer, nullable=True)
    challenge_cup_main_total_awards = db.Column(db.Integer, nullable=True)
    
    # 挑战杯配套活动
    challenge_cup_activities_registration = db.Column(db.Integer, nullable=True)
    challenge_cup_activities_national_gold = db.Column(db.Integer, nullable=True)
    challenge_cup_activities_national_silver = db.Column(db.Integer, nullable=True)
    challenge_cup_activities_national_bronze = db.Column(db.Integer, nullable=True)
    
    # 红旅赛道
    red_travel_registration = db.Column(db.Integer, nullable=True)
    red_travel_school_gold = db.Column(db.Integer, nullable=True)
    red_travel_school_silver = db.Column(db.Integer, nullable=True)
    red_travel_school_bronze = db.Column(db.Integer, nullable=True)
    red_travel_provincial_gold = db.Column(db.Integer, nullable=True)
    red_travel_provincial_silver = db.Column(db.Integer, nullable=True)
    red_travel_provincial_bronze = db.Column(db.Integer, nullable=True)
    red_travel_national_gold = db.Column(db.Integer, nullable=True)
    red_travel_national_silver = db.Column(db.Integer, nullable=True)
    red_travel_national_bronze = db.Column(db.Integer, nullable=True)
    red_travel_total_awards = db.Column(db.Integer, nullable=True)
    
    # 手动编辑的分数（如果为空则使用计算值）
    red_travel_participation_score = db.Column(db.Float, nullable=True)  # 红旅参与得分
    red_travel_award_score = db.Column(db.Float, nullable=True)  # 红旅获奖得分
    challenge_cup_participation_score = db.Column(db.Float, nullable=True)  # 挑战杯参与得分
    challenge_cup_award_score = db.Column(db.Float, nullable=True)  # 挑战杯获奖得分
    
    created_at = db.Column(db.DateTime, default=beijing_now)
    updated_at = db.Column(db.DateTime, default=beijing_now, onupdate=beijing_now)
    
    __table_args__ = (db.UniqueConstraint('year', 'college', name='unique_year_college'),)
    
    def __repr__(self):
        return f'<AssessmentConfig {self.year}-{self.college}>'

