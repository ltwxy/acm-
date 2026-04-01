"""
综合分析报告生成器
整合本地刷题数据 + 平台进度 + AI 分析
"""
from datetime import datetime, timedelta
from typing import Dict, List
from pathlib import Path
import json


class ReportGenerator:
    """刷题分析报告生成器"""
    
    def __init__(self, db, config_path: Path):
        self.db = db
        self.config_path = config_path
    
    def load_config(self) -> Dict:
        """加载配置文件"""
        if self.config_path.exists():
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def generate_full_report(self, platform_data: Dict = None) -> Dict:
        """
        生成完整的分析报告
        
        Args:
            platform_data: 从各平台获取的数据（可选）
            
        Returns:
            完整的报告数据
        """
        config = self.config if hasattr(self, 'config') else self.load_config()
        
        # 1. 本地数据统计
        local_stats = self._analyze_local_data()
        
        # 2. 平台进度（如果有）
        platform_stats = platform_data or self._analyze_platform_data(config.get('platform_accounts', {}))
        
        # 3. 知识点分析
        knowledge_analysis = self._analyze_knowledge_points()
        
        # 4. 学习轨迹
        learning_trajectory = self._analyze_learning_trajectory()
        
        # 5. 优势与不足
        swot = self._analyze_swot()
        
        return {
            'generated_at': datetime.now().isoformat(),
            'user_info': config.get('user_info', {}),
            'local_stats': local_stats,
            'platform_stats': platform_stats,
            'knowledge_analysis': knowledge_analysis,
            'learning_trajectory': learning_trajectory,
            'swot': swot,
            'recommendations': self._generate_recommendations(local_stats, knowledge_analysis, swot)
        }
    
    def _analyze_local_data(self) -> Dict:
        """分析本地刷题数据"""
        total = self.db.get_total_count()
        solved = self.db.get_solved_count()
        
        by_category = self.db.get_category_stats()
        by_difficulty = self.db.get_difficulty_stats()
        by_platform = self.db.get_platform_stats()
        
        # 计算活跃度（最近7天的提交）
        recent_problems = self.db.get_all_problems()
        seven_days_ago = datetime.now() - timedelta(days=7)
        recent_count = sum(
            1 for p in recent_problems 
            if p.get('created_at') and datetime.fromisoformat(p['created_at']) > seven_days_ago
        )
        
        return {
            'total_problems': total,
            'solved_problems': solved,
            'solve_rate': round(solved / total * 100, 2) if total > 0 else 0,
            'by_category': by_category,
            'by_difficulty': by_difficulty,
            'by_platform': by_platform,
            'active_rate': recent_count,  # 近7天解题数
            'avg_lines_per_problem': sum(
                p.get('lines_of_code', 0) for p in recent_problems
            ) // total if total > 0 else 0
        }
    
    def _analyze_platform_data(self, accounts: Dict) -> Dict:
        """分析平台数据（暂不实现爬取，只做占位）"""
        # 这里可以从 platform_fetcher 调用
        return {
            'connected_platforms': len([k for k, v in accounts.items() if v]),
            'platforms': accounts,
            'note': '完整平台数据需要在设置页面获取'
        }
    
    def _analyze_knowledge_points(self) -> Dict:
        """分析知识点掌握情况"""
        categories = self.db.get_category_stats()
        
        # 找出最擅长和最薄弱的知识点
        sorted_categories = sorted(categories.items(), key=lambda x: x[1], reverse=True)
        
        return {
            'strongest': sorted_categories[:3] if sorted_categories else [],
            'weakest': sorted_categories[-3:] if len(sorted_categories) > 3 else [],
            'category_distribution': categories
        }
    
    def _analyze_learning_trajectory(self) -> Dict:
        """分析学习轨迹"""
        problems = self.db.get_all_problems()
        
        # 按难度分组
        difficulty_trend = {}
        for p in problems:
            diff = p.get('difficulty', 0)
            difficulty_trend[diff] = difficulty_trend.get(diff, 0) + 1
        
        # 计算平均难度趋势
        avg_difficulty = sum(p.get('difficulty', 0) for p in problems) / len(problems) if problems else 0
        
        return {
            'difficulty_distribution': difficulty_trend,
            'average_difficulty': round(avg_difficulty, 2),
            'trend': 'increasing' if avg_difficulty > 3 else 'stable'
        }
    
    def _analyze_swot(self) -> Dict:
        """SWOT 分析"""
        categories = self.db.get_category_stats()
        platforms = self.db.get_platform_stats()
        
        strengths = []
        weaknesses = []
        opportunities = []
        threats = []
        
        # 优势：做题数量多的领域
        top_categories = sorted(categories.items(), key=lambda x: x[1], reverse=True)[:3]
        for cat, count in top_categories:
            strengths.append(f"{cat}: {count} 题")
        
        # 劣势：薄弱领域
        if len(categories) > 3:
            weak_categories = sorted(categories.items(), key=lambda x: x[1])[:3]
            for cat, count in weak_categories:
                weaknesses.append(f"{cat}: {count} 题 (需加强)")
        
        # 机会：未探索的领域
        all_categories = ['DP', '图论', '搜索', '数据结构', '数学', '字符串', '贪心']
        unexplored = [c for c in all_categories if c not in categories]
        opportunities.extend([f"可尝试 {c}" for c in unexplored])
        
        # 威胁：平台单一化
        if len(platforms) <= 1:
            threats.append("平台单一化，建议多平台练习")
        
        return {
            'strengths': strengths,
            'weaknesses': weaknesses,
            'opportunities': opportunities,
            'threats': threats
        }
    
    def _generate_recommendations(self, local_stats: Dict, knowledge: Dict, swot: Dict) -> List[str]:
        """生成学习建议"""
        recommendations = []
        
        # 基于活跃度
        if local_stats.get('active_rate', 0) < 5:
            recommendations.append("💪 建议提高刷题频率，保持每周至少 5 题的节奏")
        
        # 基于难度
        avg_diff = local_stats.get('average_difficulty', 0)
        if avg_diff < 3:
            recommendations.append("📈 当前题目难度较低，可以尝试挑战更高难度的题目")
        elif avg_diff > 6:
            recommendations.append("⚠️ 高难度题目比例较高，建议适当巩固基础")
        
        # 基于薄弱环节
        for weak in knowledge.get('weakest', []):
            recommendations.append(f"🎯 重点加强 {weak[0]} 的练习")
        
        # 基于优势
        for strong in knowledge.get('strongest', []):
            recommendations.append(f"✨ 继续发挥 {strong[0]} 的优势")
        
        # 基于平台
        platforms = local_stats.get('by_platform', {})
        if len(platforms) <= 1:
            recommendations.append("🌐 建议拓展到更多平台，洛谷、Codeforces、USACO 等")
        
        return recommendations[:8]  # 最多8条建议
    
    def export_to_json(self, report: Dict, output_path: Path):
        """导出为 JSON 格式"""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
    
    def export_to_html(self, report: Dict, output_path: Path):
        """导出为 HTML 格式报告"""
        html = self._render_html_report(report)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)
    
    def _render_html_report(self, report: Dict) -> str:
        """渲染 HTML 报告"""
        return f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>刷题分析报告</title>
    <style>
        body {{ font-family: -apple-system, sans-serif; background: #f5f5f5; padding: 2rem; }}
        .container {{ max-width: 900px; margin: 0 auto; background: white; padding: 2rem; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
        h1 {{ color: #333; border-bottom: 2px solid #6366f1; padding-bottom: 0.5rem; }}
        h2 {{ color: #6366f1; margin-top: 2rem; }}
        .section {{ margin: 1.5rem 0; padding: 1rem; background: #f8f9fa; border-radius: 8px; }}
        .stat {{ display: inline-block; margin: 0.5rem 1rem 0.5rem 0; padding: 0.5rem 1rem; background: #e0e7ff; border-radius: 4px; }}
        .stat strong {{ color: #4f46e5; }}
        .recommendation {{ padding: 0.8rem; background: #fef3c7; border-left: 4px solid #f59e0b; border-radius: 4px; margin: 0.5rem 0; }}
        .swot-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }}
        .swot-box {{ padding: 1rem; border-radius: 8px; }}
        .swot-strength {{ background: #d1fae5; }}
        .swot-weakness {{ background: #fee2e2; }}
        .swot-opportunity {{ background: #dbeafe; }}
        .swot-threat {{ background: #fef3c7; }}
        ul {{ margin-left: 1.5rem; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 刷题分析报告</h1>
        <p style="color: #666;">生成时间: {report['generated_at']}</p>
        
        <div class="section">
            <h2>📈 数据概览</h2>
            <div class="stat">总题数: <strong>{report['local_stats']['total_problems']}</strong></div>
            <div class="stat">已解决: <strong>{report['local_stats']['solved_problems']}</strong></div>
            <div class="stat">解决率: <strong>{report['local_stats']['solve_rate']}%</strong></div>
            <div class="stat">近7天活跃: <strong>{report['local_stats']['active_rate']} 题</strong></div>
        </div>
        
        <div class="section">
            <h2>🧠 知识点分析</h2>
            <h3>最擅长</h3>
            <ul>
                {"".join(f"<li>{cat}: {count} 题</li>" for cat, count in report['knowledge_analysis']['strongest'])}
            </ul>
            <h3>需加强</h3>
            <ul>
                {"".join(f"<li>{cat}: {count} 题</li>" for cat, count in report['knowledge_analysis']['weakest'])}
            </ul>
        </div>
        
        <div class="section">
            <h2>🎯 SWOT 分析</h2>
            <div class="swot-grid">
                <div class="swot-box swot-strength">
                    <h3>💪 优势</h3>
                    <ul>
                        {"".join(f"<li>{s}</li>" for s in report['swot']['strengths'])}
                    </ul>
                </div>
                <div class="swot-box swot-weakness">
                    <h3>⚠️ 劣势</h3>
                    <ul>
                        {"".join(f"<li>{w}</li>" for w in report['swot']['weaknesses'])}
                    </ul>
                </div>
                <div class="swot-box swot-opportunity">
                    <h3>🚀 机会</h3>
                    <ul>
                        {"".join(f"<li>{o}</li>" for o in report['swot']['opportunities'])}
                    </ul>
                </div>
                <div class="swot-box swot-threat">
                    <h3>⚡ 威胁</h3>
                    <ul>
                        {"".join(f"<li>{t}</li>" for t in report['swot']['threats'])}
                    </ul>
                </div>
            </div>
        </div>
        
        <div class="section">
            <h2>💡 学习建议</h2>
            {"".join(f'<div class="recommendation">{rec}</div>' for rec in report['recommendations'])}
        </div>
    </div>
</body>
</html>
"""


def generate_report(db, config_path: Path, output_path: Path = None) -> Dict:
    """
    便捷函数：生成报告
    
    Args:
        db: 数据库实例
        config_path: 配置文件路径
        output_path: 可选，指定输出路径
        
    Returns:
        报告数据
    """
    generator = ReportGenerator(db, config_path)
    report = generator.generate_full_report()
    
    if output_path:
        generator.export_to_html(report, output_path)
    
    return report


if __name__ == '__main__':
    from core.database import Database
    db = Database('data/problems.db')
    
    report = generate_report(
        db,
        Path('config.json'),
        Path('report.html')
    )
    
    print("报告已生成: report.html")
