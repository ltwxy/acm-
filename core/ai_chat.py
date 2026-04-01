"""
AI 对话模块
根据用户已刷题目和目标，生成候选题目池供用户选择
输出格式化的题目列表，系统解析后存入候选池
"""
import json
import os
import sys

import requests

# 修复 Windows 终端编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# API 配置
API_URL = "https://api.deepseek.com/chat/completions"
MODEL = "deepseek-chat"


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


SYSTEM_PROMPT = """你是一位资深的竞赛编程教练。

## 你的任务

根据用户提供的**已刷题目列表**和**目标难度**，为用户生成一份**候选题目池**。
你推荐的题目应该：
1. 来源于洛谷、Codeforces 等公开平台
2. 适合用户的目标难度区间
3. 覆盖用户薄弱或需要提升的知识点
4. 避开用户已经刷过的题目

## 用户信息

用户目标：{user_goals}
当前水平：{current_level}
目标难度区间：{target_difficulty}
重点提升方向：{focus_areas}

## 用户已刷过的题目（请务必避开这些！）

{solved_problems_list}

## 难度对照表（1-10 统一标准）

| 难度 | 洛谷 | CF Rating | 说明 |
|------|------|-----------|------|
| 2 | 入门 | 800 | 入门级 |
| 3 | 普及 | 900-1000 | 普及级 |
| 4 | 普及+ | 1100-1200 | 普及+/提高- |
| 5 | 提高 | 1300-1400 | 提高级 |
| 6 | 提高+ | 1500-1600 | 提高+/省选- |
| 7 | 省选- | 1700-1800 | 省选难度 |
| 8 | 省选 | 1900-2000 | 省选难度 |
| 9 | 省选+ | 2100-2300 | 省选+/NOI- |
| 10 | NOI | 2400+ | NOI水平 |

## 输出格式（严格遵循！）

首先，给出一段简短的分析，说明你为什么推荐这些题目。

然后，在 [[CANDIDATE_POOL]] 和 [[/CANDIDATE_POOL]] 之间，用以下格式列出推荐题目：

题目格式（每行一道题）：
[平台]|题目ID|[难度(归一化)]|题目名称|知识点标签|为什么推荐这道题|链接

示例：
洛谷|P1001|3|合唱队形|动态规划,序列DP|经典DP入门题，难度适中|https://www.luogu.com.cn/problem/P1001
CF|1690C|4|Gram and Memo|贪心,模拟|贴近竞赛风格的模拟题|https://codeforces.com/problemset/problem/1690/C

## 重要规则

1. **每个知识点推荐5-10道题目**，形成梯度
2. **优先推荐竞赛常考题型**
3. **难度要与目标难度匹配**
4. **避开已刷过的题目**
5. **必须包含真实可访问的题目链接**
6. **归一化难度**：必须使用 1-10 统一标准（详见上方对照表）。洛谷 1-7 → 乘以 1.43 并取整；CF rating 直接按表格转换。

## 排版规则

- **严禁使用反引号或代码块包裹内容**
- **禁止行首缩进，每行必须顶格**
- 格式标记 [[CANDIDATE_POOL]] 和 [[/CANDIDATE_POOL]] 必须单独一行

你面对的是一位高中竞赛选手（NOIP/省选方向）。"""


def handle_chat_message(message: str, history: list, stats_data: dict = None) -> dict:
    """
    处理对话消息，调用 DeepSeek API

    Args:
        message: 用户消息
        history: 对话历史 [{role, content}, ...]
        stats_data: 刷题统计数据

    Returns:
        {
            'success': True/False,
            'reply': 'AI回复内容（带分析文字）',
            'candidates': [{platform, problem_id, ...}, ...],  # 解析出的候选题目
            'error': '错误信息（失败时）'
        }
    """
    api_key = _get_api_key()
    if not api_key:
        return {
            'success': False,
            'reply': '',
            'candidates': [],
            'error': '未配置 DeepSeek API Key。请在 config.json 中设置 deepseek_api_key。'
        }

    # 获取用户配置信息
    user_goals = stats_data.get('user_goals', '') if stats_data else ''
    current_level = stats_data.get('current_level', 'intermediate') if stats_data else 'intermediate'
    competition_mode = stats_data.get('competition_mode', 'acm') if stats_data else 'acm'
    target_diff_min = stats_data.get('target_difficulty_min', 4) if stats_data else 4
    target_diff_max = stats_data.get('target_difficulty_max', 7) if stats_data else 7
    focus_areas = stats_data.get('focus_areas', []) if stats_data else []

    # 转换中文标签
    level_map = {
        'beginner': '入门（刚开始学算法）',
        'basic': '基础（掌握基本语法和简单算法）',
        'intermediate': '中级（能独立解决普及组题目）',
        'advanced': '进阶（能解决部分提高组题目）',
        'expert': '高手（省选/NOI 水平）',
    }
    competition_label = 'ACM' if competition_mode == 'acm' else 'OI'

    diff_name_map = {
        3: '普及/提高- (CF 800-1200)',
        4: '普及+/提高 (CF 1200-1400)',
        5: '提高+/省选- (CF 1400-1600)',
        6: '省选- (CF 1600-1800)',
        7: '省选 (CF 1800-2000)',
    }
    target_diff_text = f"{diff_name_map.get(target_diff_min, f'难度{target_diff_min}')} ~ {diff_name_map.get(target_diff_max, f'难度{target_diff_max}')}"
    focus_text = '、'.join(focus_areas) if focus_areas else '无特定方向，全面提升'

    # 构建已刷题目列表
    solved_problems = stats_data.get('solved_problems', []) if stats_data else []
    solved_list = _format_solved_problems(solved_problems)

    # 格式化系统提示
    effective_system_prompt = SYSTEM_PROMPT.format(
        user_goals=user_goals if user_goals else '暂未设置具体目标，全面提升算法能力',
        current_level=level_map.get(current_level, '中级'),
        target_difficulty=target_diff_text,
        focus_areas=focus_text,
        solved_problems_list=solved_list
    )

    # 构建消息列表
    messages = [
        {"role": "system", "content": effective_system_prompt}
    ]

    # 添加历史对话（只保留最近3轮）
    messages.extend(history[-6:])

    # 添加当前消息
    messages.append({"role": "user", "content": message})

    try:
        response = requests.post(
            API_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": MODEL,
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 3000,
            },
            timeout=90
        )

        if response.status_code == 200:
            result = response.json()
            reply = result['choices'][0]['message']['content']

            # 解析候选题目
            candidates = _parse_candidates(reply)

            return {
                'success': True,
                'reply': reply.strip(),
                'candidates': candidates,
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
                'reply': '',
                'candidates': [],
                'error': error_msg
            }
    except requests.Timeout:
        return {
            'success': False,
            'reply': '',
            'candidates': [],
            'error': '请求超时，请检查网络连接或稍后重试'
        }
    except requests.ConnectionError:
        return {
            'success': False,
            'reply': '',
            'candidates': [],
            'error': '网络连接失败，请检查网络设置'
        }
    except Exception as e:
        return {
            'success': False,
            'reply': '',
            'candidates': [],
            'error': f'请求失败: {str(e)}'
        }


def _format_solved_problems(problems: list) -> str:
    """格式化已刷题目列表"""
    if not problems:
        return "暂无已刷题目记录"

    lines = []
    for i, p in enumerate(problems[:50]):  # 最多显示50道
        platform = p.get('platform', 'unknown')
        pid = p.get('problem_id', '?')
        title = p.get('title', '')
        difficulty = p.get('difficulty', '?')
        tags = ','.join(p.get('tags', [])[:3]) if p.get('tags') else ''
        lines.append(f"{platform.upper()}|{pid}|{difficulty}|{title}|{tags}")

    if len(problems) > 50:
        lines.append(f"\n...（共 {len(problems)} 道题目，以上显示前50道）")

    return '\n'.join(lines)


def _parse_candidates(reply: str) -> list:
    """
    解析 AI 回复中的候选题目

    格式：平台|题目ID|难度|名称|标签|原因|链接
    """
    candidates = []

    # 查找 [[CANDIDATE_POOL]] 和 [[/CANDIDATE_POOL]] 之间的内容
    import re
    match = re.search(r'\[\[CANDIDATE_POOL\]\]([\s\S]*?)\[\[/CANDIDATE_POOL\]\]', reply)

    if not match:
        return candidates

    pool_text = match.group(1).strip()
    lines = pool_text.split('\n')

    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'):
            continue

        # 解析格式：平台|题目ID|难度|名称|标签|原因|链接
        parts = line.split('|')
        if len(parts) < 7:
            continue

        try:
            platform = parts[0].strip().lower()
            problem_id = parts[1].strip()
            raw_difficulty = float(parts[2].strip()) if parts[2].strip().replace('.', '').isdigit() else None
            title = parts[3].strip()
            tags = [t.strip() for t in parts[4].split(',') if t.strip()]
            reason = parts[5].strip()
            url = parts[6].strip()

            # 统一转换为 1-10 标准难度
            diff_norm = _normalize_difficulty(raw_difficulty, platform)

            # 生成链接
            if not url or url == '#':
                if 'luogu' in platform.lower() or 'lg' in platform.lower():
                    url = f"https://www.luogu.com.cn/problem/{problem_id}"
                elif 'cf' in platform.lower() or 'codeforces' in platform.lower():
                    # CF 格式: 1234A
                    url = f"https://codeforces.com/problemset/problem/{problem_id}"

            candidates.append({
                'platform': platform,
                'problem_id': problem_id,
                'title': title,
                'difficulty': diff_norm,  # 统一使用 1-10 标准难度
                'difficulty_normalized': diff_norm,
                'tags': tags,
                'category': tags[0] if tags else 'other',
                'url': url,
                'reason': reason,
                'priority': 1
            })
        except Exception as e:
            continue

    return candidates


def _normalize_difficulty(difficulty: float, platform: str) -> int:
    """
    将各平台的难度统一转换为 1-10 标准难度

    Args:
        difficulty: 原始难度值
        platform: 平台标识

    Returns:
        1-10 标准难度
    """
    if difficulty is None or difficulty <= 0:
        return 5  # 未知难度默认为中等

    platform = platform.lower()

    if 'luogu' in platform or 'lg' in platform:
        # 洛谷难度 → 1-10 标准难度
        # 入门(1)→1, 普及-(2)→2, 普及/(3)→3, 普及+(4)→4, 提高(5)→5, 提高+(6)→6, 省选(7)→7, NOI(8)→8, NOI+(9)→10
        luogu_map = {1: 1, 2: 2, 3: 3, 4: 4, 5: 5, 6: 6, 7: 7, 8: 8, 9: 10}
        if difficulty in luogu_map:
            return luogu_map[difficulty]
        return max(1, min(10, difficulty))

    elif 'cf' in platform or 'codeforces' in platform:
        # CF rating → 1-10
        if difficulty < 800:
            return 2
        elif difficulty >= 2400:
            return 10
        else:
            # 公式: (rating - 500) / 200 + 1
            return max(2, min(10, round((difficulty - 500) / 200 + 1)))

    # 其他平台，假设已经是 1-10 范围
    return max(1, min(10, int(difficulty)))
