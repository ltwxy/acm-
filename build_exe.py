"""
PyInstaller 打包脚本
运行: pyinstaller build.spec
或: python build_exe.py
"""
import os
import subprocess
import sys

def build():
    """构建可执行文件"""
    # 检查 pyinstaller
    try:
        subprocess.run(['pyinstaller', '--version'], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("正在安装 PyInstaller...")
        subprocess.run([sys.executable, '-m', 'pip', 'install', 'pyinstaller'], check=True)

    # 使用 spec 文件打包
    spec_file = '刷题管理系统.spec'
    if os.path.exists(spec_file):
        cmd = ['pyinstaller', spec_file, '--clean']
    else:
        # 直接打包
        cmd = [
            'pyinstaller',
            '--name=刷题管理系统',
            '--onefile',          # 打包成单个文件
            '--console',          # 控制台程序
            '--icon=NONE',
            '--clean',
            'main.py'
        ]

    print("正在打包，请稍候...")
    result = subprocess.run(cmd)
    if result.returncode == 0:
        print("\n打包成功！")
        print("可执行文件位于: dist/刷题管理系统.exe")
    else:
        print("打包失败")

if __name__ == '__main__':
    build()
