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
            
            if 'allow_award_collection' not in columns:
                cursor.execute("ALTER TABLE projects ADD COLUMN allow_award_collection BOOLEAN DEFAULT 0")
                print("✓ 已添加 allow_award_collection 字段到 projects 表")
            
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
            
            # 检查并添加 users 表的 last_login 字段
            cursor.execute("PRAGMA table_info(users)")
            columns = [row[1] for row in cursor.fetchall()]
            
            if 'last_login' not in columns:
                cursor.execute("ALTER TABLE users ADD COLUMN last_login DATETIME")
                print("✓ 已添加 last_login 字段到 users 表")
            
            # 检查并添加 competitions 表的答辩顺序抽取时间字段
            cursor.execute("PRAGMA table_info(competitions)")
            columns = [row[1] for row in cursor.fetchall()]
            
            if 'defense_order_start' not in columns:
                cursor.execute("ALTER TABLE competitions ADD COLUMN defense_order_start DATETIME")
                print("✓ 已添加 defense_order_start 字段到 competitions 表")
            
            if 'defense_order_end' not in columns:
                cursor.execute("ALTER TABLE competitions ADD COLUMN defense_order_end DATETIME")
                print("✓ 已添加 defense_order_end 字段到 competitions 表")
            
            if 'qq_group_number' not in columns:
                cursor.execute("ALTER TABLE competitions ADD COLUMN qq_group_number VARCHAR(50)")
                print("✓ 已添加 qq_group_number 字段到 competitions 表")
            
            if 'qq_group_qrcode' not in columns:
                cursor.execute("ALTER TABLE competitions ADD COLUMN qq_group_qrcode VARCHAR(500)")
                print("✓ 已添加 qq_group_qrcode 字段到 competitions 表")
            
            # 检查并创建 external_awards 表（如果不存在）
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='external_awards'")
            if not cursor.fetchone():
                cursor.execute("""
                    CREATE TABLE external_awards (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        project_id INTEGER NOT NULL,
                        award_level VARCHAR(50) NOT NULL,
                        award_name VARCHAR(100) NOT NULL,
                        award_organization VARCHAR(200),
                        award_date DATE,
                        certificate_file VARCHAR(500),
                        description TEXT,
                        uploaded_by INTEGER NOT NULL,
                        created_at DATETIME,
                        updated_at DATETIME,
                        FOREIGN KEY (project_id) REFERENCES projects(id),
                        FOREIGN KEY (uploaded_by) REFERENCES users(id)
                    )
                """)
                print("✓ 已创建 external_awards 表")
            else:
                # 如果表已存在，检查是否有所有必需的列
                cursor.execute("PRAGMA table_info(external_awards)")
                existing_columns = [row[1] for row in cursor.fetchall()]
                required_columns = {
                    'id': 'INTEGER PRIMARY KEY AUTOINCREMENT',
                    'project_id': 'INTEGER NOT NULL',
                    'award_level': 'VARCHAR(50) NOT NULL',
                    'award_name': 'VARCHAR(100) NOT NULL',
                    'award_organization': 'VARCHAR(200)',
                    'award_date': 'DATE',
                    'certificate_file': 'VARCHAR(500)',
                    'description': 'TEXT',
                    'uploaded_by': 'INTEGER NOT NULL',
                    'created_at': 'DATETIME',
                    'updated_at': 'DATETIME'
                }
                for col_name, col_def in required_columns.items():
                    if col_name not in existing_columns:
                        # SQLite 不支持直接添加带约束的列，这里只添加基本列
                        if 'NOT NULL' in col_def:
                            cursor.execute(f"ALTER TABLE external_awards ADD COLUMN {col_name} {col_def.split(' NOT NULL')[0]}")
                        elif 'PRIMARY KEY' in col_def:
                            continue  # 主键不能通过 ALTER TABLE 添加
                        else:
                            cursor.execute(f"ALTER TABLE external_awards ADD COLUMN {col_name} {col_def}")
                        print(f"✓ 已添加 {col_name} 字段到 external_awards 表")
            
            # 检查并创建 assessment_config 表（如果不存在）
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='assessment_config'")
            if not cursor.fetchone():
                cursor.execute("""
                    CREATE TABLE assessment_config (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        year INTEGER NOT NULL,
                        college VARCHAR(100) NOT NULL,
                        red_travel_requirement INTEGER,
                        challenge_cup_requirement INTEGER,
                        challenge_cup_activities TEXT,
                        challenge_cup_special_notes TEXT,
                        red_travel_special_notes TEXT,
                        created_at DATETIME,
                        updated_at DATETIME,
                        UNIQUE(year, college)
                    )
                """)
                print("✓ 已创建 assessment_config 表")
            else:
                # 如果表已存在，检查并添加缺失的列
                cursor.execute("PRAGMA table_info(assessment_config)")
                existing_columns = [row[1] for row in cursor.fetchall()]
                
                if 'red_travel_requirement' not in existing_columns:
                    cursor.execute("ALTER TABLE assessment_config ADD COLUMN red_travel_requirement INTEGER")
                    print("✓ 已添加 red_travel_requirement 字段到 assessment_config 表")
                
                if 'challenge_cup_requirement' not in existing_columns:
                    cursor.execute("ALTER TABLE assessment_config ADD COLUMN challenge_cup_requirement INTEGER")
                    print("✓ 已添加 challenge_cup_requirement 字段到 assessment_config 表")
                
                if 'challenge_cup_activities' not in existing_columns:
                    cursor.execute("ALTER TABLE assessment_config ADD COLUMN challenge_cup_activities TEXT")
                    print("✓ 已添加 challenge_cup_activities 字段到 assessment_config 表")
                
                if 'challenge_cup_special_notes' not in existing_columns:
                    cursor.execute("ALTER TABLE assessment_config ADD COLUMN challenge_cup_special_notes TEXT")
                    print("✓ 已添加 challenge_cup_special_notes 字段到 assessment_config 表")
                
                if 'red_travel_special_notes' not in existing_columns:
                    cursor.execute("ALTER TABLE assessment_config ADD COLUMN red_travel_special_notes TEXT")
                    print("✓ 已添加 red_travel_special_notes 字段到 assessment_config 表")
                
                if 'created_at' not in existing_columns:
                    cursor.execute("ALTER TABLE assessment_config ADD COLUMN created_at DATETIME")
                    print("✓ 已添加 created_at 字段到 assessment_config 表")
                
                if 'updated_at' not in existing_columns:
                    cursor.execute("ALTER TABLE assessment_config ADD COLUMN updated_at DATETIME")
                    print("✓ 已添加 updated_at 字段到 assessment_config 表")
                
                # 添加统计数字段
                stat_fields = [
                    ('challenge_cup_main_registration', 'INTEGER'),
                    ('challenge_cup_main_school_gold', 'INTEGER'),
                    ('challenge_cup_main_school_silver', 'INTEGER'),
                    ('challenge_cup_main_school_bronze', 'INTEGER'),
                    ('challenge_cup_main_provincial_gold', 'INTEGER'),
                    ('challenge_cup_main_provincial_silver', 'INTEGER'),
                    ('challenge_cup_main_provincial_bronze', 'INTEGER'),
                    ('challenge_cup_main_national_gold', 'INTEGER'),
                    ('challenge_cup_main_national_silver', 'INTEGER'),
                    ('challenge_cup_main_national_bronze', 'INTEGER'),
                    ('challenge_cup_main_total_awards', 'INTEGER'),
                    ('challenge_cup_activities_registration', 'INTEGER'),
                    ('challenge_cup_activities_national_gold', 'INTEGER'),
                    ('challenge_cup_activities_national_silver', 'INTEGER'),
                    ('challenge_cup_activities_national_bronze', 'INTEGER'),
                    ('red_travel_registration', 'INTEGER'),
                    ('red_travel_school_gold', 'INTEGER'),
                    ('red_travel_school_silver', 'INTEGER'),
                    ('red_travel_school_bronze', 'INTEGER'),
                    ('red_travel_provincial_gold', 'INTEGER'),
                    ('red_travel_provincial_silver', 'INTEGER'),
                    ('red_travel_provincial_bronze', 'INTEGER'),
                    ('red_travel_national_gold', 'INTEGER'),
                    ('red_travel_national_silver', 'INTEGER'),
                    ('red_travel_national_bronze', 'INTEGER'),
                    ('red_travel_total_awards', 'INTEGER'),
                ]
                
                for field_name, field_type in stat_fields:
                    if field_name not in existing_columns:
                        cursor.execute(f"ALTER TABLE assessment_config ADD COLUMN {field_name} {field_type}")
                        print(f"✓ 已添加 {field_name} 字段到 assessment_config 表")
                
                # 添加分数字段
                score_fields = [
                    ('red_travel_participation_score', 'REAL'),
                    ('red_travel_award_score', 'REAL'),
                    ('challenge_cup_participation_score', 'REAL'),
                    ('challenge_cup_award_score', 'REAL'),
                ]
                
                for field_name, field_type in score_fields:
                    if field_name not in existing_columns:
                        cursor.execute(f"ALTER TABLE assessment_config ADD COLUMN {field_name} {field_type}")
                        print(f"✓ 已添加 {field_name} 字段到 assessment_config 表")
            
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

