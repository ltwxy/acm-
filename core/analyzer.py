"""
代码分析模块
自动识别代码中的算法和数据结构特征
"""
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple
from collections import defaultdict

from config import CODE_PATTERNS, CATEGORIES


class CodeAnalyzer:
    """代码分析器"""
    
    def __init__(self):
        self.patterns = CODE_PATTERNS
    
    def analyze_file(self, file_path: Path) -> Dict:
        """
        分析单个代码文件
        
        Args:
            file_path: 代码文件路径
            
        Returns:
            分析结果字典
        """
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        except Exception as e:
            return {
                'error': str(e),
                'lines_of_code': 0,
                'algorithms': [],
                'data_structures': [],
                'features': {}
            }
        
        lines = content.split('\n')
        code_lines = [l for l in lines if l.strip() and not l.strip().startswith('//')]
        
        # 分析各种特征
        algorithms = self._detect_algorithms(content)
        data_structures = self._detect_data_structures(content)
        features = self._extract_features(content)
        
        return {
            'lines_of_code': len(code_lines),
            'algorithms': algorithms,
            'data_structures': data_structures,
            'features': features,
            'includes': self._extract_includes(content),
            'functions': self._extract_functions(content),
        }
    
    def _detect_algorithms(self, content: str) -> List[Dict]:
        """
        检测代码中使用的算法
        
        Returns:
            检测到的算法列表，按置信度排序
        """
        results = []
        
        for algo_name, algo_info in self.patterns.items():
            score = 0
            matched_patterns = []
            
            for pattern in algo_info.get('patterns', []):
                matches = re.findall(pattern, content, re.IGNORECASE)
                if matches:
                    score += len(matches) * algo_info.get('weight', 1)
                    matched_patterns.extend(matches[:3])  # 只记录前3个匹配
            
            if score > 0:
                results.append({
                    'name': algo_name,
                    'score': score,
                    'confidence': min(score / 5, 1.0),  # 归一化置信度
                    'matches': matched_patterns
                })
        
        # 按置信度排序
        results.sort(key=lambda x: x['confidence'], reverse=True)
        return results
    
    def _detect_data_structures(self, content: str) -> List[Dict]:
        """检测使用的数据结构"""
        ds_patterns = {
            'array': {
                'patterns': [r'int\s+\w+\s*\[', r'long\s+long\s+\w+\s*\[', r'\w+\[\d+\]'],
                'weight': 1
            },
            'vector': {
                'patterns': [r'vector\s*<', r'\.push_back\s*\(', r'\.pop_back\s*\('],
                'weight': 2
            },
            'queue': {
                'patterns': [r'queue\s*<', r'\.push\s*\(', r'\.pop\s*\(', r'\.front\s*\('],
                'weight': 2
            },
            'stack': {
                'patterns': [r'stack\s*<', r'\.push\s*\(', r'\.pop\s*\(', r'\.top\s*\('],
                'weight': 2
            },
            'priority_queue': {
                'patterns': [r'priority_queue\s*<', r'\.push\s*\(', r'\.top\s*\('],
                'weight': 2
            },
            'set': {
                'patterns': [r'set\s*<', r'\.insert\s*\(', r'\.find\s*\('],
                'weight': 2
            },
            'map': {
                'patterns': [r'map\s*<', r'unordered_map\s*<', r'\[\s*\w+\s*\]\s*='],
                'weight': 2
            },
            'pair': {
                'patterns': [r'pair\s*<', r'make_pair\s*\(', r'\.first', r'\.second'],
                'weight': 1
            },
            'string': {
                'patterns': [r'string\s+\w+', r'\.substr\s*\(', r'\.find\s*\('],
                'weight': 1
            },
            'struct': {
                'patterns': [r'struct\s+\w+', r'class\s+\w+'],
                'weight': 1
            },
        }
        
        results = []
        for ds_name, ds_info in ds_patterns.items():
            score = 0
            for pattern in ds_info['patterns']:
                matches = re.findall(pattern, content, re.IGNORECASE)
                score += len(matches) * ds_info['weight']
            
            if score > 0:
                results.append({
                    'name': ds_name,
                    'score': score,
                    'confidence': min(score / 3, 1.0)
                })
        
        results.sort(key=lambda x: x['confidence'], reverse=True)
        return results
    
    def _extract_features(self, content: str) -> Dict:
        """提取代码特征"""
        features = {
            'has_main': bool(re.search(r'int\s+main\s*\(', content)),
            'has_fast_io': bool(re.search(r'ios::sync_with_stdio|cin\.tie', content)),
            'has_typedef': bool(re.search(r'typedef|using\s+\w+\s*=', content)),
            'has_memset': bool(re.search(r'memset\s*\(', content)),
            'has_sort': bool(re.search(r'sort\s*\(', content)),
            'has_recursion': bool(re.search(r'\w+\s*\([^)]*\)\s*\{[^}]*\w+\s*\([^)]*\)', content)),
            'loop_depth': self._calculate_loop_depth(content),
            'function_count': len(re.findall(r'\w+\s+\w+\s*\([^)]*\)\s*\{', content)),
        }
        return features
    
    def _calculate_loop_depth(self, content: str) -> int:
        """计算代码中最大循环嵌套深度"""
        lines = content.split('\n')
        max_depth = 0
        current_depth = 0
        
        for line in lines:
            stripped = line.strip()
            if re.match(r'(for|while)\s*\(', stripped):
                current_depth += 1
                max_depth = max(max_depth, current_depth)
            elif stripped == '}' and current_depth > 0:
                current_depth -= 1
        
        return max_depth
    
    def _extract_includes(self, content: str) -> List[str]:
        """提取头文件包含"""
        includes = re.findall(r'#include\s*[<"]([^>"]+)[>"]', content)
        return includes
    
    def _extract_functions(self, content: str) -> List[Dict]:
        """提取函数定义"""
        functions = []
        pattern = r'(\w+)\s+(\w+)\s*\(([^)]*)\)'
        matches = re.findall(pattern, content)
        
        for match in matches:
            return_type, name, params = match
            if return_type in ['int', 'void', 'long', 'bool', 'string', 'double', 'float']:
                functions.append({
                    'name': name,
                    'return_type': return_type,
                    'params': params.strip()
                })
        
        return functions[:10]  # 只返回前10个函数


class FileNameAnalyzer:
    """文件名分析器"""
    
    def __init__(self):
        from config import PLATFORM_PATTERNS
        self.platform_patterns = PLATFORM_PATTERNS
    
    def analyze(self, file_name: str) -> Dict:
        """
        分析文件名，提取平台、题号等信息
        
        Args:
            file_name: 文件名（不含路径）
            
        Returns:
            分析结果
        """
        result = {
            'platform': None,
            'problem_id': None,
            'title': None,
            'difficulty_hint': None,
        }
        
        # 移除扩展名
        name_without_ext = file_name.rsplit('.', 1)[0]
        
        # 过滤日期格式的文件名 (如 2026_2_23, 2026.2.11)
        if re.match(r'^20\d\d[\.\-_]', name_without_ext):
            # 日期文件 - 尝试从剩余部分提取有用信息
            remaining = re.sub(r'^20\d\d[\.\-_][\d]+[\.\-_]*', '', name_without_ext)
            remaining = re.sub(r'^20\d\d[\.\-_][\d]+[\.\-_]*', '', remaining)  # 双层日期
            if remaining:
                result['title'] = remaining
            else:
                result['title'] = name_without_ext
            return result
        
        # 检测平台
        for platform, info in self.platform_patterns.items():
            for pattern in info['patterns']:
                match = re.search(pattern, name_without_ext, re.IGNORECASE)
                if match:
                    result['platform'] = platform
                    problem_id = match.group(0)
                    
                    # 标准化题号（首字母大写）
                    if re.match(r'^[a-zA-Z]\d+$', problem_id):
                        problem_id = problem_id[0].upper() + problem_id[1:]
                    elif problem_id[:2].lower() in ('cf', 'at', 'sp', 'uv'):
                        problem_id = problem_id[:2].upper() + problem_id[2:]
                    elif problem_id[:3].lower() == 'uva':
                        problem_id = 'UVA' + problem_id[3:]
                    
                    result['problem_id'] = problem_id
                    
                    # 构建URL
                    url_template = info.get('url_template')
                    if url_template:
                        result['url'] = url_template.format(problem_id=problem_id)
                    
                    # 提取标题（题号后面的中文或英文）
                    remaining = name_without_ext[match.end():]
                    # 去掉分隔符
                    title = re.sub(r'^[\s_\-()（）]+', '', remaining)
                    # 去掉括号里的算法标签
                    title = re.sub(r'[(（][^)）]*[)）]$', '', title).strip()
                    if title:
                        result['title'] = title
                    
                    return result
        
        # 如果没有匹配到平台，尝试提取纯数字题号
        number_match = re.match(r'^(\d+|[A-Za-z])\s*[._\-]', name_without_ext)
        if number_match:
            result['problem_id'] = number_match.group(1)
        
        # 使用整个文件名作为标题
        result['title'] = name_without_ext
        
        return result


class CategoryClassifier:
    """分类器"""
    
    def __init__(self):
        self.categories = CATEGORIES
        self.code_analyzer = CodeAnalyzer()
        self.filename_analyzer = FileNameAnalyzer()
    
    def classify(self, file_path: Path, code_analysis: Dict = None) -> Dict:
        """
        对题目进行分类
        
        Args:
            file_path: 文件路径
            code_analysis: 代码分析结果（可选，如果没有会重新分析）
            
        Returns:
            分类结果
        """
        if code_analysis is None:
            code_analysis = self.code_analyzer.analyze_file(file_path)
        
        filename_analysis = self.filename_analyzer.analyze(file_path.name)
        
        # 计算每个分类的得分
        scores = defaultdict(float)
        
        # 1. 文件名关键词匹配
        file_name_lower = file_path.name.lower()
        for cat_key, cat_info in self.categories.items():
            keywords = cat_info.get('keywords', [])
            if isinstance(keywords, list):
                for keyword in keywords:
                    if isinstance(keyword, str) and keyword.lower() in file_name_lower:
                        scores[cat_key] += 3
            
            # 子分类匹配
            for sub_key, sub_info in cat_info.get('subcategories', {}).items():
                sub_keywords = sub_info.get('keywords', [])
                if isinstance(sub_keywords, list):
                    for keyword in sub_keywords:
                        if isinstance(keyword, str) and keyword.lower() in file_name_lower:
                            scores[cat_key] += 5
                            scores[f'{cat_key}:{sub_key}'] += 5
        
        # 2. 代码算法特征匹配
        for algo in code_analysis.get('algorithms', []):
            algo_name = algo['name']
            confidence = algo['confidence']
            
            # 算法到分类的映射
            algo_to_cat = {
                'bfs': 'search:bfs',
                'dfs': 'search:dfs',
                'dp': 'dp:linear',
                'union_find': 'graph:union_find',
                'segment_tree': 'data_structure:segment_tree',
                'bit': 'data_structure:bit',
                'binary_search': 'binary_greedy:binary',
                'dijkstra': 'graph:shortest',
                'quick_pow': 'math:power',
                'merge_sort': 'sorting:sort',
            }
            
            if algo_name in algo_to_cat:
                cat_path = algo_to_cat[algo_name]
                if ':' in cat_path:
                    cat, sub = cat_path.split(':')
                    scores[cat] += confidence * 4
                    scores[cat_path] += confidence * 4
                else:
                    scores[cat_path] += confidence * 4
        
        # 3. 数据结构特征
        for ds in code_analysis.get('data_structures', []):
            ds_name = ds['name']
            confidence = ds['confidence']
            
            if ds_name in ['queue'] and scores.get('search:bfs', 0) > 0:
                scores['search:bfs'] += confidence * 2
            elif ds_name in ['stack'] and scores.get('search:dfs', 0) > 0:
                scores['search:dfs'] += confidence * 2
        
        # 选择最佳分类
        best_category = 'other'
        best_subcategory = None
        best_score = 0
        
        for key, score in scores.items():
            if ':' in key:
                cat, sub = key.split(':')
                if scores[cat] > best_score:
                    best_score = scores[cat]
                    best_category = cat
                    best_subcategory = sub
            else:
                if score > best_score:
                    best_score = score
                    best_category = key
        
        return {
            'category': best_category,
            'subcategory': best_subcategory,
            'confidence': min(best_score / 10, 1.0),
            'all_scores': dict(scores),
            'filename_analysis': filename_analysis,
        }


# 便捷函数
def analyze_code_file(file_path: str) -> Dict:
    """分析代码文件的便捷函数"""
    analyzer = CodeAnalyzer()
    return analyzer.analyze_file(Path(file_path))


def classify_problem(file_path: str) -> Dict:
    """对题目进行分类的便捷函数"""
    classifier = CategoryClassifier()
    return classifier.classify(Path(file_path))


if __name__ == '__main__':
    # 测试
    import sys
    
    if len(sys.argv) > 1:
        test_file = sys.argv[1]
    else:
        test_file = r"E:\大学\大学\编程\Save-point\日常刷题\B3626_跳跃机器人(bfs).cpp"
    
    print(f'分析文件: {test_file}')
    print('=' * 50)
    
    # 代码分析
    analyzer = CodeAnalyzer()
    result = analyzer.analyze_file(Path(test_file))
    
    print(f'代码行数: {result["lines_of_code"]}')
    print(f'\n检测到的算法:')
    for algo in result['algorithms'][:5]:
        print(f'  - {algo["name"]}: 置信度 {algo["confidence"]:.2f}')
    
    print(f'\n检测到的数据结构:')
    for ds in result['data_structures'][:5]:
        print(f'  - {ds["name"]}: 置信度 {ds["confidence"]:.2f}')
    
    # 分类
    print('\n' + '=' * 50)
    classifier = CategoryClassifier()
    classification = classifier.classify(Path(test_file), result)
    
    print(f'分类结果:')
    print(f'  主分类: {classification["category"]}')
    print(f'  子分类: {classification["subcategory"]}')
    print(f'  置信度: {classification["confidence"]:.2f}')
    print(f'  平台: {classification["filename_analysis"]["platform"]}')
    print(f'  题号: {classification["filename_analysis"]["problem_id"]}')
