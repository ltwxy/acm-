"""
知识点掌握度计算器
基于用户的刷题历史计算各知识点的掌握程度
"""
from typing import Dict, List, Optional
from collections import defaultdict
import json
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.database import db


class MasteryCalculator:
    """知识点掌握度计算器"""

    # 推荐题目数（按难度段）
    RECOMMENDED_COUNTS = {
        1: 30,   # 入门
        2: 40,   # 普及-
        3: 50,   # 普及/提高-
        4: 40,   # 普及+/提高
        5: 30,   # 提高+/省选-
        6: 20,   # 省选/NOI-
        7: 10,   # NOI/NOI+/CTSC
    }

    def __init__(self, user_id: int = 1):
        self.user_id = user_id

    def calculate_all(self) -> Dict[str, Dict]:
        """
        计算所有知识点的掌握度

        Returns:
            知识点掌握度字典 {tag: mastery_info}
        """
        problems = db.get_all_problems()

        # 按知识点分组
        tag_problems = defaultdict(list)
        for problem in problems:
            # 主要分类作为标签
            category = problem.get('category', 'other')
            subcategory = problem.get('subcategory')

            if category:
                tag_problems[category].append(problem)
            if subcategory:
                tag_problems[f"{category}_{subcategory}"].append(problem)

            # 同时考虑algorithms标签
            algorithms = problem.get('algorithms', [])
            for algo in algorithms:
                tag_problems[algo].append(problem)

        # 计算每个标签的掌握度
        mastery_results = {}
        for tag, tag_problems_list in tag_problems.items():
            mastery = self._calculate_tag_mastery(tag, tag_problems_list)
            mastery_results[tag] = mastery

        return mastery_results

    def _calculate_tag_mastery(self, tag: str, problems: List[Dict]) -> Dict:
        """
        计算单个知识点的掌握度

        Args:
            tag: 知识点标签
            problems: 该知识点的题目列表

        Returns:
            掌握度信息字典
        """
        if not problems:
            return {
                'tag': tag,
                'mastery_level': 0.0,
                'problem_count': 0,
                'one_submit_rate': 0.0,
                'avg_attempts': 0.0,
                'avg_complexity': 0.0,
            }

        # 统计数据
        problem_count = len(problems)
        one_submit_count = sum(1 for p in problems if p.get('one_submit', 1) == 1)
        total_attempts = sum(p.get('attempts', 1) for p in problems)
        total_complexity = sum(p.get('code_complexity', 0) for p in problems)

        # 计算指标
        one_submit_rate = one_submit_count / problem_count if problem_count > 0 else 0.0
        avg_attempts = total_attempts / problem_count if problem_count > 0 else 1.0
        avg_complexity = total_complexity / problem_count if problem_count > 0 else 0.0

        # 获取题目难度分布
        difficulties = [p.get('difficulty', 0) for p in problems if p.get('difficulty')]
        if difficulties:
            avg_difficulty = sum(difficulties) / len(difficulties)
        else:
            avg_difficulty = 0

        # 计算题目数达标率
        max_difficulty = int(max(difficulties)) if difficulties else 1
        recommended = self.RECOMMENDED_COUNTS.get(max_difficulty, 30)
        problem_rate = min(problem_count / recommended, 1.0)

        # 综合计算掌握度 (0.0-1.0)
        # 纯本地模式：没有真实AC率，用一次AC率和复杂度替代
        mastery_level = (
            one_submit_rate * 0.6 +  # 一次AC率（反映稳定性）
            problem_rate * 0.2 +       # 题目数量达标率
            avg_complexity * 0.2       # 代码复杂度（反映深度）
        )

        return {
            'tag': tag,
            'mastery_level': round(mastery_level, 2),
            'problem_count': problem_count,
            'one_submit_rate': round(one_submit_rate, 2),
            'avg_attempts': round(avg_attempts, 2),
            'avg_complexity': round(avg_complexity, 2),
            'avg_difficulty': round(avg_difficulty, 2),
        }

    def get_weak_points(self, top_n: int = 5) -> List[Dict]:
        """
        获取薄弱知识点

        Args:
            top_n: 返回前N个薄弱点

        Returns:
            薄弱点列表
        """
        all_mastery = self.calculate_all()

        # 筛选出题目数>=3的知识点（避免偶然性）
        filtered = [m for m in all_mastery.values() if m['problem_count'] >= 3]

        # 按掌握度排序
        weak_points = sorted(filtered, key=lambda x: x['mastery_level'])[:top_n]

        return weak_points

    def get_strong_points(self, top_n: int = 5) -> List[Dict]:
        """
        获取优势知识点

        Args:
            top_n: 返回前N个优势点

        Returns:
            优势点列表
        """
        all_mastery = self.calculate_all()

        # 筛选出题目数>=3的知识点
        filtered = [m for m in all_mastery.values() if m['problem_count'] >= 3]

        # 按掌握度排序（降序）
        strong_points = sorted(filtered, key=lambda x: -x['mastery_level'])[:top_n]

        return strong_points

    def get_mastery_by_difficulty(self) -> Dict[int, Dict]:
        """
        按难度段获取掌握度

        Returns:
            难度段掌握度字典 {difficulty: mastery_info}
        """
        problems = db.get_all_problems()

        # 按难度分组
        difficulty_problems = defaultdict(list)
        for problem in problems:
            difficulty = problem.get('difficulty', 0)
            if difficulty > 0:
                difficulty_problems[difficulty].append(problem)

        # 计算每个难度段的掌握度
        results = {}
        for difficulty, diff_problems in difficulty_problems.items():
            results[difficulty] = {
                'problem_count': len(diff_problems),
                'one_submit_rate': sum(
                    p.get('one_submit', 1) for p in diff_problems
                ) / len(diff_problems) if diff_problems else 0,
                'avg_complexity': sum(
                    p.get('code_complexity', 0) for p in diff_problems
                ) / len(diff_problems) if diff_problems else 0,
            }

            # 计算该难度段的推荐题数
            recommended = self.RECOMMENDED_COUNTS.get(difficulty, 30)
            problem_rate = min(len(diff_problems) / recommended, 1.0)

            results[difficulty]['mastery_level'] = round(
                results[difficulty]['one_submit_rate'] * 0.7 +
                problem_rate * 0.3,
                2
            )

        return results

    def save_to_db(self):
        """将掌握度保存到数据库"""
        import sqlite3
        from pathlib import Path
        from config import DB_PATH
        from datetime import datetime

        all_mastery = self.calculate_all()

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        try:
            for tag, mastery_info in all_mastery.items():
                # 更新或插入记录
                cursor.execute('''
                    INSERT OR REPLACE INTO mastery
                    (user_id, tag, mastery_level, problem_count, one_submit_rate, avg_attempts, last_updated)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    self.user_id,
                    tag,
                    mastery_info['mastery_level'],
                    mastery_info['problem_count'],
                    mastery_info['one_submit_rate'],
                    mastery_info['avg_attempts'],
                    datetime.now().isoformat()
                ))

            conn.commit()
            print(f'[掌握度] 已保存 {len(all_mastery)} 个知识点的掌握度')

        except Exception as e:
            conn.rollback()
            print(f'[掌握度] 保存失败: {e}')
        finally:
            conn.close()


# 全局实例
mastery_calculator = MasteryCalculator()


if __name__ == '__main__':
    # 测试
    calculator = MasteryCalculator()

    print("=== 所有知识点掌握度 ===")
    all_mastery = calculator.calculate_all()
    for tag, mastery in sorted(all_mastery.items(), key=lambda x: -x[1]['mastery_level']):
        print(f"{tag}: {mastery['mastery_level']:.2f} ({mastery['problem_count']}题)")

    print("\n=== 薄弱点 TOP5 ===")
    weak_points = calculator.get_weak_points(5)
    for wp in weak_points:
        print(f"{wp['tag']}: {wp['mastery_level']:.2f} ({wp['problem_count']}题)")

    print("\n=== 优势点 TOP5 ===")
    strong_points = calculator.get_strong_points(5)
    for sp in strong_points:
        print(f"{sp['tag']}: {sp['mastery_level']:.2f} ({sp['problem_count']}题)")

    print("\n=== 保存到数据库 ===")
    calculator.save_to_db()
