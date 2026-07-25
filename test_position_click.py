# -*- coding: utf-8 -*-
"""
位置点击测试工具 - 测试 'open_method=position' 方案是否可行

使用方法:
    1. 打开 PC 微信
    2. 鼠标点击班级群 (进入班级群)
    3. 鼠标点击班主任群 (进入班主任群)
    4. 运行: python test_position_click.py
    5. 工具会依次点击会话列表第 1 项和第 2 项, 看是否切换到了正确的群
"""

import sys
import time
import logging
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("test")


def main():
    print("=" * 60)
    print("  位置点击测试工具")
    print("=" * 60)
    print()
    print("  本工具测试 'open_method=position' 方案")
    print()
    print("  测试前请确保:")
    print("    1. PC 微信已打开")
    print("    2. 鼠标点击过班级群 (进入班级群聊天界面)")
    print("    3. 鼠标点击过班主任群 (进入班主任群聊天界面)")
    print("    (顺序: 班级群先, 班主任群后)")
    print()
    print("  这样会话列表顺序应该是:")
    print("    第 1 项 = 班主任群 (最近打开)")
    print("    第 2 项 = 班级群")
    print()
    input("准备好后按回车开始测试...")
    print()

    # 找微信窗口
    from pywinauto import Desktop
    desktop = Desktop(backend="uia")
    win = None
    for title_pattern in ["微信", "WeChat"]:
        try:
            wins = desktop.windows(title=title_pattern)
            if wins:
                win = wins[0]
                break
        except Exception:
            pass
    if not win:
        print("未找到微信窗口")
        return

    try:
        if win.is_minimized():
            win.restore()
        win.set_focus()
        time.sleep(1.0)
    except Exception:
        pass

    rect = win.rectangle()
    print(f"微信窗口: ({rect.left},{rect.top},{rect.right},{rect.bottom}) {rect.width()}x{rect.height()}")
    print()

    # 导入 open_chat_by_session_position
    from wechat_daily import open_chat_by_session_position

    # 测试点击第 2 项 (应该是班级群)
    print("=" * 60)
    print("  测试 1: 点击会话列表第 2 项 (应该是班级群)")
    print("=" * 60)
    print("  3 秒后开始点击...")
    time.sleep(3)
    if open_chat_by_session_position(win, 2):
        print("  ✓ 点击完成")
    else:
        print("  ✗ 点击失败")
    print()
    print("  请观察微信当前显示的是哪个群?")
    print("    A. 班级群 (正确!)")
    print("    B. 班主任群 (位置不对, 可能要点第 1 项)")
    print("    C. 其他群 (顺序不对)")
    print("    D. 没切换 (坐标不对)")
    result1 = input("  请输入 A/B/C/D: ").strip().upper()
    print()

    # 测试点击第 1 项 (应该是班主任群)
    print("=" * 60)
    print("  测试 2: 点击会话列表第 1 项 (应该是班主任群)")
    print("=" * 60)
    print("  3 秒后开始点击...")
    time.sleep(3)
    if open_chat_by_session_position(win, 1):
        print("  ✓ 点击完成")
    else:
        print("  ✗ 点击失败")
    print()
    print("  请观察微信当前显示的是哪个群?")
    print("    A. 班主任群 (正确!)")
    print("    B. 班级群")
    print("    C. 其他群")
    print("    D. 没切换")
    result2 = input("  请输入 A/B/C/D: ").strip().upper()
    print()

    print("=" * 60)
    print("  测试结果")
    print("=" * 60)
    print(f"  测试 1 (点击第 2 项): {result1}")
    print(f"  测试 2 (点击第 1 项): {result2}")
    print()

    if result1 == "A" and result2 == "A":
        print("  ✓✓ 位置点击方案完美工作!")
        print("  config.json 里 open_method 设为 'position' 即可使用此方案")
        print()
        print("  每天只需要:")
        print("    1. 电脑开机后打开微信")
        print("    2. 鼠标点一下班级群")
        print("    3. 鼠标点一下班主任群")
        print("  然后定时任务会自动完成发送")
    elif result1 == "D" or result2 == "D":
        print("  ✗ 坐标不对, 需要调整")
        print("  可能原因:")
        print("    - 微信窗口大小/位置不同")
        print("    - 微信版本不同, 左侧栏布局不同")
        print("  请把测试输出截图给开发者调整坐标")
    else:
        print("  ⚠ 位置不对, 可能需要调整 position 值")
        print("  可以尝试修改 config.json 里的:")
        print("    class_group_position (班级群位置)")
        print("    teacher_group_position (班主任群位置)")
        print(f"  根据测试结果, 班级群可能在第 {2 if result1=='B' else '?'} 项")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"执行失败: {e}")
        import traceback
        traceback.print_exc()
    input("\n按回车键退出...")
