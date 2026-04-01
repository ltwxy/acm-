"""
刷题管理系统 - 主程序入口
"""
import sys
import os
import argparse
from pathlib import Path

# 修复 Windows 终端编码问题
os.environ['PYTHONIOENCODING'] = 'utf-8'
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# 添加当前目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from core.file_manager import ProblemManager
from core.database import db
from config import TARGET_DIR


def print_banner():
    """打印欢迎界面"""
    print("""
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║           📚 智能刷题管理系统 v1.0                            ║
║                                                              ║
║     自动分类 · 智能归档 · 进度追踪 · 跨平台支持              ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
    """)


def cmd_init(args):
    """初始化命令"""
    print_banner()
    print("🚀 正在初始化系统...\n")
    
    manager = ProblemManager(TARGET_DIR)
    manager.init_system()
    
    print("\n✅ 初始化完成！")
    print(f"📁 监控目录: {TARGET_DIR}")
    print("\n你可以使用以下命令：")
    print("  python main.py watch    - 启动文件监控")
    print("  python main.py web      - 启动Web界面")
    print("  python main.py stats    - 查看统计信息")


def cmd_watch(args):
    """监控命令"""
    import time
    
    print_banner()
    print("👁️  启动文件监控...")
    print(f"📁 监控目录: {TARGET_DIR}")
    print("\n按 Ctrl+C 停止监控\n")
    
    manager = ProblemManager(TARGET_DIR)
    manager.start_monitoring()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n🛑 停止监控...")
        manager.stop_monitoring()


def cmd_web(args):
    """启动Web界面"""
    print_banner()
    print("🌐 启动Web界面...")
    print("\n请在浏览器中访问: http://localhost:5000")
    print("按 Ctrl+C 停止服务\n")
    
    from web.app import app
    app.run(host='0.0.0.0', port=5000, debug=False)


def cmd_stats(args):
    """查看统计"""
    print_banner()
    print("📊 统计信息\n")
    
    stats = {
        'total': db.get_total_count(),
        'solved': db.get_solved_count(),
        'by_category': db.get_category_stats(),
        'by_difficulty': db.get_difficulty_stats(),
        'by_platform': db.get_platform_stats(),
    }
    
    print(f"总题数: {stats['total']}")
    print(f"已解决: {stats['solved']}")
    print(f"完成率: {stats['solved'] / stats['total'] * 100:.1f}%" if stats['total'] > 0 else "完成率: 0%")
    
    print("\n📚 知识点分布:")
    for cat, count in sorted(stats['by_category'].items(), key=lambda x: -x[1]):
        bar = '█' * (count * 2)
        print(f"  {cat:15} {bar} {count}")
    
    if stats['by_platform']:
        print("\n🌐 平台分布:")
        for platform, count in sorted(stats['by_platform'].items(), key=lambda x: -x[1]):
            print(f"  {platform:15} {count}")
    
    if stats['by_difficulty']:
        print("\n📈 难度分布:")
        for diff, count in sorted(stats['by_difficulty'].items()):
            print(f"  难度 {diff:2}: {count}")


def cmd_scan(args):
    """扫描文件"""
    print_banner()
    print("🔍 扫描文件中...\n")
    
    manager = ProblemManager(TARGET_DIR)
    count = manager.watcher.scan_existing()
    
    print(f"\n✅ 扫描完成！发现了 {count} 个新文件")


def cmd_organize(args):
    """整理文件"""
    print_banner()
    
    manager = ProblemManager(TARGET_DIR)
    
    if args.preview:
        print("📋 预览整理计划...\n")
        result = manager.organize_files(dry_run=True)
        
        print(f"计划移动: {len(result['plan'])} 个文件")
        print(f"将跳过: {result['skipped']} 个文件")
        
        if result['plan']:
            print("\n移动计划:")
            for item in result['plan'][:10]:
                print(f"  {Path(item['source']).name:30} -> {item['category']}/{item['subcategory'] or ''}")
            if len(result['plan']) > 10:
                print(f"  ... 还有 {len(result['plan']) - 10} 个文件")
    else:
        print("📁 执行文件整理...\n")
        result = manager.organize_files(dry_run=False)
        
        print(f"✅ 移动: {result['moved']} 个文件")
        print(f"⏭️  跳过: {result['skipped']} 个文件")
        
        if result['errors']:
            print(f"\n❌ 错误: {len(result['errors'])} 个")
            for err in result['errors'][:5]:
                print(f"  {err['file']}: {err['error']}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='智能刷题管理系统 - 自动分类、归档、追踪你的刷题进度',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python main.py init       # 初始化系统
  python main.py watch      # 启动文件监控
  python main.py web        # 启动Web界面
  python main.py stats      # 查看统计
  python main.py scan       # 手动扫描文件
  python main.py organize   # 整理文件（预览）
  python main.py organize --exec  # 执行整理
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # init 命令
    init_parser = subparsers.add_parser('init', help='初始化系统')
    init_parser.set_defaults(func=cmd_init)
    
    # watch 命令
    watch_parser = subparsers.add_parser('watch', help='启动文件监控')
    watch_parser.set_defaults(func=cmd_watch)
    
    # web 命令
    web_parser = subparsers.add_parser('web', help='启动Web界面')
    web_parser.set_defaults(func=cmd_web)
    
    # stats 命令
    stats_parser = subparsers.add_parser('stats', help='查看统计信息')
    stats_parser.set_defaults(func=cmd_stats)
    
    # scan 命令
    scan_parser = subparsers.add_parser('scan', help='手动扫描文件')
    scan_parser.set_defaults(func=cmd_scan)
    
    # organize 命令
    org_parser = subparsers.add_parser('organize', help='整理文件')
    org_parser.add_argument('--exec', action='store_true', dest='execute',
                           help='执行整理（默认仅预览）')
    org_parser.add_argument('--preview', action='store_true',
                           help='预览整理计划（默认）')
    org_parser.set_defaults(func=cmd_organize, preview=True)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # 执行命令
    args.func(args)


if __name__ == '__main__':
    main()
