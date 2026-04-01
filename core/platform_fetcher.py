"""
多平台用户进度爬虫
从洛谷、Codeforces、牛客等平台获取用户刷题数据
"""
import requests
import json
import re
from typing import Dict, List, Optional
from datetime import datetime
import time


class PlatformFetcher:
    """多平台数据抓取器"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    @staticmethod
    def normalize_difficulty(difficulty: int, platform: str) -> int:
        """
        将各平台的难度统一转换为 1-10 标准难度
        
        Args:
            difficulty: 原始难度值
            platform: 平台标识 (luogu/codeforces)
        
        Returns:
            1-10 标准难度
        """
        if difficulty is None or difficulty <= 0:
            return 5  # 未知难度默认为中等
        
        if platform == 'luogu':
            # 洛谷难度 1-7 → 1-10: 1→1, 2→3, 3→4, 4→6, 5→7, 6→9, 7→10
            # 映射表
            luogu_map = {1: 1, 2: 3, 3: 4, 4: 6, 5: 7, 6: 9, 7: 10}
            return luogu_map.get(difficulty, max(1, min(10, round(difficulty * 1.43))))
        
        elif platform == 'codeforces':
            # Codeforces rating → 1-10: 800→3, 1000→4, 1200→5, 1400→6, ...
            # 公式: (rating - 500) / 200 + 1
            if difficulty < 800:
                return 2
            elif difficulty >= 2400:
                return 10
            else:
                return max(2, min(10, round((difficulty - 500) / 200 + 1)))
        
        # 其他平台默认返回
        return max(1, min(10, difficulty))
    
    # ============== 洛谷 ==============
    def fetch_luogu(self, username: str, api_key: str = None) -> Dict:
        """
        获取洛谷用户数据

        策略: 通过搜索API获取UID,然后解析用户主页的JSON数据

        Returns:
            {
                'username': str,
                'rating': int,
                'solved_count': int,
                'submission_count': int,
                'rank': str,
                'badges': list,
                'recent_problems': list
            }
        """
        try:
            # 步骤1: 通过用户名搜索获取UID
            uid_url = f"https://www.luogu.com.cn/api/user/search?keyword={username}"
            uid_resp = self.session.get(uid_url, timeout=10)

            if uid_resp.status_code != 200:
                return {'error': f'无法搜索用户 {username} (HTTP {uid_resp.status_code})', 'platform': 'luogu'}

            uid_data = uid_resp.json()

            # 检查搜索结果
            if not uid_data.get('users') or len(uid_data['users']) == 0:
                return {'error': f'未找到用户 {username}', 'platform': 'luogu'}

            # 获取第一个匹配用户的UID
            uid = uid_data['users'][0].get('uid')
            if not uid:
                return {'error': f'无法获取用户 {username} 的UID', 'platform': 'luogu'}

            # 步骤2: 使用UID访问用户主页,获取JSON数据
            user_url = f"https://www.luogu.com.cn/user/{uid}"
            user_resp = self.session.get(user_url, timeout=10)

            if user_resp.status_code != 200:
                return {'error': f'无法访问用户主页 (HTTP {user_resp.status_code})', 'platform': 'luogu'}

            html = user_resp.text

            # 步骤3: 从script标签中解析JSON数据
            json_match = re.search(r'<script[^>]*type="application/json"[^>]*>(\{.+?\})</script>', html, re.DOTALL)
            if not json_match:
                return {'error': '无法解析用户数据', 'platform': 'luogu'}

            try:
                data = json.loads(json_match.group(1))
            except json.JSONDecodeError:
                return {'error': '用户数据解析失败', 'platform': 'luogu'}

            # 步骤4: 提取用户信息
            user_data = data.get('data', {}).get('user', {})
            if not user_data:
                return {'error': '用户数据格式异常', 'platform': 'luogu'}

            # 获取rating (eloValue字段)
            elo_value = user_data.get('eloValue')
            rating = elo_value if elo_value and elo_value > 0 else 0

            return {
                'platform': 'luogu',
                'username': username,
                'uid': uid,
                'rating': rating,
                'solved_count': user_data.get('passedProblemCount', 0),
                'submission_count': user_data.get('submittedProblemCount', 0),
                'rank': self._get_luogu_rank(rating),
                'ranking': user_data.get('ranking', 0),
                'badges': user_data.get('badge', []) if user_data.get('badge') else [],
                'color': user_data.get('color', ''),
                'fetched_at': datetime.now().isoformat()
            }

        except requests.exceptions.Timeout:
            return {'error': '请求超时，请检查网络连接', 'platform': 'luogu'}
        except requests.exceptions.RequestException as e:
            return {'error': f'网络请求失败: {str(e)}', 'platform': 'luogu'}
        except Exception as e:
            return {'error': f'未知错误: {str(e)}', 'platform': 'luogu'}
    
    def _get_luogu_rank(self, rating: int) -> str:
        """根据分数获取洛谷段位"""
        if rating >= 2600: return "LGM"
        elif rating >= 2400: return "IGM"
        elif rating >= 2100: return "GM"
        elif rating >= 1900: return "IM"
        elif rating >= 1700: return "M"
        elif rating >= 1500: return "CM"
        elif rating >= 1300: return "Expert"
        elif rating >= 1200: return "Pupil"
        else: return "Newbie"

    def fetch_luogu_solved_problems(self, username: str, limit: int = 500) -> List[Dict]:
        """
        获取洛谷用户已通过的题目列表及详情

        Args:
            username: 用户名
            limit: 最多获取多少题

        Returns:
            题目列表 [{'problem_id': 'P1001', 'title': '...', 'difficulty': 1, 'tags': [...]}]
        """
        try:
            # 先获取 UID
            uid_url = f"https://www.luogu.com.cn/api/user/search?keyword={username}"
            uid_resp = self.session.get(uid_url, timeout=10)

            if uid_resp.status_code != 200:
                return []

            uid_data = uid_resp.json()
            if not uid_data.get('users'):
                return []

            uid = uid_data['users'][0].get('uid')
            if not uid:
                return []

            # 获取用户主页数据
            user_url = f"https://www.luogu.com.cn/user/{uid}"
            user_resp = self.session.get(user_url, timeout=10)

            if user_resp.status_code != 200:
                return []

            html = user_resp.text

            # 解析 JSON 数据
            json_match = re.search(r'<script[^>]*type="application/json"[^>]*>(\{.+?\})</script>', html, re.DOTALL)
            if not json_match:
                return []

            data = json.loads(json_match.group(1))
            user_data = data.get('data', {}).get('user', {})

            # 获取通过记录
            passed_problems = user_data.get('passedProblems', [])
            if not passed_problems:
                return []

            problems = []
            count = 0

            for problem in passed_problems[:limit]:
                problem_id = problem.get('pid', '')
                if not problem_id:
                    continue

                # 从题目数据中提取信息
                problem_detail = problem.get('problem', {})
                raw_difficulty = problem_detail.get('difficulty', 0)
                # 转换为 1-10 标准难度
                difficulty = self.normalize_difficulty(raw_difficulty, 'luogu')

                # 获取标签
                tags = []
                problem_tags = problem_detail.get('tags', [])
                for tag in problem_tags[:10]:  # 限制标签数量
                    tags.append(tag.get('name', ''))

                problems.append({
                    'platform': 'luogu',
                    'problem_id': problem_id,
                    'title': problem_detail.get('title', ''),
                    'difficulty': difficulty,
                    'raw_difficulty': raw_difficulty,  # 保存原始值以便参考
                    'tags': tags,
                    'category': None,  # 需要后续用 AI 分析
                    'subcategory': None
                })

                count += 1
                if count >= limit:
                    break

            return problems

        except Exception as e:
            print(f"获取洛谷题目列表失败: {e}")
            return []

    def fetch_codeforces_solved_problems(self, handle: str, limit: int = 500) -> List[Dict]:
        """
        获取 Codeforces 用户已通过的题目列表

        Args:
            handle: 用户名
            limit: 最多获取多少题

        Returns:
            题目列表
        """
        try:
            # 获取提交记录
            status_url = f"https://codeforces.com/api/user.status?handle={handle}"
            status_resp = self.session.get(status_url, timeout=15)

            if status_resp.status_code != 200:
                return []

            status_data = status_resp.json()
            if status_data.get('status') != 'OK':
                return []

            seen = set()
            problems = []

            for sub in status_data.get('result', []):
                if sub.get('verdict') == 'OK':
                    prob = sub.get('problem', {})
                    contest_id = prob.get('contestId', '')
                    index = prob.get('index', '')
                    problem_id = f"{contest_id}{index}"

                    if problem_id in seen:
                        continue

                    seen.add(problem_id)

                    # 生成正确的 Codeforces URL
                    url = f"https://codeforces.com/problemset/problem/{contest_id}/{index}"

                    # 转换 rating 为 1-10 标准难度
                    raw_rating = prob.get('rating', 0)
                    difficulty = self.normalize_difficulty(raw_rating, 'codeforces')

                    problems.append({
                        'platform': 'codeforces',
                        'problem_id': problem_id,
                        'title': prob.get('name', ''),
                        'difficulty': difficulty,
                        'raw_difficulty': raw_rating,  # 保存原始 rating 以便参考
                        'tags': prob.get('tags', []),
                        'category': None,
                        'subcategory': None,
                        'url': url
                    })

                    if len(problems) >= limit:
                        break

            return problems

        except Exception as e:
            print(f"获取 Codeforces 题目列表失败: {e}")
            return []
    
    # ============== Codeforces ==============
    def fetch_codeforces(self, handle: str) -> Dict:
        """
        获取 Codeforces 用户数据

        Returns:
            {
                'handle': str,
                'rating': int,
                'max_rating': int,
                'rank': str,
                'solved_count': int,
                'contest_count': int
            }
        """
        try:
            # 用户信息 API
            url = f"https://codeforces.com/api/user.info?handles={handle}"
            resp = self.session.get(url, timeout=10)

            if resp.status_code != 200:
                return {'error': f'无法访问 Codeforces API (HTTP {resp.status_code})', 'platform': 'codeforces'}

            data = resp.json()

            if data.get('status') != 'OK':
                return {'error': data.get('comment', '用户不存在'), 'platform': 'codeforces'}

            user_info = data['result'][0]

            # 获取提交统计
            status_url = f"https://codeforces.com/api/user.status?handle={handle}&count=1000"
            status_resp = self.session.get(status_url, timeout=15)

            solved_set = set()
            if status_resp.status_code == 200:
                status_data = status_resp.json()
                if status_data.get('status') == 'OK':
                    for sub in status_data['result']:
                        if sub.get('verdict') == 'OK':
                            prob = sub['problem']
                            solved_set.add(f"{prob.get('contestId', '')}{prob.get('index', '')}")

            return {
                'platform': 'codeforces',
                'handle': handle,
                'rating': user_info.get('rating', 0),
                'max_rating': user_info.get('maxRating', 0),
                'rank': user_info.get('rank', 'unrated'),
                'solved_count': len(solved_set),
                'contest_count': user_info.get('contributor', 0),  # 近似值
                'fetched_at': datetime.now().isoformat()
            }

        except requests.exceptions.Timeout:
            return {'error': '请求超时，请检查网络连接', 'platform': 'codeforces'}
        except requests.exceptions.RequestException as e:
            return {'error': f'网络请求失败: {str(e)}', 'platform': 'codeforces'}
        except Exception as e:
            return {'error': f'未知错误: {str(e)}', 'platform': 'codeforces'}
    
    # ============== 牛客 ==============
    def fetch_nowcoder(self, username: str, cookies: str = None) -> Dict:
        """
        获取牛客用户数据

        Args:
            username: 牛客用户ID（数字）
            cookies: 可选，用于访问需要登录的数据

        注意：牛客分为主站(www)和竞赛站(ac),数据主要在竞赛站
        """
        try:
            # 策略: 优先访问牛客竞赛站(ac.nowcoder.com)
            ac_url = f"https://ac.nowcoder.com/users/{username}"
            headers = {}

            if cookies:
                headers['Cookie'] = cookies

            resp = self.session.get(ac_url, headers=headers, timeout=10)

            if resp.status_code != 200:
                # 如果竞赛站失败,尝试主站
                main_url = f"https://www.nowcoder.com/users/{username}"
                main_resp = self.session.get(main_url, headers=headers, timeout=10)

                if main_resp.status_code != 200:
                    return {'error': f'用户 {username} 不存在或无法访问', 'platform': 'nowcoder'}

                html = main_resp.text

                # 尝试从主站解析
                ac_match = re.search(r'AC\s*<[^>]*>(\d+)', html)
                submit_match = re.search(r'提交\s*<[^>]*>(\d+)', html)

                return {
                    'platform': 'nowcoder',
                    'username': username,
                    'ac_count': int(ac_match.group(1)) if ac_match else 0,
                    'submit_count': int(submit_match.group(1)) if submit_match else 0,
                    'source': 'main_site',
                    'note': '部分数据可能需要登录',
                    'fetched_at': datetime.now().isoformat()
                }

            # 解析竞赛站数据
            html = resp.text

            # 查找AC数
            ac_match = re.search(r'AC[^\d]*(\d+)', html)
            submit_match = re.search(r'提交[^\d]*(\d+)', html)

            return {
                'platform': 'nowcoder',
                'username': username,
                'ac_count': int(ac_match.group(1)) if ac_match else 0,
                'submit_count': int(submit_match.group(1)) if submit_match else 0,
                'source': 'ac_site',
                'fetched_at': datetime.now().isoformat()
            }

        except Exception as e:
            return {'error': str(e), 'platform': 'nowcoder'}
    
    # ============== AtCoder ==============
    def fetch_atcoder(self, username: str) -> Dict:
        """
        获取 AtCoder 用户数据
        通过爬取用户页面
        """
        try:
            url = f"https://atcoder.jp/users/{username}"
            resp = self.session.get(url, timeout=10)
            
            if resp.status_code != 200:
                return {'error': f'用户 {username} 不存在'}
            
            html = resp.text
            
            # 解析 rating
            rating_match = re.search(r'<span class="user-[a-z]+">(\d+)</span>', html)
            rating = int(rating_match.group(1)) if rating_match else 0
            
            # 解析 rank
            rank_match = re.search(r'class="user-([a-z]+)">', html)
            rank = rank_match.group(1) if rank_match else 'unrated'
            
            return {
                'platform': 'atcoder',
                'username': username,
                'rating': rating,
                'rank': rank,
                'fetched_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {'error': str(e), 'platform': 'atcoder'}
    
    # ============== 综合获取 ==============
    def fetch_all(self, accounts: Dict[str, str], cookies: Dict[str, str] = None) -> Dict:
        """
        获取所有平台数据

        Args:
            accounts: {'luogu': '用户名', 'codeforces': 'handle', ...}
            cookies: {'nowcoder': 'cookie字符串', ...}

        Returns:
            各平台数据的汇总
        """
        results = {}

        # 获取洛谷API key（如果有）
        luogu_api_key = cookies.get('luogu_api_key') if cookies else None

        if 'luogu' in accounts:
            results['luogu'] = self.fetch_luogu(accounts['luogu'], api_key=luogu_api_key)
            time.sleep(0.5)  # 避免请求过快

        if 'codeforces' in accounts:
            results['codeforces'] = self.fetch_codeforces(accounts['codeforces'])
            time.sleep(0.5)

        if 'atcoder' in accounts:
            results['atcoder'] = self.fetch_atcoder(accounts['atcoder'])

        if 'nowcoder' in accounts:
            nowcoder_cookie = cookies.get('nowcoder') if cookies else None
            results['nowcoder'] = self.fetch_nowcoder(accounts['nowcoder'], cookies=nowcoder_cookie)

        # 汇总统计
        total_solved = sum(
            r.get('solved_count', 0)
            for r in results.values()
            if 'solved_count' in r
        )

        return {
            'platforms': results,
            'total_solved': total_solved,
            'fetched_at': datetime.now().isoformat()
        }


def get_platform_progress(accounts: Dict[str, str]) -> Dict:
    """
    便捷函数：获取多平台进度
    
    Args:
        accounts: {'luogu': '用户名', 'codeforces': 'handle'}
        
    Returns:
        进度数据
    """
    fetcher = PlatformFetcher()
    return fetcher.fetch_all(accounts)


if __name__ == '__main__':
    # 测试
    fetcher = PlatformFetcher()
    
    # 测试洛谷
    print("=== 测试洛谷 ===")
    result = fetcher.fetch_luogu('chen_zhe')  # 洛谷管理员账号，公开数据
    print(json.dumps(result, indent=2, ensure_ascii=False))
    
    # 测试 CF
    print("\n=== 测试 Codeforces ===")
    result = fetcher.fetch_codeforces('tourist')  # CF 排名第一的账号
    print(json.dumps(result, indent=2, ensure_ascii=False))
