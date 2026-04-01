"""
数据库操作模块
"""
import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from contextlib import contextmanager

from config import DB_PATH


class Database:
    """数据库管理类"""
    
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self._init_db()
    
    @contextmanager
    def _get_connection(self):
        """获取数据库连接上下文管理器"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    def _init_db(self):
        """初始化数据库表结构"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # 题目信息表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS problems (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_path TEXT UNIQUE NOT NULL,
                    file_name TEXT NOT NULL,
                    title TEXT,
                    platform TEXT,
                    problem_id TEXT,
                    url TEXT,
                    difficulty INTEGER,
                    status TEXT DEFAULT 'pending',
                    category TEXT,
                    subcategory TEXT,
                    tags TEXT,
                    algorithms TEXT,
                    data_structures TEXT,
                    code_features TEXT,
                    lines_of_code INTEGER,
                    submit_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # 平台题目表（线上已做题）
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS platform_problems (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    platform TEXT NOT NULL,
                    problem_id TEXT NOT NULL,
                    title TEXT,
                    difficulty REAL,
                    tags TEXT,
                    category TEXT,
                    subcategory TEXT,
                    solved_at TIMESTAMP,
                    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    url TEXT,
                    UNIQUE(platform, problem_id)
                )
            ''')

            # 为已有的数据库添加 url 字段（如果不存在）
            try:
                cursor.execute('ALTER TABLE platform_problems ADD COLUMN url TEXT')
            except sqlite3.OperationalError:
                # 字段已存在，忽略错误
                pass

            # 分类定义表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS categories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    parent_key TEXT,
                    keywords TEXT,
                    color TEXT,
                    description TEXT,
                    FOREIGN KEY (parent_key) REFERENCES categories(key)
                )
            ''')
            
            # 每日统计表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS daily_stats (
                    date DATE PRIMARY KEY,
                    problems_solved INTEGER DEFAULT 0,
                    new_problems INTEGER DEFAULT 0,
                    by_category TEXT,
                    by_difficulty TEXT
                )
            ''')
            
            # 创建索引
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_problems_category ON problems(category)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_problems_platform ON problems(platform)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_problems_status ON problems(status)')
            
            # 迁移：给旧数据库添加 url 列
            try:
                cursor.execute("SELECT url FROM problems LIMIT 1")
            except sqlite3.OperationalError:
                cursor.execute("ALTER TABLE problems ADD COLUMN url TEXT")

            # 每日训练计划表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS daily_plans (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER DEFAULT 1,
                    date TEXT NOT NULL UNIQUE,
                    training_mode TEXT DEFAULT 'distributed',
                    goal TEXT,
                    tasks TEXT,
                    total_estimated_time INTEGER,
                    difficulty_level TEXT,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # 任务执行记录表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS task_execution (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    plan_id INTEGER,
                    task_order INTEGER,
                    problem_id TEXT,
                    problem_title TEXT,
                    platform TEXT,
                    difficulty REAL,
                    tags TEXT,
                    priority TEXT,
                    reason TEXT,
                    estimated_time INTEGER,
                    status TEXT DEFAULT 'pending',
                    user_feedback TEXT,
                    completed_at TIMESTAMP,
                    source TEXT DEFAULT 'manual',
                    FOREIGN KEY (plan_id) REFERENCES daily_plans(id)
                )
            ''')

            # 候选题目池表（AI推荐的大量题目）
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS candidate_pool (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    platform TEXT NOT NULL,
                    problem_id TEXT NOT NULL,
                    title TEXT,
                    difficulty REAL,
                    difficulty_normalized REAL,
                    tags TEXT,
                    category TEXT,
                    url TEXT,
                    reason TEXT,
                    priority INTEGER DEFAULT 1,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(platform, problem_id)
                )
            ''')
            
            # 添加 generated_at 字段（如果不存在）
            try:
                cursor.execute('ALTER TABLE candidate_pool ADD COLUMN generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP')
            except sqlite3.OperationalError:
                pass

            # 题目状态变更记录（用于记录"已刷过"/"太难"等标记）
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS problem_status_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    platform TEXT NOT NULL,
                    problem_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    reason TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # 同步记录表（记录每次同步的信息）
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sync_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    platform TEXT NOT NULL,
                    sync_type TEXT NOT NULL,  -- 'full' 或 'incremental'
                    problems_fetched INTEGER DEFAULT 0,  -- 本次获取的题目数
                    problems_added INTEGER DEFAULT 0,   -- 本次新增的题目数
                    problems_skipped INTEGER DEFAULT 0, -- 跳过的题目数（已存在）
                    status TEXT DEFAULT 'pending',     -- pending/success/failed
                    error_message TEXT,
                    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    finished_at TIMESTAMP
                )
            ''')

            # 为 platform_problems 表添加最后同步时间字段（如果不存在）
            try:
                cursor.execute('ALTER TABLE platform_problems ADD COLUMN last_sync_at TIMESTAMP')
            except sqlite3.OperationalError:
                pass

            conn.commit()
    
    # ==================== Problem CRUD ====================
    
    def add_problem(self, problem_data: Dict) -> int:
        """
        添加新题目
        
        Args:
            problem_data: 题目信息字典
            
        Returns:
            新插入的题目ID
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # 将列表转换为JSON字符串
            for key in ['tags', 'algorithms', 'data_structures', 'code_features']:
                if key in problem_data and isinstance(problem_data[key], (list, dict)):
                    problem_data[key] = json.dumps(problem_data[key], ensure_ascii=False)
            
            fields = list(problem_data.keys())
            placeholders = ', '.join(['?' for _ in fields])
            field_names = ', '.join(fields)
            
            sql = f'INSERT OR REPLACE INTO problems ({field_names}) VALUES ({placeholders})'
            cursor.execute(sql, list(problem_data.values()))
            
            return cursor.lastrowid
    
    def get_problem(self, file_path: str) -> Optional[Dict]:
        """根据文件路径获取题目信息"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM problems WHERE file_path = ?', (file_path,))
            row = cursor.fetchone()
            
            if row:
                return self._row_to_dict(row)
            return None
    
    def get_problem_by_id(self, problem_id: int) -> Optional[Dict]:
        """根据ID获取题目信息"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM problems WHERE id = ?', (problem_id,))
            row = cursor.fetchone()
            
            if row:
                return self._row_to_dict(row)
            return None
    
    def update_problem(self, file_path: str, updates: Dict) -> bool:
        """
        更新题目信息
        
        Args:
            file_path: 文件路径
            updates: 要更新的字段字典
            
        Returns:
            是否更新成功
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # 将列表转换为JSON字符串
            for key in ['tags', 'algorithms', 'data_structures', 'code_features']:
                if key in updates and isinstance(updates[key], (list, dict)):
                    updates[key] = json.dumps(updates[key], ensure_ascii=False)
            
            updates['updated_at'] = datetime.now().isoformat()
            
            set_clause = ', '.join([f'{k} = ?' for k in updates.keys()])
            sql = f'UPDATE problems SET {set_clause} WHERE file_path = ?'
            
            cursor.execute(sql, list(updates.values()) + [file_path])
            return cursor.rowcount > 0
    
    def delete_problem(self, file_path: str) -> bool:
        """删除题目"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM problems WHERE file_path = ?', (file_path,))
            return cursor.rowcount > 0
    
    def get_all_problems(self, category: str = None, status: str = None) -> List[Dict]:
        """
        获取所有题目（本地+平台），支持筛选和去重

        Args:
            category: 按分类筛选
            status: 按状态筛选（仅对本地题目有效）

        Returns:
            题目列表（去重后）
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # 构建本地题目查询
            local_conditions = []
            local_params = []
            if category:
                local_conditions.append('category = ?')
                local_params.append(category)
            if status:
                local_conditions.append('status = ?')
                local_params.append(status)

            where_local = ' AND '.join(local_conditions) if local_conditions else '1=1'
            sql_local = f'SELECT * FROM problems WHERE {where_local}'
            cursor.execute(sql_local, local_params)
            local_problems = [self._row_to_dict(row) for row in cursor.fetchall()]

            # 构建平台题目查询
            platform_conditions = []
            platform_params = []
            if category:
                platform_conditions.append('category = ?')
                platform_params.append(category)

            where_platform = ' AND '.join(platform_conditions) if platform_conditions else '1=1'
            sql_platform = f'SELECT * FROM platform_problems WHERE {where_platform}'
            cursor.execute(sql_platform, platform_params)
            platform_problems = [self._row_to_dict(row) for row in cursor.fetchall()]

            # 合并并去重：同一 platform + problem_id 只保留一条
            # 本地题目优先（有本地文件信息）
            seen = set()
            merged = []

            # 先处理本地题目，同时去重本地内部的重复
            for p in local_problems:
                # 对于无 platform+problem_id 的题目，用 id 作为唯一标识
                if not p.get('platform') or not p.get('problem_id'):
                    key = ('local', p['id'])
                else:
                    key = (p.get('platform'), p.get('problem_id'))

                if key in seen:
                    continue  # 本地已有同一题目（不同 .cpp 文件）
                seen.add(key)
                merged.append(p)

            # 再处理平台题目
            for p in platform_problems:
                key = (p.get('platform'), p.get('problem_id'))
                if not key[0] or not key[1]:
                    continue  # 跳过无 platform+problem_id 的平台题目
                if key in seen:
                    continue  # 已被本地题目覆盖
                seen.add(key)
                merged.append(p)

            # 按时间排序（本地按 created_at，平台按 fetched_at）
            merged.sort(key=lambda x: x.get('created_at') or x.get('fetched_at') or '', reverse=True)

            return merged
    
    # ==================== Statistics ====================
    
    def get_category_stats(self) -> Dict[str, int]:
        """获取各分类的题目数量统计"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT category, COUNT(*) as count 
                FROM problems 
                WHERE category IS NOT NULL
                GROUP BY category
            ''')
            
            return {row['category']: row['count'] for row in cursor.fetchall()}
    
    def get_subcategory_stats(self, category: str) -> Dict[str, int]:
        """获取指定分类下的子分类统计"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT subcategory, COUNT(*) as count 
                FROM problems 
                WHERE category = ? AND subcategory IS NOT NULL
                GROUP BY subcategory
            ''', (category,))
            
            return {row['subcategory']: row['count'] for row in cursor.fetchall()}
    
    def get_difficulty_stats(self) -> Dict[int, int]:
        """获取难度分布统计"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT difficulty, COUNT(*) as count 
                FROM problems 
                WHERE difficulty IS NOT NULL
                GROUP BY difficulty
                ORDER BY difficulty
            ''')
            
            return {row['difficulty']: row['count'] for row in cursor.fetchall()}
    
    def get_platform_stats(self) -> Dict[str, int]:
        """获取各平台的题目数量"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT platform, COUNT(*) as count 
                FROM problems 
                WHERE platform IS NOT NULL
                GROUP BY platform
            ''')
            
            return {row['platform']: row['count'] for row in cursor.fetchall()}
    
    def get_daily_stats(self, days: int = 30) -> List[Dict]:
        """获取最近N天的统计"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM daily_stats 
                WHERE date >= date('now', '-{} days')
                ORDER BY date
            '''.format(days))
            
            return [self._row_to_dict(row) for row in cursor.fetchall()]
    
    def get_total_count(self) -> int:
        """获取题目总数"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM problems')
            return cursor.fetchone()[0]
    
    def get_solved_count(self) -> int:
        """获取已解决题目数"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM problems WHERE status = 'solved'")
            return cursor.fetchone()[0]
    
    # ==================== Helper Methods ====================
    
    def _row_to_dict(self, row: sqlite3.Row) -> Dict:
        """将数据库行转换为字典"""
        result = dict(row)
        
        # 将JSON字符串转换回Python对象
        for key in ['tags', 'algorithms', 'data_structures', 'code_features']:
            if key in result and result[key]:
                try:
                    result[key] = json.loads(result[key])
                except json.JSONDecodeError:
                    pass
        
        return result
    
    def problem_exists(self, file_path: str) -> bool:
        """检查题目是否已存在"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT 1 FROM problems WHERE file_path = ?', (file_path,))
            return cursor.fetchone() is not None

    # ==================== Training Plan Methods ====================

    def get_daily_plan(self, date: str) -> Optional[Dict]:
        """获取指定日期的训练计划"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM daily_plans WHERE date = ?
            ''', (date,))
            row = cursor.fetchone()

            if row:
                plan = self._row_to_dict(row)
                # 将 JSON 字符串转回列表
                if plan.get('tasks'):
                    plan['tasks'] = json.loads(plan['tasks'])
                
                # 从 task_execution 表获取任务（手动添加的任务存储在这里）
                cursor.execute('''
                    SELECT * FROM task_execution WHERE plan_id = ? ORDER BY id
                ''', (plan['id'],))
                execution_tasks = []
                for task_row in cursor.fetchall():
                    task = self._row_to_dict(task_row)
                    # 解析 tags JSON
                    if task.get('tags'):
                        try:
                            task['tags'] = json.loads(task['tags'])
                        except:
                            pass
                    execution_tasks.append(task)
                
                # 合并任务：如果 task_execution 表有任务，用它替代 daily_plans.tasks
                if execution_tasks:
                    plan['tasks'] = execution_tasks
                elif not plan.get('tasks'):
                    plan['tasks'] = []
                    
                return plan
            return None

    def save_daily_plan(self, date: str, plan_data: Dict) -> int:
        """保存每日训练计划"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # 保存计划主体
            cursor.execute('''
                INSERT OR REPLACE INTO daily_plans
                (user_id, date, training_mode, goal, tasks, total_estimated_time, difficulty_level, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                plan_data.get('user_id', 1),
                date,
                plan_data.get('training_mode', 'distributed'),
                plan_data.get('goal', ''),
                json.dumps(plan_data.get('tasks', []), ensure_ascii=False),
                plan_data.get('total_estimated_time', 0),
                plan_data.get('difficulty_level', '未知'),
                plan_data.get('status', 'pending'),
                plan_data.get('created_at', datetime.now().isoformat())
            ))

            plan_id = cursor.lastrowid

            # 删除旧任务（如果同一日期有旧计划）
            cursor.execute('DELETE FROM task_execution WHERE plan_id = ?', (plan_id,))

            # 保存任务列表
            for task in plan_data.get('tasks', []):
                cursor.execute('''
                    INSERT INTO task_execution
                    (plan_id, problem_id, problem_title, platform, difficulty, tags, priority, reason, estimated_time, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    plan_id,
                    task.get('problem_id'),
                    task.get('problem_title'),
                    task.get('platform'),
                    task.get('difficulty'),
                    json.dumps(task.get('tags', []), ensure_ascii=False),
                    task.get('priority'),
                    task.get('reason'),
                    task.get('estimated_time', 30),
                    task.get('status', 'pending')
                ))

            return plan_id

    def save_task(self, plan_id: int, task: Dict) -> int:
        """保存手动添加的任务"""
        import json
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # 解析 tags
            tags_json = json.dumps(task.get('tags', []), ensure_ascii=False)

            cursor.execute('''
                INSERT INTO task_execution (
                    plan_id, problem_id, problem_title, platform,
                    difficulty, tags, priority, reason, estimated_time, status, source
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                plan_id,
                task.get('problem_id', ''),
                task.get('problem_title', '未命名任务'),
                task.get('platform', 'local'),
                task.get('difficulty', 5),
                tags_json,
                task.get('priority', 'MEDIUM'),
                task.get('reason', ''),
                int(task.get('estimated_time', '30分钟').replace('分钟', '').strip()) if isinstance(task.get('estimated_time'), str) else task.get('estimated_time', 30),
                task.get('status', 'pending'),
                task.get('source', 'manual')
            ))

            return cursor.lastrowid

    def delete_task(self, plan_id: int, problem_id: str) -> bool:
        """删除指定的任务"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'DELETE FROM task_execution WHERE plan_id = ? AND problem_id = ?',
                (plan_id, problem_id)
            )
            return cursor.rowcount > 0

    def update_task_status(self, task_id: int, status: str,
                           completion_type: str = None, difficulty_adjust: float = None) -> bool:
        """更新任务状态"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            set_parts = ['status = ?', 'completed_at = CURRENT_TIMESTAMP']
            params = [status]

            if completion_type:
                set_parts.append('completion_type = ?')
                params.append(completion_type)

            if difficulty_adjust is not None:
                set_parts.append('difficulty_adjustment = ?')
                params.append(difficulty_adjust)

            params.append(task_id)

            sql = f'UPDATE task_execution SET {", ".join(set_parts)} WHERE id = ?'
            cursor.execute(sql, params)

            return cursor.rowcount > 0

    def get_task_by_id(self, task_id: int) -> Optional[Dict]:
        """根据ID获取任务"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM task_execution WHERE id = ?', (task_id,))
            row = cursor.fetchone()

            if row:
                return self._row_to_dict(row)
            return None

    def get_knowledge_mastery(self, knowledge: str) -> Optional[float]:
        """获取指定知识点的掌握度"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT mastery_score FROM knowledge_mastery WHERE knowledge = ?
            ''', (knowledge,))
            row = cursor.fetchone()

            if row:
                return row['mastery_score']
            return None

    def update_knowledge_mastery(self, knowledge: str, **kwargs) -> bool:
        """更新知识点掌握度"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # 检查是否存在
            cursor.execute('SELECT id FROM knowledge_mastery WHERE knowledge = ?', (knowledge,))
            exists = cursor.fetchone() is not None

            if exists:
                set_clause = ', '.join([f'{k} = ?' for k in kwargs.keys()])
                params = list(kwargs.values()) + [knowledge]
                sql = f'UPDATE knowledge_mastery SET {set_clause} WHERE knowledge = ?'
                cursor.execute(sql, params)
            else:
                # 插入新记录
                fields = ['knowledge'] + list(kwargs.keys())
                placeholders = ', '.join(['?' for _ in fields])
                field_names = ', '.join(fields)
                values = [knowledge] + list(kwargs.values())
                sql = f'INSERT INTO knowledge_mastery ({field_names}) VALUES ({placeholders})'
                cursor.execute(sql, values)

            return cursor.rowcount > 0

    def get_streak_days(self) -> int:
        """计算连续打卡天数"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # 获取最近30天有完成任务的天数
            cursor.execute('''
                SELECT DISTINCT date(completed_at) as date
                FROM task_execution
                WHERE status = 'completed'
                AND date(completed_at) >= date('now', '-30 days')
                ORDER BY date DESC
            ''')
            dates = [row['date'] for row in cursor.fetchall()]

            if not dates:
                return 0

            # 计算连续天数
            from datetime import datetime, timedelta
            streak = 0
            current_date = datetime.now().date()

            for date_str in dates:
                date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
                if (current_date - date_obj).days <= 1:
                    streak += 1
                    current_date = date_obj
                else:
                    break

            return streak

    # ==================== Platform Problems ====================

    def save_platform_problem(self, problem_data: Dict) -> bool:
        """保存平台题目信息"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute('''
                    INSERT OR REPLACE INTO platform_problems
                    (platform, problem_id, title, difficulty, tags, category, subcategory, solved_at, fetched_at, url)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?)
                ''', (
                    problem_data.get('platform'),
                    problem_data.get('problem_id'),
                    problem_data.get('title'),
                    problem_data.get('difficulty'),
                    json.dumps(problem_data.get('tags', []), ensure_ascii=False),
                    problem_data.get('category'),
                    problem_data.get('subcategory'),
                    problem_data.get('solved_at'),
                    problem_data.get('url')
                ))
                return True
            except Exception as e:
                print(f"保存平台题目失败: {e}")
                return False

    def update_platform_problem_difficulty(self, problem_id: int, new_difficulty: int) -> bool:
        """更新平台题目的难度（统一为 1-10 标准）"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute('''
                    UPDATE platform_problems
                    SET difficulty = ?
                    WHERE id = ?
                ''', (new_difficulty, problem_id))
                return True
            except Exception as e:
                print(f"更新题目难度失败: {e}")
                return False

    def get_platform_problems(self, platform: str = None) -> List[Dict]:
        """获取平台题目列表"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if platform:
                cursor.execute('''
                    SELECT * FROM platform_problems WHERE platform = ?
                ''', (platform,))
            else:
                cursor.execute('SELECT * FROM platform_problems')

            return [self._row_to_dict(row) for row in cursor.fetchall()]

    def get_all_platform_problems(self) -> List[Dict]:
        """获取所有平台题目（别名，保持API一致性）"""
        return self.get_platform_problems()

    def get_platform_category_stats(self) -> Dict[str, int]:
        """获取平台题目的分类统计"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT category, COUNT(*) as count
                FROM platform_problems
                WHERE category IS NOT NULL
                GROUP BY category
            ''')
            return {row['category']: row['count'] for row in cursor.fetchall()}

    def get_platform_difficulty_stats(self) -> Dict[float, int]:
        """获取平台题目的难度统计"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT difficulty, COUNT(*) as count
                FROM platform_problems
                WHERE difficulty IS NOT NULL
                GROUP BY difficulty
                ORDER BY difficulty
            ''')
            return {row['difficulty']: row['count'] for row in cursor.fetchall()}

    def get_combined_category_stats(self) -> Dict[str, int]:
        """获取本地+平台的合并分类统计（去重）"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # 使用 UNION 去重合并两个表
            cursor.execute('''
                SELECT category, COUNT(*) as count
                FROM (
                    SELECT platform, problem_id, category FROM problems
                    WHERE platform IS NOT NULL AND problem_id IS NOT NULL AND category IS NOT NULL

                    UNION

                    SELECT platform, problem_id, category FROM platform_problems
                    WHERE category IS NOT NULL

                    UNION

                    SELECT platform, problem_id, category FROM problems
                    WHERE (platform IS NULL OR problem_id IS NULL) AND category IS NOT NULL
                )
                GROUP BY category
            ''')
            return {row['category']: row['count'] for row in cursor.fetchall()}

    def get_combined_tags_stats(self) -> Dict[str, int]:
        """获取本地+平台的合并知识点标签统计（去重）"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # 获取平台题目的 tags（JSON 格式）
            cursor.execute('''
                SELECT tags
                FROM platform_problems
                WHERE tags IS NOT NULL AND tags != ''
            ''')
            platform_tags = []
            for row in cursor.fetchall():
                try:
                    tags = json.loads(row['tags'])
                    platform_tags.extend(tags)
                except:
                    pass

            # 获取本地题目的 algorithms 字段
            cursor.execute('''
                SELECT algorithms
                FROM problems
                WHERE algorithms IS NOT NULL AND algorithms != ''
            ''')
            local_tags = []
            for row in cursor.fetchall():
                try:
                    tags = json.loads(row['algorithms'])
                    local_tags.extend(tags)
                except:
                    pass

            # 合并并统计
            all_tags = platform_tags + local_tags
            tag_stats = {}
            for tag in all_tags:
                tag_stats[tag] = tag_stats.get(tag, 0) + 1

            return tag_stats

    def _normalize_difficulty(self, platform: str, difficulty: float) -> int:
        """
        将各平台难度归一化为 1-10 的标准难度

        Args:
            platform: 平台名称 (luogu, codeforces, nowcoder, etc.)
            difficulty: 原始难度值

        Returns:
            归一化后的难度 (1-10)
        """
        if difficulty is None or difficulty == 0:
            return 1

        platform_lower = platform.lower() if platform else ''

        # 洛谷难度：直接 1-7 映射到 1-7（稍微扩展一下到 10）
        if platform_lower in ['luogu', 'lg']:
            diff = int(difficulty)
            if diff <= 0:
                return 1
            elif diff <= 7:
                return diff
            else:
                # 超过 7 的映射到 8-10
                return min(10, 7 + (diff - 7))

        # Codeforces 难度：rating 映射
        # 800-1000 -> 1, 1000-1200 -> 2, ..., 2400+ -> 10
        elif platform_lower in ['codeforces', 'cf']:
            rating = float(difficulty)
            if rating < 800:
                return 1
            elif rating < 1000:
                return 2
            elif rating < 1200:
                return 3
            elif rating < 1400:
                return 4
            elif rating < 1600:
                return 5
            elif rating < 1800:
                return 6
            elif rating < 2000:
                return 7
            elif rating < 2200:
                return 8
            elif rating < 2400:
                return 9
            else:
                return 10

        # 牛客难度：简单/中等/困难 映射
        elif platform_lower in ['nowcoder', 'nk']:
            if isinstance(difficulty, str):
                diff_lower = difficulty.lower()
                if '简单' in diff_lower or 'easy' in diff_lower:
                    return 3
                elif '中等' in diff_lower or 'medium' in diff_lower:
                    return 6
                elif '困难' in diff_lower or '困难' in diff_lower or 'hard' in diff_lower:
                    return 9
            return 5  # 默认中等

        # 其他平台/本地文件：假设已经是 1-10 或 1-7
        elif difficulty <= 10:
            return int(difficulty)
        elif difficulty <= 7:
            return int(difficulty)
        else:
            # 超出范围的尝试归一化
            return min(10, max(1, int(difficulty)))

    def get_combined_difficulty_stats(self) -> Dict[int, int]:
        """获取本地+平台的合并难度统计（去重，难度归一化）"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # 使用 UNION 去重合并两个表，然后按归一化难度分组统计
            cursor.execute('''
                SELECT normalized_difficulty, COUNT(*) as count
                FROM (
                    -- 去重：有平台信息的题目（本地+平台）
                    SELECT
                        CASE
                            WHEN LOWER(platform) IN ('luogu', 'lg') AND difficulty BETWEEN 1 AND 7
                                THEN CAST(difficulty AS INTEGER)
                            WHEN LOWER(platform) IN ('codeforces', 'cf')
                                THEN
                                    CASE
                                        WHEN difficulty < 800 THEN 1
                                        WHEN difficulty < 1000 THEN 2
                                        WHEN difficulty < 1200 THEN 3
                                        WHEN difficulty < 1400 THEN 4
                                        WHEN difficulty < 1600 THEN 5
                                        WHEN difficulty < 1800 THEN 6
                                        WHEN difficulty < 2000 THEN 7
                                        WHEN difficulty < 2200 THEN 8
                                        WHEN difficulty < 2400 THEN 9
                                        ELSE 10
                                    END
                            WHEN difficulty <= 10 AND difficulty >= 1 THEN CAST(difficulty AS INTEGER)
                            WHEN difficulty <= 7 AND difficulty >= 1 THEN CAST(difficulty AS INTEGER)
                            ELSE 1
                        END AS normalized_difficulty
                    FROM (
                        SELECT platform, problem_id, difficulty
                        FROM problems
                        WHERE platform IS NOT NULL AND problem_id IS NOT NULL AND difficulty IS NOT NULL

                        UNION

                        SELECT platform, problem_id, difficulty
                        FROM platform_problems
                        WHERE difficulty IS NOT NULL
                    ) AS unique_platform_problems

                    UNION ALL

                    -- 本地题目（无平台信息，不需要去重）
                    SELECT
                        CASE
                            WHEN difficulty <= 10 AND difficulty >= 1 THEN CAST(difficulty AS INTEGER)
                            WHEN difficulty <= 7 AND difficulty >= 1 THEN CAST(difficulty AS INTEGER)
                            ELSE 1
                        END AS normalized_difficulty
                    FROM problems
                    WHERE (platform IS NULL OR problem_id IS NULL) AND difficulty IS NOT NULL
                )
                GROUP BY normalized_difficulty
                ORDER BY normalized_difficulty
            ''')
            return {int(row['normalized_difficulty']): row['count'] for row in cursor.fetchall()}

    def get_combined_total_count(self) -> int:
        """获取本地+平台的合并总题数（去重）"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # 使用 UNION 去重：platform + problem_id 唯一
            # 对于无 platform/problem_id 的题目，用 id 唯一
            cursor.execute('''
                SELECT COUNT(*) as count
                FROM (
                    -- 有平台信息的题目（去重）
                    SELECT platform, problem_id FROM problems
                    WHERE platform IS NOT NULL AND problem_id IS NOT NULL

                    UNION

                    SELECT platform, problem_id FROM platform_problems

                    UNION ALL

                    -- 无平台信息的本地题目（用 id 去重）
                    SELECT CAST(id AS TEXT), file_name FROM problems
                    WHERE platform IS NULL OR problem_id IS NULL
                )
            ''')
            return cursor.fetchone()['count']

    def get_combined_solved_count(self) -> int:
        """获取本地+平台的合并已解决题数（去重）"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # 使用 UNION 去重
            cursor.execute('''
                SELECT COUNT(*) as count
                FROM (
                    SELECT platform, problem_id FROM problems
                    WHERE platform IS NOT NULL AND problem_id IS NOT NULL AND status = 'solved'

                    UNION

                    SELECT platform, problem_id FROM platform_problems

                    UNION

                    SELECT platform, problem_id FROM problems
                    WHERE (platform IS NULL OR problem_id IS NULL) AND status = 'solved'
                )
            ''')
            return cursor.fetchone()['count']

    # ==================== 已刷题目（本地+平台统一视图） ====================

    def get_solved_problems(self) -> List[Dict]:
        """
        获取所有已解决题目（本地+平台统一视图）
        用于AI分析用户已刷题目，避免重复推荐
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # 本地题目（有平台信息且已解决）
            cursor.execute('''
                SELECT platform, problem_id, title, difficulty, tags, category
                FROM problems
                WHERE platform IS NOT NULL AND problem_id IS NOT NULL
            ''')
            local = [self._row_to_dict(row) for row in cursor.fetchall()]

            # 平台题目（线上已刷）
            cursor.execute('''
                SELECT platform, problem_id, title, difficulty, tags, category, url
                FROM platform_problems
            ''')
            platform = [self._row_to_dict(row) for row in cursor.fetchall()]

            # 合并并去重
            seen = set()
            all_problems = []
            for p in local + platform:
                key = (p.get('platform', '').lower(), p.get('problem_id', '').upper())
                if key not in seen and key[0] and key[1]:
                    seen.add(key)
                    all_problems.append(p)

            return all_problems

    # ==================== 候选题目池 ====================

    def add_candidate_problem(self, problem_data: Dict) -> bool:
        """
        添加候选题目到候选池

        Args:
            problem_data: {
                'platform': 'luogu'/'cf'/'atcoder',
                'problem_id': 'P1000'/'1234A',
                'title': '题目名称',
                'difficulty': 4.0,
                'difficulty_normalized': 4,
                'tags': ['dp', 'greedy'],
                'category': 'dp',
                'url': 'https://...',
                'reason': '为什么推荐这道题',
                'priority': 1
            }
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute('''
                    INSERT OR REPLACE INTO candidate_pool
                    (platform, problem_id, title, difficulty, difficulty_normalized,
                     tags, category, url, reason, priority)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    problem_data.get('platform'),
                    problem_data.get('problem_id'),
                    problem_data.get('title'),
                    problem_data.get('difficulty'),
                    problem_data.get('difficulty_normalized'),
                    json.dumps(problem_data.get('tags', []), ensure_ascii=False),
                    problem_data.get('category'),
                    problem_data.get('url'),
                    problem_data.get('reason'),
                    problem_data.get('priority', 1)
                ))
                return True
            except Exception as e:
                print(f"添加候选题目失败: {e}")
                return False

    def add_candidate_problems_batch(self, problems: List[Dict]) -> int:
        """
        批量添加候选题目

        Returns:
            成功添加的数量
        """
        count = 0
        for p in problems:
            if self.add_candidate_problem(p):
                count += 1
        return count

    def get_candidate_pool(self, limit: int = 100) -> List[Dict]:
        """
        获取候选题目池

        Args:
            limit: 返回数量限制

        Returns:
            候选题目列表（按priority降序）
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM candidate_pool
                WHERE status = 'pending'
                ORDER BY priority DESC, difficulty ASC
                LIMIT ?
            ''', (limit,))
            results = []
            for row in cursor.fetchall():
                p = self._row_to_dict(row)
                # 解析 tags JSON
                if p.get('tags'):
                    try:
                        p['tags'] = json.loads(p['tags'])
                    except:
                        p['tags'] = []
                results.append(p)
            return results

    def clear_candidate_pool(self) -> bool:
        """清空候选题目池"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM candidate_pool')
            return True

    def mark_candidate_done(self, platform: str, problem_id: str, action: str) -> bool:
        """
        标记候选题目状态

        Args:
            platform: 平台
            problem_id: 题目ID
            action: 'solved'（已刷过）、'too_hard'（太难）或 'cancel'（取消）
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            if action == 'cancel':
                # 取消标记 - 将状态改为 pending
                cursor.execute('''
                    UPDATE candidate_pool
                    SET status = 'pending'
                    WHERE platform = ? AND problem_id = ?
                ''', (platform, problem_id))
                # 记录到状态日志
                cursor.execute('''
                    INSERT INTO problem_status_log (platform, problem_id, action)
                    VALUES (?, ?, 'cancel')
                ''', (platform, problem_id))
            else:
                # 更新候选池状态
                cursor.execute('''
                    UPDATE candidate_pool
                    SET status = ?
                    WHERE platform = ? AND problem_id = ?
                ''', (action, platform, problem_id))

                # 记录到状态日志
                cursor.execute('''
                    INSERT INTO problem_status_log (platform, problem_id, action)
                    VALUES (?, ?, ?)
                ''', (platform, problem_id, action))

                # 如果是"已刷过"，添加到平台题目表（包含完整信息）
                if action == 'solved':
                    # 先从候选题目池获取该题目的详细信息
                    cursor.execute('''
                        SELECT title, difficulty, difficulty_normalized, tags, url, category
                        FROM candidate_pool
                        WHERE platform = ? AND problem_id = ?
                    ''', (platform, problem_id))
                    row = cursor.fetchone()
                    
                    if row:
                        title = row[0]
                        difficulty = row[1]
                        difficulty_normalized = row[2]
                        tags_json = row[3]
                        url = row[4]
                        category = row[5]
                        # 使用标准化的难度（1-10）
                        final_difficulty = difficulty_normalized if difficulty_normalized else difficulty
                    else:
                        title = None
                        final_difficulty = None
                        tags_json = None
                        url = None
                        category = None
                    
                    # 使用 INSERT OR REPLACE 更新平台题目表（包含完整信息）
                    cursor.execute('''
                        INSERT OR REPLACE INTO platform_problems
                        (platform, problem_id, title, difficulty, tags, category, url, solved_at, fetched_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    ''', (platform, problem_id, title, final_difficulty, tags_json, category, url))

            return cursor.rowcount > 0

    def get_solved_candidates(self) -> List[Dict]:
        """获取所有已刷过的候选题目"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM candidate_pool
                WHERE status = 'solved'
                ORDER BY updated_at DESC
            ''')
            results = []
            for row in cursor.fetchall():
                p = self._row_to_dict(row)
                if p.get('tags'):
                    try:
                        p['tags'] = json.loads(p['tags'])
                    except:
                        p['tags'] = []
                results.append(p)
            return results

    def update_candidate_tags(self, platform: str, problem_id: str, tags: List[str], category: str) -> bool:
        """更新候选题目的分类标签"""
        import json as json_module
        with self._get_connection() as conn:
            cursor = conn.cursor()
            tags_json = json_module.dumps(tags, ensure_ascii=False)
            cursor.execute('''
                UPDATE candidate_pool
                SET tags = ?, category = ?, updated_at = CURRENT_TIMESTAMP
                WHERE platform = ? AND problem_id = ?
            ''', (tags_json, category, platform, problem_id))
            return cursor.rowcount > 0

    def get_problems_without_category(self) -> List[Dict]:
        """获取没有分类标签的本地题目"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # 只查询 category 为空或 'other' 的题目
            cursor.execute('''
                SELECT id, title, platform, problem_id, category
                FROM problems
                WHERE category IS NULL OR category = '' OR category = 'other'
                ORDER BY id
            ''')
            results = []
            for row in cursor.fetchall():
                results.append(self._row_to_dict(row))
            return results

    def update_problem_category(self, problem_id: int, category: str, tags: List[str] = None) -> bool:
        """更新本地题目的分类标签"""
        import json as json_module
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if tags:
                tags_json = json_module.dumps(tags, ensure_ascii=False)
                cursor.execute('''
                    UPDATE problems
                    SET category = ?, tags = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (category, tags_json, problem_id))
            else:
                cursor.execute('''
                    UPDATE problems
                    SET category = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (category, problem_id))
            return cursor.rowcount > 0

    def delete_platform_problem(self, platform: str, problem_id: str) -> bool:
        """
        删除平台题目（从 platform_problems 表）
        同时将候选池中的题目恢复为 pending 状态
        
        Args:
            platform: 平台名称
            problem_id: 题目ID
            
        Returns:
            是否删除成功
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # 1. 从 platform_problems 删除
            cursor.execute('''
                DELETE FROM platform_problems
                WHERE LOWER(platform) = LOWER(?) AND UPPER(problem_id) = UPPER(?)
            ''', (platform, problem_id))
            deleted = cursor.rowcount > 0
            
            # 2. 将候选池中的题目恢复为 pending 状态（保留历史记录）
            cursor.execute('''
                UPDATE candidate_pool
                SET status = 'pending'
                WHERE LOWER(platform) = LOWER(?) AND UPPER(problem_id) = UPPER(?)
            ''', (platform, problem_id))
            
            return deleted

    def is_problem_solved(self, platform: str, problem_id: str) -> bool:
        """检查题目是否已刷过"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # 检查本地
            cursor.execute('''
                SELECT 1 FROM problems
                WHERE LOWER(platform) = LOWER(?) AND UPPER(problem_id) = UPPER(?)
                LIMIT 1
            ''', (platform, problem_id))
            if cursor.fetchone():
                return True

            # 检查平台已刷
            cursor.execute('''
                SELECT 1 FROM platform_problems
                WHERE LOWER(platform) = LOWER(?) AND UPPER(problem_id) = UPPER(?)
                LIMIT 1
            ''', (platform, problem_id))
            if cursor.fetchone():
                return True

            # 检查候选池已刷标记
            cursor.execute('''
                SELECT 1 FROM candidate_pool
                WHERE LOWER(platform) = LOWER(?) AND UPPER(problem_id) = UPPER(?)
                AND status = 'solved'
                LIMIT 1
            ''', (platform, problem_id))
            return cursor.fetchone() is not None

    # ==================== 增量同步 ====================

    def get_existing_problem_ids(self, platform: str = None) -> set:
        """
        获取数据库中已存在的题目ID集合

        Args:
            platform: 可选，只获取指定平台的

        Returns:
            {(platform, problem_id), ...} 集合
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if platform:
                cursor.execute('''
                    SELECT LOWER(platform), UPPER(problem_id)
                    FROM platform_problems
                    WHERE LOWER(platform) = LOWER(?)
                ''', (platform,))
            else:
                cursor.execute('''
                    SELECT LOWER(platform), UPPER(problem_id)
                    FROM platform_problems
                ''')
            return {(row[0], row[1]) for row in cursor.fetchall()}

    def get_platform_problem_count(self, platform: str) -> int:
        """获取指定平台的题目数量"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT COUNT(*) FROM platform_problems WHERE LOWER(platform) = LOWER(?)
            ''', (platform,))
            return cursor.fetchone()[0]

    def save_sync_log(self, platform: str, sync_type: str,
                      problems_fetched: int, problems_added: int,
                      problems_skipped: int, status: str,
                      error_message: str = None) -> int:
        """
        保存同步记录

        Returns:
            同步记录的ID
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO sync_log
                (platform, sync_type, problems_fetched, problems_added,
                 problems_skipped, status, error_message, finished_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (platform, sync_type, problems_fetched, problems_added,
                  problems_skipped, status, error_message))
            return cursor.lastrowid

    def get_last_sync_info(self, platform: str = None) -> Optional[Dict]:
        """
        获取最后一次同步信息

        Args:
            platform: 可选，只获取指定平台的

        Returns:
            最后一次同步的信息
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if platform:
                cursor.execute('''
                    SELECT * FROM sync_log
                    WHERE LOWER(platform) = LOWER(?) AND status = 'success'
                    ORDER BY finished_at DESC LIMIT 1
                ''', (platform,))
            else:
                cursor.execute('''
                    SELECT * FROM sync_log
                    WHERE status = 'success'
                    ORDER BY finished_at DESC LIMIT 1
                ''')
            row = cursor.fetchone()
            return self._row_to_dict(row) if row else None

    def get_sync_history(self, limit: int = 10) -> List[Dict]:
        """获取同步历史记录"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM sync_log
                ORDER BY started_at DESC
                LIMIT ?
            ''', (limit,))
            return [self._row_to_dict(row) for row in cursor.fetchall()]


# 全局数据库实例
db = Database()


if __name__ == '__main__':
    # 测试代码
    test_db = Database()
    
    # 添加测试数据
    test_problem = {
        'file_path': r'E:\test\P1001.cpp',
        'file_name': 'P1001.cpp',
        'title': 'A+B Problem',
        'platform': 'luogu',
        'problem_id': 'P1001',
        'difficulty': 1,
        'category': 'simulation',
        'subcategory': 'simulation',
        'tags': ['入门', '模拟'],
        'lines_of_code': 10,
    }
    
    problem_id = test_db.add_problem(test_problem)
    print(f'Added problem with ID: {problem_id}')
    
    # 查询
    problem = test_db.get_problem(r'E:\test\P1001.cpp')
    print(f'Query result: {problem}')
    
    # 统计
    stats = test_db.get_category_stats()
    print(f'Category stats: {stats}')
