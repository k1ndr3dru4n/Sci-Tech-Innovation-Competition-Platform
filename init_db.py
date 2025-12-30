"""
数据库初始化脚本
创建初始数据：竞赛、赛道、测试账户等
"""
from app import app
from models import db, User, UserRole, COLLEGES

def init_database():
    """初始化数据库"""
    with app.app_context():
        # 创建所有表
        db.create_all()
        
        # 竞赛由管理员通过界面创建，不再自动创建示例竞赛
        
        # 创建测试账户（如果不存在则创建）
        # 1. 学生账户（使用学工号登录）
        student = User.query.filter_by(work_id='2023115871').first()
        if not student:
            student = User(
                work_id='2023115871',
                real_name='测试学生',
                college='利兹学院',
                role=UserRole.STUDENT,
                is_active=True
            )
            student.set_password('swjtu12345')
            db.session.add(student)
        else:
            # 如果已存在，更新密码和学院
            student.set_password('swjtu12345')
            student.college = '利兹学院'
        
        # 2. 学院管理员账户（使用学工号登录）
        college_admin = User.query.filter_by(work_id='T2023115871').first()
        if not college_admin:
            college_admin = User(
                work_id='T2023115871',
                real_name='学院管理员',
                college='利兹学院',
                role=UserRole.COLLEGE_ADMIN,
                is_active=True
            )
            college_admin.set_password('swjtu12345')
            db.session.add(college_admin)
        else:
            # 如果已存在，更新密码和学院
            college_admin.set_password('swjtu12345')
            college_admin.college = '利兹学院'
        
        # 3. 校级管理员账户（使用学工号登录）
        school_admin = User.query.filter_by(work_id='A2023115871').first()
        if not school_admin:
            school_admin = User(
                work_id='A2023115871',
                real_name='校级管理员',
                unit='教务处',
                role=UserRole.SCHOOL_ADMIN,
                is_active=True
            )
            school_admin.set_password('swjtu12345')
            db.session.add(school_admin)
        else:
            school_admin.set_password('swjtu12345')
            # 如果单位未设置，设置默认单位
            if not school_admin.unit:
                school_admin.unit = '教务处'
        
        # 4. 校外专家账户（使用用户名/邮箱登录）
        judge = User.query.filter_by(username='J2023115871').first()
        if not judge:
            # 检查邮箱是否已被其他用户使用
            existing_email_user = User.query.filter_by(email='judge@example.com').first()
            if existing_email_user and existing_email_user.username != 'J2023115871':
                # 如果邮箱被其他用户使用，使用不同的邮箱
                judge_email = 'judgeJ2023115871@example.com'
            else:
                judge_email = 'judge@example.com'
            
            judge = User(
                username='J2023115871',
                email=judge_email,
                real_name='校外专家',
                unit='外部评审机构',
                role=UserRole.JUDGE,
                is_active=True
            )
            judge.set_password('swjtu12345')
            db.session.add(judge)
        else:
            # 如果用户已存在，确保邮箱正确
            if not judge.email or judge.email != 'judge@example.com':
                # 检查 judge@example.com 是否被其他用户使用
                existing_email_user = User.query.filter_by(email='judge@example.com').first()
                if not existing_email_user or existing_email_user.id == judge.id:
                    judge.email = 'judge@example.com'
            # 更新单位（确保始终为"外部评审机构"）
            judge.unit = '外部评审机构'
            judge.set_password('swjtu12345')
        
        db.session.commit()
        print('数据库初始化完成！')
        print('=' * 50)
        print('已创建以下测试账户：')
        print('=' * 50)
        print('【校内用户（使用学工号登录）】')
        print('1. 学生账户')
        print('   学工号: 2023115871')
        print('   密码: swjtu12345')
        print('   角色: 学生')
        print('')
        print('2. 学院管理员账户')
        print('   学工号: T2023115871')
        print('   密码: swjtu12345')
        print('   角色: 学院管理员')
        print('   所属学院: 利兹学院')
        print('')
        print('3. 校级管理员账户')
        print('   学工号: A2023115871')
        print('   密码: swjtu12345')
        print('   角色: 校级管理员')
        print('')
        print('【校外专家（使用用户名/邮箱登录）】')
        print('4. 校外专家账户')
        print('   用户名: J2023115871')
        print('   邮箱: judge@example.com')
        print('   密码: swjtu12345')
        print('   角色: 校外专家')
        print('=' * 50)
        print('提示：')
        print('- 所有账户初始密码统一为: swjtu12345')
        print('- 校内用户请访问 /auth/login 使用学工号登录')
        print('- 校外专家请访问 /auth/judge/login 使用用户名或邮箱登录')
        print('- 系统已禁用注册功能，账户由管理员统一管理')
        print('=' * 50)

if __name__ == '__main__':
    init_database()

