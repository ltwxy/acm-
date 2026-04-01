"""
平台题目爬取与分析脚本
自动爬取用户在各平台的已解题，并使用 AI 分析分类
"""
import json
import sys
from pathlib import Path

# 修复 Windows 控制台编码问题
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import DB_PATH, CONFIG_PATH
from core.database import Database
from core.platform_fetcher import PlatformFetcher
from openai import OpenAI


def analyze_problem_category(problem: dict, api_key: str) -> tuple:
    """
    使用 AI 分析题目的知识点分类

    Args:
        problem: 题目信息
        api_key: DeepSeek API Key

    Returns:
        (category, subcategory)
    """
    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")

    # 构建提示词
    prompt = f"""请分析以下编程题目的主要知识点分类：

平台: {problem['platform']}
题目ID: {problem['problem_id']}
标题: {problem['title']}
难度: {problem.get('difficulty', '未知')}
标签: {', '.join(problem.get('tags', []))}

请从以下分类中选择最匹配的一个：
- simulation: 模拟
- dp: 动态规划
- greedy: 贪心
- graph: 图论
- math: 数学
- data_structure: 数据结构
- string: 字符串
- search: 搜索
- geometry: 计算几何
- number_theory: 数论
- combinatorics: 组合数学

格式要求：只返回两个词，用空格分隔。例如："dp 区间dp" 或 "graph 最短路"
"""

    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=50,
            timeout=15  # 增加超时到 15 秒
        )

        result = response.choices[0].message.content.strip()

        # 解析结果
        parts = result.split()
        category = parts[0] if parts else None
        subcategory = parts[1] if len(parts) > 1 else None

        return category, subcategory

    except Exception as e:
        error_str = str(e)
        if 'timeout' in error_str.lower() or 'timed out' in error_str.lower():
            print(f"  ⚠️ AI 超时")
        elif 'connection' in error_str.lower():
            print(f"  ⚠️ 网络错误")
        else:
            print(f"  ⚠️ AI 失败: {error_str[:30]}")
        return None, None


def crawl_platform_problems():
    """爬取平台题目并入库"""
    import time

    # 加载配置
    if not CONFIG_PATH.exists():
        print("配置文件不存在！")
        return

    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        config = json.load(f)

    api_key = config.get('deepseek_api_key')
    accounts = config.get('platform_accounts', {})

    if not api_key:
        print("未配置 DeepSeek API Key！")
        return

    # 初始化
    db = Database()
    fetcher = PlatformFetcher()

    print("🚀 开始爬取平台题目...\n")

    # 洛谷
    if 'luogu' in accounts and accounts['luogu']:
        print(f"=== 🌙 爬取洛谷题目 ({accounts['luogu']}) ===")
        print("正在获取题目列表...")
        problems = fetcher.fetch_luogu_solved_problems(accounts['luogu'], limit=500)
        print(f"✓ 获取到 {len(problems)} 道已通过题目\n")

        # 先跳过已保存的题目
        existing = db.get_platform_problems()
        existing_ids = {f"{p['platform']}_{p['problem_id']}" for p in existing}
        new_problems = [p for p in problems if f"{p['platform']}_{p['problem_id']}" not in existing_ids]

        if new_problems:
            print(f"其中 {len(new_problems)} 道是新题目，需要分析")
            print("开始 AI 分析（这可能需要几分钟）...\n")

            saved = 0
            failed = 0
            for i, problem in enumerate(new_problems, 1):
                print(f"[{i}/{len(new_problems)}] {problem['problem_id']}: {problem['title'][:40]}", end=" ... ")

                # 使用 AI 分析分类
                category, subcategory = analyze_problem_category(problem, api_key)
                problem['category'] = category
                problem['subcategory'] = subcategory

                if category:
                    problem['solved_at'] = time.strftime('%Y-%m-%d %H:%M:%S')
                    # 保存到数据库
                    if db.save_platform_problem(problem):
                        print(f"✓ [{category}/{subcategory or '-'}]")
                        saved += 1
                    else:
                        print("✗ (保存失败)")
                        failed += 1
                else:
                    print("✗ (AI 分析失败)")
                    failed += 1

                # 每10题后暂停1秒，避免限流
                if i % 10 == 0:
                    print(f"\n已保存 {saved} 题，暂停1秒...\n")
                    time.sleep(1)

            print(f"\n🌙 洛谷：新增 {len(new_problems)} 题，成功保存 {saved} 题，失败 {failed} 题")
        else:
            print(f"所有题目都已存在，无需更新")

    # Codeforces
    if 'codeforces' in accounts and accounts['codeforces']:
        print(f"\n=== ⚡ 爬取 Codeforces 题目 ({accounts['codeforces']}) ===")
        print("正在获取题目列表...")
        problems = fetcher.fetch_codeforces_solved_problems(accounts['codeforces'], limit=500)
        print(f"✓ 获取到 {len(problems)} 道已通过题目\n")

        # 先跳过已保存的题目
        existing = db.get_platform_problems()
        existing_ids = {f"{p['platform']}_{p['problem_id']}" for p in existing}
        new_problems = [p for p in problems if f"{p['platform']}_{p['problem_id']}" not in existing_ids]

        if new_problems:
            print(f"其中 {len(new_problems)} 道是新题目，需要分析")
            print("开始 AI 分析（这可能需要几分钟）...\n")

            saved = 0
            failed = 0
            for i, problem in enumerate(new_problems, 1):
                print(f"[{i}/{len(new_problems)}] {problem['problem_id']}: {problem['title'][:40]}", end=" ... ")

                # 使用 AI 分析分类
                category, subcategory = analyze_problem_category(problem, api_key)
                problem['category'] = category
                problem['subcategory'] = subcategory

                if category:
                    problem['solved_at'] = time.strftime('%Y-%m-%d %H:%M:%S')
                    # 保存到数据库
                    if db.save_platform_problem(problem):
                        print(f"✓ [{category}/{subcategory or '-'}]")
                        saved += 1
                    else:
                        print("✗ (保存失败)")
                        failed += 1
                else:
                    print("✗ (AI 分析失败)")
                    failed += 1

                # 每10题后暂停1秒，避免限流
                if i % 10 == 0:
                    print(f"\n已保存 {saved} 题，暂停1秒...\n")
                    time.sleep(1)

            print(f"\n⚡ Codeforces：新增 {len(new_problems)} 题，成功保存 {saved} 题，失败 {failed} 题")
        else:
            print(f"所有题目都已存在，无需更新")

    print("\n✅ 爬取完成！")

    # 显示统计
    print("\n=== 📊 统计信息 ===")
    all_platform_problems = db.get_platform_problems()
    print(f"平台题目总数: {len(all_platform_problems)}")

    platform_stats = db.get_platform_category_stats()
    if platform_stats:
        print("\n分类统计:")
        for cat, count in sorted(platform_stats.items(), key=lambda x: x[1], reverse=True):
            print(f"  {cat}: {count} 题")


if __name__ == '__main__':
    crawl_platform_problems()
