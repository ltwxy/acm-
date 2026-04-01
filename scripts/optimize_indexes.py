"""
数据库索引优化脚本
用于添加常用查询的索引，提升系统性能
"""
import sqlite3
from pathlib import Path
import sys

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import DB_PATH


def add_indexes():
    """添加所有必要的索引"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 要创建的索引列表
    indexes = [
        # problems 表索引
        ("idx_problems_difficulty", "problems", "difficulty"),
        ("idx_problems_tags", "problems", "tags"),
        ("idx_problems_difficulty_status", "problems", "difficulty, status"),
        
        # platform_problems 表索引
        ("idx_platform_problems_platform", "platform_problems", "platform"),
        ("idx_platform_problems_difficulty", "platform_problems", "difficulty"),
        ("idx_platform_problems_category", "platform_problems", "category"),
        ("idx_platform_problems_solved", "platform_problems", "solved_at"),
        
        # candidate_pool 表索引
        ("idx_candidate_status", "candidate_pool", "status"),
        ("idx_candidate_priority", "candidate_pool", "priority"),
        ("idx_candidate_platform", "candidate_pool", "platform"),
        ("idx_candidate_created", "candidate_pool", "created_at"),
        
        # task_execution 表索引
        ("idx_task_plan", "task_execution", "plan_id"),
        ("idx_task_status", "task_execution", "status"),
        ("idx_task_difficulty", "task_execution", "difficulty"),
        ("idx_task_priority", "task_execution", "priority"),
        
        # daily_plans 表索引
        ("idx_plan_status", "daily_plans", "status"),
        ("idx_plan_difficulty", "daily_plans", "difficulty_level"),
        
        # sync_log 表索引
        ("idx_sync_platform", "sync_log", "platform"),
        ("idx_sync_status", "sync_log", "status"),
        ("idx_sync_started", "sync_log", "started_at"),
        
        # problem_status_log 表索引
        ("idx_statuslog_platform", "problem_status_log", "platform"),
        ("idx_statuslog_action", "problem_status_log", "action"),
        
        # daily_stats 表索引
        ("idx_stats_date", "daily_stats", "date"),
    ]
    
    created = 0
    skipped = 0
    
    for idx_name, table, columns in indexes:
        try:
            # 先检查索引是否已存在
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='index' AND name=?", (idx_name,))
            if cursor.fetchone():
                print(f"  跳过: {idx_name} (已存在)")
                skipped += 1
            else:
                sql = f"CREATE INDEX {idx_name} ON {table}({columns})"
                cursor.execute(sql)
                print(f"  创建: {idx_name} ON {table}({columns})")
                created += 1
        except sqlite3.Error as e:
            print(f"  错误: {idx_name} - {e}")
    
    conn.commit()
    
    # 显示当前所有索引
    print("\n当前数据库所有索引:")
    cursor.execute("SELECT name, tbl_name, sql FROM sqlite_master WHERE type='index' ORDER BY tbl_name, name")
    indexes_list = cursor.fetchall()
    for idx in indexes_list:
        print(f"  {idx[0]}: {idx[1]}")
    
    print(f"\n索引创建完成: 新建 {created} 个, 跳过 {skipped} 个, 共 {len(indexes_list)} 个索引")
    
    # 显示数据库统计
    print("\n数据库统计:")
    tables = ['problems', 'platform_problems', 'candidate_pool', 'task_execution', 
              'daily_plans', 'sync_log', 'problem_status_log', 'daily_stats']
    for table in tables:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"  {table}: {count} 条记录")
        except sqlite3.Error:
            print(f"  {table}: (表不存在)")
    
    conn.close()


if __name__ == "__main__":
    print("=" * 50)
    print("数据库索引优化")
    print("=" * 50)
    add_indexes()
    print("\n优化完成!")
