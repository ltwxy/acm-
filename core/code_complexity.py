"""
代码复杂度分析器
通过静态分析评估代码复杂度（0-1）
"""
import re
from pathlib import Path
from typing import Dict, List, Tuple


class CodeComplexityAnalyzer:
    """代码复杂度分析器"""

    # 关键字权重
    KEYWORD_WEIGHTS = {
        '循环': 0.15,
        '递归': 0.25,
        '条件': 0.08,
        '数据结构': 0.12,
        '算法': 0.2,
    }

    def __init__(self):
        # 各种代码模式的正则表达式
        self.patterns = {
            # 循环相关
            'for_loop': r'\bfor\s*\([^)]*\)',
            'while_loop': r'\bwhile\s*\([^)]*\)',
            'nested_loop': r'(for|while)[^{]*{[^}]*\s*(for|while)',  # 嵌套循环

            # 递归相关
            'recursive_call': r'\b(\w+)\s*\(\s*[^)]*\)\s*{[^}]*\1\s*\(',
            'self_recursion': r'\breturn\s+\w+\s*\(',  # return func(...
            'dfs_pattern': r'\bvoid\s+dfs\s*\(',

            # 条件分支
            'if': r'\bif\s*\([^)]*\)',
            'else_if': r'\belse\s+if\s*\([^)]*\)',
            'switch': r'\bswitch\s*\(',
            'ternary': r'\?\s*:',

            # 数据结构
            'vector': r'\bvector\s*<',
            'set': r'\bset\s*<',
            'map': r'\bmap\s*<',
            'priority_queue': r'\bpriority_queue\s*<',
            'stack': r'\bstack\s*<',
            'queue': r'\bqueue\s*<',
            'deque': r'\bdeque\s*<',
            'array': r'\w+\s*\[\s*\d+\s*\]',  # 固定大小数组

            # 算法相关
            'sort': r'\bsort\s*\(',
            'binary_search': r'\blower_bound\s*\(|\bupper_bound\s*\(|\bbinary_search\s*\(',
            'dynamic_programming': r'\bdp\s*\[|int\s+dp\s*\[|ll\s+dp\s*\[',
            'memset': r'\bmemset\s*\(',
            'gcd': r'\bgcd\s*\(|\b__gcd\s*\(',
            'quick_pow': r'\b(qpow|fast_pow|quick_pow)\s*\(',
            'dijkstra': r'\bdijkstra\s*\(',
            'bfs': r'\bqueue\s*<|while\s*\([^)]*queue[^)]*\)',
            'dfs': r'\bvoid\s+dfs\s*\(|\bvoid\s+solve\s*\([^)]*\)\s*{[^}]*dfs',
        }

    def analyze(self, file_path: Path) -> Dict:
        """
        分析代码复杂度

        Args:
            file_path: 代码文件路径

        Returns:
            复杂度分析结果字典
        """
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                code = f.read()
        except Exception:
            return {
                'complexity': 0.0,
                'lines': 0,
                'loops': 0,
                'recursions': 0,
                'conditions': 0,
                'data_structures': 0,
                'algorithms': 0,
            }

        # 基础统计
        lines = len([line for line in code.split('\n') if line.strip() and not line.strip().startswith('//')])
        lines_no_comments = self._remove_comments(code)
        lines_no_comments = len([line for line in lines_no_comments.split('\n') if line.strip()])

        # 各类计数
        loops = self._count_patterns(code, ['for_loop', 'while_loop', 'nested_loop'])
        recursions = self._count_patterns(code, ['recursive_call', 'self_recursion', 'dfs_pattern'])
        conditions = self._count_patterns(code, ['if', 'else_if', 'switch', 'ternary'])
        data_structures = self._count_patterns(code, ['vector', 'set', 'map', 'priority_queue', 'stack', 'queue', 'deque', 'array'])
        algorithms = self._count_patterns(code, ['sort', 'binary_search', 'dynamic_programming', 'memset', 'gcd', 'quick_pow', 'dijkstra', 'bfs', 'dfs'])

        # 计算复杂度 (0-1)
        complexity = self._calculate_complexity(
            lines_no_comments,
            loops,
            recursions,
            conditions,
            data_structures,
            algorithms
        )

        return {
            'complexity': round(complexity, 2),
            'lines': lines_no_comments,
            'loops': loops,
            'recursions': recursions,
            'conditions': conditions,
            'data_structures': data_structures,
            'algorithms': algorithms,
        }

    def _remove_comments(self, code: str) -> str:
        """移除代码注释"""
        # 移除单行注释
        code = re.sub(r'//.*', '', code)
        # 移除多行注释
        code = re.sub(r'/\*.*?\*/', '', code, flags=re.DOTALL)
        return code

    def _count_patterns(self, code: str, pattern_names: List[str]) -> int:
        """统计匹配的模式数量"""
        count = 0
        for name in pattern_names:
            pattern = self.patterns.get(name)
            if pattern:
                matches = re.findall(pattern, code, re.IGNORECASE)
                count += len(matches)
        return count

    def _calculate_complexity(self, lines: int, loops: int, recursions: int,
                            conditions: int, data_structures: int, algorithms: int) -> float:
        """
        计算综合复杂度 (0-1)

        计算公式：
        - 基础复杂度：行数归一化
        - 结构复杂度：循环、递归、条件分支
        - 逻辑复杂度：数据结构、算法使用
        """
        # 行数归一化 (假设100行为高复杂度)
        line_factor = min(lines / 100.0, 1.0) * 0.2

        # 结构复杂度
        loop_factor = min(loops / 10.0, 1.0) * self.KEYWORD_WEIGHTS['循环']
        recursion_factor = min(recursions / 5.0, 1.0) * self.KEYWORD_WEIGHTS['递归']
        condition_factor = min(conditions / 15.0, 1.0) * self.KEYWORD_WEIGHTS['条件']

        # 逻辑复杂度
        ds_factor = min(data_structures / 5.0, 1.0) * self.KEYWORD_WEIGHTS['数据结构']
        algo_factor = min(algorithms / 5.0, 1.0) * self.KEYWORD_WEIGHTS['算法']

        # 综合计算
        complexity = (
            line_factor +
            loop_factor +
            recursion_factor +
            condition_factor +
            ds_factor +
            algo_factor
        )

        # 归一化到0-1范围
        return min(max(complexity, 0.0), 1.0)


# 全局实例
complexity_analyzer = CodeComplexityAnalyzer()


if __name__ == '__main__':
    # 测试代码
    test_code = '''
#include <iostream>
#include <vector>
using namespace std;

void dfs(int x) {
    if (x == 0) return;
    for (int i = 0; i < 5; i++) {
        dfs(x - 1);
    }
}

int main() {
    int dp[100];
    vector<int> v;
    sort(v.begin(), v.end());
    dfs(5);
    return 0;
}
'''

    # 保存测试文件
    test_file = Path('test_code.cpp')
    test_file.write_text(test_code, encoding='utf-8')

    # 分析
    result = complexity_analyzer.analyze(test_file)
    print("代码复杂度分析结果:")
    for key, value in result.items():
        print(f"  {key}: {value}")

    # 清理
    test_file.unlink()
