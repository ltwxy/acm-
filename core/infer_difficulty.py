"""
基于知识点自动推断题目难度
"""
import os
import sys
from pathlib import Path

# 修复 Windows 终端编码问题
os.environ['PYTHONIOENCODING'] = 'utf-8'
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

sys.path.insert(0, str(Path(__file__).parent))

from core.database import db


# 知识点难度映射
CATEGORY_DIFFICULTY_MAP = {
    # 搜索算法 - 中等
    'search': {
        'bfs': 3,
        'dfs': 3,
    },
    
    # 动态规划 - 根据子类型
    'dp': {
        'linear': 4,           # 线性DP - 中高
        'knapsack': 4,         # 背包 - 中高
        'interval': 5,         # 区间DP - 高
        'tree': 5,             # 树形DP - 高
        'digit': 5,            # 数位DP - 高
    },
    
    # 图论 - 根据子类型
    'graph': {
        'shortest': 4,         # 最短路 - 中高
        'mst': 4,              # 最小生成树 - 中高
        'union_find': 3,       # 并查集 - 中等
        'other': 5,            # 其他图论 - 高
    },
    
    # 数据结构 - 根据子类型
    'data_structure': {
        'segment_tree': 5,     # 线段树 - 高
        'bit': 5,              # 树状数组 - 高
        'monotonic': 4,        # 单调栈/队列 - 中高
        'other': 3,            # 其他 - 中等
    },
    
    # 数学 - 根据子类型
    'math': {
        'number_theory': 4,    # 数论 - 中高
        'power': 3,            # 快速幂 - 中等
        'game': 4,             # 博弈论 - 中高
        'other': 3,            # 其他 - 中等
    },
    
    # 字符串 - 根据子类型
    'string': {
        'basic': 2,            # 基础字符串 - 普及
        'advanced': 4,         # 高级字符串 - 中高
    },
    
    # 排序与分治
    'sorting': {
        'sort': 2,             # 排序 - 普及
        'divide': 4,           # 分治 - 中高
    },
    
    # 二分与贪心
    'binary_greedy': {
        'binary': 3,           # 二分 - 中等
        'greedy': 3,           # 贪心 - 中等
    },
    
    # 模拟与构造
    'simulation': {
        'simulation': 2,       # 模拟 - 普及
        'construction': 3,     # 构造 - 中等
    },
    
    # 其他
    'other': {
        None: 2,               # 默认 - 普及
    }
}


def infer_difficulty(category, subcategory=None):
    """根据分类推断难度"""
    if not category:
        return None
    
    cat_map = CATEGORY_DIFFICULTY_MAP.get(category, {})
    
    if subcategory and subcategory in cat_map:
        return cat_map[subcategory]
    
    # 如果没有子分类，返回该分类的平均难度
    if isinstance(cat_map, dict) and cat_map:
        return max(cat_map.values()) if cat_map.values() else 3
    
    return 3  # 默认中等难度


def infer_all_difficulties():
    """为所有题目推断难度"""
    
    problems = db.get_all_problems()
    updated = 0
    
    print(f"为 {len(problems)} 个题目推断难度...\n")
    
    for i, problem in enumerate(problems, 1):
        if problem.get('difficulty'):
            # 已有难度，跳过
            continue
        
        category = problem.get('category')
        subcategory = problem.get('subcategory')
        
        difficulty = infer_difficulty(category, subcategory)
        
        if difficulty:
            db.update_problem(problem['file_path'], {'difficulty': difficulty})
            updated += 1
            
            if i % 10 == 0:
                print(f"已处理 {i}/{len(problems)} 个题目...")
    
    print(f"\n✓ 完成！更新了 {updated} 个题目的难度")
    
    # 显示新的难度分布
    print("\n难度分布:")
    stats = db.get_difficulty_stats()
    difficulty_names = {
        1: '入门', 2: '普及-', 3: '普及/提高-', 4: '普及+/提高',
        5: '提高+/省选-', 6: '省选/NOI-', 7: 'NOI/NOI+/CTSC'
    }
    
    for diff in range(1, 8):
        count = stats.get(diff, 0)
        name = difficulty_names.get(diff, f'难度{diff}')
        bar = '█' * (count * 2)
        print(f"  {name:15} {bar} {count}")


if __name__ == '__main__':
    infer_all_difficulties()
