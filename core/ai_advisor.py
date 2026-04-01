"""
AI 学习建议模块
通过 DeepSeek API 分析刷题情况，给出个性化的学习路线建议
包含知识点分析 + 智能题目推荐
"""
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple

import requests

# 修复 Windows 终端编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# API 配置
API_URL = "https://api.deepseek.com/chat/completions"
MODEL = "deepseek-chat"

# 从环境变量或配置文件读取 Key
def _get_api_key():
    """获取 DeepSeek API Key"""
    # 1. 环境变量
    key = os.environ.get('DEEPSEEK_API_KEY')
    if key:
        return key
    # 2. 配置文件
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.json')
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            cfg = json.load(f)
        return cfg.get('deepseek_api_key')
    return None


SYSTEM_PROMPT = """你是一位资深的竞赛编程教练，擅长分析选手的刷题数据并给出针对性的学习建议。

## 核心原则

**★★★ 完全基于用户已做题目的统计数据来分析，不编造具体题目 ★★★**
**★★★ 只推荐搜索关键词和训练方向，不推荐具体题目 ★★★**

## 用户背景

用户目标：{user_goals}
当前水平：{current_level}
竞赛模式：{competition_mode}
目标难度区间：{target_difficulty}
重点提升方向：{focus_areas}

## 难度评估标准（洛谷1-10标准）

| 难度 | 名称 | 水平描述 |
|------|------|----------|
| 1-2 | 入门/普及- | 刚入门，掌握基础语法 |
| 3 | 普及/提高- | 有一定基础，能解决简单算法题 |
| 4 | 普及+/提高 | 有较好的算法基础，能解决中等题 |
| 5 | 提高+/省选- | 算法扎实，能解决较难题 |
| 6-7 | 省选/NOI- | 算法深入，能解决省选级别题目 |
| 8-10 | NOI/NOI+/大师 | 顶级水平，解决国赛/大师赛难题 |

## 分析策略

### 1. 基于已掌握知识点的进阶路径

对于已掌握的知识点，推荐策略如下：

- **深度扩展**：推荐该知识点的高难度变种或优化技巧
- **交叉融合**：推荐与其他已掌握知识点结合的综合题
- **实际应用**：推荐该知识点在实际竞赛中的经典题型

### 2. 薄弱知识点的强化

- 从简单题开始建立信心
- 推荐2-3道同一知识点的梯度练习
- 提供该知识点的学习建议和常见套路

### 3. 知识盲区的开拓

- 优先选择与已掌握知识点相关的新知识
- 推荐入门教程或经典入门题
- 说明学习顺序和必要性

## 输出格式（严格遵循！）

### 水平分析
根据用户已做题目的数量、难度分布、知识点覆盖情况，分析：
- 当前整体水平
- 已掌握的知识点
- 薄弱环节
- 与目标的差距

### 目标难度推荐
用户目标难度区间：**{target_difficulty}**
- 给出达到目标需要重点练习的知识点
- 指出当前水平与目标的差距

### 薄弱知识点强化（重点方向：{focus_areas}）
根据用户已做题目分析薄弱点：
- 具体指出哪些知识点掌握不够
- 给出针对性的学习建议

### 下一步学习建议
- 推荐搜索关键词组合
- 给出洛谷和CF的搜索方向
- 建议学习顺序

## 排版协议（必须严格遵守！）

**严禁使用反引号或代码块包裹内容**
**禁止行首缩进，每行必须顶格**

**输出示例：**
1. 动态规划薄弱点强化
洛谷搜索：DP 状态压缩 提高
CF搜索：dp bitmask 1600
评析：你已掌握基础DP，但状态压缩DP是省选常见考点，建议每天做2道相关题

2. 图论最短路专题
洛谷搜索：最短路 SPFA dijkstra 提高+
CF搜索：shortest path dijkstra 1800
评析：最短路变形题是竞赛常考点，需要熟练掌握多种算法优化

## 搜索链接格式

- 洛谷搜索：https://www.luogu.com.cn/problem/list?keyword=关键词
- CF搜索：https://codeforces.com/problemset?order=BY_RATING_ASC&tags=标签

## 重要注意事项

- **★★★ 完全基于用户已做题目的统计数据来分析 ★★★**
- **根据知识点和难度给出搜索关键词和方向**
- **分析要具体，指出用户真正需要提升的地方**
- **推荐要实用，给出可操作的搜索和学习建议**

你面对的是一位高中竞赛选手（NOIP/省选方向），主要刷洛谷平台。"""


def analyze_learning_advice(stats_data: dict) -> dict:
    """
    调用 DeepSeek API 获取学习建议
    
    Args:
        stats_data: 统计数据，包含题目分类、难度分布等
        
    Returns:
        {
            'success': True/False,
            'advice': '建议文本',
            'error': '错误信息（失败时）'
        }
    """
    api_key = _get_api_key()
    if not api_key:
        return {
            'success': False,
            'advice': '',
            'error': '未配置 DeepSeek API Key。请在 config.json 中设置 deepseek_api_key，或设置环境变量 DEEPSEEK_API_KEY。'
        }
    
    # 构建用户消息
    user_message = _build_analysis_prompt(stats_data)
    
    # 注入用户目标信息到 system prompt
    user_goals = stats_data.get('user_goals', '')
    current_level = stats_data.get('current_level', 'intermediate')
    competition_mode = stats_data.get('competition_mode', 'acm')
    target_diff_min = stats_data.get('target_difficulty_min', 4)
    target_diff_max = stats_data.get('target_difficulty_max', 7)
    focus_areas = stats_data.get('focus_areas', [])
    
    # 转换当前水平为中文
    level_map = {
        'beginner': '入门（刚开始学算法）',
        'basic': '基础（掌握基本语法和简单算法）',
        'intermediate': '中级（能独立解决普及组题目）',
        'advanced': '进阶（能解决部分提高组题目）',
        'expert': '高手（省选/NOI 水平）',
    }
    level_text = level_map.get(current_level, '中级')
    competition_label = 'ACM' if competition_mode == 'acm' else 'OI'
    
    # 难度区间名称映射
    diff_name_map = {
        1: '普及- (CF 800)', 2: '普及 (CF 1000)', 3: '普及+ (CF 1200)',
        4: '提高 (CF 1400)', 5: '提高+ (CF 1500)', 6: '省选- (CF 1600)',
        7: '省选 (CF 1800)', 8: 'NOI- (CF 2000)', 9: 'NOI (CF 2200)', 10: 'NOI+ (CF 2400+)'
    }
    target_diff_text = f"{diff_name_map.get(target_diff_min, f'难度{target_diff_min}')} ~ {diff_name_map.get(target_diff_max, f'难度{target_diff_max}')}"
    focus_text = '、'.join(focus_areas) if focus_areas else '无特定方向，全面提升'
    
    # 替换 prompt 中的占位符
    effective_system_prompt = SYSTEM_PROMPT.format(
        user_goals=user_goals if user_goals else '暂未设置具体目标，全面提升算法能力',
        current_level=level_text,
        competition_mode=competition_label,
        target_difficulty=target_diff_text,
        focus_areas=focus_text
    )
    
    try:
        response = requests.post(
            API_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": MODEL,
                "messages": [
                    {"role": "system", "content": effective_system_prompt},
                    {"role": "user", "content": user_message}
                ],
                "temperature": 0.7,
                "max_tokens": 2000,
            },
            timeout=60  # 增加超时时间到 60 秒
        )

        if response.status_code == 200:
            result = response.json()
            advice = result['choices'][0]['message']['content']
            return {
                'success': True,
                'advice': advice.strip(),
                'error': None
            }
        else:
            error_msg = f'API 返回错误 {response.status_code}'
            try:
                error_detail = response.json()
                if 'error' in error_detail:
                    error_msg += f": {error_detail['error'].get('message', '')[:200]}"
            except:
                error_msg += f": {response.text[:200]}"
            return {
                'success': False,
                'advice': '',
                'error': error_msg
            }
    except requests.Timeout:
        return {
            'success': False,
            'advice': '',
            'error': '请求超时，请检查网络连接或稍后重试'
        }
    except requests.ConnectionError:
        return {
            'success': False,
            'advice': '',
            'error': '网络连接失败，请检查网络设置'
        }
    except Exception as e:
        return {
            'success': False,
            'advice': '',
            'error': f'请求失败: {str(e)}'
        }


def _build_analysis_prompt(stats_data: dict) -> str:
    """构建发送给 AI 的分析 prompt（增强版）"""
    # 难度名称映射
    diff_names = {
        1: '入门', 2: '普及-',
        3: '普及/提高-', 4: '普及+/提高',
        5: '提高+/省选-', 6: '省选/NOI-',
        7: 'NOI/NOI+', 8: '大师-',
        9: '大师', 10: '大师+'
    }

    lines = []
    lines.append("这是我目前的刷题数据统计，请分析并给出学习建议：\n")

    # 总体情况
    total = stats_data.get('total', 0)
    solved = stats_data.get('solved', 0)
    lines.append(f"📊 总体情况：共 {total} 道题，已解决 {solved} 道\n")

    # ========== 知识点掌握度分析 ==========
    category = stats_data.get('by_category', {})
    if category:
        lines.append("📚 知识点分布与掌握度分析：")
        lines.append("")

        # 分类知识点
        mastered = []       # 8题以上：熟练掌握
        learning = []       # 3-7题：初步掌握
        weak = []          # 1-2题：薄弱
        for cat, count in sorted(category.items(), key=lambda x: x[1], reverse=True):
            pct = count / total * 100 if total > 0 else 0
            if count >= 8:
                mastered.append((cat, count, pct))
            elif count >= 3:
                learning.append((cat, count, pct))
            elif count > 0:
                weak.append((cat, count, pct))

        # 已掌握知识点（进阶方向）
        if mastered:
            lines.append("✅ 已熟练掌握（建议进阶）：")
            for cat, count, pct in mastered:
                lines.append(f"  🌟 {cat}: {count}题 ({pct:.0f}%) - 可学习进阶技巧/优化/综合应用")
            lines.append('')

        if learning:
            lines.append("📝 初步掌握（建议巩固）：")
            for cat, count, pct in learning:
                lines.append(f"  ✓ {cat}: {count}题 ({pct:.0f}%) - 可增加题量/提升难度")
            lines.append('')

        if weak:
            lines.append("⚠️ 薄弱环节（需要强化）：")
            for cat, count, pct in weak:
                lines.append(f"  🔸 {cat}: {count}题 ({pct:.0f}%) - 需要系统训练")
            lines.append('')

        # 知识盲区
        common_categories = ['动态规划', '图论', '贪心', '数学', '字符串', '搜索', '数据结构',
                           '二分', '数论', '网络流', '并查集', '线段树', '树状数组',
                           '最短路', '最小生成树', '倍增', 'LCA', '拓扑排序', '强连通分量']
        missing = [cat for cat in common_categories if cat not in category]
        if missing:
            lines.append("🌟 尚未涉猎的知识点（建议从模板题开始）：")
            for cat in missing[:10]:  # 只显示前10个
                lines.append(f"  • {cat}")
            lines.append('')

    # ========== 难度分布 ==========
    difficulty = stats_data.get('by_difficulty', {})
    if difficulty:
        lines.append("🔥 难度分布与水平评估：")

        # 计算平均难度
        total_score = 0
        total_count = 0
        for diff, count in difficulty.items():
            total_score += float(diff) * count
            total_count += count
        avg_diff = total_score / total_count if total_count > 0 else 0

        # 找出主力难度
        max_diff = max(difficulty.items(), key=lambda x: x[1])

        lines.append(f"  【主力难度】{diff_names.get(max_diff[0], f'难度{max_diff[0]}')}（{max_diff[1]}题）")
        lines.append(f"  【平均难度】{diff_names.get(round(avg_diff), f'难度{avg_diff:.1f}')}")

        # ★★★ 明确推荐难度范围 ★★★
        # 计算应该推荐的难度（比主力难度高1-2级）
        recommend_diff = max_diff[0] + 1 if max_diff[0] < 10 else max_diff[0]
        lines.append(f"  【推荐难度】应推荐 {diff_names.get(recommend_diff, f'难度{recommend_diff}')} 或以上")
        if max_diff[0] >= 2:
            lines.append(f"  【重要】请优先推荐难度 >= {recommend_diff} 的题目！")

        # 分析难度分布
        diff_values = sorted(difficulty.keys())
        if len(diff_values) > 1:
            diff_range = diff_values[-1] - diff_values[0]
            if diff_range >= 5:
                lines.append(f"  【难度跨度】跨度较大，涉猎广泛")
            else:
                lines.append(f"  【难度跨度】集中在 {diff_names.get(diff_values[0])} ~ {diff_names.get(diff_values[-1])}")

        lines.append("  详细分布：")
        for diff, count in sorted(difficulty.items()):
            name = diff_names.get(diff, f'难度{diff}')
            pct = count / total * 100 if total > 0 else 0
            bar = '█' * int(pct / 3)
            lines.append(f"    {name}: {count}题 ({pct:.0f}%) {bar}")
        lines.append('')

    # ========== 平台分布 ==========
    platform = stats_data.get('by_platform', {})
    if platform:
        lines.append("🌐 平台分布：")
        for plat, count in sorted(platform.items(), key=lambda x: x[1], reverse=True):
            lines.append(f"  {plat}: {count}题")
        lines.append('')

    # ========== 已做题目列表（避免重复推荐） ==========
    solved_problems = stats_data.get('solved_problems', [])
    if solved_problems:
        lines.append("⚠️ 已做过的本地题目（请不要再推荐这些题目）：")
        # 提取有标题的已做题目
        solved_titles = [p.get('title') or p.get('file_name', '') for p in solved_problems if p.get('title') or p.get('file_name')]
        # 只列出前50个，避免prompt过长
        for title in sorted(set(solved_titles))[:50]:
            lines.append(f"  - {title}")
        lines.append('')
        lines.append('【重要】上面列出的所有已做题目请不要再推荐！\n')

    # ========== 可用题库信息（用于智能推荐） ==========
    available_problems = stats_data.get('available_problems', [])
    if available_problems:
        lines.append("📖 可用题库（数据库中的平台题目）：")

        # 按知识点分组统计
        tags_stats = {}
        for p in available_problems:
            tags = p.get('tags', [])
            if isinstance(tags, str):
                tags = json.loads(tags)
            for tag in tags:
                if tag not in tags_stats:
                    tags_stats[tag] = 0
                tags_stats[tag] += 1

        # 显示前20个知识点
        sorted_tags = sorted(tags_stats.items(), key=lambda x: x[1], reverse=True)[:20]
        lines.append("  【按知识点统计】")
        for tag, count in sorted_tags:
            lines.append(f"    {tag}: {count}题")

        # 按难度分组统计
        diff_stats = {}
        for p in available_problems:
            diff = p.get('difficulty', 0)
            if diff > 0:
                diff_stats[diff] = diff_stats.get(diff, 0) + 1

        if diff_stats:
            lines.append("  【按难度统计】")
            for diff, count in sorted(diff_stats.items()):
                name = diff_names.get(diff, f'难度{diff}')
                lines.append(f"    {name}: {count}题")

        lines.append('')
        lines.append('【重要】推荐题目必须来自上面的可用题库，不要编造题目！\n')
    else:
        lines.append("⚠️ 可用题库为空，无法推荐题目。请先在设置页面爬取平台题库。\n")

    # ========== 请求分析 ==========
    lines.append("请基于以上数据分析我的学习情况，给出具体的改进建议。按以下结构输出：")
    lines.append("")
    lines.append("### 📊 水平分析")
    lines.append("（2-3句话总结当前水平）")
    lines.append("")
    lines.append("### 💡 已掌握知识点（进阶方向）")
    lines.append("（对每个已熟练掌握的知识点，推荐2-3道进阶题）")
    lines.append("")
    lines.append("### ⚠️ 薄弱知识点（强化训练）")
    lines.append("（对每个薄弱知识点，推荐2-3道基础题）")
    lines.append("")
    lines.append("### 🌟 新知识点（模板题入门）")
    lines.append("（对知识盲区，推荐2-3道模板题/入门题）")
    lines.append("")
    if solved_problems:
        lines.append("⚠️ 重要提示：避开上面列出的所有已做题目！")
    lines.append("⚠️ 重要提示：推荐题目必须来自可用题库！")

    return '\n'.join(lines)


if __name__ == '__main__':
    # 测试
    test_data = {
        'total': 84,
        'solved': 84,
        'by_category': {'DP': 19, '搜索': 15, '二分/贪心': 9, '图论': 7, '字符串': 5, '数论': 4, '数据结构': 3, '模拟': 3, '其他': 19},
        'by_difficulty': {2: 23, 3: 24, 4: 7, 5: 30},
        'by_platform': {'luogu': 15, 'noip': 8, 'usaco': 1},
        'recent_problems': []
    }
    
    print("正在请求 DeepSeek AI 分析...")
    result = analyze_learning_advice(test_data)
    
    if result['success']:
        print("\n" + "="*60)
        print(result['advice'])
        print("="*60)
    else:
        print(f"失败: {result['error']}")
