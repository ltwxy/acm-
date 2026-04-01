"""
Web界面 - Flask应用
提供统计面板和题目管理界面
"""
from flask import Flask, render_template, jsonify, request
import json
from pathlib import Path
from datetime import datetime, timedelta

# 添加父目录到路径
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.database import db
from core.daily_plan_generator import DailyPlanGenerator
from core.mastery_calculator import MasteryCalculator
from core.weakness_analyzer import WeaknessAnalyzer
from config import CATEGORIES
from core.backup_manager import BackupManager

app = Flask(__name__,
    template_folder='templates',
    static_folder='static'
)

# 英文知识点到中文的映射表
TAG_TRANSLATION = {
    # Codeforces 标签
    'implementation': '实现',
    'bitmasks': '位运算',
    'brute force': '暴力',
    'brute': '暴力',
    'combinatorics': '组合数学',
    'constructive algorithms': '构造算法',
    'constructive': '构造',
    'data structures': '数据结构',
    'dp': '动态规划',
    'dynamic programming': '动态规划',
    'divide and conquer': '分治',
    'games': '博弈论',
    'geometry': '几何',
    'graphs': '图论',
    'graph': '图论',
    'greedy': '贪心',
    'hashing': '哈希',
    'math': '数学',
    'mathematics': '数学',
    'number theory': '数论',
    'probabilities': '概率',
    'probability': '概率',
    'string suffix structures': '字符串后缀结构',
    'strings': '字符串',
    'string': '字符串',
    'trees': '树',
    'dfs': '深度优先搜索',
    'bfs': '广度优先搜索',
    'binary search': '二分查找',
    'sorting': '排序',
    'sort': '排序',
    'shortest paths': '最短路',
    'shortest path': '最短路',
    'dfs and similar': 'DFS及其变种',
    'bfs and similar': 'BFS及其变种',
    'number theory': '数论',
    'graph matchings': '二分图匹配',
    '2-sat': '2-SAT',
    'meet-in-the-middle': '折半搜索',
    'flow': '网络流',
    'flows': '网络流',
    'dsu': '并查集',
    'union-find': '并查集',
    'graphs': '图论',
    'greedy': '贪心',
    'hashing': '哈希',
    'math': '数学',
    'matrices': '矩阵',
    'number theory': '数论',
    'probabilities': '概率',
    'schedules': '调度',
    'shortest paths': '最短路',
    'sortings': '排序',
    'strings': '字符串',
    'ternary search': '三分查找',
    'trees': '树',
    'two pointers': '双指针',
    'fft': '快速傅里叶变换',
    'chinese remainder theorem': '中国剩余定理',
    'expression parsing': '表达式解析',
    'geometry': '几何',
    'graph matchings': '二分图匹配',
    'line sweep': '扫描线',
    'meet-in-the-middle': '折半搜索',
    'schedules': '调度',
    'sortings': '排序',
    'string suffix structures': '字符串后缀结构',
    'ternary search': '三分查找',
    'two pointers': '双指针',
}


@app.route('/')
def index():
    """主页"""
    return render_template('index.html')


@app.route('/guide')
def guide():
    """命名规范手册"""
    return render_template('guide.html')


@app.route('/settings')
def settings():
    """设置页面"""
    return render_template('settings.html')


@app.route('/plan')
def plan():
    """训练计划页面"""
    return render_template('plan.html')


@app.route('/api/stats')
def get_stats():
    """获取统计数据（本地+平台合并）"""
    local_total = db.get_total_count()
    local_solved = db.get_solved_count()
    platform_problems = db.get_platform_problems()
    platform_total = len(platform_problems)
    
    # 获取本地统计数据，并确保 key 是字符串
    by_category = {str(k): v for k, v in db.get_category_stats().items()}
    by_difficulty = {str(k): v for k, v in db.get_difficulty_stats().items()}
    
    # 合并平台题目的统计数据
    # 分类翻译：英文 -> 中文（与前端 CATEGORY_TRANSLATION 保持一致）
    CATEGORY_MAP = {
        'math': 'math', 'dp': 'dp', 'greedy': 'binary_greedy', 'graph': 'graph',
        'data structure': 'data_structure', 'data structures': 'data_structure',
        'string': 'string', 'strings': 'string', 'search': 'search',
        'sorting': 'sorting', 'binary search': 'search', 'two pointers': 'search',
        'brute force': 'search', 'brute': 'search', 'dfs': 'search', 'bfs': 'search',
        'implementation': 'other', 'simulation': 'other', 'constructive': 'other',
    }
    
    # 难度映射：Codeforces rating -> 1-10 统一难度
    def cf_rating_to_difficulty(rating):
        if not rating or rating <= 0:
            return 5  # 默认中等难度
        if rating < 900: return 2
        if rating < 1100: return 3
        if rating < 1300: return 4
        if rating < 1500: return 5
        if rating < 1700: return 6
        if rating < 1900: return 7
        if rating < 2100: return 8
        if rating < 2300: return 9
        return 10
    
    # 合并平台题目的分类和难度统计
    for p in platform_problems:
        # 分类
        cat = (p.get('category') or '').lower()
        mapped_cat = CATEGORY_MAP.get(cat, cat) if cat else 'other'
        # 如果本地已有该分类则累加，否则添加
        if mapped_cat in by_category:
            by_category[mapped_cat] += 1
        else:
            by_category[mapped_cat] = 1
        
        # 难度（platform_problems.difficulty 已经是 1-10 标准难度，直接使用）
        diff = p.get('difficulty', 5)  # 默认 5（中等难度）
        if not isinstance(diff, (int, float)) or diff <= 0:
            diff = 5
        diff_key = str(int(diff))
        if diff_key in by_difficulty:
            by_difficulty[diff_key] += 1
        else:
            by_difficulty[diff_key] = 1
    
    stats = {
        'total': local_total + platform_total,
        'local_total': local_total,
        'local_solved': local_solved,
        'platform_total': platform_total,
        'solved': local_solved,
        'by_category': by_category,
        'by_difficulty': by_difficulty,
        'by_platform': db.get_platform_stats(),
    }

    return jsonify(stats)


@app.route('/api/categories')
def get_categories():
    """获取分类信息"""
    result = {}
    for key, info in CATEGORIES.items():
        result[key] = {
            'name': info['name'],
            'color': info['color'],
            'subcategories': {
                k: v['name'] for k, v in info.get('subcategories', {}).items()
            }
        }
    return jsonify(result)


@app.route('/api/problems')
def get_problems():
    """获取题目列表（本地+平台合并）"""
    category = request.args.get('category')
    status = request.args.get('status')

    problems = db.get_all_problems(category=category, status=status)

    # 简化返回数据
    simplified = []
    for p in problems:
        # 构建题目URL（如果本地没有URL，则根据平台+ID生成）
        url = p.get('url')
        if not url and p.get('platform') and p.get('problem_id'):
            platform = p['platform']
            pid = p['problem_id']
            if platform == 'luogu':
                url = f'https://www.luogu.com.cn/problem/{pid}'
            elif platform == 'codeforces':
                url = f'https://codeforces.com/problemset/problem/{pid}'
            elif platform == 'usaco':
                url = f'https://usaco.org/index.php?page=viewproblem2&cpid={pid}'
            elif platform == 'atcoder':
                url = f'https://atcoder.jp/contests/{pid.split("_")[0]}/tasks/{pid}'
            elif platform == 'nowcoder':
                url = f'https://ac.nowcoder.com/acm/problem/{pid}'
            elif platform == 'leetcode':
                url = f'https://leetcode.com/problems/{pid}/'

        simplified.append({
            'id': p['id'],
            'file_name': p.get('file_name'),  # 平台题目可能没有 file_name
            'title': p['title'],
            'platform': p['platform'],
            'problem_id': p['problem_id'],
            'difficulty': p['difficulty'],
            'status': p.get('status', 'solved'),  # 平台题目默认为 solved
            'category': p['category'],
            'subcategory': p.get('subcategory'),
            'tags': p.get('tags'),
            'lines_of_code': p.get('lines_of_code'),
            'url': url,
            'created_at': p.get('created_at') or p.get('fetched_at'),  # 兼容两种时间字段
        })

    return jsonify(simplified)


@app.route('/api/problems/<int:problem_id>')
def get_problem_detail(problem_id):
    """获取题目详情"""
    problem = db.get_problem_by_id(problem_id)
    if problem:
        return jsonify(problem)
    return jsonify({'error': 'Not found'}), 404


@app.route('/api/problems/<int:problem_id>/status', methods=['POST'])
def update_problem_status(problem_id):
    """更新题目状态"""
    data = request.get_json()
    status = data.get('status')
    
    problem = db.get_problem_by_id(problem_id)
    if not problem:
        return jsonify({'error': 'Not found'}), 404
    
    updates = {'status': status}
    if status == 'solved':
        updates['solved_at'] = datetime.now().isoformat()
    
    db.update_problem(problem['file_path'], updates)
    return jsonify({'success': True})


@app.route('/api/organize', methods=['POST'])
def organize_files():
    """整理文件"""
    dry_run = request.args.get('dry_run', 'false').lower() == 'true'
    
    from core.file_manager import FileOrganizer
    from config import TARGET_DIR
    
    organizer = FileOrganizer(TARGET_DIR)
    result = organizer.organize_by_category(dry_run=dry_run)
    
    return jsonify(result)


@app.route('/api/scan', methods=['POST'])
def scan_files():
    """手动扫描文件"""
    from core.file_manager import FileWatcher
    from config import TARGET_DIR

    print('[扫描] 开始手动扫描文件...')

    try:
        watcher = FileWatcher(TARGET_DIR)
        count = watcher.scan_existing()

        print(f'[扫描] 扫描完成，处理了 {count} 个新文件')

        return jsonify({'scanned': count, 'success': True})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'scanned': 0, 'success': False, 'error': str(e)})


@app.route('/api/ai-advice', methods=['POST', 'GET'])
def get_ai_advice():
    """获取 AI 学习建议（整合本地+平台数据，去重）"""
    from core.ai_advisor import analyze_learning_advice

    # 检查是否有缓存的建议（30分钟内有效）
    cache_key = 'ai_advice'
    cache_file = Path(__file__).parent.parent / 'data' / 'ai_advice_cache.json'

    if cache_file.exists():
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                cache = json.load(f)
            import time
            if time.time() - cache.get('timestamp', 0) < 1800:  # 30分钟
                return jsonify(cache.get('data', {}))
        except:
            pass

    # 收集统计数据 - 纯本地数据，不依赖题库
    CONFIG_PATH = Path(__file__).parent.parent / 'config.json'
    config = {}
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            config = json.load(f)
    
    # 获取本地已做题目（仅从本地文件统计，不涉及题库）
    local_problems = db.get_all_problems()
    
    stats = {
        'total': db.get_total_count(),  # 仅本地总题数
        'solved': db.get_solved_count(),  # 仅本地已解决
        'by_category': db.get_category_stats(),  # 仅本地分类统计
        'by_difficulty': db.get_difficulty_stats(),  # 仅本地难度统计
        'recent_problems': local_problems[:20],  # 最近 20 道题目
        'solved_topics': list(set([p.get('category', '') for p in local_problems])),  # 已涉及的知识点
        # 用户目标信息
        'user_goals': config.get('user_goals', ''),
        'current_level': config.get('current_level', 'intermediate'),
        'competition_mode': config.get('competition_mode', 'acm'),
        # 目标难度区间
        'target_difficulty_min': config.get('target_difficulty_min', 4),
        'target_difficulty_max': config.get('target_difficulty_max', 7),
        # 重点提升方向
        'focus_areas': config.get('focus_areas', []),
    }

    # AI 根据用户情况直接分析推荐，不依赖题库
    result = analyze_learning_advice(stats)

    # 缓存成功的结果
    if result.get('success'):
        import time
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump({
                'timestamp': time.time(),
                'data': result
            }, f, ensure_ascii=False)

    return jsonify(result)


@app.route('/api/problems/<int:problem_id>/url', methods=['POST'])
def update_problem_url(problem_id):
    """手动更新题目 URL"""
    data = request.get_json()
    url = data.get('url')
    
    problem = db.get_problem_by_id(problem_id)
    if not problem:
        return jsonify({'error': 'Not found'}), 404
    
    db.update_problem(problem['file_path'], {'url': url})
    return jsonify({'success': True})


# ============== 配置管理 ==============
CONFIG_PATH = Path(__file__).parent.parent / 'config.json'

@app.route('/api/config')
def get_config():
    """获取当前配置"""
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            config = json.load(f)
    else:
        config = {}
    
    # 隐藏敏感信息
    safe_config = config.copy()
    if 'deepseek_api_key' in safe_config:
        safe_config['deepseek_api_key'] = '******' if safe_config['deepseek_api_key'] else ''
    
    return jsonify(safe_config)


@app.route('/api/config', methods=['POST'])
def update_config():
    """更新配置"""
    data = request.get_json()
    
    # 读取现有配置
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            config = json.load(f)
    else:
        config = {}
    
    # 更新字段
    if 'target_folder' in data:
        config['target_folder'] = data['target_folder']
    if 'competition_mode' in data:
        config['competition_mode'] = data['competition_mode']
    if 'training_mode' in data:
        config['training_mode'] = data['training_mode']
    if 'platform_accounts' in data:
        config['platform_accounts'] = data['platform_accounts']
    if 'platform_cookies' in data:
        config['platform_cookies'] = data['platform_cookies']
    if 'user_info' in data:
        config['user_info'] = data['user_info']
    if 'user_goals' in data:
        config['user_goals'] = data['user_goals']
    if 'current_level' in data:
        config['current_level'] = data['current_level']
    if 'target_difficulty_min' in data:
        config['target_difficulty_min'] = data['target_difficulty_min']
    if 'target_difficulty_max' in data:
        config['target_difficulty_max'] = data['target_difficulty_max']
    if 'focus_areas' in data:
        config['focus_areas'] = data['focus_areas']
    # 候选池设置
    if 'candidate_reset_hour' in data:
        config['candidate_reset_hour'] = data['candidate_reset_hour']
    if 'candidate_count' in data:
        config['candidate_count'] = data['candidate_count']
    if 'deepseek_api_key' in data and data['deepseek_api_key'] != '******':
        config['deepseek_api_key'] = data['deepseek_api_key']
    
    # 保存
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=4, ensure_ascii=False)
    
    return jsonify({'success': True})


@app.route('/api/platform-progress')
def get_platform_progress():
    """获取多平台刷题进度"""
    from core.platform_fetcher import PlatformFetcher

    # 读取配置中的账号
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            config = json.load(f)
    else:
        config = {}

    accounts = config.get('platform_accounts', {})
    cookies = config.get('platform_cookies', {})
    # 过滤空值
    accounts = {k: v for k, v in accounts.items() if v}
    cookies = {k: v for k, v in cookies.items() if v}

    if not accounts:
        return jsonify({'error': '请先在配置页面设置平台账号'})

    # 创建fetcher并传递cookies
    fetcher = PlatformFetcher()
    result = fetcher.fetch_all(accounts, cookies)
    return jsonify(result)


@app.route('/api/report')
def get_report():
    """生成综合分析报告（JSON）- 整合本地+平台数据"""
    from core.report_generator import ReportGenerator
    from core.platform_fetcher import PlatformFetcher

    # 获取平台数据
    platform_data = None
    try:
        if CONFIG_PATH.exists():
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                config = json.load(f)
        else:
            config = {}

        accounts = config.get('platform_accounts', {})
        cookies = config.get('platform_cookies', {})
        accounts = {k: v for k, v in accounts.items() if v}
        cookies = {k: v for k, v in cookies.items() if v}

        if accounts:
            fetcher = PlatformFetcher()
            platform_data = fetcher.fetch_all(accounts, cookies)
    except:
        pass

    # 生成报告（传递平台数据）
    gen = ReportGenerator(db, CONFIG_PATH)
    report = gen.generate_full_report(platform_data)
    return jsonify(report)


@app.route('/api/report/download')
def download_report():
    """下载 HTML 格式报告"""
    from core.report_generator import generate_report
    from flask import send_file
    import io

    report = generate_report(db, CONFIG_PATH)

    # 生成 HTML
    from core.report_generator import ReportGenerator
    gen = ReportGenerator(db, CONFIG_PATH)
    html = gen._render_html_report(report)

    # 返回文件
    output = io.BytesIO(html.encode('utf-8'))
    return send_file(
        output,
        mimetype='text/html',
        as_attachment=True,
        download_name=f'刷题分析报告_{datetime.now().strftime("%Y%m%d")}.html'
    )


# ============== 每日训练计划 API ==============

@app.route('/api/plan/<date>')
def get_plan(date):
    """获取指定日期的训练计划"""
    try:
        plan = db.get_daily_plan(date)
        if plan:
            return jsonify({'success': True, 'plan': plan})
        else:
            return jsonify({'success': False, 'error': '计划不存在'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


def _generate_ai_plan(mastery_data, config, today, training_mode, problem_count, topic_cycle):
    """
    使用 AI 基于用户本地数据生成每日训练计划。
    不依赖题库，AI 根据用户刷题情况推荐搜索关键词和练习方向。
    """
    from core.ai_chat import handle_chat_message

    # 获取已做题目
    solved_problems = db.get_all_problems()
    solved_titles = set()
    for p in solved_problems:
        if p.get('title'):
            solved_titles.add(p['title'])
        if p.get('file_name'):
            solved_titles.add(p['file_name'])

    # 构建 AI 推荐的 prompt（基于搜索关键词推荐）
    weak_points = sorted(mastery_data.items(), key=lambda x: x[1].get('mastery_level', 0))[:5]
    strong_points = sorted(mastery_data.items(), key=lambda x: x[1].get('mastery_level', 0), reverse=True)[:5]

    weak_desc = []
    for tag, info in weak_points[:5]:
        weak_desc.append(f"{tag}: 掌握度{info.get('mastery_level', 0):.2f} ({info.get('problem_count', 0)}题)")

    strong_desc = []
    for tag, info in strong_points[:3]:
        strong_desc.append(f"{tag}: 掌握度{info.get('mastery_level', 0):.2f} ({info.get('problem_count', 0)}题)")

    # 解析用户目标信息
    goals_raw = config.get('user_goals', '').strip()
    goals_list = [g.strip() for g in goals_raw.split('\n') if g.strip()] if goals_raw else []
    goals_text = '\n'.join([f"- {g}" for g in goals_list]) if goals_list else "暂未设置目标，请帮我全面提升"

    # 竞赛模式标签
    competition_mode_val = config.get('competition_mode', 'acm')
    competition_mode_label = 'ACM（注重解题速度和思维敏捷性）' if competition_mode_val == 'acm' else 'OI（注重知识体系完整性和代码正确性）'

    # 当前水平标签
    level_val = config.get('current_level', 'intermediate')
    level_map = {
        'beginner': '入门（刚开始学算法）',
        'basic': '基础（掌握基本语法和简单算法）',
        'intermediate': '中级（能独立解决普及组题目）',
        'advanced': '进阶（能解决部分提高组题目）',
        'expert': '高手（省选/NOI 水平）',
    }
    level_label = level_map.get(level_val, '中级')

    # 目标难度
    target_diff_min = config.get('target_difficulty_min', 4)
    target_diff_max = config.get('target_difficulty_max', 7)
    diff_name_map = {
        1: '普及-', 2: '普及', 3: '普及+', 4: '提高',
        5: '提高+', 6: '省选-', 7: '省选', 8: 'NOI-', 9: 'NOI', 10: 'NOI+'
    }
    target_diff_text = f"{diff_name_map.get(target_diff_min, f'难度{target_diff_min}')} ~ {diff_name_map.get(target_diff_max, f'难度{target_diff_max}')}"

    # 本地统计数据
    stats_data = {
        'total': db.get_total_count(),
        'solved': db.get_solved_count(),
        'by_category': db.get_category_stats(),
        'by_difficulty': db.get_difficulty_stats(),
        'solved_problems': solved_problems,
        'user_goals': goals_raw,
        'current_level': level_val,
        'competition_mode': competition_mode_val,
        'target_difficulty_min': target_diff_min,
        'target_difficulty_max': target_diff_max,
    }

    # AI 根据用户情况生成搜索关键词推荐
    prompt = f"""请为我今天推荐 {problem_count} 个训练方向，要求如下：

【我的训练目标】
{goals_text}

【我的竞赛模式】{competition_mode_label}
【我的当前水平】{level_label}
【我的目标难度】{target_diff_text}

【我的薄弱知识点】
{chr(10).join(weak_desc)}

【我的优势知识点】
{chr(10).join(strong_desc)}

【推荐要求】
1. 优先推荐薄弱知识点的练习方向（补漏）
2. 其次推荐已掌握知识点的进阶方向（拔高）
3. 每条推荐包含：训练方向、搜索关键词、预期收获
4. 难度应该比当前水平略高或符合目标难度
5. 推荐服务于我的训练目标，帮助我朝着目标前进
6. 如果目标是特定竞赛（如NOIP/省赛），优先推荐该竞赛常考题型

【输出格式】严格按以下 JSON 数组格式输出：
[
  {{
    "topic": "训练方向名称",
    "luogu_keywords": "洛谷搜索关键词",
    "cf_tags": "CF搜索标签",
    "priority": "HIGH/MEDIUM/LOW",
    "reason": "推荐理由（简短一句话）"
  }}
]

请直接输出 JSON 数组，不要加 ```json 代码块标记。"""

    ai_result = handle_chat_message(prompt, [], stats_data)

    tasks = []
    if ai_result.get('success'):
        try:
            # 尝试解析 AI 返回的 JSON
            reply = ai_result['reply'].strip()
            # 去掉可能的 markdown 代码块标记
            if reply.startswith('```'):
                lines = reply.split('\n')
                reply = '\n'.join(lines[1:-1]) if len(lines) > 2 else reply

            recommended = json.loads(reply)
            if isinstance(recommended, list) and len(recommended) > 0:
                for rec in recommended[:problem_count]:
                    priority = rec.get('priority', 'MEDIUM')
                    estimated_time = {
                        'HIGH': 45, 'MEDIUM': 30, 'LOW': 25
                    }.get(priority, 30)

                    # 生成搜索链接
                    luogu_keywords = rec.get('luogu_keywords', '')
                    luogu_url = f'https://www.luogu.com.cn/problem/list?keyword={luogu_keywords}' if luogu_keywords else ''

                    tasks.append({
                        'problem_id': f"ai_{len(tasks)}",
                        'problem_title': rec.get('topic', '今日训练方向'),
                        'platform': 'luogu',
                        'difficulty': 0,
                        'tags': [],
                        'priority': priority,
                        'reason': rec.get('reason', 'AI推荐'),
                        'estimated_time': estimated_time,
                        'url': luogu_url,
                        'search_keywords': {
                            'luogu': luogu_keywords,
                            'cf': rec.get('cf_tags', '')
                        },
                        'source': 'ai_keyword_recommend',
                        'status': 'pending',
                    })
        except (json.JSONDecodeError, TypeError, KeyError) as e:
            print(f'[AI推荐] JSON 解析失败: {e}, 回退到规则匹配')
            tasks = []

    # 如果 AI 推荐失败，回退到规则匹配（基于本地数据生成推荐）
    if not tasks:
        print('[AI推荐] 回退到规则匹配选题')
        tasks = _fallback_select_tasks(
            weak_points, strong_points, mastery_data,
            problem_count, goals_list, competition_mode_val
        )

    # 确定目标（结合用户自定义目标）
    if goals_list:
        goal = f"为目标奋斗：{goals_list[0]}"
    elif weak_points:
        primary = weak_points[0]
        goal = f"提升{primary[0]}能力（当前掌握度{primary[1].get('mastery_level', 0):.2f}）"
    else:
        goal = "保持刷题手感，稳步提升"

    # 计算难度等级（基于优先级估算）
    high_count = sum(1 for t in tasks if t.get('priority') == 'HIGH')
    avg_diff = 3 + high_count * 0.5 if tasks else 3
    if avg_diff < 3.5:
        difficulty_level = "简单"
    elif avg_diff < 4:
        difficulty_level = "适中"
    elif avg_diff < 4.5:
        difficulty_level = "中等偏上"
    else:
        difficulty_level = "困难"

    plan = {
        'date': today,
        'training_mode': training_mode,
        'goal': goal,
        'tasks': tasks,
        'total_estimated_time': sum(t.get('estimated_time', 30) for t in tasks),
        'difficulty_level': difficulty_level,
        'topic_cycle': topic_cycle,
        'introduce_new_topic': False,
        'created_at': datetime.now().isoformat(),
        'source': 'ai_keyword_recommend',
    }

    return plan


def _fallback_select_tasks(weak_points, strong_points, mastery_data,
                           problem_count, goals_list=None, competition_mode='acm'):
    """
    规则匹配回退方案：基于本地数据生成搜索关键词推荐。
    结合用户目标和竞赛模式优化推荐策略。
    不依赖任何题库。
    """
    import random

    tasks = []

    # 标准化标签映射
    tag_map = {
        '动态规划': ['dp', 'dynamic programming'],
        '贪心': ['greedy'],
        '图论': ['graphs', 'graph'],
        '搜索': ['dfs', 'bfs', 'dfs and similar', 'binary search'],
        '数学': ['math', 'mathematics', 'number theory'],
        '字符串': ['strings', 'string'],
        '数据结构': ['data structures'],
        '二分': ['binary search'],
        '数论': ['number theory'],
        '网络流': ['flows', 'flow'],
        '并查集': ['dsu'],
        '树': ['trees'],
        '构造': ['constructive algorithms', 'constructive'],
        '博弈': ['games'],
        '几何': ['geometry'],
    }

    # 根据用户目标推导优先知识点和搜索关键词
    goal_priority = []
    if goals_list:
        goals_text = ' '.join(goals_list)
        if any(kw in goals_text for kw in ['NOIP', '省赛', '提高组', '省一']):
            goal_priority = [
                ('动态规划', 'DP 状态压缩 省选', 'dp optimization'),
                ('图论', '最短路 生成树', 'shortest paths trees'),
                ('搜索', 'DFS BFS 搜索优化', 'dfs bfs optimization'),
                ('贪心', '贪心证明 构造', 'greedy construction'),
                ('数学', '数论 组合数学', 'math combinatorics'),
            ]
        elif any(kw in goals_text for kw in ['普及组', '省二']):
            goal_priority = [
                ('贪心', '贪心 模拟', 'greedy simulation'),
                ('动态规划', 'DP入门 线性DP', 'dp basics'),
                ('二分', '二分查找 二分答案', 'binary search'),
                ('搜索', 'DFS BFS 暴力搜索', 'dfs bfs brute force'),
                ('数学', '简单数论 模运算', 'math modulo'),
            ]
        if any(kw in goals_text for kw in ['CF', 'Codeforces', '蓝名', '紫名']):
            goal_priority = [
                ('贪心', '贪心 构造', 'greedy constructive'),
                ('动态规划', 'DP 优化', 'dp optimization'),
                ('实现', '实现 模拟', 'implementation'),
                ('数学', '数学 快速幂', 'math fast exponent'),
                ('构造', '构造算法', 'constructive algorithms'),
            ]
        if any(kw in goals_text for kw in ['图论', 'graphs']):
            goal_priority = [
                ('图论', '最短路 dijkstra', 'shortest paths dijkstra'),
                ('图论', '生成树 prim kruskal', 'mst spanning tree'),
                ('树', 'LCA 倍增', 'lca binary lifting'),
                ('图论', '网络流', 'flow network'),
                ('搜索', 'DFS 图上搜索', 'dfs graph'),
            ]
        if any(kw in goals_text for kw in ['动态规划', 'dp', 'DP']):
            goal_priority = [
                ('动态规划', 'DP 状态压缩', 'dp bitmask'),
                ('动态规划', 'DP 优化 单调队列', 'dp optimization monotone queue'),
                ('动态规划', '树形DP', 'dp on trees'),
                ('动态规划', '区间DP', 'dp intervals'),
                ('动态规划', 'DP 斜率优化', 'dp divide optimization'),
            ]
        if any(kw in goals_text for kw in ['AtCoder']):
            goal_priority = [
                ('动态规划', 'DP 入门', 'dp'),
                ('贪心', '贪心', 'greedy'),
                ('数学', '数学', 'math'),
                ('图论', '图论', 'graphs'),
            ]

    # 按优先级选题：先薄弱点，再巩固，最后拔高
    slots = []

    # 薄弱点
    for tag, info in weak_points[:3]:
        tag_str = str(tag) if tag else 'other'
        en_tags = tag_map.get(tag_str, [tag_str.lower()])
        luogu_kw = f"{tag_str} 提高"
        cf_tag = ','.join(en_tags[:2])
        slots.append(('HIGH', f"{tag_str}补漏 - 掌握度{info.get('mastery_level', 0):.2f}", luogu_kw, cf_tag))

    # 巩固（中等掌握度）
    intermediate = [m for m in mastery_data.values()
                    if 0.6 <= m.get('mastery_level', 0) < 0.8 and m.get('problem_count', 0) >= 3]
    if intermediate:
        sel = random.choice(intermediate)
        tag = sel['tag']
        tag_str = str(tag) if tag else 'other'
        en_tags = tag_map.get(tag_str, [tag_str.lower()])
        luogu_kw = f"{tag_str} 提高+"
        cf_tag = ','.join(en_tags[:2])
        slots.append(('MEDIUM', f"{tag_str}巩固 - 保持手感", luogu_kw, cf_tag))

    # 拔高
    for tag, info in strong_points[:1]:
        tag_str = str(tag) if tag else 'other'
        en_tags = tag_map.get(tag_str, [tag_str.lower()])
        luogu_kw = f"{tag_str} 省选"
        cf_tag = ','.join(en_tags[:2])
        slots.append(('LOW', f"{tag_str}拔高 - 你在此领域有优势", luogu_kw, cf_tag))

    # 填充任务
    attempts = 0
    idx = 0
    while len(tasks) < problem_count and attempts < problem_count * 3:
        attempts += 1
        if slots:
            priority, reason, luogu_kw, cf_tag = slots[idx % len(slots)]
            idx += 1

            # 生成搜索链接
            luogu_url = f'https://www.luogu.com.cn/problem/list?keyword={luogu_kw}'
            estimated_time = {'HIGH': 45, 'MEDIUM': 30, 'LOW': 25}.get(priority, 30)

            tasks.append({
                'problem_id': f"fallback_{len(tasks)}",
                'problem_title': reason.split(' - ')[0],
                'platform': 'luogu',
                'difficulty': 0,
                'tags': [],
                'priority': priority,
                'reason': reason,
                'estimated_time': estimated_time,
                'url': luogu_url,
                'search_keywords': {
                    'luogu': luogu_kw,
                    'cf': cf_tag
                },
                'source': 'fallback_keyword_recommend',
                'status': 'pending',
            })

    return tasks[:problem_count]


@app.route('/api/plan/generate', methods=['POST'])
def generate_plan():
    """生成今日训练计划（使用 AI 推荐题目）"""
    try:
        # 读取用户配置
        config_path = Path(__file__).parent.parent / 'config.json'
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        else:
            config = {}

        training_mode = config.get('training_mode', 'distributed')
        competition_mode = config.get('competition_mode', 'acm')

        # 从请求体中读取 problem_count、topic_cycle（前端传入）
        req_data = request.get_json(silent=True) or {}
        problem_count = int(req_data.get('problem_count', 3))
        problem_count = max(1, min(5, problem_count))
        topic_cycle = int(req_data.get('topic_cycle', config.get('topic_cycle', 3)))
        topic_cycle = max(1, min(5, topic_cycle))

        # 获取今日日期
        today = datetime.now().strftime('%Y-%m-%d')

        # 计算掌握度
        calculator = MasteryCalculator()
        mastery_data = calculator.calculate_all()

        # 使用 AI 基于本地数据推荐搜索关键词
        plan = _generate_ai_plan(mastery_data, config, today, training_mode,
                                 problem_count, topic_cycle)

        # 保存到数据库
        db.save_daily_plan(today, plan)

        return jsonify({'success': True, 'plan': plan})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/task/<int:task_id>/complete', methods=['POST'])
def complete_task(task_id):
    """标记任务为完成"""
    try:
        db.update_task_status(task_id, 'completed', 'success')
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/task/by-problem-id/complete', methods=['POST'])
def complete_task_by_problem_id():
    """通过problem_id标记任务为完成"""
    try:
        data = request.get_json()
        problem_id = data.get('problem_id')
        date = data.get('date', datetime.now().strftime('%Y-%m-%d'))

        # 获取计划并找到对应任务
        plan = db.get_daily_plan(date)
        if not plan:
            return jsonify({'success': False, 'error': '计划不存在'})

        # 更新tasks字段中的状态
        tasks = plan.get('tasks', [])
        for task in tasks:
            if task.get('problem_id') == problem_id:
                task['status'] = 'completed'
                break

        # 保存更新后的计划
        db.save_daily_plan(date, plan)
        return jsonify({'success': True})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)})



@app.route('/api/task/by-problem-id/delete', methods=['POST'])
def delete_task_by_problem_id():
    """通过problem_id删除任务"""
    try:
        data = request.get_json()
        problem_id = data.get('problem_id')
        date = data.get('date', datetime.now().strftime('%Y-%m-%d'))

        # 获取计划
        plan = db.get_daily_plan(date)
        if not plan:
            return jsonify({'success': False, 'error': '计划不存在'})

        # 删除 task_execution 表中的任务
        db.delete_task(plan['id'], problem_id)

        return jsonify({'success': True})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/task/<int:task_id>/fail', methods=['POST'])
def fail_task(task_id):
    """标记任务失败并调整难度"""
    try:
        data = request.get_json()
        reason = data.get('reason', '')
        adjustment = data.get('adjustment', 0)

        db.update_task_status(task_id, 'failed', reason, adjustment)

        # 如果有知识点，调整掌握度
        task = db.get_task_by_id(task_id)
        if task and task.get('knowledge'):
            knowledge = task['knowledge']
            current_mastery = db.get_knowledge_mastery(knowledge)
            if current_mastery:
                new_mastery = max(0, min(1, current_mastery + adjustment))
                db.update_knowledge_mastery(knowledge, mastery_score=new_mastery)

        return jsonify({'success': True})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/task/<int:task_id>/skip', methods=['POST'])
def skip_task(task_id):
    """跳过任务"""
    try:
        db.update_task_status(task_id, 'skipped', 'user_skipped')
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/task/add', methods=['POST'])
def add_manual_task():
    """手动添加任务"""
    try:
        data = request.get_json()
        date = data.get('date')
        task_data = data.get('task', {})

        if not date:
            return jsonify({'success': False, 'error': '日期不能为空'})

        # 确保当天的计划存在
        plan = db.get_daily_plan(date)
        if not plan:
            db.save_daily_plan(date, {
                'date': date,
                'mode': 'manual',
                'tasks': []
            })
            plan = db.get_daily_plan(date)

        # 构建任务数据
        task = {
            'problem_id': task_data.get('problem_id', task_data.get('title', '')),
            'problem_title': task_data.get('title', '未命名任务'),
            'platform': task_data.get('platform', 'local'),
            'difficulty': task_data.get('difficulty', 5),
            'tags': task_data.get('tags', []),
            'category': task_data.get('tags', [''])[0] if task_data.get('tags') else 'other',
            'reason': task_data.get('reason', ''),
            'url': task_data.get('url', ''),
            'estimated_time': task_data.get('estimated_time', '30分钟'),
            'status': 'pending',
            'source': 'manual',  # 标记为手动添加
            'is_new_topic': False
        }

        # 保存任务到数据库
        task_id = db.save_task(plan['id'], task)

        return jsonify({'success': True, 'task_id': task_id})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/chat', methods=['POST'])
def chat():
    """AI 对话接口 - 根据用户已刷题目生成候选题目池"""
    from core.ai_chat import handle_chat_message

    data = request.get_json()
    message = data.get('message', '').strip()
    history = data.get('history', [])

    if not message:
        return jsonify({'success': False, 'error': '消息不能为空'})

    try:
        # 加载用户配置
        config_path = Path(__file__).parent.parent / 'config.json'
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        else:
            config = {}
        
        # 收集统计数据作为上下文
        stats_data = {
            'total': db.get_total_count(),
            'solved': db.get_solved_count(),
            'by_category': db.get_category_stats(),
            'by_difficulty': db.get_difficulty_stats(),
            'recent_problems': db.get_all_problems()[:20],
            'solved_problems': db.get_solved_problems(),
            # 用户配置信息
            'user_goals': config.get('user_goals', ''),
            'current_level': config.get('current_level', 'intermediate'),
            'competition_mode': config.get('competition_mode', 'acm'),
            'target_difficulty_min': config.get('target_difficulty_min', 4),
            'target_difficulty_max': config.get('target_difficulty_max', 7),
            'focus_areas': config.get('focus_areas', []),
        }

        result = handle_chat_message(message, history, stats_data)

        # 如果成功且有候选题目，存储到数据库
        if result.get('success') and result.get('candidates'):
            count = db.add_candidate_problems_batch(result['candidates'])
            result['candidates_added'] = count

        return jsonify(result)
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': f'处理失败: {str(e)}\n{traceback.format_exc()}'
        })


@app.route('/api/candidates', methods=['GET'])
def get_candidates():
    """获取候选题目池"""
    try:
        limit = request.args.get('limit', 50, type=int)
        candidates = db.get_candidate_pool(limit)
        return jsonify({
            'success': True,
            'candidates': candidates,
            'total': len(candidates)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })


@app.route('/api/candidates/clear', methods=['POST'])
def clear_candidates():
    """清空候选题目池"""
    try:
        db.clear_candidate_pool()
        return jsonify({
            'success': True,
            'message': '候选题目池已清空'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })


@app.route('/api/candidates/mark', methods=['POST'])
def mark_candidate():
    """标记候选题目（已刷过/太难）"""
    try:
        data = request.get_json()
        platform = data.get('platform', '')
        problem_id = data.get('problem_id', '')
        action = data.get('action', 'solved')  # 'solved' 或 'too_hard'

        if not platform or not problem_id:
            return jsonify({
                'success': False,
                'error': '缺少 platform 或 problem_id'
            })

        db.mark_candidate_done(platform, problem_id, action)
        message_map = {
            'solved': '已刷过',
            'too_hard': '太难了',
            'cancel': '已取消标记'
        }
        message = message_map.get(action, '未知操作')
        return jsonify({
            'success': True,
            'message': f'题目已标记为 {message}'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })


@app.route('/api/platform-problem/delete', methods=['POST'])
def delete_platform_problem():
    """删除平台题目（从全部题目列表）"""
    try:
        data = request.get_json()
        platform = data.get('platform', '')
        problem_id = data.get('problem_id', '')

        if not platform or not problem_id:
            return jsonify({
                'success': False,
                'error': '缺少 platform 或 problem_id'
            })

        success = db.delete_platform_problem(platform, problem_id)
        if success:
            return jsonify({
                'success': True,
                'message': '题目已删除'
            })
        else:
            return jsonify({
                'success': False,
                'error': '题目不存在或删除失败'
            })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })


@app.route('/api/platform/sync', methods=['POST'])
def sync_platform():
    """
    增量同步平台题目

    支持增量同步：只获取新增的题目，跳过已存在的
    可选全量同步：传入 force=true 时执行全量同步

    请求参数:
        platform: 平台名称 (luogu/codeforces/atcoder/nowcoder/all)
        force: 是否强制全量同步 (true/false)
    """
    import time
    try:
        data = request.get_json() or {}
        platform = data.get('platform', 'all')
        force_full = data.get('force', False)

        # 导入必要的模块
        from core.platform_fetcher import PlatformFetcher
        from openai import OpenAI

        # 加载配置
        config_path = Path(__file__).parent.parent / 'config.json'
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        accounts = config.get('platform_accounts', {})
        api_key = config.get('deepseek_api_key')

        fetcher = PlatformFetcher()
        results = []

        # 确定要同步的平台列表
        platforms_to_sync = []
        if platform == 'all':
            platforms_to_sync = ['luogu', 'codeforces']
        elif platform in ['luogu', 'codeforces']:
            platforms_to_sync = [platform]
        else:
            return jsonify({
                'success': False,
                'error': f'不支持的平台: {platform}'
            })

        for plat in platforms_to_sync:
            username = accounts.get(plat)
            if not username:
                results.append({
                    'platform': plat,
                    'success': False,
                    'message': f'未配置 {plat} 用户名'
                })
                continue

            try:
                # 增量同步：只获取新增题目
                if not force_full:
                    # 获取已存在的题目ID
                    existing_ids = db.get_existing_problem_ids(plat)
                    print(f"增量同步 {plat}: 已存在 {len(existing_ids)} 道题目")

                    # 获取平台已刷题目
                    if plat == 'luogu':
                        problems = fetcher.fetch_luogu_solved_problems(username, limit=500)
                    elif plat == 'codeforces':
                        problems = fetcher.fetch_codeforces_solved_problems(username, limit=500)
                    else:
                        problems = []

                    # 过滤出新增题目
                    new_problems = []
                    for p in problems:
                        key = (plat.lower(), p['problem_id'].upper())
                        if key not in existing_ids:
                            new_problems.append(p)

                    problems_fetched = len(problems)
                    problems_added = 0

                    if new_problems:
                        print(f"发现 {len(new_problems)} 道新题目需要保存")
                        for p in new_problems:
                            p['platform'] = plat
                            # 使用平台原始标签（暂不通过AI分析）
                            p['category'] = p.get('tags', [''])[0] if p.get('tags') else None
                            p['subcategory'] = None
                            p['solved_at'] = time.strftime('%Y-%m-%d %H:%M:%S')
                            if db.save_platform_problem(p):
                                problems_added += 1
                            time.sleep(0.1)  # 避免请求过快

                    # 记录同步日志
                    sync_type = 'incremental'
                    db.save_sync_log(plat, sync_type, problems_fetched,
                                    problems_added, problems_fetched - problems_added,
                                    'success')

                    results.append({
                        'platform': plat,
                        'success': True,
                        'sync_type': sync_type,
                        'fetched': problems_fetched,
                        'added': problems_added,
                        'skipped': problems_fetched - problems_added
                    })

                # 全量同步：重新获取并保存所有题目
                else:
                    if plat == 'luogu':
                        problems = fetcher.fetch_luogu_solved_problems(username, limit=500)
                    elif plat == 'codeforces':
                        problems = fetcher.fetch_codeforces_solved_problems(username, limit=500)
                    else:
                        problems = []

                    problems_fetched = len(problems)
                    problems_added = 0

                    for p in problems:
                        p['platform'] = plat
                        p['category'] = p.get('tags', [''])[0] if p.get('tags') else None
                        p['subcategory'] = None
                        p['solved_at'] = time.strftime('%Y-%m-%d %H:%M:%S')
                        if db.save_platform_problem(p):
                            problems_added += 1
                        time.sleep(0.1)

                    sync_type = 'full'
                    db.save_sync_log(plat, sync_type, problems_fetched,
                                    problems_added, 0,
                                    'success')

                    results.append({
                        'platform': plat,
                        'success': True,
                        'sync_type': sync_type,
                        'fetched': problems_fetched,
                        'added': problems_added
                    })

            except Exception as e:
                db.save_sync_log(plat, 'incremental' if not force_full else 'full',
                                0, 0, 0, 'failed', str(e))
                results.append({
                    'platform': plat,
                    'success': False,
                    'message': str(e)
                })

        # 汇总结果
        total_added = sum(r.get('added', 0) for r in results if r.get('success'))
        return jsonify({
            'success': True,
            'results': results,
            'summary': f"新增 {total_added} 道题目"
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })


@app.route('/api/platform/sync-status', methods=['GET'])
def get_sync_status():
    """获取同步状态和历史"""
    try:
        # 获取各平台的题目数量
        platforms = ['luogu', 'codeforces']
        stats = {}
        for plat in platforms:
            count = db.get_platform_problem_count(plat)
            last_sync = db.get_last_sync_info(plat)
            stats[plat] = {
                'count': count,
                'last_sync': last_sync
            }

        # 获取最近同步历史
        history = db.get_sync_history(5)

        return jsonify({
            'success': True,
            'stats': stats,
            'history': history
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })


@app.route('/api/candidates/analyze-tags', methods=['POST'])
def analyze_solved_candidates():
    """批量分析已刷过题目的分类标签"""
    try:
        # 获取配置
        config_path = Path(__file__).parent.parent / 'config.json'
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        api_key = config.get('deepseek_api_key')
        
        if not api_key:
            return jsonify({
                'success': False,
                'error': '请先在设置中配置 DeepSeek API Key'
            })
        
        # 获取所有已刷过的题目
        solved_problems = db.get_solved_candidates()
        
        if not solved_problems:
            return jsonify({
                'success': True,
                'message': '没有需要分析的已刷过题目',
                'analyzed': 0
            })
        
        import requests
        analyzed_count = 0
        
        for problem in solved_problems:
            platform = problem.get('platform', '')
            problem_id = problem.get('problem_id', '')
            title = problem.get('title', '') or problem_id
            
            # 构建分析 prompt
            prompt = f"""请分析以下算法题目的分类标签（知识点）。

题目信息：
- 平台：{platform}
- 题号/标题：{title}

请从以下知识点中选择最合适的1-3个（用逗号分隔）：
数学, 动态规划, 贪心, 图论, 搜索, 二分, 字符串, 数据结构, 位运算, 模拟, 分治, 排序, BFS/DFS, Dijkstra, Floyd, SPFA, 并查集, 线段树, 树状数组, 单调栈, 单调队列, 状态压缩, 记忆化搜索, 拓扑排序, 最小生成树, 最大流, 博弈论, 容斥原理, 组合数学

只需要返回标签列表，不需要其他解释。格式：标签1, 标签2, 标签3"""
            
            try:
                response = requests.post(
                    'https://api.deepseek.com/chat/completions',
                    headers={
                        'Authorization': f'Bearer {api_key}',
                        'Content-Type': 'application/json'
                    },
                    json={
                        'model': 'deepseek-chat',
                        'messages': [
                            {'role': 'user', 'content': prompt}
                        ],
                        'temperature': 0.3,
                        'max_tokens': 200
                    },
                    timeout=30
                )
                
                if response.status_code == 200:
                    result = response.json()
                    tags_text = result['choices'][0]['message']['content'].strip()
                    
                    # 解析标签
                    tags = [t.strip() for t in tags_text.split(',') if t.strip()]
                    category = tags[0] if tags else 'other'
                    
                    # 更新数据库
                    db.update_candidate_tags(platform, problem_id, tags, category)
                    analyzed_count += 1
                    
            except Exception as e:
                print(f"分析题目 {problem_id} 失败: {e}")
                continue
        
        return jsonify({
            'success': True,
            'message': f'成功分析 {analyzed_count} 道题目',
            'analyzed': analyzed_count
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })


@app.route('/api/problems/analyze-tags', methods=['POST'])
def analyze_problems_tags():
    """批量分析本地题目的分类标签"""
    try:
        # 获取配置
        config_path = Path(__file__).parent.parent / 'config.json'
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        api_key = config.get('deepseek_api_key')

        if not api_key:
            return jsonify({
                'success': False,
                'error': '请先在设置中配置 DeepSeek API Key'
            })

        # 获取没有分类的题目
        problems = db.get_problems_without_category()

        if not problems:
            return jsonify({
                'success': True,
                'message': '所有题目已有分类，无需分析',
                'analyzed': 0
            })

        import requests
        analyzed_count = 0

        for problem in problems:
            pid = problem.get('id')
            title = problem.get('title', '')
            platform = problem.get('platform', '')
            problem_id = problem.get('problem_id', '')

            # 构建分析 prompt
            prompt = f"""请分析以下算法题目的分类标签（知识点）。

题目信息：
- 平台：{platform}
- 题号/标题：{title}

请从以下知识点中选择最合适的1-3个（用逗号分隔）：
数学, 动态规划, 贪心, 图论, 搜索, 二分, 字符串, 数据结构, 位运算, 模拟, 分治, 排序, BFS/DFS, Dijkstra, Floyd, SPFA, 并查集, 线段树, 树状数组, 单调栈, 单调队列, 状态压缩, 记忆化搜索, 拓扑排序, 最小生成树, 最大流, 博弈论, 容斥原理, 组合数学

只需要返回标签列表，不需要其他解释。格式：标签1, 标签2, 标签3"""

            try:
                response = requests.post(
                    'https://api.deepseek.com/chat/completions',
                    headers={
                        'Authorization': f'Bearer {api_key}',
                        'Content-Type': 'application/json'
                    },
                    json={
                        'model': 'deepseek-chat',
                        'messages': [
                            {'role': 'user', 'content': prompt}
                        ],
                        'temperature': 0.3,
                        'max_tokens': 200
                    },
                    timeout=30
                )

                if response.status_code == 200:
                    result = response.json()
                    tags_text = result['choices'][0]['message']['content'].strip()

                    # 解析标签
                    tags = [t.strip() for t in tags_text.split(',') if t.strip()]
                    category = tags[0] if tags else 'other'

                    # 更新数据库
                    db.update_problem_category(pid, category, tags)
                    analyzed_count += 1

            except Exception as e:
                print(f"分析题目 {title} 失败: {e}")
                continue

        return jsonify({
            'success': True,
            'message': f'成功分析 {analyzed_count} 道题目',
            'analyzed': analyzed_count
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })


@app.route('/api/user-stats')
def get_user_stats():
    """获取用户统计数据"""
    try:
        config_path = Path(__file__).parent.parent / 'config.json'
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        else:
            config = {}

        # 计算连续打卡天数
        streak_days = db.get_streak_days()

        # 获取弱点分析
        weaknesses_text = None
        calculator = MasteryCalculator()
        mastery_data = calculator.calculate_all()
        analyzer = WeaknessAnalyzer()

        # 检查缓存的分析结果
        analysis_cache = config.get('weakness_analysis_cache')
        if analysis_cache:
            weaknesses_text = analysis_cache.get('text')

        # 如果没有缓存，尝试生成
        if not weaknesses_text:
            api_key = config.get('deepseek_api_key')
            competition_mode = config.get('competition_mode', 'acm')
            weaknesses = analyzer.identify_weaknesses(mastery_data, api_key, competition_mode)
            if weaknesses and 'analysis' in weaknesses:
                weaknesses_text = weaknesses['analysis']

        return jsonify({
            'success': True,
            'streak_days': streak_days,
            'training_mode': config.get('training_mode', 'distributed'),
            'weakness_analysis': weaknesses_text
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)})


# ==================== 备份与恢复 API ====================

@app.route('/api/backup/create', methods=['POST'])
def create_backup():
    """创建数据库备份"""
    try:
        config_path = Path(__file__).parent.parent / 'config.json'
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        db_path = Path(config.get('db_path', Path(__file__).parent.parent / '刷题管理系统.db'))
        backup_manager = BackupManager(db_path)
        result = backup_manager.create_backup()
        
        return jsonify(result)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/backup/list', methods=['GET'])
def list_backups():
    """列出所有备份"""
    try:
        config_path = Path(__file__).parent.parent / 'config.json'
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        db_path = Path(config.get('db_path', Path(__file__).parent.parent / '刷题管理系统.db'))
        backup_manager = BackupManager(db_path)
        backups = backup_manager.list_backups()
        
        return jsonify({'success': True, 'backups': backups})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/backup/restore', methods=['POST'])
def restore_backup():
    """恢复指定备份"""
    try:
        data = request.get_json()
        name = data.get('name')
        
        if not name:
            return jsonify({'success': False, 'error': '请指定备份名称'})
        
        config_path = Path(__file__).parent.parent / 'config.json'
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        db_path = Path(config.get('db_path', Path(__file__).parent.parent / '刷题管理系统.db'))
        backup_manager = BackupManager(db_path)
        result = backup_manager.restore_backup(name)
        
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/backup/delete', methods=['POST'])
def delete_backup():
    """删除指定备份"""
    try:
        data = request.get_json()
        name = data.get('name')
        
        if not name:
            return jsonify({'success': False, 'error': '请指定备份名称'})
        
        config_path = Path(__file__).parent.parent / 'config.json'
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        db_path = Path(config.get('db_path', Path(__file__).parent.parent / '刷题管理系统.db'))
        backup_manager = BackupManager(db_path)
        result = backup_manager.delete_backup(name)
        
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


if __name__ == '__main__':
    app.run(debug=True, port=5000)
