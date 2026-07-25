# -*- coding: utf-8 -*-
"""
配置向导 - 交互式 CLI
让老师不需要懂 JSON 也能完成配置:
- 输入班级群名
- 输入班主任群名
- 选择发送时间
- 测试发送 (可选)
- 注册 cron 定时任务
"""

import json
import os
import re
import subprocess
from pathlib import Path
from datetime import datetime

PROJECT_DIR = Path("/storage/emulated/0/WeChat-notice")
ANDROID_DIR = PROJECT_DIR / "android"
CONFIG_PATH = ANDROID_DIR / "config.json"
CRON_MARKER = "wechat_daily_android.py"

# ANSI 颜色
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
CYAN = '\033[0;36m'
RED = '\033[0;31m'
NC = '\033[0m'


def info(msg):
    print(f"{CYAN}[?]{NC} {msg}")


def ok(msg):
    print(f"{GREEN}[OK]{NC} {msg}")


def warn(msg):
    print(f"{YELLOW}[!]{NC} {msg}")


def err(msg):
    print(f"{RED}[ERR]{NC} {msg}")


def input_with_default(prompt, default=""):
    if default:
        s = input(f"{CYAN}[?]{NC} {prompt} [{default}]: ").strip()
        return s if s else default
    else:
        return input(f"{CYAN}[?]{NC} {prompt}: ").strip()


def load_existing_config():
    if CONFIG_PATH.exists():
        try:
            return json.load(open(CONFIG_PATH, "r", encoding="utf-8"))
        except Exception:
            return {}
    return {}


def save_config(cfg):
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
    ok(f"配置已保存到 {CONFIG_PATH}")


def validate_group_name(name):
    """群名校验"""
    if not name:
        return False, "群名不能为空"
    if len(name) > 50:
        return False, "群名太长 (超过 50 字符)"
    if name.lower() in ["test", "测试"]:
        return False, "请输入真实的群名"
    return True, ""


def validate_time(t):
    """时间校验 HH:MM"""
    if not re.match(r"^\d{1,2}:\d{2}$", t):
        return False, "时间格式错误, 应为 HH:MM, 例如 07:30"
    h, m = t.split(":")
    h, m = int(h), int(m)
    if not (0 <= h <= 23 and 0 <= m <= 59):
        return False, "时间数值超出范围"
    return True, ""


def setup_cron(send_time):
    """注册 cron 定时任务"""
    h, m = send_time.split(":")
    python_bin = subprocess.check_output(["which", "python"]).decode().strip()
    script_path = str(ANDROID_DIR / "wechat_daily_android.py")
    log_path = str(ANDROID_DIR / "logs" / "cron.log")
    cron_line = f"{m} {h} * * * {python_bin} {script_path} >> {log_path} 2>&1"

    # 备份并替换
    try:
        existing = subprocess.check_output(["crontab", "-l"], stderr=subprocess.DEVNULL).decode()
    except Exception:
        existing = ""

    new_lines = [l for l in existing.splitlines() if CRON_MARKER not in l]
    new_lines.append(cron_line)
    new_content = "\n".join(new_lines) + "\n"

    proc = subprocess.Popen(["crontab", "-"], stdin=subprocess.PIPE)
    proc.communicate(new_content.encode())
    if proc.returncode == 0:
        ok(f"已注册 cron 任务: 每天 {send_time} 自动执行")
    else:
        err("cron 注册失败")
    return cron_line


def test_send():
    """询问是否测试发送"""
    print()
    info("现在可以测试发送一条消息到「文件传输助手」")
    info("(不会影响真实群, 仅验证脚本与微信对接正常)")
    info("请确保手机微信已登录, 然后按回车开始测试")
    info("测试过程中会自动打开微信, 请勿手动操作手机")
    ans = input(f"{CYAN}[?]{NC} 现在测试吗? [Y/n]: ").strip().lower()
    if ans in ["", "y", "yes"]:
        script = str(ANDROID_DIR / "wechat_daily_android.py")
        ok("开始测试, 请观察手机...")
        os.system(f"python {script} --test")
        print()
        info("如果文件传输助手收到了测试消息+截图, 说明配置成功!")
        info("如果没收到, 请查看日志: cat " + str(ANDROID_DIR / "logs" / "run_$(date +%F).log"))
    else:
        warn("已跳过测试, 你可以稍后手动运行: python " + str(ANDROID_DIR / "wechat_daily_android.py") + " --test")


def main():
    print()
    print("=" * 60)
    print("  定州市第八中学 安全提醒 - 配置向导")
    print("=" * 60)
    print()
    print("本向导将引导你完成 3 步配置:")
    print("  1. 班级群名")
    print("  2. 班主任群名")
    print("  3. 发送时间")
    print()

    existing = load_existing_config()
    existing_wechat = existing.get("wechat", {})
    existing_schedule = existing.get("schedule", {})

    # === 1. 班级群名 ===
    while True:
        class_group = input_with_default(
            "请输入班级微信群名 (必须与微信中显示完全一致)",
            existing_wechat.get("class_group_name", "")
        )
        valid, msg = validate_group_name(class_group)
        if valid:
            ok(f"班级群: {class_group}")
            break
        err(msg)

    # === 2. 班主任群名 ===
    while True:
        teacher_group = input_with_default(
            "请输入班主任工作群名",
            existing_wechat.get("teacher_group_name", "")
        )
        valid, msg = validate_group_name(teacher_group)
        if valid:
            ok(f"班主任群: {teacher_group}")
            break
        err(msg)

    # === 3. 发送时间 ===
    while True:
        send_time = input_with_default(
            "请输入每日发送时间 (学校要求 8:00 前, 推荐 07:30)",
            existing_schedule.get("send_time", "07:30")
        )
        valid, msg = validate_time(send_time)
        if valid:
            ok(f"发送时间: 每天 {send_time}")
            break
        err(msg)

    # === 保存配置 ===
    print()
    print("=" * 60)
    print("  配置确认")
    print("=" * 60)
    print(f"  班级微信群: {class_group}")
    print(f"  班主任群:   {teacher_group}")
    print(f"  发送时间:   每天 {send_time}")
    print(f"  文案内容:   定州市第八中学假期安全提醒 (日期每天自动更新)")
    print("=" * 60)
    ans = input(f"{CYAN}[?]{NC} 确认无误? [Y/n]: ").strip().lower()
    if ans not in ["", "y", "yes"]:
        warn("已取消, 配置未保存")
        return

    cfg = {
        "_comment": "由 config_wizard.py 自动生成",
        "wechat": {
            "class_group_name": class_group,
            "teacher_group_name": teacher_group
        },
        "schedule": {
            "send_time": send_time,
            "max_retries": 3,
            "retry_interval_sec": 60
        },
        "alert": {
            "enable_vibrate": True,
            "enable_notification": True,
            "enable_termux_notification": True
        }
    }
    save_config(cfg)

    # === 注册 cron ===
    print()
    info("正在注册定时任务...")
    setup_cron(send_time)

    # === 启动 cron 服务 ===
    info("启动 cron 服务...")
    os.system("pkill crond 2>/dev/null; crond")
    ok("cron 服务已启动")

    # === 测试 ===
    test_send()

    print()
    print("=" * 60)
    print(f"{GREEN}  全部完成!{NC}")
    print("=" * 60)
    print()
    print("重要提示:")
    print("  1. 关闭 Termux/Termux:API/ATX 的电池优化 (设置->应用)")
    print("  2. 在 Termux 通知栏长按 -> 锁定 (防止被系统清理)")
    print("  3. 在手机自启动管理中允许 Termux")
    print(f"  4. 每天约 {send_time} 自动执行, 失败会震动告警")
    print()
    print("修改配置: 重新运行 python " + str(ANDROID_DIR / "easy-install" / "config_wizard.py"))
    print("立即手动发一次: python " + str(ANDROID_DIR / "wechat_daily_android.py"))
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n已取消")
    except Exception as e:
        err(f"配置失败: {e}")
        import traceback
        traceback.print_exc()
