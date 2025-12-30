"""
表单定义
"""
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, BooleanField, TextAreaField, SelectField, FloatField, IntegerField, DateTimeLocalField
from wtforms.validators import DataRequired, Email, Length, EqualTo, Optional, NumberRange
from datetime import datetime
from models import COLLEGES

class LoginForm(FlaskForm):
    """校内用户登录表单（学工号登录）"""
    work_id = StringField('学工号', validators=[DataRequired(), Length(max=20)])
    password = PasswordField('密码', validators=[DataRequired()])
    remember_me = BooleanField('记住我')

class JudgeLoginForm(FlaskForm):
    """校外专家登录表单"""
    username = StringField('用户名或邮箱', validators=[DataRequired(), Length(min=4, max=120)])
    password = PasswordField('密码', validators=[DataRequired()])
    remember_me = BooleanField('记住我')

class RegisterForm(FlaskForm):
    """校内用户注册表单"""
    work_id = StringField('学工号', validators=[DataRequired(), Length(max=20)])
    real_name = StringField('真实姓名', validators=[DataRequired(), Length(max=80)])
    email = StringField('邮箱', validators=[Optional(), Email()])
    password = PasswordField('密码', validators=[DataRequired(), Length(min=6)])
    password2 = PasswordField('确认密码', validators=[DataRequired(), EqualTo('password', message='两次密码输入不一致')])
    college = SelectField('学院', validators=[Optional()], choices=[('', '请选择')] + [(college, college) for college in COLLEGES])

class JudgeRegisterForm(FlaskForm):
    """校外专家注册表单"""
    username = StringField('用户名', validators=[DataRequired(), Length(min=4, max=80)])
    email = StringField('邮箱', validators=[DataRequired(), Email()])
    password = PasswordField('密码', validators=[DataRequired(), Length(min=6)])
    password2 = PasswordField('确认密码', validators=[DataRequired(), EqualTo('password', message='两次密码输入不一致')])
    real_name = StringField('真实姓名', validators=[DataRequired(), Length(max=80)])

class ProjectForm(FlaskForm):
    """项目提交表单（基础字段，根据竞赛类型动态显示）"""
    title = StringField('项目名称', validators=[DataRequired(), Length(max=200)])
    description = TextAreaField('项目简介', validators=[DataRequired()])
    # 以下字段根据竞赛类型动态显示和验证
    project_category = SelectField('项目组别', validators=[Optional()], choices=[
        ('', '请选择'),
        ('公益组', '公益组'),
        ('创意组', '创意组'),
        ('创业组', '创业组')
    ], default='')
    push_college = SelectField('作品推送学院', validators=[Optional()], choices=[('', '请选择')] + [(college, college) for college in COLLEGES])
    # 挑战杯全国大学生课外学术科技作品竞赛的字段
    project_type = SelectField('作品类别', validators=[Optional()], choices=[
        ('', '请选择'),
        ('自然科学类学术论文', '自然科学类学术论文'),
        ('哲学社会科学类社会调查报告和学术论文', '哲学社会科学类社会调查报告和学术论文'),
        ('科技发明制作A类', '科技发明制作A类'),
        ('科技发明制作B类', '科技发明制作B类')
    ], default='')
    # 挑战杯中国大学生创业计划大赛的字段
    project_field = SelectField('项目领域', validators=[Optional()], choices=[
        ('', '请选择'),
        ('科技创新和未来产业', '科技创新和未来产业'),
        ('乡村振兴和农业农村现代化', '乡村振兴和农业农村现代化'),
        ('城市治理和社会服务', '城市治理和社会服务'),
        ('生态环保和可持续发展', '生态环保和可持续发展'),
        ('文化创意和区域合作', '文化创意和区域合作')
    ], default='')
    # 适用于所有三个竞赛类型的额外字段
    innovation_points = TextAreaField('项目创新点', validators=[Optional()], render_kw={'rows': 4, 'placeholder': '请描述项目的创新点'})
    development_status = TextAreaField('项目开发现状', validators=[Optional()], render_kw={'rows': 4, 'placeholder': '请描述项目的开发现状'})
    awards_patents_papers = TextAreaField('获奖、专利及论文情况', validators=[Optional()], render_kw={'rows': 4, 'placeholder': '请填写获奖、专利及论文情况'})

class ReviewForm(FlaskForm):
    """审核表单"""
    action = SelectField('审核操作', choices=[
        ('approve', '通过'),
        ('reject', '不通过')
    ], validators=[DataRequired()])
    comment = TextAreaField('备注说明', validators=[Optional()])

class ScoreForm(FlaskForm):
    """评分表单"""
    score_value = FloatField('评分（100分制）', validators=[DataRequired(), NumberRange(min=0, max=100)], 
                            render_kw={'placeholder': '请输入0-100之间的分数', 'step': '0.1'})
    comment = TextAreaField('项目意见', validators=[Optional()], 
                           render_kw={'placeholder': '请输入对项目的评价意见', 'rows': 5})

class AwardForm(FlaskForm):
    """奖项设置表单"""
    award_name = StringField('奖项名称', validators=[DataRequired(), Length(max=100)])

class FilterForm(FlaskForm):
    """筛选表单"""
    team_name = StringField('队伍名称', validators=[Optional()])
    track_id = SelectField('赛道', coerce=int, validators=[Optional()], choices=[(0, '全部')])
    college = SelectField('学院', validators=[Optional()], choices=[('', '全部')] + [(college, college) for college in COLLEGES])
    status = SelectField('审核状态', validators=[Optional()], choices=[
        ('', '全部'),
        ('draft', '草稿'),
        ('submitted', '已提交'),
        ('college_approved', '学院审核通过'),
        ('college_rejected', '学院审核打回'),
        ('final_approved', '校级审核通过'),
        ('final_rejected', '校级审核打回')
    ])

class ProfileForm(FlaskForm):
    """个人资料表单"""
    real_name = StringField('真实姓名', validators=[DataRequired(), Length(max=80)])
    email = StringField('邮箱', validators=[Optional(), Email()])
    college = SelectField('学院', validators=[Optional()], choices=[('', '请选择')] + [(college, college) for college in COLLEGES])
    unit = StringField('单位', validators=[Optional(), Length(max=100)])
    contact_info = StringField('联系方式', validators=[Optional(), Length(max=20)])
    old_password = PasswordField('当前密码', validators=[Optional()])
    new_password = PasswordField('新密码', validators=[Optional(), Length(min=6)])
    confirm_password = PasswordField('确认新密码', validators=[Optional(), EqualTo('new_password', message='两次密码输入不一致')])

# 竞赛类型选项
COMPETITION_TYPES = [
    ('', '请选择'),
    ('中国国际大学生创新大赛"青年红色筑梦之旅"赛道', '中国国际大学生创新大赛"青年红色筑梦之旅"赛道'),
    ('"挑战杯"全国大学生课外学术科技作品竞赛', '"挑战杯"全国大学生课外学术科技作品竞赛'),
    ('"挑战杯"中国大学生创业计划大赛', '"挑战杯"中国大学生创业计划大赛')
]

class CompetitionForm(FlaskForm):
    """竞赛表单"""
    name = StringField('竞赛名称', validators=[DataRequired(), Length(max=200)])
    year = IntegerField('年份', validators=[DataRequired()], default=datetime.now().year)
    competition_type = SelectField('竞赛类型', validators=[DataRequired()], choices=COMPETITION_TYPES, description='用于匹配对应的报名流程')
    description = TextAreaField('描述', validators=[Optional()])
    registration_start = DateTimeLocalField('注册开始时间', validators=[Optional()], format='%Y-%m-%dT%H:%M')
    registration_end = DateTimeLocalField('注册结束时间', validators=[Optional()], format='%Y-%m-%dT%H:%M')
    final_quota = IntegerField('决赛名额', validators=[Optional()], render_kw={'placeholder': '排名前几可以进入决赛', 'min': 1})
    is_published = BooleanField('立即发布', validators=[Optional()], default=False)

