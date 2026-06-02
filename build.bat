@echo off
chcp 65001 >nul
echo ========================================
echo   小赫桌面宠物 - 打包工具
echo ========================================
echo.

:: 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请先安装 Python 3.10+
    pause
    exit /b 1
)

:: 检查 PyInstaller
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo [信息] 正在安装 PyInstaller...
    pip install pyinstaller
)

:: 安装项目依赖
echo [信息] 正在安装项目依赖...
pip install -r requirements.txt

:: 打包
echo.
echo [信息] 开始打包...
echo [信息] 这可能需要几分钟，请耐心等待...
echo.

pyinstaller build.spec --clean --noconfirm

if errorlevel 1 (
    echo.
    echo [错误] 打包失败！请检查错误信息。
    pause
    exit /b 1
)

echo.
echo ========================================
echo   打包完成！
echo ========================================
echo.
echo 输出目录: dist\小赫桌面宠物\
echo 可执行文件: dist\小赫桌面宠物\小赫桌面宠物.exe
echo.
echo 提示: 
echo   1. 将 dist\小赫桌面宠物 整个文件夹复制到任意位置即可运行
echo   2. 首次运行需要配置 Hermes API 服务地址
echo.
pause
