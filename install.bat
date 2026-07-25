@echo off
cd /d "%~dp0"

echo ============================================================
echo  定州市第八中学 每日安全提醒 - 一键安装
echo  兼容 Python 3.9-3.14, 使用 pywinauto 替代 wxauto
echo ============================================================
echo.

REM 检查 Python
where python >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到 Python, 请先安装 Python 3.9+ 并加入 PATH
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [1/5] 已检测到 Python:
python --version
echo.

echo [2/5] 安装依赖库 pywinauto / Pillow / psutil / numpy / uiautomation ...
python -m pip install --upgrade pip
python -m pip install pywinauto Pillow psutil numpy uiautomation
if errorlevel 1 (
    echo [错误] 依赖安装失败
    echo 请检查网络, 或尝试使用国内镜像:
    echo   python -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple pywinauto Pillow psutil numpy uiautomation
    pause
    exit /b 1
)
echo.

echo [3/5] 配置电源选项: 允许定时任务唤醒电脑...
powercfg /SETACVALUEINDEX SCHEME_CURRENT SUB_SLEEP RTCWAKE 1
powercfg /SETDCVALUEINDEX SCHEME_CURRENT SUB_SLEEP RTCWAKE 1
powercfg /SETACTIVE SCHEME_CURRENT
echo   唤醒定时器已启用
echo.

echo [4/5] 安装定时任务 - 需要管理员权限 ...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install_task.ps1"
if errorlevel 1 (
    echo [警告] 定时任务安装失败, 可能是权限不足
    echo 请右键此 .bat 文件, 以管理员身份运行
    pause
)
echo.

echo [5/5] 测试发送...
echo 即将向 文件传输助手 发送一条测试消息
echo 请确保 PC 微信已登录并保持在前台
echo.
pause
python "%~dp0wechat_daily.py" --test

echo.
echo ============================================================
echo  安装完成!
echo ============================================================
echo.
echo  接下来你需要做:
echo  1. 用记事本打开 config.json, 把 class_group_name 和
echo     teacher_group_name 改成你真实的微信群名 - 务必一字不差
echo  2. 再次运行测试: python wechat_daily.py --test
echo  3. 一切正常后, 每天 7:30 系统会自动执行
echo  4. 失败时会弹窗+响铃, 请听到后手动补发
echo.
echo  关于休眠问题:
echo  - 脚本运行期间会自动阻止系统睡眠, 结束后自动恢复
echo  - 定时任务通过唤醒定时器在 7:30 唤醒电脑
echo  - 笔记本用户: 控制面板 - 电源选项 - 选择关闭盖子的功能
echo    设为 不采取任何操作, 避免合盖导致任务失败
echo.
pause
