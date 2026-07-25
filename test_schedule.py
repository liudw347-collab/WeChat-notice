# -*- coding: utf-8 -*-
"""
快速测试定时任务 - 把下次触发时间设为 N 分钟后

使用方法 (推荐, 不会报权限错误):
    1. 按 Win+X → 选 "Windows PowerShell (管理员)" 或 "终端 (管理员)"
    2. cd 到项目目录: cd D:\\sth\\pro\\WeChat-notice
    3. 运行: python test_schedule.py 3

或非管理员运行 (会自动检测, 没权限就提示):
    python test_schedule.py 3        # 3 分钟后触发
    python test_schedule.py 5        # 5 分钟后触发
    python test_schedule.py          # 默认 3 分钟后触发

脚本会:
    1. 检测当前是否有管理员权限
    2. 计算当前时间 + N 分钟
    3. 临时修改 config.json 的 send_time
    4. 重新注册定时任务 (需管理员权限, 否则提示用户提权)
    5. 等到时间自动触发, 观察微信是否被自动操作

测试完后请恢复: 改 config.json 后重新运行 install.bat
"""

import sys
import json
import subprocess
import ctypes
import os
from datetime import datetime, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.json"
TASK_NAME = "WeChatDailySafety"


def is_admin():
    """检测当前进程是否有管理员权限"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


def relaunch_as_admin():
    """以管理员身份重新运行本脚本 (会弹 UAC 提示)"""
    params = " ".join(f'"{a}"' for a in sys.argv)
    try:
        # 用 ShellExecuteW 触发 UAC 提示
        rc = ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, params, str(BASE_DIR), 1
        )
        # rc <= 32 表示失败
        if rc <= 32:
            print("用户取消了 UAC 提示")
            return False
        return True
    except Exception as e:
        print(f"提权失败: {e}")
        return False


def main():
    # 解析参数
    if len(sys.argv) > 1:
        try:
            minutes = int(sys.argv[1])
        except ValueError:
            print(f"错误: 参数必须是数字 (分钟数), 你输入的是: {sys.argv[1]}")
            sys.exit(1)
    else:
        minutes = 3

    if minutes < 1 or minutes > 60:
        print(f"错误: 分钟数必须在 1-60 之间, 你输入的是: {minutes}")
        sys.exit(1)

    # === 检测管理员权限 ===
    if not is_admin():
        print("=" * 60)
        print("  需要管理员权限")
        print("=" * 60)
        print()
        print("  注册定时任务需要管理员权限 (Windows 安全限制)")
        print()
        print("  现在会弹出 UAC 提示, 请点击 是")
        print("  (如果不想弹 UAC, 可以手动以管理员身份打开 PowerShell")
        print("   再运行: python test_schedule.py " + str(minutes) + ")")
        print()
        ans = input("按回车弹 UAC 提权, 或输入 q 退出: ").strip().lower()
        if ans == "q":
            print("已取消")
            return

        # 重新以管理员身份运行本脚本
        if relaunch_as_admin():
            return  # 当前进程退出, 由新进程继续
        else:
            print()
            print("提权失败, 请手动操作:")
            print("  1. 按 Win+X → 选 'Windows PowerShell (管理员)' 或 '终端 (管理员)'")
            print(f"  2. cd /d {BASE_DIR}")
            print(f"  3. python test_schedule.py {minutes}")
            return

    # === 以下是有管理员权限的流程 ===
    # 计算触发时间
    now = datetime.now()
    trigger_time = now + timedelta(minutes=minutes)
    trigger_str = trigger_time.strftime("%H:%M")
    trigger_full = trigger_time.strftime("%Y-%m-%d %H:%M:%S")

    print("=" * 60)
    print("  快速测试定时任务 (管理员模式)")
    print("=" * 60)
    print()
    print(f"  当前时间: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  触发时间: {trigger_full} (约 {minutes} 分钟后)")
    print()
    print("  注意: 这会临时覆盖你 config.json 里的 send_time")
    print("        测试完后请恢复:")
    print("          1. 用记事本打开 config.json 改回原时间 (例如 07:30)")
    print("          2. 重新运行 install.bat")
    print()
    print("=" * 60)
    print()

    # 询问确认
    ans = input(f"确认 {minutes} 分钟后触发? [Y/n]: ").strip().lower()
    if ans not in ["", "y", "yes"]:
        print("已取消")
        return

    # 1. 修改 config.json
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            config = json.load(f)
        old_time = config.get("schedule", {}).get("send_time", "07:30")
        config["schedule"]["send_time"] = trigger_str
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        print(f"OK config.json: send_time {old_time} -> {trigger_str}")
    except Exception as e:
        print(f"修改 config.json 失败: {e}")
        return

    # 2. 重新注册定时任务 (运行 install_task.ps1)
    print()
    print("重新注册定时任务...")
    ps_script = BASE_DIR / "install_task.ps1"
    result = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
         "-File", str(ps_script)],
        capture_output=True, text=True
    )
    print(result.stdout)
    if result.returncode != 0:
        print(f"注册失败: {result.stderr}")
        return

    # 3. 验证任务计划程序里的下次运行时间
    print("=" * 60)
    print("  验证定时任务")
    print("=" * 60)
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         f"Get-ScheduledTaskInfo -TaskName '{TASK_NAME}' | "
         "Format-List LastRunTime, LastTaskResult, NextRunTime, NumberOfMissedRuns"],
        capture_output=True, text=True
    )
    print(result.stdout)

    # 4. 提醒用户
    print("=" * 60)
    print("  测试说明")
    print("=" * 60)
    print()
    print(f"  现在等 {minutes} 分钟, 到 {trigger_str} 时任务会自动触发")
    print()
    print("  在等待期间:")
    print("    - 不要关闭电脑/休眠")
    print("    - 不要锁定屏幕 (Win+L)")
    print("    - 微信窗口保持打开, 不要最小化")
    print("    - 可以正常用电脑, 但不要操作微信")
    print()
    print("  到点后观察:")
    print("    - 微信窗口会被自动激活到前台")
    print("    - 自动切到班级群发文案")
    print("    - 自动截图")
    print("    - 自动切到班主任群发截图")
    print()
    print("  发完后检查:")
    print("    1. 班级群是否收到了安全提醒文案")
    print("    2. 班主任群是否收到了截图")
    print("    3. 截图是否正确 (只包含聊天区域, 顶部能看到群名)")
    print()
    print("  测试完后恢复正式时间:")
    print("    1. 用记事本打开 config.json")
    print(f"    2. 把 send_time 从 {trigger_str} 改回 {old_time}")
    print("    3. 重新运行 install.bat")
    print()
    print("=" * 60)
    print(f"  触发时间: {trigger_full}")
    print(f"  距离触发还有约 {minutes} 分钟")
    print("=" * 60)

    # 5. 等待用户回车, 避免管理员窗口立即关闭
    print()
    input("按回车键关闭此窗口...")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n已取消")
    except Exception as e:
        print(f"执行失败: {e}")
        import traceback
        traceback.print_exc()
        input("按回车键关闭...")
