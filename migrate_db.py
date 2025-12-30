"""
数据库迁移脚本
添加新字段到现有数据库表
"""
from app import app
from models import db
import sqlite3

def migrate_database():
    """迁移数据库，添加新字段"""
    with app.app_context():
        db_path = app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')
        
        # 连接数据库
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        try:
            # 检查并添加 projects 表的新字段
            cursor.execute("PRAGMA table_info(projects)")
            columns = [row[1] for row in cursor.fetchall()]
            
            if 'project_category' not in columns:
                cursor.execute("ALTER TABLE projects ADD COLUMN project_category VARCHAR(20)")
                print("✓ 已添加 project_category 字段")
            
            if 'push_college' not in columns:
                cursor.execute("ALTER TABLE projects ADD COLUMN push_college VARCHAR(100)")
                print("✓ 已添加 push_college 字段")
            
            if 'instructor_work_id' not in columns:
                cursor.execute("ALTER TABLE projects ADD COLUMN instructor_work_id VARCHAR(20)")
                print("✓ 已添加 instructor_work_id 字段")
            
            if 'instructor_unit' not in columns:
                cursor.execute("ALTER TABLE projects ADD COLUMN instructor_unit VARCHAR(100)")
                print("✓ 已添加 instructor_unit 字段")
            
            if 'instructor_phone' not in columns:
                cursor.execute("ALTER TABLE projects ADD COLUMN instructor_phone VARCHAR(20)")
                print("✓ 已添加 instructor_phone 字段")
            
            # 检查并添加 project_members 表的新字段
            cursor.execute("PRAGMA table_info(project_members)")
            columns = [row[1] for row in cursor.fetchall()]
            
            if 'member_name' not in columns:
                cursor.execute("ALTER TABLE project_members ADD COLUMN member_name VARCHAR(80)")
                print("✓ 已添加 member_name 字段")
            
            if 'member_work_id' not in columns:
                cursor.execute("ALTER TABLE project_members ADD COLUMN member_work_id VARCHAR(20)")
                print("✓ 已添加 member_work_id 字段")
            
            if 'member_college' not in columns:
                cursor.execute("ALTER TABLE project_members ADD COLUMN member_college VARCHAR(100)")
                print("✓ 已添加 member_college 字段")
            
            if 'member_major' not in columns:
                cursor.execute("ALTER TABLE project_members ADD COLUMN member_major VARCHAR(100)")
                print("✓ 已添加 member_major 字段")
            
            if 'member_phone' not in columns:
                cursor.execute("ALTER TABLE project_members ADD COLUMN member_phone VARCHAR(20)")
                print("✓ 已添加 member_phone 字段")
            
            if 'member_email' not in columns:
                cursor.execute("ALTER TABLE project_members ADD COLUMN member_email VARCHAR(120)")
                print("✓ 已添加 member_email 字段")
            
            # 修改 user_id 为可空（如果还没有修改）
            # SQLite不支持直接修改列，需要重建表，这里先跳过
            # 如果user_id不可空导致问题，需要手动处理
            
            conn.commit()
            print("\n数据库迁移完成！")
            
        except Exception as e:
            conn.rollback()
            print(f"迁移失败: {e}")
            raise
        finally:
            conn.close()

if __name__ == '__main__':
    migrate_database()

