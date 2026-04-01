"""
在线平台API模块
抓取各OJ平台的题目信息
"""
import asyncio
import aiohttp
import json
import re
from typing import Dict, Optional, List
from dataclasses import dataclass
from abc import ABC, abstractmethod

from config import DIFFICULTY_MAP


@dataclass
class ProblemInfo:
    """题目信息数据类"""
    platform: str
    problem_id: str
    title: str
    difficulty: Optional[int] = None
    difficulty_name: Optional[str] = None
    tags: List[str] = None
    url: Optional[str] = None
    description: Optional[str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []


class BasePlatformAPI(ABC):
    """平台API基类"""
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    @abstractmethod
    async def fetch_problem(self, problem_id: str) -> Optional[ProblemInfo]:
        """获取题目信息"""
        pass
    
    async def _fetch_json(self, url: str, **kwargs) -> Optional[Dict]:
        """发送GET请求并返回JSON"""
        try:
            async with self.session.get(url, timeout=aiohttp.ClientTimeout(total=10), **kwargs) as response:
                if response.status == 200:
                    return await response.json()
                return None
        except Exception as e:
            print(f'请求失败 {url}: {e}')
            return None
    
    async def _fetch_html(self, url: str, **kwargs) -> Optional[str]:
        """发送GET请求并返回HTML文本"""
        try:
            async with self.session.get(url, timeout=aiohttp.ClientTimeout(total=10), **kwargs) as response:
                if response.status == 200:
                    return await response.text()
                return None
        except Exception as e:
            print(f'请求失败 {url}: {e}')
            return None


class LuoguAPI(BasePlatformAPI):
    """洛谷API"""
    
    BASE_URL = 'https://www.luogu.com.cn'
    
    async def fetch_problem(self, problem_id: str) -> Optional[ProblemInfo]:
        """
        获取洛谷题目信息
        
        Args:
            problem_id: 题号，如 'P1001', 'T1234'
            
        Returns:
            ProblemInfo对象
        """
        # 标准化题号
        problem_id = problem_id.upper()
        if not problem_id[0].isalpha():
            problem_id = 'P' + problem_id
        
        url = f'{self.BASE_URL}/problem/{problem_id}'
        
        # 洛谷的API需要通过页面解析获取
        html = await self._fetch_html(url)
        if not html:
            return None
        
        try:
            # 提取题目数据（洛谷在页面中嵌入了JSON数据）
            match = re.search(r'decodeURIComponent\("([^"]+)"\)', html)
            if match:
                import urllib.parse
                json_str = urllib.parse.unquote(match.group(1))
                data = json.loads(json_str)
                
                problem_data = data.get('currentData', {}).get('problem', {})
                
                title = problem_data.get('title', 'Unknown')
                difficulty_name = problem_data.get('difficulty', None)
                tags = problem_data.get('tags', [])
                
                # 转换难度
                difficulty = DIFFICULTY_MAP.get('luogu', {}).get(difficulty_name, None)
                
                return ProblemInfo(
                    platform='luogu',
                    problem_id=problem_id,
                    title=title,
                    difficulty=difficulty,
                    difficulty_name=difficulty_name,
                    tags=tags,
                    url=url
                )
        except Exception as e:
            print(f'解析洛谷题目失败: {e}')
        
        # 如果解析失败，返回基本信息
        return ProblemInfo(
            platform='luogu',
            problem_id=problem_id,
            title=f'洛谷 {problem_id}',
            url=url
        )


class CodeforcesAPI(BasePlatformAPI):
    """Codeforces API"""
    
    API_URL = 'https://codeforces.com/api'
    
    async def fetch_problem(self, problem_id: str) -> Optional[ProblemInfo]:
        """
        获取Codeforces题目信息
        
        Args:
            problem_id: 题号，如 '1234A', '567B'
            
        Returns:
            ProblemInfo对象
        """
        # 解析contest_id和index
        match = re.match(r'(\d+)([A-Z]\d?)', problem_id.upper())
        if not match:
            return None
        
        contest_id = match.group(1)
        index = match.group(2)
        
        # Codeforces API返回所有题目，需要筛选
        url = f'{self.API_URL}/problemset.problems'
        data = await self._fetch_json(url)
        
        if not data or data.get('status') != 'OK':
            return None
        
        try:
            problems = data['result']['problems']
            for prob in problems:
                if str(prob.get('contestId')) == contest_id and prob.get('index') == index:
                    title = prob.get('name', 'Unknown')
                    tags = prob.get('tags', [])
                    rating = prob.get('rating', None)
                    
                    # 根据rating估算难度
                    difficulty = None
                    if rating:
                        # Codeforces rating 映射到 1-10
                        difficulty = min(max((rating - 800) // 200 + 1, 1), 10)
                    
                    problem_url = f'https://codeforces.com/problemset/problem/{contest_id}/{index}'
                    
                    return ProblemInfo(
                        platform='codeforces',
                        problem_id=problem_id.upper(),
                        title=title,
                        difficulty=difficulty,
                        difficulty_name=f'{rating}' if rating else None,
                        tags=tags,
                        url=problem_url
                    )
        except Exception as e:
            print(f'解析Codeforces题目失败: {e}')
        
        return None


class LeetCodeAPI(BasePlatformAPI):
    """LeetCode API"""
    
    BASE_URL = 'https://leetcode.cn'
    
    async def fetch_problem(self, problem_id: str) -> Optional[ProblemInfo]:
        """
        获取LeetCode题目信息
        
        Args:
            problem_id: 题号，如 '1', '两数之和'
            
        Returns:
            ProblemInfo对象
        """
        # 如果是数字ID，需要查询对应slug
        if problem_id.isdigit():
            # 通过题目列表API查找
            slug = await self._get_slug_by_id(int(problem_id))
            if not slug:
                return ProblemInfo(
                    platform='leetcode',
                    problem_id=problem_id,
                    title=f'LeetCode {problem_id}',
                    url=f'{self.BASE_URL}/problems/'
                )
        else:
            # 假设是slug
            slug = problem_id.lower().replace(' ', '-')
        
        # GraphQL查询
        query = {
            'query': '''
                query getQuestionDetail($titleSlug: String!) {
                    question(titleSlug: $titleSlug) {
                        questionId
                        title
                        titleSlug
                        difficulty
                        topicTags {
                            name
                        }
                    }
                }
            ''',
            'variables': {'titleSlug': slug}
        }
        
        url = f'{self.BASE_URL}/graphql'
        
        try:
            async with self.session.post(url, json=query) as response:
                if response.status == 200:
                    data = await response.json()
                    question = data.get('data', {}).get('question', {})
                    
                    if question:
                        title = question.get('title', 'Unknown')
                        difficulty_name = question.get('difficulty', None)
                        tags = [tag['name'] for tag in question.get('topicTags', [])]
                        
                        difficulty = DIFFICULTY_MAP.get('leetcode', {}).get(difficulty_name, None)
                        
                        return ProblemInfo(
                            platform='leetcode',
                            problem_id=question.get('questionId', problem_id),
                            title=title,
                            difficulty=difficulty,
                            difficulty_name=difficulty_name,
                            tags=tags,
                            url=f'{self.BASE_URL}/problems/{slug}'
                        )
        except Exception as e:
            print(f'解析LeetCode题目失败: {e}')
        
        return ProblemInfo(
            platform='leetcode',
            problem_id=problem_id,
            title=f'LeetCode {problem_id}',
            url=f'{self.BASE_URL}/problems/{slug}'
        )
    
    async def _get_slug_by_id(self, problem_id: int) -> Optional[str]:
        """通过题号获取slug"""
        # 获取题目列表
        query = {
            'query': '''
                query problemsetQuestionList($categorySlug: String, $skip: Int, $limit: Int) {
                    problemsetQuestionList(
                        categorySlug: $categorySlug
                        skip: $skip
                        limit: $limit
                    ) {
                        questions {
                            questionId
                            titleSlug
                        }
                    }
                }
            ''',
            'variables': {
                'categorySlug': 'all-code-essentials',
                'skip': 0,
                'limit': 3000
            }
        }
        
        url = f'{self.BASE_URL}/graphql'
        
        try:
            async with self.session.post(url, json=query) as response:
                if response.status == 200:
                    data = await response.json()
                    questions = data.get('data', {}).get('problemsetQuestionList', {}).get('questions', [])
                    
                    for q in questions:
                        if q.get('questionId') == str(problem_id):
                            return q.get('titleSlug')
        except Exception as e:
            print(f'获取LeetCode slug失败: {e}')
        
        return None


class PlatformAPIManager:
    """平台API管理器"""
    
    def __init__(self):
        self.apis = {
            'luogu': LuoguAPI,
            'codeforces': CodeforcesAPI,
            'leetcode': LeetCodeAPI,
        }
    
    async def fetch_problem_info(self, platform: str, problem_id: str) -> Optional[ProblemInfo]:
        """
        获取指定平台的题目信息
        
        Args:
            platform: 平台名称
            problem_id: 题号
            
        Returns:
            ProblemInfo对象或None
        """
        api_class = self.apis.get(platform.lower())
        if not api_class:
            return None
        
        async with api_class() as api:
            return await api.fetch_problem(problem_id)
    
    async def fetch_multiple(self, requests: List[tuple]) -> List[Optional[ProblemInfo]]:
        """
        批量获取题目信息
        
        Args:
            requests: [(platform, problem_id), ...]
            
        Returns:
            ProblemInfo列表
        """
        tasks = []
        for platform, problem_id in requests:
            tasks.append(self.fetch_problem_info(platform, problem_id))
        
        return await asyncio.gather(*tasks, return_exceptions=True)


# 同步接口（方便调用）
async def fetch_problem_info_async(platform: str, problem_id: str) -> Optional[ProblemInfo]:
    """异步获取题目信息"""
    manager = PlatformAPIManager()
    return await manager.fetch_problem_info(platform, problem_id)


def fetch_problem_info(platform: str, problem_id: str) -> Optional[ProblemInfo]:
    """同步获取题目信息（阻塞调用）"""
    return asyncio.run(fetch_problem_info_async(platform, problem_id))


# 测试代码
if __name__ == '__main__':
    async def test():
        manager = PlatformAPIManager()
        
        # 测试洛谷
        print('测试洛谷...')
        info = await manager.fetch_problem_info('luogu', 'P1001')
        if info:
            print(f'  标题: {info.title}')
            print(f'  难度: {info.difficulty_name} ({info.difficulty})')
            print(f'  标签: {info.tags}')
        
        # 测试Codeforces
        print('\n测试Codeforces...')
        info = await manager.fetch_problem_info('codeforces', '4A')
        if info:
            print(f'  标题: {info.title}')
            print(f'  难度: {info.difficulty_name} ({info.difficulty})')
            print(f'  标签: {info.tags}')
        
        # 测试LeetCode
        print('\n测试LeetCode...')
        info = await manager.fetch_problem_info('leetcode', '1')
        if info:
            print(f'  标题: {info.title}')
            print(f'  难度: {info.difficulty_name} ({info.difficulty})')
            print(f'  标签: {info.tags}')
    
    asyncio.run(test())
