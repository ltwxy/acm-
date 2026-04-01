"""
数据库迁移脚本 - Phase 1
添加用户配置、训练计划等新表和字段
"""
import sqlite3
from pathlib import Path
from datetime import datetime
import json
import sys
import io

# 设置UTF-8输出
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config import DB_PATH


def migrate_database():
    """执行数据库迁移"""
    db_path = DB_PATH
    print(f"开始迁移数据库: {db_path}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # 1. 添加用户配置表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT DEFAULT '用户',
                goals TEXT,              -- JSON: ["省赛省二", "CF蓝名"]
                target_date TEXT,
                daily_time_limit INTEGER DEFAULT 120, -- 每天可用分钟数，默认2小时
                preferences TEXT,        -- JSON: {"hate": ["DFS"], "like": ["DP"]}
                competition_mode TEXT DEFAULT 'oi',  -- 'oi'/'acm'
                training_mode TEXT DEFAULT 'distributed',  -- 'distributed'/'focused'
                fetch_mode TEXT DEFAULT 'local',  -- 'local'/'hybrid'
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        print("✓ 用户配置表创建成功")

        # 2. 添加知识点掌握度表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS mastery (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER DEFAULT 1,
                tag TEXT,                 -- "dp", "graph", "string"等
                mastery_level REAL,      -- 0.0-1.0
                problem_count INTEGER DEFAULT 0,
                one_submit_rate REAL,   -- 一次AC率
                avg_attempts REAL,      -- 平均尝试次数
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        print("✓ 知识点掌握度表创建成功")

        # 3. 添加每日计划表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_plans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER DEFAULT 1,
                date TEXT UNIQUE NOT NULL,
                goal TEXT,
                tasks TEXT,              -- JSON: 任务列表
                total_estimated_time INTEGER,
                difficulty_level TEXT,
                status TEXT DEFAULT 'pending',  -- pending/in-progress/completed
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        print("✓ 每日计划表创建成功")

        # 4. 添加任务执行记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS task_execution (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                daily_plan_id INTEGER,
                problem_id INTEGER,
                priority TEXT,           -- HIGH/MEDIUM/LOW
                reason TEXT,
                result TEXT,             -- ac/wa/skipped
                user_rating TEXT,        -- too-easy/suitable/too-hard
                completion_type TEXT,    -- independent/hint/solution
                completed_at TIMESTAMP,
                FOREIGN KEY (daily_plan_id) REFERENCES daily_plans(id),
                FOREIGN KEY (problem_id) REFERENCES problems(id)
            )
        ''')
        print("✓ 任务执行记录表创建成功")

        # 5. 添加每周总结表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS weekly_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER DEFAULT 1,
                week_start TEXT,
                week_end TEXT,
                tasks_completed INTEGER DEFAULT 0,
                tasks_total INTEGER DEFAULT 0,
                ac_rate REAL,
                mastery_changes TEXT,    -- JSON: {"dp": "+0.1"}
                highlights TEXT,        -- JSON: []
                next_week_plan TEXT,
                ai_suggestions TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        print("✓ 每周总结表创建成功")

        # 6. 给problems表添加新字段
        new_columns = {
            'code_complexity': 'REAL DEFAULT 0',  # 代码复杂度（0-1）
            'one_submit': 'INTEGER DEFAULT 1',   # 是否一次AC（1是，0否）
            'attempts': 'INTEGER DEFAULT 1',      # 尝试次数
        }

        for column, definition in new_columns.items():
            try:
                cursor.execute(f"SELECT {column} FROM problems LIMIT 1")
                print(f"  - 字段 {column} 已存在")
            except sqlite3.OperationalError:
                cursor.execute(f"ALTER TABLE problems ADD COLUMN {column} {definition}")
                print(f"  ✓ 添加字段 problems.{column}")

        # 7. 创建索引
        indexes = [
            ('idx_mastery_user_tag', 'mastery', ['user_id', 'tag']),
            ('idx_mastery_level', 'mastery', ['mastery_level']),
            ('idx_daily_plans_user_date', 'daily_plans', ['user_id', 'date']),
            ('idx_task_execution_plan', 'task_execution', ['daily_plan_id']),
            ('idx_weekly_reports_user', 'weekly_reports', ['user_id', 'week_start']),
        ]

        for index_name, table, columns in indexes:
            try:
                cursor.execute(f'''
                    CREATE INDEX IF NOT EXISTS {index_name}
                    ON {table}({', '.join(columns)})
                ''')
                print(f"  ✓ 创建索引 {index_name}")
            except Exception as e:
                print(f"  - 索引 {index_name} 已存在或创建失败: {e}")

        # 8. 初始化默认用户
        cursor.execute('SELECT COUNT(*) FROM users')
        if cursor.fetchone()[0] == 0:
            default_user = {
                'name': '用户',
                'goals': json.dumps([]),
                'daily_time_limit': 120,
                'preferences': json.dumps({"hate": [], "like": []}),
                'competition_mode': 'oi',
                'training_mode': 'distributed',
                'fetch_mode': 'local',
            }

            cursor.execute('''
                INSERT INTO users (name, goals, daily_time_limit, preferences,
                                   competition_mode, training_mode, fetch_mode)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                default_user['name'],
                default_user['goals'],
                default_user['daily_time_limit'],
                default_user['preferences'],
                default_user['competition_mode'],
                default_user['training_mode'],
                default_user['fetch_mode']
            ))
            print("✓ 初始化默认用户")

        conn.commit()
        print("\n✅ 数据库迁移完成！")
        return True

    except Exception as e:
        conn.rollback()
        print(f"\n❌ 迁移失败: {e}")
        return False
    finally:
        conn.close()


if __name__ == '__main__':
    migrate_database()
