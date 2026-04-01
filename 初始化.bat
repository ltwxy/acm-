@echo off
chcp 65001 >nul
echo.
echo 🔧 正在初始化刷题管理系统...
echo.

:: 安装依赖
echo 📦 安装依赖...
pip install flask watchdog aiohttp beautifulsoup4 lxml

echo.
echo ✅ 依赖安装完成！
echo.
echo 📝 下一步：
echo    1. 编辑 config.py，修改 TARGET_DIR 为你的刷题文件夹路径
echo    2. 运行 启动.bat 启动系统
echo.

pause
