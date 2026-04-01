"""
AI弱点识别与训练建议
基于DeepSeek API分析用户刷题数据，识别薄弱点并给出训练建议
"""
import json
import sys
import os
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime, timedelta

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.mastery_calculator import MasteryCalculator
from core.database import db


def get_deepseek_api_key() -> Optional[str]:
    """获取DeepSeek API Key"""
    # 1. 尝试从环境变量获取
    key = os.environ.get('DEEPSEEK_API_KEY')
    if key:
        return key

    # 2. 尝试从config.json获取
    try:
        config_path = project_root / 'config.json'
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                return config.get('deepseek_api_key')
    except Exception:
        pass

    return None


class WeaknessAnalyzer:
    """弱点分析器"""

    # OI/ACM双模板
    PROMPT_TEMPLATES = {
        'oi': {
            'focus': '知识体系完整性',
            'platforms': ['洛谷', 'USACO', 'NOIP'],
            'description': 'OI模式：注重知识体系完整性，覆盖全面，适合备战省赛/NOI',
        },
        'acm': {
            'focus': '思维敏捷性',
            'platforms': ['Codeforces', 'AtCoder', '牛客'],
            'description': 'ACM模式：注重思维转换速度，快速应变，适合CF/AtCoder竞赛',
        }
    }

    def __init__(self, user_id: int = 1):
        self.user_id = user_id
        self.mastery_calculator = MasteryCalculator(user_id)

    def identify_weaknesses(self, mastery_data: Dict, api_key: str, competition_mode: str = 'acm') -> Optional[Dict]:
        """
        识别用户弱点（供API调用的兼容方法）

        Args:
            mastery_data: 掌握度数据
            api_key: API密钥
            competition_mode: 竞赛模式

        Returns:
            分析结果字典
        """
        try:
            # 获取薄弱点和优势点
            weak_points = sorted(mastery_data.items(), key=lambda x: x[1]['mastery'])[:5]
            strong_points = sorted(mastery_data.items(), key=lambda x: x[1]['mastery'], reverse=True)[:5]

            # 获取统计信息（整合本地+平台数据）
            local_count = db.get_total_count()

            # 尝试获取平台数据
            platform_data = self._get_platform_progress()
            platform_count = sum(p.get('solved_count', 0) for p in platform_data.values())
            total_count = local_count + platform_count

            # 构建用户画像
            user_profile = {
                'total_problems': total_count,
                'local_problems': local_count,
                'platform_problems': platform_count,
                'weak_points': [{'knowledge': k, 'mastery': v['mastery']} for k, v in weak_points],
                'strong_points': [{'knowledge': k, 'mastery': v['mastery']} for k, v in strong_points],
                'platform_data': platform_data,
                'competition_mode': competition_mode,
            }

            # 调用AI分析
            if api_key:
                ai_analysis = self._call_deepseek(user_profile, api_key)
                return {
                    'user_profile': user_profile,
                    'analysis': ai_analysis.get('analysis', ''),
                    'recommendations': ai_analysis.get('recommendations', []),
                    'weaknesses': weak_points,
                }
            else:
                # 降级到规则分析
                return {
                    'user_profile': user_profile,
                    'analysis': self._fallback_analysis(user_profile),
                    'weaknesses': weak_points,
                }
        except Exception as e:
            import traceback
            traceback.print_exc()
            return None

    def analyze_weakness(self, competition_mode: str = 'oi', goals: List[str] = None) -> Dict:
        """
        分析用户弱点

        Args:
            competition_mode: 'oi' 或 'acm'
            goals: 用户目标列表

        Returns:
            分析结果字典
        """
        # 获取基础数据
        all_mastery = self.mastery_calculator.calculate_all()
        weak_points = self.mastery_calculator.get_weak_points(top_n=5)
        strong_points = self.mastery_calculator.get_strong_points(top_n=5)
        difficulty_mastery = self.mastery_calculator.get_mastery_by_difficulty()

        # 获取统计信息
        total_problems = db.get_total_count()
        recent_problems = self._get_recent_problems(days=30)

        # 构建用户画像
        user_profile = {
            'total_problems': total_problems,
            'recent_30_days': len(recent_problems),
            'weak_points': weak_points,
            'strong_points': strong_points,
            'difficulty_distribution': difficulty_mastery,
            'goals': goals or [],
            'competition_mode': competition_mode,
        }

        # 调用AI分析
        api_key = get_deepseek_api_key()
        if api_key:
            ai_analysis = self._call_deepseek(user_profile, api_key)
        else:
            ai_analysis = self._fallback_analysis(user_profile)

        return {
            'user_profile': user_profile,
            'ai_analysis': ai_analysis,
            'generated_at': datetime.now().isoformat(),
        }

    def _get_platform_progress(self) -> Dict:
        """获取平台刷题进度"""
        try:
            from core.platform_fetcher import PlatformFetcher
            import json

            # 读取配置
            config_path = Path(__file__).parent.parent / 'config.json'
            if not config_path.exists():
                return {}

            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)

            accounts = config.get('platform_accounts', {})
            cookies = config.get('platform_cookies', {})

            # 过滤空值
            accounts = {k: v for k, v in accounts.items() if v}
            cookies = {k: v for k, v in cookies.items() if v}

            if not accounts:
                return {}

            # 获取平台数据
            fetcher = PlatformFetcher()
            return fetcher.fetch_all(accounts, cookies)
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {}

    def _get_recent_problems(self, days: int = 30) -> List[Dict]:
        """获取最近N天的题目"""
        # 简化实现，实际需要数据库查询
        # 这里暂时返回所有题目
        return db.get_all_problems()

    def _call_deepseek(self, user_profile: Dict, api_key: str) -> Dict:
        """
        调用DeepSeek API进行分析

        Args:
            user_profile: 用户画像
            api_key: API密钥

        Returns:
            AI分析结果
        """
        try:
            import requests

            # 选择模板
            mode = user_profile.get('competition_mode', 'oi')
            template = self.PROMPT_TEMPLATES.get(mode, self.PROMPT_TEMPLATES['oi'])

            # 构建Prompt
            prompt = self._build_prompt(user_profile, template)

            # 调用API
            response = requests.post(
                'https://api.deepseek.com/v1/chat/completions',
                headers={
                    'Authorization': f'Bearer {api_key}',
                    'Content-Type': 'application/json',
                },
                json={
                    'model': 'deepseek-chat',
                    'messages': [
                        {
                            'role': 'system',
                            'content': f'你是算法竞赛教练，专攻{template["focus"]}。{template["description"]}'
                        },
                        {
                            'role': 'user',
                            'content': prompt
                        }
                    ],
                    'temperature': 0.7,
                    'max_tokens': 2000,
                },
                timeout=30
            )

            response.raise_for_status()
            result = response.json()

            # 解析AI回复
            ai_content = result['choices'][0]['message']['content']

            return {
                'analysis': ai_content,
                'source': 'deepseek',
                'model': 'deepseek-chat',
            }

        except Exception as e:
            print(f'[AI] DeepSeek调用失败: {e}')
            return self._fallback_analysis(user_profile)

    def _build_prompt(self, user_profile: Dict, template: Dict) -> str:
        """构建分析Prompt"""
        weak_points = user_profile['weak_points']
        strong_points = user_profile['strong_points']

        prompt = f"""分析学生数据：

【刷题历史】
- 总题数：{user_profile['total_problems']}
- 近30天完成：{user_profile['recent_30_days']}题

【知识点掌握度TOP5（优势）】
"""
        for sp in strong_points[:3]:
            prompt += f"* {sp['tag']}: 掌握度{sp['mastery_level']:.2f} ({sp['problem_count']}题)\n"

        prompt += "\n【知识点掌握度倒数TOP5（薄弱）】\n"
        for wp in weak_points[:3]:
            prompt += f"* {wp['tag']}: 掌握度{wp['mastery_level']:.2f} ({wp['problem_count']}题)\n"

        if user_profile.get('goals'):
            prompt += "\n【目标】\n"
            for i, goal in enumerate(user_profile['goals'], 1):
                prompt += f"- {goal}\n"

        prompt += """
【输出格式】（严格按此格式输出）
1. 当前水平评估（3句话，简洁明了）
2. 核心弱点TOP3（知识点 + 掌握度 + 原因分析）
3. 本周训练重点（3个方向，每个方向具体说明）
4. 不建议练习的题型（已掌握，浪费时间）

请直接输出，不要有任何其他内容。
"""

        return prompt

    def _fallback_analysis(self, user_profile: Dict) -> Dict:
        """
        降级分析（无API或API调用失败时）

        Args:
            user_profile: 用户画像

        Returns:
            降级分析结果
        """
        weak_points = user_profile['weak_points']
        strong_points = user_profile['strong_points']

        # 当前水平评估
        total = user_profile['total_problems']
        if total < 50:
            level = "初级水平，需要夯实基础"
        elif total < 150:
            level = "中级水平，知识点覆盖较全，但深度不够"
        else:
            level = "高级水平，建议向专项领域突破"

        # 核心弱点
        weakness_desc = []
        for wp in weak_points[:3]:
            reason = self._get_weakness_reason(wp)
            weakness_desc.append(f"{wp['tag']}: 掌握度{wp['mastery_level']:.2f} - {reason}")

        # 本周训练重点
        training_focus = []
        for wp in weak_points[:3]:
            training_focus.append(
                f"重点攻克{wp['tag']}，推荐每天1-2道{wp['tag']}题目，循序渐进"
            )

        # 不建议练习的题型
        avoid_desc = []
        for sp in strong_points[:2]:
            if sp['mastery_level'] > 0.8:
                avoid_desc.append(f"{sp['tag']}（已掌握，掌握度{sp['mastery_level']:.2f}）")

        analysis = f"""1. 当前水平评估
{level}

2. 核心弱点TOP3
{chr(10).join([f'- {w}' for w in weakness_desc])}

3. 本周训练重点
{chr(10).join([f'- {t}' for t in training_focus])}

4. 不建议练习的题型
{chr(10).join([f'- {a}' for a in avoid_desc]) if avoid_desc else '暂无'}
"""

        return {
            'analysis': analysis,
            'source': 'rule_based',
        }

    def _get_weakness_reason(self, weakness: Dict) -> str:
        """获取弱点原因"""
        mastery = weakness['mastery_level']
        count = weakness['problem_count']
        one_submit = weakness.get('one_submit_rate', 0)

        if count < 5:
            return "题目数量不足，缺乏系统训练"
        elif one_submit < 0.6:
            return "一次AC率低，稳定性差，需要多练"
        elif mastery < 0.6:
            return "掌握度低，需要加强基础练习"
        else:
            return "需要提升熟练度"


# 全局实例
weakness_analyzer = WeaknessAnalyzer()


if __name__ == '__main__':
    # 测试
    print("=== 弱点分析测试 ===\n")

    # OI模式测试
    result_oi = weakness_analyzer.analyze_weakness(competition_mode='oi')
    print(f"[OI模式] 分析时间: {result_oi['generated_at']}")
    print(f"\nAI分析结果:\n{result_oi['ai_analysis']['analysis']}")

    print("\n" + "="*80 + "\n")

    # ACM模式测试
    result_acm = weakness_analyzer.analyze_weakness(competition_mode='acm')
    print(f"[ACM模式] 分析时间: {result_acm['generated_at']}")
    print(f"\nAI分析结果:\n{result_acm['ai_analysis']['analysis']}")
