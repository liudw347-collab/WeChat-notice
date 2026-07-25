# -*- coding: utf-8 -*-
"""
配置保存助手 - 配合 HTML 配置页面使用

用法 1: 交互式粘贴
    python save_config.py
    (然后粘贴 HTML 页面生成的 JSON, 按 Ctrl+D 结束)

用法 2: 从剪贴板读取
    python save_config.py --clip

用法 3: 从文件读取
    python save_config.py --file /sdcard/Download/config.json
"""

import json
import os
import sys
import subprocess
from pathlib import Path

CONFIG_PATH = Path("/storage/emulated/0/WeChat-notice/android/config.json")

GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
CYAN = '\033[0;36m'
RED = '\033[0;31m'
NC = '\033[0m'


def ok(msg): print(f"{GREEN}[OK]{NC} {msg}")
def info(msg): print(f"{CYAN}[?]{NC} {msg}")
def err(msg): print(f"{RED}[ERR]{NC} {msg}")
def warn(msg): print(f"{YELLOW}[!]{NC} {msg}")


def validate_config(cfg):
    """简单校验配置格式"""
    if not isinstance(cfg, dict):
        return False, "配置必须是 JSON 对象"
    w = cfg.get("wechat", {})
    if not w.get("class_group_name"):
        return False, "缺少 wechat.class_group_name"
    if not w.get("teacher_group_name"):
        return False, "缺少 wechat.teacher_group_name"
    s = cfg.get("schedule", {})
    t = s.get("send_time", "07:30")
    import re
    if not re.match(r"^\d{1,2}:\d{2}$", t):
        return False, f"send_time 格式错误: {t}"
    return True, ""


def save(cfg):
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
    ok(f"配置已保存到 {CONFIG_PATH}")
    print()
    print("配置内容:")
    print(json.dumps(cfg, ensure_ascii=False, indent=2))


def read_from_clipboard():
    """从 Android 剪贴板读取 (需要 termux-api)"""
    try:
        result = subprocess.run(["termux-clipboard-get"], capture_output=True, text=True, timeout=5)
        return result.stdout.strip()
    except Exception as e:
        err(f"读取剪贴板失败: {e}")
        return None


def main():
    args = sys.argv[1:]
    content = None

    if args:
        if args[0] == "--clip":
            info("从剪贴板读取配置...")
            content = read_from_clipboard()
            if not content:
                err("剪贴板为空或读取失败")
                return
        elif args[0] == "--file":
            if len(args) < 2:
                err("请指定文件路径, 例如: --file /sdcard/Download/config.json")
                return
            try:
                content = Path(args[1]).read_text(encoding="utf-8")
            except Exception as e:
                err(f"读取文件失败: {e}")
                return
    else:
        info("请粘贴配置 JSON (从 HTML 配置页面复制)")
        info("粘贴完成后按 Ctrl+D 结束")
        print()
        try:
            content = sys.stdin.read().strip()
        except KeyboardInterrupt:
            print()
            warn("已取消")
            return

    if not content:
        err("未读取到任何内容")
        return

    # 尝试解析 JSON
    try:
        cfg = json.loads(content)
    except json.JSONDecodeError as e:
        err(f"JSON 格式错误: {e}")
        print()
        print("收到的内容前 200 字符:")
        print(content[:200])
        return

    # 校验
    valid, msg = validate_config(cfg)
    if not valid:
        err(f"配置校验失败: {msg}")
        return

    # 确认
    print()
    print("=" * 50)
    print("配置确认:")
    print(f"  班级群: {cfg['wechat']['class_group_name']}")
    print(f"  班主任群: {cfg['wechat']['teacher_group_name']}")
    print(f"  发送时间: {cfg.get('schedule', {}).get('send_time', '07:30')}")
    print("=" * 50)
    ans = input(f"{CYAN}[?]{NC} 确认保存? [Y/n]: ").strip().lower()
    if ans not in ["", "y", "yes"]:
        warn("已取消")
        return

    save(cfg)

    # 询问是否立即注册 cron
    print()
    ans = input(f"{CYAN}[?]{NC} 是否立即注册定时任务? [Y/n]: ").strip().lower()
    if ans in ["", "y", "yes"]:
        send_time = cfg.get("schedule", {}).get("send_time", "07:30")
        h, m = send_time.split(":")
        script_path = "/storage/emulated/0/WeChat-notice/android/wechat_daily_android.py"
        log_path = "/storage/emulated/0/WeChat-notice/android/logs/cron.log"
        python_bin = subprocess.check_output(["which", "python"]).decode().strip()
        cron_line = f"{m} {h} * * * {python_bin} {script_path} >> {log_path} 2>&1"

        try:
            existing = subprocess.check_output(["crontab", "-l"], stderr=subprocess.DEVNULL).decode()
        except Exception:
            existing = ""

        new_lines = [l for l in existing.splitlines() if "wechat_daily_android.py" not in l]
        new_lines.append(cron_line)
        new_content = "\n".join(new_lines) + "\n"

        proc = subprocess.Popen(["crontab", "-"], stdin=subprocess.PIPE)
        proc.communicate(new_content.encode())
        if proc.returncode == 0:
            ok(f"已注册 cron: 每天 {send_time} 自动执行")
            os.system("pkill crond 2>/dev/null; crond")
            ok("cron 服务已启动")
        else:
            err("cron 注册失败")

    print()
    print("=" * 50)
    print(f"{GREEN}  配置完成!{NC}")
    print("=" * 50)
    print()
    print("接下来:")
    print("  1. 测试发送 (发到文件传输助手):")
    print(f"     python {script_path} --test")
    print()
    print("  2. 立即手动发一次:")
    print(f"     python {script_path}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        err(f"执行失败: {e}")
        import traceback
        traceback.print_exc()
