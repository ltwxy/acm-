"""
每日计划生成器
根据用户掌握度、弱点、目标等生成每日训练计划
"""
import json
import random
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime, timedelta

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.mastery_calculator import MasteryCalculator
from core.weakness_analyzer import WeaknessAnalyzer
from core.database import db


class DailyPlanGenerator:
    """每日计划生成器"""

    def __init__(self, user_id: int = 1):
        self.user_id = user_id
        self.mastery_calculator = MasteryCalculator(user_id)
        self.weakness_analyzer = WeaknessAnalyzer(user_id)

    def generate_daily_plan(self, date: str = None, training_mode: str = 'distributed',
                           goals: List[str] = None, problem_count: int = 3,
                           topic_cycle: int = 3) -> Dict:
        """
        生成每日训练计划

        Args:
            date: 计划日期 (YYYY-MM-DD)，默认为今天
            training_mode: 'distributed'(分散) 或 'focused'(集中)
            goals: 用户目标列表
            problem_count: 生成题目数量 (1-5)，默认3
            topic_cycle: 每隔几天引入一个新知识点 (1-5)，默认3

        Returns:
            每日计划字典
        """
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')

        problem_count = max(1, min(5, int(problem_count)))
        topic_cycle = max(1, min(5, int(topic_cycle)))

        # 获取用户状态
        weak_points = self.mastery_calculator.get_weak_points(top_n=5)
        strong_points = self.mastery_calculator.get_strong_points(top_n=5)
        all_mastery = self.mastery_calculator.calculate_all()

        # 判断今天是否是"引入新知识点"的日子
        introduce_new_topic = self._should_introduce_new_topic(date, topic_cycle)

        # 根据训练模式生成任务
        if training_mode == 'focused':
            tasks = self._generate_focused_tasks(weak_points, all_mastery, problem_count,
                                                 introduce_new_topic=introduce_new_topic)
        else:
            tasks = self._generate_distributed_tasks(weak_points, strong_points, all_mastery,
                                                     problem_count,
                                                     introduce_new_topic=introduce_new_topic)

        # 构建计划
        plan = {
            'date': date,
            'training_mode': training_mode,
            'goal': self._determine_goal(weak_points, goals),
            'tasks': tasks,
            'total_estimated_time': sum(t.get('estimated_time', 30) for t in tasks),
            'difficulty_level': self._calculate_difficulty_level(tasks),
            'topic_cycle': topic_cycle,
            'introduce_new_topic': introduce_new_topic,
            'created_at': datetime.now().isoformat(),
        }

        # 保存到数据库
        self._save_plan_to_db(plan)

        return plan

    def _should_introduce_new_topic(self, date: str, topic_cycle: int) -> bool:
        """
        判断今天是否应该引入新知识点。
        逻辑：以计划起始日为基准，每隔 topic_cycle 天引入一次。
        如果数据库里没有历史计划，今天就是第1天（不引入，从第 cycle 天起引入）。
        """
        import sqlite3
        from config import DB_PATH

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        try:
            # 查询历史计划数量（不含今天）
            cursor.execute('''
                SELECT COUNT(*) FROM daily_plans
                WHERE user_id = ? AND date < ?
            ''', (self.user_id, date))
            row = cursor.fetchone()
            past_count = row[0] if row else 0
        except Exception:
            past_count = 0
        finally:
            conn.close()

        # 第0天不引入，第 topic_cycle 天引入，第 2*topic_cycle 天再引入…
        # 即 past_count % topic_cycle == 0 且 past_count > 0
        return past_count > 0 and (past_count % topic_cycle == 0)

    def _pick_new_topic(self, all_mastery: Dict) -> Optional[str]:
        """
        选出一个"新知识点"：用户掌握度最低且不在当前弱点主列表里的标签。
        如果无法确定，返回 None。
        """
        # 知识图谱：所有竞赛常见知识点（CF 标签为准）
        TOPIC_LADDER = [
            'implementation', 'brute force', 'math', 'greedy', 'sortings',
            'binary search', 'two pointers', 'strings', 'number theory',
            'combinatorics', 'bitmasks', 'dp', 'graphs', 'dfs and similar',
            'trees', 'data structures', 'dsu', 'shortest paths',
            'constructive algorithms', 'games', 'geometry', 'fft',
        ]
        known_tags = {info['tag'] for info in all_mastery.values()}
        # 优先推荐用户还没接触过（mastery 里没有）的标签
        for topic in TOPIC_LADDER:
            normalized = self._normalize_tag(topic)
            if normalized not in known_tags and topic not in known_tags:
                return topic
        # 全都接触过，推荐掌握度最低的
        if all_mastery:
            return min(all_mastery.values(), key=lambda x: x['mastery_level'])['tag']
        return None

    def _generate_distributed_tasks(self, weak_points: List[Dict],
                                   strong_points: List[Dict],
                                   all_mastery: Dict,
                                   problem_count: int = 3,
                                   introduce_new_topic: bool = False) -> List[Dict]:
        """
        生成分散模式的任务（每天多种类型）

        策略：补漏题 → 巩固题 → 拔高题，循环填充到 problem_count 道
        若 introduce_new_topic=True，最后一道替换为新知识点的入门模板题
        """
        tasks = []
        selected_problem_ids = set()

        def try_add(tag, priority, reason, mastery_level, count=0):
            """尝试添加一道题，成功返回 True"""
            task = self._create_task(tag, priority, reason, mastery_level, count)
            pid = task['problem_id']
            if pid not in selected_problem_ids:
                selected_problem_ids.add(pid)
                tasks.append(task)
                return True
            return False

        # 先依次填一轮：补漏 → 巩固 → 拔高
        slots = []
        if weak_points:
            w = weak_points[0]
            slots.append((w['tag'], 'HIGH', f"{w['tag']}补漏 - 掌握度{w['mastery_level']:.2f}", w['mastery_level'], w['problem_count']))

        intermediate = [m for m in all_mastery.values() if 0.6 <= m['mastery_level'] < 0.8 and m['problem_count'] >= 3]
        if intermediate:
            sel = random.choice(intermediate)
            slots.append((sel['tag'], 'MEDIUM', f"{sel['tag']}巩固 - 保持手感", sel['mastery_level'], sel['problem_count']))

        if strong_points:
            s = strong_points[0]
            slots.append((s['tag'], 'LOW', f"{s['tag']}拔高 - 你在此领域有优势", s['mastery_level'], s['problem_count']))

        # 如果需要引入新知识点，预留最后一道给新知识点
        new_topic_reserved = introduce_new_topic and problem_count >= 2
        fill_count = problem_count - (1 if new_topic_reserved else 0)

        # 循环多轮填满 fill_count
        round_idx = 0
        attempts = 0
        while len(tasks) < fill_count and attempts < fill_count * 5:
            attempts += 1
            if slots:
                idx = round_idx % len(slots)
                t = slots[idx]
                try_add(t[0], t[1], t[2], t[3], t[4] if len(t) > 4 else 0)
                round_idx += 1
            else:
                if not try_add('other', 'LOW', '综合练习 - 保持刷题手感', 0.5):
                    break

        # 追加新知识点入门模板题
        if new_topic_reserved:
            new_topic = self._pick_new_topic(all_mastery)
            if new_topic:
                task = self._create_task(
                    new_topic, 'MEDIUM',
                    f'🆕 新知识点入门：{new_topic}（今日开始学习）',
                    0.1, 0  # 掌握度极低，推荐入门难度
                )
                task['is_new_topic'] = True
                pid = task['problem_id']
                if pid not in selected_problem_ids:
                    selected_problem_ids.add(pid)
                    tasks.append(task)

        return tasks[:problem_count]



    def _generate_focused_tasks(self, weak_points: List[Dict],
                                all_mastery: Dict,
                                problem_count: int = 3,
                                introduce_new_topic: bool = False) -> List[Dict]:
        """
        生成集中模式的任务（专注于1-2个薄弱点）

        策略：前 ceil(problem_count*2/3) 道来自第一弱点，其余来自第二弱点
        若 introduce_new_topic=True，最后一道替换为新知识点模板题
        不够时用不同弱点补充，绝不重复
        """
        tasks = []
        selected_problem_ids = set()

        def try_add(tag, priority, reason, mastery, count=0, max_attempts=5):
            for _ in range(max_attempts):
                task = self._create_task(tag, priority, reason, mastery, count)
                pid = task['problem_id']
                if pid not in selected_problem_ids and '待定' not in str(pid):
                    selected_problem_ids.add(pid)
                    tasks.append(task)
                    return True
            return False

        # 预留新知识点槽位
        new_topic_reserved = introduce_new_topic and problem_count >= 2
        fill_count = problem_count - (1 if new_topic_reserved else 0)

        if not weak_points:
            for i in range(fill_count):
                try_add('other', 'MEDIUM', '综合练习', 0.5)
        else:
            primary = weak_points[0]
            secondary = weak_points[1] if len(weak_points) > 1 else None

            primary_count = max(1, fill_count - (1 if secondary else 0))

            for i in range(primary_count):
                idx_str = f"({i+1}/{primary_count})"
                added = try_add(
                    primary['tag'], 'HIGH',
                    f"{primary['tag']}专项突破{idx_str}",
                    primary['mastery_level'], primary['problem_count']
                )
                if not added and secondary:
                    try_add(secondary['tag'], 'MEDIUM',
                            f"{secondary['tag']}辅助练习",
                            secondary['mastery_level'], secondary['problem_count'])

            if secondary and len(tasks) < fill_count:
                remaining = fill_count - len(tasks)
                for _ in range(remaining):
                    if not try_add(secondary['tag'], 'MEDIUM',
                                   f"{secondary['tag']}辅助练习",
                                   secondary['mastery_level'], secondary['problem_count']):
                        break

            extra_idx = 2
            while len(tasks) < fill_count and extra_idx < len(weak_points):
                wp = weak_points[extra_idx]
                try_add(wp['tag'], 'MEDIUM', f"{wp['tag']}额外练习",
                        wp['mastery_level'], wp['problem_count'])
                extra_idx += 1

        # 追加新知识点入门模板题
        if new_topic_reserved:
            new_topic = self._pick_new_topic(all_mastery)
            if new_topic:
                task = self._create_task(
                    new_topic, 'MEDIUM',
                    f'🆕 新知识点入门：{new_topic}（今日开始学习）',
                    0.1, 0
                )
                task['is_new_topic'] = True
                pid = task['problem_id']
                if pid not in selected_problem_ids:
                    selected_problem_ids.add(pid)
                    tasks.append(task)

        return tasks[:problem_count]



    def _create_task(self, tag: str, priority: str, reason: str,
                    mastery_level: float, problem_count: int = 0) -> Dict:
        """
        创建单个任务

        Args:
            tag: 知识点标签
            priority: 优先级 (HIGH/MEDIUM/LOW)
            reason: 推荐原因
            mastery_level: 掌握度
            problem_count: 该知识点的题目数量

        Returns:
            任务字典
        """
        # 根据掌握度和题目数量确定难度
        difficulty = self._map_mastery_to_difficulty(mastery_level)

        # 如果题目数量很少（<5），适当提高推荐难度
        if problem_count > 0 and problem_count < 5:
            difficulty += 1.0

        # 根据优先级估算时间
        estimated_time = {
            'HIGH': 45,
            'MEDIUM': 30,
            'LOW': 25,
        }.get(priority, 30)

        # 选择具体题目
        problem = self._select_problem(tag, difficulty)

        return {
            'problem_id': problem.get('id', f'示例_{tag}'),
            'problem_title': problem.get('title', f'{tag}练习题'),
            'platform': problem.get('platform', '待定'),
            'difficulty': difficulty,
            'tags': [tag],
            'priority': priority,
            'reason': reason,
            'estimated_time': estimated_time,
            'url': problem.get('url', ''),
        }

    def _map_mastery_to_difficulty(self, mastery_level: float) -> float:
        """
        将掌握度映射到推荐难度

        Args:
            mastery_level: 掌握度 (0.0-1.0)

        Returns:
            推荐难度
        """
        if mastery_level < 0.3:
            return 2.5  # 入门
        elif mastery_level < 0.5:
            return 3.0  # 普及-
        elif mastery_level < 0.7:
            return 3.5  # 普及/提高-
        elif mastery_level < 0.9:
            return 4.0  # 普及+/提高
        else:
            return 4.5  # 提高+/省选-

    def _normalize_tag(self, tag: str) -> str:
        """
        将本地标签映射到平台标签
        例如: math_组合数学 -> number_theory/combinatorics
        """
        tag_mapping = {
            # 数学类
            'math_组合数学': 'combinatorics',
            'math_数论': 'number theory',
            'math_number_theory': 'number theory',
            'number_theory': 'number theory',
            'math_博弈': 'games',
            'math_几何': 'geometry',
            'math_筛法': 'sieve',

            # DP
            'dp': 'dp',
            'dp_bitmasks': 'dp',
            'dp_number_theory': 'dp',
            'dp_greedy': 'dp',

            # 贪心
            'greedy': 'greedy',
            'greedy_构造': 'greedy',
            'greedy_constructive': 'greedy',
            'greedy_sortings': 'greedy',
            'greedy_implementation': 'greedy',
            'greedy_binary_search': 'greedy',
            'greedy_data_structure': 'greedy',

            # 数据结构
            'data_structure': 'data structures',
            'data_structure_two_pointers': 'two pointers',
            'data_structure_dsu': 'dsu',
            'data_structure_栈': 'stacks',
            'data_structure_单调栈': 'stacks',

            # 图论
            'graph': 'graphs',
            'graph_dfs': 'dfs',
            'graph_树': 'trees',
            'bfs': 'bfs',
            'dfs': 'dfs',

            # 搜索
            'search': 'binary search',
            'binary_search': 'binary search',

            # 字符串
            'string': 'strings',
            'string_构造': 'constructive algorithms',
            'string_constructive': 'constructive algorithms',
            'string_模拟': 'simulation',
            'string_sortings': 'sortings',

            # 模拟
            'simulation': 'implementation',
            'simulation_模拟': 'implementation',

            # 其他
            'sorting': 'sortings',
            'bit': 'bitmasks',
            'bitmasks': 'bitmasks',
            'bfs': 'graphs',
            'implementation': 'implementation',
            'brute_force': 'brute force',
            'brute': 'brute force',
        }

        # 如果直接有映射，返回
        if tag in tag_mapping:
            return tag_mapping[tag]

        # 否则尝试按前缀匹配
        if tag.startswith('math_'):
            return 'number theory'
        elif tag.startswith('greedy_'):
            return 'greedy'
        elif tag.startswith('dp_'):
            return 'dp'
        elif tag.startswith('graph_'):
            return 'graphs'
        elif tag.startswith('string_'):
            return 'strings'

        # 默认返回原始标签
        return tag

    def _get_solved_set(self) -> set:
        """
        获取所有已做过的题目集合（本地 problems 表 + platform_problems 表）
        返回 set of (platform, problem_id) 小写标准化
        """
        import sqlite3
        from config import DB_PATH

        solved = set()
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        try:
            # 本地已写的题
            cursor.execute('''
                SELECT platform, problem_id FROM problems
                WHERE platform IS NOT NULL AND problem_id IS NOT NULL
            ''')
            for platform, problem_id in cursor.fetchall():
                solved.add((platform.lower().strip(), problem_id.strip()))

            # 平台爬取的已做题（platform_problems 里的全部都是已做过的）
            cursor.execute('''
                SELECT platform, problem_id FROM platform_problems
                WHERE platform IS NOT NULL AND problem_id IS NOT NULL
            ''')
            for platform, problem_id in cursor.fetchall():
                solved.add((platform.lower().strip(), problem_id.strip()))
        finally:
            conn.close()
        return solved

    def _fetch_cf_problems_by_tag(self, tag: str, target_rating: int,
                                  solved_set: set, limit: int = 20) -> List[Dict]:
        """
        通过 Codeforces API 按 tag 搜索未做过的题目
        target_rating: CF rating（800-3000）
        返回最多 limit 条候选，按 rating 接近度排序
        """
        import urllib.request
        import urllib.parse

        # CF rating 容差 ±300
        tolerance = 300

        try:
            tag_encoded = urllib.parse.quote(tag)
            url = f"https://codeforces.com/api/problemset.problems?tags={tag_encoded}"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode())
        except Exception as e:
            print(f"[CF API] 请求失败: {e}")
            return []

        if data.get('status') != 'OK':
            return []

        problems = data.get('result', {}).get('problems', [])
        candidates = []
        for p in problems:
            pid = f"{p.get('contestId', '')}{p.get('index', '')}"
            platform_key = ('codeforces', pid)
            if platform_key in solved_set:
                continue  # 已做过，跳过

            rating = p.get('rating', 0)
            if rating == 0:
                continue  # 无难度信息，跳过

            diff = abs(rating - target_rating)
            if diff > tolerance:
                continue

            cf_url = f"https://codeforces.com/problemset/problem/{p.get('contestId', '')}/{p.get('index', '')}"
            candidates.append({
                'id': f"codeforces:{pid}",
                'platform': 'codeforces',
                'problem_id': pid,
                'title': p.get('name', ''),
                'difficulty': rating,
                'tags': p.get('tags', []),
                'url': cf_url,
                '_diff': diff,
            })

        # 按接近度排序，取前 limit 条
        candidates.sort(key=lambda x: x['_diff'])
        return candidates[:limit]

    @staticmethod
    def _cf_rating_from_difficulty(difficulty: float) -> int:
        """
        将内部难度（1-10）转换回 CF rating，用于 API 查询
        反向映射：rating = difficulty * 300，钳制在 800-3000
        """
        rating = int(difficulty * 300)
        return max(800, min(3000, rating))

    def _select_problem(self, tag: str, difficulty: float) -> Dict:
        """
        从 Codeforces 公开题库（API）中选择一道未做过的题目。
        已做题 = problems 表（本地） ∪ platform_problems 表（平台已做）

        Args:
            tag: 知识点标签
            difficulty: 目标难度（内部 1-10 标准）

        Returns:
            题目信息字典
        """
        # 1. 获取所有已做过的题目（两张表合并）
        solved_set = self._get_solved_set()

        # 2. 将内部难度转换为 CF rating
        target_rating = self._cf_rating_from_difficulty(difficulty)

        # 3. 标签标准化（映射到 CF 标签）
        normalized_tag = self._normalize_tag(tag)

        # 4. 调用 CF API 查询未做过的候选题
        candidates = self._fetch_cf_problems_by_tag(
            normalized_tag, target_rating, solved_set, limit=10
        )

        # 5. 如果 CF API 没找到，放宽难度容差再试一次（±600）
        if not candidates:
            # 放宽容差到 ±600，通过扩大 limit 捕获更多
            candidates = self._fetch_cf_problems_by_tag(
                normalized_tag, target_rating, solved_set, limit=30
            )
            # 从中取 rating 差最小的
            if candidates:
                candidates = sorted(candidates, key=lambda x: x['_diff'])

        if candidates:
            # 随机从前3中选一道，增加多样性
            pool = candidates[:min(3, len(candidates))]
            selected = random.choice(pool)
            return {
                'id': selected['id'],
                'title': selected['title'],
                'platform': 'codeforces',
                'difficulty': selected['difficulty'],
                'url': selected['url'],
            }

        # 6. 最终降级：返回 CF 题目搜索链接，至少让用户能找到题目
        cf_search_tag = urllib.parse.quote(normalized_tag)
        return {
            'id': f'待定_{tag}',
            'title': f'{tag} 练习（点击前往 CF 搜索）',
            'platform': 'codeforces',
            'difficulty': difficulty,
            'url': f'https://codeforces.com/problemset?tags={cf_search_tag}',
        }

    def _determine_goal(self, weak_points: List[Dict], goals: List[str]) -> str:
        """确定当日目标"""
        if weak_points:
            primary_weakness = weak_points[0]
            return f"提升{primary_weakness['tag']}能力（当前掌握度{primary_weakness['mastery_level']:.2f}）"

        if goals:
            return f"为目标奋斗：{goals[0]}"

        return "保持刷题手感，稳步提升"

    def _calculate_difficulty_level(self, tasks: List[Dict]) -> str:
        """计算整体难度等级"""
        if not tasks:
            return "未知"

        avg_difficulty = sum(t.get('difficulty', 0) for t in tasks) / len(tasks)

        if avg_difficulty < 2.5:
            return "简单"
        elif avg_difficulty < 3.5:
            return "适中"
        elif avg_difficulty < 4.5:
            return "中等偏上"
        else:
            return "困难"

    def _save_plan_to_db(self, plan: Dict):
        """保存计划到数据库"""
        import sqlite3
        from pathlib import Path
        from config import DB_PATH

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        try:
            # 插入计划
            cursor.execute('''
                INSERT OR REPLACE INTO daily_plans
                (user_id, date, goal, tasks, total_estimated_time, difficulty_level, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                self.user_id,
                plan['date'],
                plan['goal'],
                json.dumps(plan['tasks'], ensure_ascii=False),
                plan['total_estimated_time'],
                plan['difficulty_level'],
                'pending',
                plan['created_at']
            ))

            conn.commit()
            print(f'[计划] 已保存 {plan["date"]} 的每日计划')

        except Exception as e:
            conn.rollback()
            print(f'[计划] 保存失败: {e}')
        finally:
            conn.close()

    def get_plan(self, date: str = None) -> Optional[Dict]:
        """
        获取指定日期的计划

        Args:
            date: 计划日期

        Returns:
            计划字典，如果不存在则返回None
        """
        import sqlite3
        from pathlib import Path
        from config import DB_PATH

        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        try:
            cursor.execute('''
                SELECT * FROM daily_plans
                WHERE user_id = ? AND date = ?
            ''', (self.user_id, date))

            row = cursor.fetchone()
            if row:
                plan = dict(row)
                plan['tasks'] = json.loads(plan['tasks'])
                return plan

            return None

        except Exception as e:
            print(f'[计划] 获取失败: {e}')
            return None
        finally:
            conn.close()


# 全局实例
plan_generator = DailyPlanGenerator()


if __name__ == '__main__':
    # 测试
    print("=== 分散模式测试 ===\n")
    plan_distributed = plan_generator.generate_daily_plan(
        training_mode='distributed',
        goals=['省赛省二']
    )
    print(f"日期: {plan_distributed['date']}")
    print(f"目标: {plan_distributed['goal']}")
    print(f"难度等级: {plan_distributed['difficulty_level']}")
    print(f"预计耗时: {plan_distributed['total_estimated_time']}分钟\n")
    print("任务列表:")
    for i, task in enumerate(plan_distributed['tasks'], 1):
        print(f"{i}. [{task['priority']}] {task['problem_title']}")
        print(f"   难度: {task['difficulty']} | 预计: {task['estimated_time']}分钟")
        print(f"   原因: {task['reason']}\n")

    print("\n" + "="*80 + "\n")

    print("=== 集中模式测试 ===\n")
    plan_focused = plan_generator.generate_daily_plan(
        training_mode='focused',
        goals=['省赛省二']
    )
    print(f"日期: {plan_focused['date']}")
    print(f"目标: {plan_focused['goal']}")
    print(f"难度等级: {plan_focused['difficulty_level']}")
    print(f"预计耗时: {plan_focused['total_estimated_time']}分钟\n")
    print("任务列表:")
    for i, task in enumerate(plan_focused['tasks'], 1):
        print(f"{i}. [{task['priority']}] {task['problem_title']}")
        print(f"   难度: {task['difficulty']} | 预计: {task['estimated_time']}分钟")
        print(f"   原因: {task['reason']}\n")
