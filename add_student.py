"""
添加学生账号脚本
"""
from app import app
from models import db, User, UserRole
from werkzeug.security import generate_password_hash

def add_student():
    """添加学生账号"""
    with app.app_context():
        work_id = '2023115872'
        password = 'swjtu12345'  # 统一初始密码
        
        # 检查用户是否已存在
        existing_user = User.query.filter_by(work_id=work_id).first()
        
        if existing_user:
            # 如果已存在，更新密码
            existing_user.set_password(password)
            print(f"用户 {work_id} 已存在，已更新密码为 {password}")
        else:
            # 创建新用户
            new_user = User(
                work_id=work_id,
                real_name=f'学生{work_id[-4:]}',  # 使用学工号后4位作为默认姓名
                college='计算机学院',  # 默认学院
                role=UserRole.STUDENT,
                is_active=True
            )
            new_user.set_password(password)
            db.session.add(new_user)
            print(f"已创建学生账号：{work_id}")
        
        db.session.commit()
        print(f"登录信息：")
        print(f"  学工号：{work_id}")
        print(f"  密码：{password}")

if __name__ == '__main__':
    add_student()

