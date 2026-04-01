"""
刷题管理系统 - 系统自检脚本
用于检测系统配置、依赖、环境是否正常
"""
import sys
import json
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

import importlib


class SystemChecker:
    """系统健康检查器"""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.results: List[Dict] = []

    def add_result(self, category: str, name: str, status: bool,
                   message: str = "", details: str = ""):
        """添加检查结果"""
        self.results.append({
            "category": category,
            "name": name,
            "status": "OK" if status else "FAIL",
            "pass": status,
            "message": message,
            "details": details
        })

    def check_python_version(self):
        """检查Python版本"""
        version = sys.version_info
        ok = version.major >= 3 and (version.major > 3 or version.minor >= 8)
        self.add_result(
            "ENV",
            "Python Version",
            ok,
            f"Python {version.major}.{version.minor}.{version.micro}",
            "Need Python 3.8+" if not ok else "OK"
        )

    def check_dependencies(self):
        """检查依赖包"""
        required = {
            'flask': 'Flask',
            'watchdog': 'watchdog',
            'requests': 'requests',
        }

        for pkg_name, display_name in required.items():
            try:
                mod = importlib.import_module(pkg_name)
                try:
                    from importlib.metadata import version
                    ver = version(pkg_name)
                except Exception:
                    ver = getattr(mod, '__version__', 'N/A')
                self.add_result("依赖", f"{display_name}", True, f"v{ver}")
            except ImportError:
                self.add_result("依赖", f"{display_name}", False, "未安装", "请运行: pip install -r requirements.txt")

    def check_config_files(self):
        """检查配置文件"""
        config_path = self.project_root / "config.json"
        config_py = self.project_root / "config.py"

        # config.py
        if config_py.exists():
            try:
                sys.path.insert(0, str(self.project_root))
                import config
                self.add_result("配置", "config.py", True, "文件存在")

                # 检查关键配置
                if hasattr(config, 'DB_PATH'):
                    db_path = Path(config.DB_PATH)
                    # Also check project root as fallback
                    if not db_path.exists():
                        db_path_alt = self.project_root / "刷题管理系统.db"
                        if db_path_alt.exists():
                            db_path = db_path_alt
                    if db_path.exists():
                        self.add_result("配置", "数据库路径", True, str(db_path))
                    else:
                        self.add_result("配置", "数据库路径", False, "Database not found", str(db_path))
                else:
                    self.add_result("配置", "数据库路径", False, "DB_PATH not defined in config.py")
            except Exception as e:
                self.add_result("配置", "config.py", False, f"加载失败: {e}")
        else:
            self.add_result("配置", "config.py", False, "文件不存在")

        # config.json
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)

                # 检查关键配置项
                checks = [
                    ("target_folder", "刷题目录", lambda v: Path(v).exists() if v else False),
                    ("deepseek_api_key", "DeepSeek API Key", lambda v: bool(v)),
                    ("competition_mode", "竞赛模式", lambda v: v in ['acm', 'oi']),
                ]

                for key, label, validator in checks:
                    value = config_data.get(key)
                    ok = validator(value) if value else False
                    display_val = value[:20] + "..." if value and len(value) > 20 else value
                    self.add_result(
                        "配置",
                        label,
                        ok,
                        display_val if value else "未设置",
                        "请在设置页面配置" if not ok else ""
                    )
            except Exception as e:
                self.add_result("配置", "config.json", False, f"解析失败: {e}")
        else:
            self.add_result("配置", "config.json", False, "文件不存在")

    def check_database(self):
        """检查数据库"""
        # 优先使用 config.py 定义的路径
        sys.path.insert(0, str(self.project_root))
        try:
            from config import DB_PATH
            db_path = Path(DB_PATH)
        except Exception:
            db_path = None

        # 如果配置路径不存在或为空，尝试备选路径
        if not db_path or not db_path.exists() or db_path.stat().st_size == 0:
            db_path = self.project_root / "data" / "problems.db"
        if not db_path.exists() or db_path.stat().st_size == 0:
            db_path = self.project_root / "刷题管理系统.db"
        if not db_path.exists():
            self.add_result("数据库", "数据库文件", False, "Database file not found")
            return

        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # 检查表
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]

            expected_tables = [
                'problems', 'platform_problems', 'categories',
                'daily_stats', 'daily_plans', 'task_execution',
                'candidate_pool', 'problem_status_log', 'sync_log'
            ]

            for table in expected_tables:
                if table in tables:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    count = cursor.fetchone()[0]
                    self.add_result("数据库", f"表: {table}", True, f"{count} 条记录")
                else:
                    self.add_result("数据库", f"表: {table}", False, "表不存在")

            # 检查索引
            cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%'")
            indexes = cursor.fetchall()
            self.add_result("数据库", "索引数量", True, f"{len(indexes)} 个索引")

            # 数据库大小
            size_kb = db_path.stat().st_size / 1024
            self.add_result("数据库", "数据库大小", True, f"{size_kb:.1f} KB")

            conn.close()

        except Exception as e:
            self.add_result("数据库", "数据库连接", False, str(e))

    def check_folders(self):
        """检查文件夹"""
        config_path = self.project_root / "config.json"
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                target_folder = config.get('target_folder')
                if target_folder:
                    folder = Path(target_folder)
                    if folder.exists():
                        # 统计cpp文件数量
                        cpp_files = list(folder.rglob("*.cpp")) + list(folder.rglob("*.cc"))
                        self.add_result("目录", "刷题目录", True, f"{len(cpp_files)} 个代码文件")
                    else:
                        self.add_result("目录", "刷题目录", False, "目录不存在", str(folder))
            except Exception:
                pass

        # 检查关键目录
        for folder in ['core', 'web', 'scripts', 'docs']:
            path = self.project_root / folder
            if path.exists():
                file_count = len(list(path.rglob("*"))) if path.is_dir() else 0
                self.add_result("目录", folder, True, f"{file_count} 个文件")
            else:
                self.add_result("目录", folder, False, "目录不存在")

    def check_web_server(self):
        """检查Web服务配置"""
        app_path = self.project_root / "web" / "app.py"
        if app_path.exists():
            try:
                sys.path.insert(0, str(self.project_root / "web"))
                # 尝试导入app
                import app as flask_app
                self.add_result("Web服务", "Flask应用", True, "app.py 可正常导入")
            except Exception as e:
                self.add_result("Web服务", "Flask应用", False, f"导入失败: {e}")
        else:
            self.add_result("Web服务", "Flask应用", False, "app.py 不存在")

        # 检查模板文件
        templates = ['index.html', 'settings.html', 'plan.html', 'guide.html']
        template_dir = self.project_root / "web" / "templates"
        if template_dir.exists():
            for tpl in templates:
                path = template_dir / tpl
                if path.exists():
                    size = path.stat().st_size
                    self.add_result("Web服务", f"模板: {tpl}", True, f"{size // 1024} KB")
                else:
                    self.add_result("Web服务", f"模板: {tpl}", False, "文件不存在")

    def check_platform_connectivity(self):
        """检查平台连接"""
        try:
            import requests
        except ImportError:
            self.add_result("网络", "requests library", False, "Not installed", "pip install requests (SSL may have issues)")
            # Try system Python
            try:
                import subprocess
                result = subprocess.run(
                    [sys.executable, "-m", "pip", "install", "requests", "--quiet"],
                    capture_output=True, timeout=30
                )
                if result.returncode == 0:
                    import requests
                    self.add_result("网络", "requests library", True, "Installed successfully")
                else:
                    return
            except Exception:
                return

        platforms = [
            ("Luogu", "https://www.luogu.com.cn"),
            ("Codeforces", "https://codeforces.com"),
            ("NowCoder", "https://www.nowcoder.com"),
        ]

        for name, url in platforms:
            try:
                resp = requests.get(url, timeout=5, verify=False)
                ok = resp.status_code < 500
                self.add_result(
                    "网络",
                    f"{name} Connection",
                    ok,
                    f"HTTP {resp.status_code}",
                    "" if ok else "Unreachable"
                )
            except Exception as e:
                self.add_result("网络", f"{name} Connection", False, "Failed", str(e))

        # Check DeepSeek API
        config_path = self.project_root / "config.json"
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            api_key = config.get('deepseek_api_key')
            if api_key:
                try:
                    resp = requests.get(
                        "https://api.deepseek.com/v1/models",
                        headers={"Authorization": f"Bearer {api_key}"},
                        timeout=10
                    )
                    if resp.status_code == 200:
                        self.add_result("AI", "DeepSeek API", True, "Available")
                    else:
                        self.add_result("AI", "DeepSeek API", False, f"HTTP {resp.status_code}")
                except Exception as e:
                    self.add_result("AI", "DeepSeek API", False, "Failed", str(e))
            else:
                self.add_result("AI", "DeepSeek API", False, "Not configured")

    def run_all(self):
        """运行所有检查"""
        print("=" * 60)
        print("[SYS CHECK] 刷题管理系统 - System Health Check")
        print("=" * 60)
        print(f"检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"项目路径: {self.project_root}")
        print()

        self.check_python_version()
        self.check_dependencies()
        self.check_config_files()
        self.check_database()
        self.check_folders()
        self.check_web_server()
        self.check_platform_connectivity()

        # 按类别显示结果
        categories = {}
        for result in self.results:
            cat = result["category"]
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(result)

        for category, items in categories.items():
            print(f"\n[{category}]")
            for item in items:
                status_icon = "[PASS]" if item["pass"] else "[FAIL]"
                detail = f" | {item['details']}" if item['details'] and not item["pass"] else ""
                print(f"  {status_icon} {item['name']}: {item['message']}{detail}")

        # 汇总
        total = len(self.results)
        passed = sum(1 for r in self.results if r["pass"])
        failed = total - passed

        print("\n" + "=" * 60)
        print(f"[SUMMARY] Check: {passed}/{total} passed" + (f" | FAIL {failed}" if failed else " | ALL PASS"))
        print("=" * 60)

        if failed > 0:
            print("\n[ADVICE] Suggestions:")
            for item in self.results:
                if not item["pass"] and item["details"]:
                    print(f"  - {item['name']}: {item['details']}")

        return {
            "total": total,
            "passed": passed,
            "failed": failed,
            "results": self.results,
            "timestamp": datetime.now().isoformat()
        }


if __name__ == "__main__":
    project_root = Path(__file__).parent.parent
    checker = SystemChecker(project_root)
    checker.run_all()
