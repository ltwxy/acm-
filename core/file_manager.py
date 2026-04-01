"""
文件管理模块
负责文件监控、自动归档
"""
import os
import shutil
from pathlib import Path
from typing import List, Dict, Optional, Callable
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent, FileModifiedEvent

from config import TARGET_DIR, SUPPORTED_EXTENSIONS, CATEGORIES
from core.database import db
from core.analyzer import CodeAnalyzer, CategoryClassifier
from core.infer_difficulty import infer_difficulty
from core.platform_api import PlatformAPIManager
from core.code_complexity import complexity_analyzer


class ProblemFileHandler(FileSystemEventHandler):
    """文件事件处理器"""
    
    def __init__(self, on_file_added: Optional[Callable] = None):
        self.on_file_added = on_file_added
        self.analyzer = CodeAnalyzer()
        self.classifier = CategoryClassifier()
        self.api_manager = PlatformAPIManager()
    
    def on_created(self, event):
        """文件创建事件"""
        if event.is_directory:
            return
        
        if Path(event.src_path).suffix.lower() in SUPPORTED_EXTENSIONS:
            print(f'[监控] 检测到新文件: {event.src_path}')
            self._process_file(event.src_path)
    
    def on_modified(self, event):
        """文件修改事件"""
        if event.is_directory:
            return
        
        if Path(event.src_path).suffix.lower() in SUPPORTED_EXTENSIONS:
            # 检查文件是否已在数据库中
            if not db.problem_exists(event.src_path):
                print(f'[监控] 检测到修改: {event.src_path}')
                self._process_file(event.src_path)
    
    def _process_file(self, file_path: str):
        """处理单个文件"""
        try:
            import time
            start_time = time.time()
            file_path = Path(file_path)

            print(f'[处理] 开始处理: {file_path.name}')

            # 1. 代码分析
            t1 = time.time()
            code_analysis = self.analyzer.analyze_file(file_path)
            print(f'[处理] 代码分析完成: {time.time() - t1:.2f}s')

            # 2. 代码复杂度分析
            t2 = time.time()
            complexity_result = complexity_analyzer.analyze(file_path)
            print(f'[处理] 复杂度分析完成: {time.time() - t2:.2f}s')

            # 3. 分类
            t3 = time.time()
            classification = self.classifier.classify(file_path, code_analysis)
            print(f'[处理] 分类完成: {time.time() - t3:.2f}s')

            # 4. 获取平台信息
            platform_info = classification['filename_analysis']

            # 5. 准备数据
            inferred_difficulty = infer_difficulty(classification['category'], classification.get('subcategory'))
            problem_data = {
                'file_path': str(file_path),
                'file_name': file_path.name,
                'title': platform_info.get('title') or file_path.stem,
                'platform': platform_info.get('platform'),
                'problem_id': platform_info.get('problem_id'),
                'url': platform_info.get('url'),
                'category': classification['category'],
                'subcategory': classification['subcategory'],
                'difficulty': inferred_difficulty,
                'tags': [],
                'algorithms': [a['name'] for a in code_analysis.get('algorithms', [])[:5]],
                'data_structures': [d['name'] for d in code_analysis.get('data_structures', [])[:5]],
                'code_features': code_analysis.get('features', {}),
                'lines_of_code': code_analysis.get('lines_of_code', 0),
                'code_complexity': complexity_result['complexity'],  # 修复拼写
                'one_submit': 1,  # 默认一次AC，后续可通过OJ数据更新
                'attempts': 1,  # 默认1次，后续可通过OJ数据更新
                'status': 'solved',  # 文件存在 = 已完成
            }

            # 6. 保存到数据库
            t4 = time.time()
            db.add_problem(problem_data)
            print(f'[处理] 数据库保存完成: {time.time() - t4:.2f}s')
            print(f'[数据库] 已添加: {file_path.name} -> {classification["category"]} (复杂度: {complexity_result["complexity"]:.2f})')

            # 7. 回调
            if self.on_file_added:
                self.on_file_added(problem_data)

            # 8. 平台信息获取（跳过，避免异步调用导致扫描卡死）
            # 注意：扫描时不获取平台信息，可以在监控模式下通过后台线程获取
            # 用户可以通过"更新平台信息"功能手动刷新

            total_time = time.time() - start_time
            print(f'[处理] 文件处理完成，总耗时: {total_time:.2f}s')

        except Exception as e:
            print(f'[错误] 处理文件失败 {file_path}: {e}')
            import traceback
            traceback.print_exc()
    
    async def _fetch_platform_info(self, file_path: str, platform: str, problem_id: str):
        """异步获取平台信息"""
        try:
            async with self.api_manager.apis[platform]() as api:
                info = await api.fetch_problem(problem_id)
                if info:
                    updates = {
                        'title': info.title,
                        'difficulty': info.difficulty,
                        'tags': info.tags,
                    }
                    db.update_problem(file_path, updates)
                    print(f'[平台] 已更新 {platform} {problem_id} 的信息')
        except Exception as e:
            print(f'[平台] 获取信息失败 {platform} {problem_id}: {e}')


class FileWatcher:
    """文件监控器"""
    
    def __init__(self, target_dir: Path = TARGET_DIR):
        self.target_dir = target_dir
        self.observer = Observer()
        self.handler = ProblemFileHandler()
    
    def start(self):
        """启动监控"""
        self.observer.schedule(self.handler, str(self.target_dir), recursive=True)
        self.observer.start()
        print(f'[监控] 开始监控目录: {self.target_dir}')
    
    def stop(self):
        """停止监控"""
        self.observer.stop()
        self.observer.join()
        print('[监控] 已停止')
    
    def scan_existing(self):
        """扫描现有文件"""
        print(f'[扫描] 开始扫描现有文件...')
        count = 0
        errors = []

        try:
            # 检查目标目录是否存在
            if not self.target_dir.exists():
                print(f'[扫描] 警告：目标目录不存在: {self.target_dir}')
                return 0

            for ext in SUPPORTED_EXTENSIONS:
                for file_path in self.target_dir.rglob(f'*{ext}'):
                    try:
                        # 跳过隐藏文件
                        if any(part.startswith('.') for part in file_path.parts):
                            continue

                        # 检查文件是否已在数据库中
                        if not db.problem_exists(str(file_path)):
                            print(f'[扫描] 处理新文件: {file_path}')
                            self.handler._process_file(str(file_path))
                            count += 1
                    except Exception as e:
                        error_msg = f'{file_path}: {str(e)}'
                        errors.append(error_msg)
                        print(f'[扫描] 错误: {error_msg}')

            print(f'[扫描] 完成，处理了 {count} 个新文件')
            if errors:
                print(f'[扫描] 发生了 {len(errors)} 个错误:')
                for err in errors[:5]:  # 只显示前5个
                    print(f'  - {err}')

            return count

        except Exception as e:
            print(f'[扫描] 扫描失败: {e}')
            import traceback
            traceback.print_exc()
            return 0


class FileOrganizer:
    """文件整理器"""
    
    def __init__(self, target_dir: Path = TARGET_DIR):
        self.target_dir = target_dir
        self.categories = CATEGORIES
    
    def organize_by_category(self, dry_run: bool = False) -> Dict:
        """
        按分类整理文件
        
        Args:
            dry_run: 如果为True，只返回计划而不实际执行
            
        Returns:
            整理结果统计
        """
        stats = {
            'moved': 0,
            'skipped': 0,
            'errors': [],
            'plan': []
        }
        
        problems = db.get_all_problems()
        
        for problem in problems:
            file_path = Path(problem['file_path'])
            category = problem.get('category', 'other')
            subcategory = problem.get('subcategory')
            
            # 确定目标目录
            target_subdir = self._get_target_dir(category, subcategory)
            target_path = self.target_dir / target_subdir / file_path.name
            
            # 检查是否需要移动
            if file_path.parent == target_path.parent:
                stats['skipped'] += 1
                continue
            
            action = {
                'source': str(file_path),
                'target': str(target_path),
                'category': category,
                'subcategory': subcategory
            }
            
            if dry_run:
                stats['plan'].append(action)
            else:
                try:
                    # 创建目标目录
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # 移动文件
                    shutil.move(str(file_path), str(target_path))
                    
                    # 更新数据库
                    db.update_problem(str(file_path), {'file_path': str(target_path)})
                    
                    stats['moved'] += 1
                    print(f'[整理] 移动: {file_path.name} -> {target_subdir}')
                    
                except Exception as e:
                    stats['errors'].append({
                        'file': str(file_path),
                        'error': str(e)
                    })
        
        return stats
    
    def _get_target_dir(self, category: str, subcategory: Optional[str]) -> str:
        """获取目标目录路径"""
        cat_info = self.categories.get(category, {})
        cat_name = cat_info.get('name', category)
        
        if subcategory:
            sub_info = cat_info.get('subcategories', {}).get(subcategory, {})
            sub_name = sub_info.get('name', subcategory)
            return f'{cat_name}/{sub_name}'
        
        return cat_name
    
    def create_directory_structure(self):
        """创建分类目录结构"""
        for cat_key, cat_info in self.categories.items():
            cat_name = cat_info.get('name', cat_key)
            cat_dir = self.target_dir / cat_name
            cat_dir.mkdir(exist_ok=True)
            
            # 创建子分类目录
            for sub_key, sub_info in cat_info.get('subcategories', {}).items():
                sub_name = sub_info.get('name', sub_key)
                sub_dir = cat_dir / sub_name
                sub_dir.mkdir(parents=True, exist_ok=True)
        
        print('[整理] 目录结构创建完成')


class ProblemManager:
    """题目管理器（整合功能）"""
    
    def __init__(self, target_dir: Path = TARGET_DIR):
        self.target_dir = target_dir
        self.watcher = FileWatcher(target_dir)
        self.organizer = FileOrganizer(target_dir)
    
    def init_system(self):
        """初始化系统"""
        print('=' * 50)
        print('刷题管理系统初始化')
        print('=' * 50)
        
        # 1. 创建目录结构
        self.organizer.create_directory_structure()
        
        # 2. 扫描现有文件
        self.watcher.scan_existing()
        
        print('=' * 50)
        print('初始化完成')
        print('=' * 50)
    
    def start_monitoring(self):
        """开始监控"""
        self.watcher.start()
    
    def stop_monitoring(self):
        """停止监控"""
        self.watcher.stop()
    
    def organize_files(self, dry_run: bool = False):
        """整理文件"""
        return self.organizer.organize_by_category(dry_run)
    
    def get_statistics(self) -> Dict:
        """获取统计信息"""
        return {
            'total': db.get_total_count(),
            'solved': db.get_solved_count(),
            'by_category': db.get_category_stats(),
            'by_difficulty': db.get_difficulty_stats(),
            'by_platform': db.get_platform_stats(),
        }


if __name__ == '__main__':
    # 测试
    manager = ProblemManager()
    
    # 初始化
    manager.init_system()
    
    # 获取统计
    stats = manager.get_statistics()
    print('\n统计信息:')
    print(f'  总数: {stats["total"]}')
    print(f'  已解决: {stats["solved"]}')
    print(f'  分类分布: {stats["by_category"]}')
