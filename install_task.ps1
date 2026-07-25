# Windows 任务计划程序安装脚本
# 用法 (管理员 PowerShell):
#   powershell -ExecutionPolicy Bypass -File install_task.ps1

$ErrorActionPreference = "Stop"

# ===== 0. 检测管理员权限 =====
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host ""
    Write-Host "[错误] 必须以管理员身份运行!" -ForegroundColor Red
    Write-Host ""
    Write-Host "解决方法 (任选其一):" -ForegroundColor Yellow
    Write-Host "  方法1: 右键 install.bat -> 以管理员身份运行"
    Write-Host "  方法2: 按 Win+X -> 选 'Windows PowerShell (管理员)' 或 '终端 (管理员)'"
    Write-Host "         然后运行: cd /d $PSScriptRoot"
    Write-Host "         再运行:   powershell -ExecutionPolicy Bypass -File install_task.ps1"
    Write-Host ""
    throw "需要管理员权限"
}

$TaskName = "WeChatDailySafety"
$ProjectDir = $PSScriptRoot
$ScriptPath = Join-Path $ProjectDir "wechat_daily.py"
$LogDir = Join-Path $ProjectDir "logs"
$LogFile = Join-Path $LogDir "task_run.log"

# 确保日志目录存在
if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
}

$ConfigPath = Join-Path $ProjectDir "config.json"
$Config = Get-Content $ConfigPath -Raw -Encoding UTF8 | ConvertFrom-Json
$SendTime = $Config.schedule.send_time
Write-Host "发送时间设定为: $SendTime" -ForegroundColor Cyan

# ===== 1. 找 python.exe 的完整路径 =====
# 优先用官方版 Python, 找不到才用 Microsoft Store 版
Write-Host "查找 python.exe..." -ForegroundColor Cyan

$PythonExe = $null
$PythonIsStore = $false

# 候选路径列表 (按优先级排序)
# 优先官方版, 最后才考虑 Microsoft Store 版
$officialCandidates = @()

# 1) 用 where 命令找所有 python.exe, 优先收集非 WindowsApps 的
try {
    $whereResults = (where.exe python 2>$null) -split "`n"
    foreach ($p in $whereResults) {
        $p = $p.Trim()
        if ($p -and ($p -notlike "*WindowsApps*")) {
            $officialCandidates += $p
        }
    }
} catch {}

# 2) 常见官方安装路径
$officialCandidates += @(
    "C:\Python314\python.exe",
    "C:\Python313\python.exe",
    "C:\Python312\python.exe",
    "C:\Python311\python.exe",
    "C:\Python310\python.exe",
    "C:\Python39\python.exe",
    "$env:LOCALAPPDATA\Programs\Python\Python314\python.exe",
    "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe",
    "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
    "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe",
    "$env:LOCALAPPDATA\Programs\Python\Python310\python.exe",
    "$env:LOCALAPPDATA\Programs\Python\Python39\python.exe",
    "C:\Program Files\Python314\python.exe",
    "C:\Program Files\Python313\python.exe",
    "C:\Program Files\Python312\python.exe",
    "C:\Program Files\Python311\python.exe",
    "C:\Program Files\Python310\python.exe",
    "C:\Program Files\Python39\python.exe"
)

# 取第一个存在的官方版
foreach ($c in $officialCandidates) {
    if (Test-Path $c) {
        $PythonExe = $c
        break
    }
}

# 没找到官方版, 用 Microsoft Store 版
if (-not $PythonExe) {
    $storePath = "$env:LOCALAPPDATA\Microsoft\WindowsApps\python.exe"
    if (Test-Path $storePath) {
        $PythonExe = $storePath
        $PythonIsStore = $true
        Write-Host "  [警告] 仅找到 Microsoft Store 版 Python" -ForegroundColor Yellow
        Write-Host "  这个版本在任务计划里运行可能有兼容问题, 但已尝试兼容" -ForegroundColor Yellow
        Write-Host "  如果任务失败, 建议安装官方版: https://www.python.org/downloads/" -ForegroundColor Yellow
    }
}

if (-not $PythonExe) {
    Write-Host "  [错误] 未找到 python.exe" -ForegroundColor Red
    Write-Host "  请确认 Python 已安装" -ForegroundColor Yellow
    throw "未找到 python.exe"
}

Write-Host "  找到: $PythonExe" -ForegroundColor Green
$version = & $PythonExe --version 2>&1
Write-Host "  版本: $version" -ForegroundColor Green

# ===== 2. 配置电源: 允许唤醒定时器 =====
Write-Host "配置电源选项..." -ForegroundColor Cyan
try {
    powercfg /SETACVALUEINDEX SCHEME_CURRENT SUB_SLEEP RTCWAKE 1 | Out-Null
    powercfg /SETDCVALUEINDEX SCHEME_CURRENT SUB_SLEEP RTCWAKE 1 | Out-Null
    powercfg /SETACTIVE SCHEME_CURRENT | Out-Null
    Write-Host "  已启用唤醒定时器" -ForegroundColor Green
} catch {
    Write-Host "  警告: 电源配置失败, 可能权限不足" -ForegroundColor Yellow
}

# ===== 3. 构建任务动作 =====
# 关键改动: 用 run_task.bat 包装器, 而不是直接调 python.exe
# 包装器会:
#   1. 设置 PATH 包含所有可能的 Python 路径 (兼容 Microsoft Store 版)
#   2. 设置 PYTHONPATH 包含用户 site-packages
#   3. 输出时间戳到日志
#   4. 调用 python wechat_daily.py
#   5. 把退出码透传
$RunBatPath = Join-Path $ProjectDir "run_task.bat"

if (-not (Test-Path $RunBatPath)) {
    Write-Host "  [错误] 找不到 run_task.bat" -ForegroundColor Red
    throw "run_task.bat 不存在"
}

Write-Host "  包装器: $RunBatPath" -ForegroundColor Green

$Action = New-ScheduledTaskAction -Execute $RunBatPath -WorkingDirectory $ProjectDir

# 触发器 1: 每天定时
$Trigger1 = New-ScheduledTaskTrigger -Daily -At $SendTime

# 触发器 2: 用户登录时补发 (如果今天还没发过)
$Trigger2 = New-ScheduledTaskTrigger -AtLogOn

# 设置
$Settings = New-ScheduledTaskSettingsSet -WakeToRun -StartWhenAvailable -RestartCount 2 -RestartInterval (New-TimeSpan -Minutes 5) -ExecutionTimeLimit (New-TimeSpan -Minutes 30) -DontStopOnIdleEnd -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries

# 主体: 当前用户交互式 (这样能操作微信窗口)
$User = "$env:USERDOMAIN\$env:USERNAME"
$Principal = New-ScheduledTaskPrincipal -UserId $User -LogonType Interactive -RunLevel Limited

# ===== 4. 注册任务 =====
# 先检查是否存在, 存在就删除 (现在是管理员, 可以删除)
$existingTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existingTask) {
    try {
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
        Write-Host "已删除旧任务: $TaskName" -ForegroundColor Yellow
    } catch {
        Write-Host "删除旧任务失败, 尝试用 schtasks 命令删除..." -ForegroundColor Yellow
        schtasks /Delete /TN $TaskName /F 2>&1 | Out-Host
    }
}

Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger @($Trigger1, $Trigger2) -Settings $Settings -Principal $Principal -Description "每日 $SendTime 自动向班级微信群发送定州市第八中学假期安全提醒并截图转发班主任群" | Out-Null

Write-Host ""
Write-Host "定时任务已安装: $TaskName" -ForegroundColor Green
Write-Host "  触发时间: 每天 $SendTime + 登录时补发"
Write-Host "  Python 路径: $PythonExe"
Write-Host "  脚本路径: $ScriptPath"
Write-Host "  日志文件: $LogFile"
Write-Host "  唤醒电脑: 已启用 WakeToRun"
Write-Host "  脚本运行期间: 自动阻止系统睡眠"
Write-Host ""
Write-Host "常用管理命令:"
Write-Host "  查看任务:        Get-ScheduledTask -TaskName '$TaskName'"
Write-Host "  立即手动触发:    Start-ScheduledTask -TaskName '$TaskName'"
Write-Host "  查看运行结果:    Get-ScheduledTaskInfo -TaskName '$TaskName'"
Write-Host "  查看任务日志:    type '$LogFile'"
Write-Host "  卸载任务:        Unregister-ScheduledTask -TaskName '$TaskName' -Confirm:`$false"
Write-Host ""
Write-Host "重要: 如果任务执行失败, 看 $LogFile 文件能找到具体错误"
Write-Host ""
Write-Host "笔记本用户必读 - 防合盖休眠:"
Write-Host "  控制面板 - 电源选项 - 选择关闭盖子的功能 - 设为 不采取任何操作"
Write-Host "  或运行管理员命令:"
Write-Host "    powercfg /SETACVALUEINDEX SCHEME_CURRENT SUB_BUTTONS LIDACTION 0"
Write-Host "    powercfg /SETDCVALUEINDEX SCHEME_CURRENT SUB_BUTTONS LIDACTION 0"
Write-Host "    powercfg /SETACTIVE SCHEME_CURRENT"
Write-Host ""
Write-Host "下一步:"
Write-Host "  1. 先手动执行一次测试: '$PythonExe' `"$ScriptPath`" --test"
Write-Host "  2. 确认无误后明天 $SendTime 即可自动执行"
Write-Host "  3. 如果定时任务没成功, 看 $LogFile 找原因"
