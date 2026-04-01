"""
刷题管理系统配置文件
"""
import os
from pathlib import Path

# 基础路径
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

# 数据库路径
DB_PATH = DATA_DIR / "problems.db"

# 配置文件路径
CONFIG_PATH = BASE_DIR / "config.json"

# 监控的刷题文件夹路径
# 用户可以修改这里
TARGET_DIR = Path(r"E:\大学\大学\编程\Save-point\日常刷题")

# 文件扩展名
SUPPORTED_EXTENSIONS = ['.cpp', '.c', '.py', '.java', '.go', '.rs']

# 分类配置
CATEGORIES = {
    'search': {
        'name': '搜索算法',
        'color': '#FF6B6B',
        'keywords': ['bfs', 'dfs', '搜索', 'queue', 'stack', '递归', '回溯', '剪枝'],
        'subcategories': {
            'bfs': {'name': 'BFS', 'keywords': ['bfs', '广度', 'queue', '队列']},
            'dfs': {'name': 'DFS', 'keywords': ['dfs', '深度', '递归', '回溯']},
        }
    },
    'dp': {
        'name': '动态规划',
        'color': '#4ECDC4',
        'keywords': ['dp', '动态规划', '记忆化', '状态转移', '背包', '区间dp', '树形dp', '数位dp'],
        'subcategories': {
            'linear': {'name': '线性DP', 'keywords': ['线性', '最长', '子序列', '子段和']},
            'knapsack': {'name': '背包问题', 'keywords': ['背包', '01背包', '完全背包', '多重背包']},
            'interval': {'name': '区间DP', 'keywords': ['区间', '合并', '三角形']},
            'tree': {'name': '树形DP', 'keywords': ['树形', '树上', '依赖']},
            'digit': {'name': '数位DP', 'keywords': ['数位', '数字', '计数']},
        }
    },
    'graph': {
        'name': '图论',
        'color': '#45B7D1',
        'keywords': ['图', '边', '点', '最短', '生成树', '并查集', '拓扑', '连通'],
        'subcategories': {
            'shortest': {'name': '最短路', 'keywords': ['最短路', 'dijkstra', 'spfa', 'floyd', 'bellman']},
            'mst': {'name': '最小生成树', 'keywords': ['最小生成树', 'kruskal', 'prim']},
            'union_find': {'name': '并查集', 'keywords': ['并查集', '连通', '集合']},
            'other': {'name': '其他图论', 'keywords': ['拓扑', '二分图', '网络流']},
        }
    },
    'data_structure': {
        'name': '数据结构',
        'color': '#96CEB4',
        'keywords': ['数据结构', '线段树', '树状数组', '单调', '栈', '队列', '堆', '优先队列'],
        'subcategories': {
            'segment_tree': {'name': '线段树', 'keywords': ['线段树', 'seg', '区间修改', '区间查询']},
            'bit': {'name': '树状数组', 'keywords': ['树状数组', 'BIT', 'lowbit', '前缀和']},
            'monotonic': {'name': '单调栈/队列', 'keywords': ['单调', '单调栈', '单调队列']},
            'other': {'name': '其他', 'keywords': ['堆', '优先队列', 'set', 'map']},
        }
    },
    'math': {
        'name': '数学',
        'color': '#FFEAA7',
        'keywords': ['数学', '数论', 'gcd', '质数', '素数', '快速幂', '组合', '概率', '博弈'],
        'subcategories': {
            'number_theory': {'name': '数论', 'keywords': ['gcd', 'lcm', '质数', '素数', '欧拉', '莫比乌斯']},
            'power': {'name': '快速幂', 'keywords': ['快速幂', '幂', 'mod', '逆元']},
            'game': {'name': '博弈论', 'keywords': ['博弈', 'nim', 'sg函数']},
            'other': {'name': '其他数学', 'keywords': ['组合', '概率', '期望']},
        }
    },
    'string': {
        'name': '字符串',
        'color': '#DDA0DD',
        'keywords': ['字符串', 'kmp', 'trie', '后缀', '哈希', 'manacher'],
        'subcategories': {
            'basic': {'name': '基础字符串', 'keywords': ['字符串', '子串', '匹配']},
            'advanced': {'name': '高级字符串', 'keywords': ['kmp', 'trie', 'ac自动机', '后缀数组']},
        }
    },
    'sorting': {
        'name': '排序与分治',
        'color': '#98D8C8',
        'keywords': ['排序', '分治', '归并', '快排', '逆序对', '第k大'],
        'subcategories': {
            'sort': {'name': '排序', 'keywords': ['排序', 'sort', '快排', '归并排序']},
            'divide': {'name': '分治', 'keywords': ['分治', '逆序对', '第k大', 'cdq']},
        }
    },
    'binary_greedy': {
        'name': '二分与贪心',
        'color': '#F7DC6F',
        'keywords': ['二分', '贪心', '排序', '最值', '答案'],
        'subcategories': {
            'binary': {'name': '二分', 'keywords': ['二分', 'lower_bound', 'upper_bound', '答案']},
            'greedy': {'name': '贪心', 'keywords': ['贪心', '排序', '最优']},
        }
    },
    'simulation': {
        'name': '模拟与构造',
        'color': '#BB8FCE',
        'keywords': ['模拟', '构造', '实现', '大模拟'],
        'subcategories': {
            'simulation': {'name': '模拟', 'keywords': ['模拟', '实现']},
            'construction': {'name': '构造', 'keywords': ['构造', '方案']},
        }
    },
    'other': {
        'name': '其他',
        'color': '#95A5A6',
        'keywords': [],
        'subcategories': {}
    }
}

# 平台识别规则
PLATFORM_PATTERNS = {
    'luogu': {
        'name': '洛谷',
        'patterns': [
            r'[BPTUbptu]\d+',     # B/P/T/U + 数字，如 B3626, P1314
            r'CF\d+',              # 洛谷中的CF题
            r'SP\d+',              # SPOJ
            r'AT[_-]?\w+',         # AtCoder
            r'UVA\d+',             # UVA
        ],
        'url_template': 'https://www.luogu.com.cn/problem/{problem_id}'
    },
    'codeforces': {
        'name': 'Codeforces',
        'patterns': [
            r'\d+[A-Z]\d?',       # 1234A, 1234B2
        ],
        'url_template': 'https://codeforces.com/problemset/problem/{contest_id}/{problem_index}'
    },
    'leetcode': {
        'name': 'LeetCode',
        'patterns': [
            r'LC\d+',              # LC1, lc1
        ],
        'url_template': 'https://leetcode.cn/problems/{title_slug}'
    },
    'nowcoder': {
        'name': '牛客',
        'patterns': [
            r'牛客',               # 中文标识
            r'NC\d+',              # NC1
        ],
        'url_template': None
    },
    'usaco': {
        'name': 'USACO',
        'patterns': [
            r'USACO',
            r'usaco',
        ],
        'url_template': None
    },
    'noip': {
        'name': 'NOIP',
        'patterns': [
            r'NOIP',
            r'noip',
        ],
        'url_template': None
    }
}

# 难度映射
DIFFICULTY_MAP = {
    'luogu': {
        '入门': 1,
        '普及-': 2,
        '普及/': 3,
        '普及+': 4,
        '提高': 5,
        '提高+': 6,
        '省选': 7,
        'NOI': 8,
        'NOI+': 9,
    },
    'codeforces': {
        'newbie': 1,
        'pupil': 2,
        'specialist': 3,
        'expert': 4,
        'candidate master': 5,
        'master': 6,
        'international master': 7,
        'grandmaster': 8,
        'international grandmaster': 9,
        'legendary grandmaster': 10,
    },
    'leetcode': {
        '简单': 2,
        '中等': 4,
        '困难': 6,
    }
}

# 代码特征正则
CODE_PATTERNS = {
    'bfs': {
        'patterns': [
            r'queue\s*<\s*\w+\s*>\s*\w+',
            r'while\s*\(\s*!\w+\.empty\s*\)',
            r'\w+\.push\s*\(',
            r'\w+\.pop\s*\(',
        ],
        'weight': 3
    },
    'dfs': {
        'patterns': [
            r'void\s+dfs\s*\(',
            r'dfs\s*\([^)]+\)\s*;',
            r'void\s+solve\s*\([^)]*\)\s*{[^}]*dfs',
        ],
        'weight': 3
    },
    'dp': {
        'patterns': [
            r'dp\s*\[.+\]\s*=',
            r'f\s*\[.+\]\s*=',
            r'for\s*\([^)]+\)\s*{[^}]*dp\[',
            r'vector\s*<\s*\w+\s*>\s+dp\s*\(',
            r'memset\s*\([^,]+,\s*-1',
        ],
        'weight': 3
    },
    'union_find': {
        'patterns': [
            r'int\s+find\s*\(\s*int',
            r'fa\s*\[\s*find',
            r'fa\s*\[.+\]\s*=\s*fa\[',
        ],
        'weight': 3
    },
    'segment_tree': {
        'patterns': [
            r'struct\s+\w*\s*Tree\w*',
            r'struct\s+SegTree',
            r'void\s+build\s*\([^)]*l\s*,\s*[^)]*r\)',
            r'void\s+pushup',
            r'void\s+pushdown',
        ],
        'weight': 3
    },
    'bit': {
        'patterns': [
            r'int\s+lowbit\s*\(',
            r'lowbit\s*\(',
            r'c\s*\[.+\]\s*\+=',
        ],
        'weight': 3
    },
    'binary_search': {
        'patterns': [
            r'while\s*\(\s*l\s*<\s*r\)',
            r'mid\s*=\s*l\s*\+\s*\(\s*r\s*-\s*l\s*\)\s*/\s*2',
            r'lower_bound\s*\(',
            r'upper_bound\s*\(',
        ],
        'weight': 2
    },
    'dijkstra': {
        'patterns': [
            r'dijkstra',
            r'priority_queue.*pair',
            r'dis\s*\[.+\]\s*\+\s*\w+',
        ],
        'weight': 3
    },
    'graph': {
        'patterns': [
            r'struct\s+Edge',
            r'add_edge\s*\(',
            r'vector\s*<\s*\w+\s*>\s+g\s*\[',
            r'vector\s*<\s*\w+\s*>\s+adj',
        ],
        'weight': 2
    },
    'quick_pow': {
        'patterns': [
            r'qpow|quick_pow|fast_pow',
            r'while\s*\(\s*\w+\s*\)\s*{[^}]*\w+\s*\*=\s*\w+',
        ],
        'weight': 2
    },
    'merge_sort': {
        'patterns': [
            r'void\s+merge\s*\(',
            r'void\s+merge_sort\s*\(',
            r'temp\s*\[.+\]\s*=\s*\w+\s*\[',
        ],
        'weight': 2
    },
}
