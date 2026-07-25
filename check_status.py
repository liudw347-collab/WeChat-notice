# -*- coding: utf-8 -*-
"""
查看今日发送状态 - 一行命令看清楚今天到底发没发, 发得对不对

用法:
    python check_status.py            # 看今天
    python check_status.py 2026-07-24 # 看指定日期
"""

import json
import sys
from datetime import date, datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
RECORDS_PATH = BASE_DIR / "sent_records.json"
LOGS_DIR = BASE_DIR / "logs"
SCREENSHOTS_DIR = BASE_DIR / "screenshots"


def main():
    target = sys.argv[1] if len(sys.argv) > 1 else date.today().isoformat()

    print("=" * 60)
    print(f"  发送状态查询 - {target}")
    print("=" * 60)
    print()

    # 1. 查发送记录
    print("[1] 发送记录 (sent_records.json):")
    if not RECORDS_PATH.exists():
        print("    文件不存在 - 从未发送过")
    else:
        try:
            records = json.load(open(RECORDS_PATH, "r", encoding="utf-8"))
            today_record = records.get(target)
            if today_record:
                print(f"    {target}: {json.dumps(today_record, ensure_ascii=False, indent=2)}")
            else:
                print(f"    {target}: 无记录 (今天没发送过)")
                print(f"    (历史记录共 {len(records)} 天)")
                if records:
                    recent = sorted(records.keys())[-3:]
                    print(f"    最近记录日期: {recent}")
        except Exception as e:
            print(f"    读取失败: {e}")
    print()

    # 2. 查日志文件
    print("[2] 日志文件 (logs/run_*.log):")
    log_file = LOGS_DIR / f"run_{target}.log"
    if not log_file.exists():
        print(f"    {log_file.name} 不存在 - 今天没运行过")
    else:
        try:
            content = log_file.read_text(encoding="utf-8", errors="replace")
            lines = content.splitlines()
            print(f"    {log_file.name} ({len(lines)} 行)")
            print(f"    --- 关键信息 ---")
            # 显示最后 30 行
            for line in lines[-30:]:
                print(f"    {line}")
        except Exception as e:
            print(f"    读取失败: {e}")
    print()

    # 3. 查截图
    print("[3] 截图文件 (screenshots/screenshot_*.png):")
    if not SCREENSHOTS_DIR.exists():
        print("    screenshots 目录不存在")
    else:
        shots = sorted(SCREENSHOTS_DIR.glob(f"screenshot_{target}_*.png"))
        if not shots:
            print(f"    没有 {target} 的截图")
        else:
            for s in shots:
                size_kb = s.stat().st_size / 1024
                print(f"    {s.name} ({size_kb:.1f} KB)")
    print()

    # 4. 查定时任务状态
    print("[4] 定时任务状态:")
    import subprocess
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         "Get-ScheduledTaskInfo -TaskName 'WeChatDailySafety' | "
         "Format-List LastRunTime, LastTaskResult, NextRunTime, NumberOfMissedRuns"],
        capture_output=True, text=True
    )
    if result.stdout.strip():
        for line in result.stdout.splitlines():
            if line.strip():
                print(f"    {line}")
    else:
        print("    查询失败 (可能不是 Windows 或任务未注册)")
    print()

    print("=" * 60)
    print("  提示:")
    print("=" * 60)
    print()
    print("  - 如果'发送记录'显示 success=true, 说明今天已发成功")
    print("    后续触发会被'防重复机制'跳过 (避免群里刷屏)")
    print()
    print("  - 想强制再发一次测试:")
    print("    1. 删掉 sent_records.json 里今天那一条")
    print("    2. 或直接删除 sent_records.json")
    print("    3. 再运行 python wechat_daily.py")
    print()
    print("  - 想发到文件传输助手不影响真实群:")
    print("    python wechat_daily.py --test")


if __name__ == "__main__":
    main()
