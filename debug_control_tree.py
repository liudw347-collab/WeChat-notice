# -*- coding: utf-8 -*-
"""
微信控件深度调试 - 用 pywinauto 的 print_control_identifier 打印完整控件树

使用方法:
    1. 打开 PC 微信, 回到主界面
    2. 运行: python debug_control_tree.py
    3. 工具会:
       - Ctrl+F 打开搜索
       - 输入群名
       - 等 3 秒让搜索结果加载
       - 把当前微信窗口的完整控件树打印出来
       - 同时截一张图保存
    4. 把输出贴给开发者
"""

import sys
import time
import logging
from pathlib import Path
from datetime import date

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("debug")

DEBUG_DIR = BASE_DIR / "debug"
DEBUG_DIR.mkdir(exist_ok=True)


def main():
    print("=" * 60)
    print("  微信控件深度调试工具")
    print("=" * 60)
    print()
    print("  这个工具会:")
    print("    1. 让你输入群名")
    print("    2. Ctrl+F 搜索")
    print("    3. 等搜索结果加载")
    print("    4. 打印微信窗口的完整控件树")
    print("    5. 截图保存")
    print()
    name = input("请输入要搜索的群名 (回车确认): ").strip()
    if not name:
        print("未输入群名, 退出")
        return

    print()
    print("[1/4] 查找并激活微信窗口...")
    from pywinauto import Desktop
    import pywinauto.keyboard as kb

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
        print("  未找到微信窗口")
        return
    try:
        if win.is_minimized():
            win.restore()
        win.set_focus()
        time.sleep(1.0)
    except Exception as e:
        print(f"  激活失败: {e}")
    print("  已激活")
    print()

    print("[2/4] Ctrl+F 搜索...")
    try:
        kb.send_keys("^f")
        time.sleep(1.0)

        import subprocess
        tmp = Path(BASE_DIR) / "logs" / "_debug_search.txt"
        tmp.parent.mkdir(exist_ok=True)
        tmp.write_text(name, encoding="utf-8")
        ps_cmd = (
            f"$text = Get-Content -LiteralPath '{tmp}' -Raw -Encoding UTF8; "
            "Set-Clipboard -Value $text"
        )
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_cmd],
            capture_output=True, timeout=5
        )
        time.sleep(0.3)
        kb.send_keys("^v")
        print(f"  已粘贴群名: {name}")
        time.sleep(3.0)  # 等搜索结果加载
    except Exception as e:
        print(f"  搜索失败: {e}")
        return
    print("  搜索完成")
    print()

    print("[3/4] 截图...")
    try:
        from PIL import ImageGrab
        rect = win.rectangle()
        bbox = (rect.left, rect.top, rect.right, rect.bottom)
        img = ImageGrab.grab(bbox=bbox)
        shot_path = DEBUG_DIR / f"search_result_{date.today().isoformat()}.png"
        img.save(str(shot_path))
        print(f"  已保存: {shot_path}")
    except Exception as e:
        print(f"  截图失败: {e}")
    print()

    print("[4/4] 打印控件树 (深度 6)...")
    print("-" * 60)
    print("下面是微信窗口的完整控件树 (深度限制 6 层):")
    print("-" * 60)
    print()

    try:
        # print_control_identifier 是 pywinauto 内置的控件树打印函数
        win.print_control_identifier(depth=6)
    except Exception as e:
        print(f"print_control_identifier 失败: {e}")
        print()
        print("尝试手动遍历...")
        try:
            _manual_dump(win, 0, 6)
        except Exception as e2:
            print(f"手动遍历也失败: {e2}")

    print()
    print("-" * 60)
    print()
    print("[额外] 列出所有可见的 Text 和 ListItem 控件:")
    print()

    found_count = 0
    try:
        for ctrl_type in ["Text", "ListItem", "Button", "Edit", "Custom", "Group", "Pane"]:
            print(f"\n--- {ctrl_type} 控件 ---")
            try:
                controls = win.descendants(control_type=ctrl_type)
                print(f"  找到 {len(controls)} 个 {ctrl_type}")
                for i, c in enumerate(controls[:30]):  # 每种最多打印 30 个
                    try:
                        r = c.rectangle()
                        info = c.element_info
                        text = info.name or ""
                        print(f"  [{i}] '{text[:60]}' "
                              f"({r.left},{r.top},{r.right},{r.bottom}) "
                              f"{r.width()}x{r.height()} "
                              f"auto_id={info.automation_id} "
                              f"class={info.class_name}")
                        found_count += 1
                    except Exception as e:
                        print(f"  [{i}] 读取失败: {e}")
            except Exception as e:
                print(f"  找 {ctrl_type} 失败: {e}")
    except Exception as e:
        print(f"枚举失败: {e}")

    print()
    print("-" * 60)
    print(f"总计找到 {found_count} 个控件")
    print("-" * 60)
    print()
    print("请把上面的输出全部复制粘贴给开发者")
    print(f"同时把截图 {DEBUG_DIR}/search_result_*.png 也给开发者")


def _manual_dump(ctrl, indent, max_depth):
    """手动遍历控件树"""
    if indent > max_depth:
        return
    prefix = "  " * indent
    try:
        r = ctrl.rectangle()
        info = ctrl.element_info
        text = info.name or ""
        print(f"{prefix}- [{info.control_type}] '{text[:50]}' "
              f"({r.left},{r.top},{r.right},{r.bottom}) "
              f"auto_id={info.automation_id} class={info.class_name}")
    except Exception as e:
        print(f"{prefix}- (读取失败: {e})")
        return
    try:
        for child in ctrl.children():
            _manual_dump(child, indent + 1, max_depth)
    except Exception:
        pass


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"执行失败: {e}")
        import traceback
        traceback.print_exc()
    input("\n按回车键退出...")
