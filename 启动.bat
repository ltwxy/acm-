@echo off
chcp 65001 >nul
echo.
echo ============================================
echo    智能刷题管理系统 v1.0
echo ============================================
echo.

:: 检查Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到Python，请先安装Python 3.8+
    echo.
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [OK] Python已安装

:: 安装依赖
echo.
echo [安装] 正在检查依赖...
pip install -q flask watchdog aiohttp beautifulsoup4 lxml
if errorlevel 1 (
    echo [安装] 依赖安装中...
    pip install flask watchdog aiohttp beautifulsoup4 lxml
)

:: 启动Web界面
echo.
echo [启动] Web界面...
echo    浏览器访问: http://localhost:5000
echo    按 Ctrl+C 停止服务
echo.

python main.py web

pause
