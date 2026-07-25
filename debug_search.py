# -*- coding: utf-8 -*-
"""
搜索框调试工具 - 找出你的微信搜索框到底是什么控件

使用方法:
    1. 打开 PC 微信 (停在最主界面, 不要进入任何聊天)
    2. 运行: python debug_search.py
    3. 工具会:
       - 打印所有 Edit 控件 (搜索框通常是 Edit)
       - 打印顶部 100px 区域内的所有控件
       - 尝试用各种方式找搜索框
       - 把结果输出, 方便贴给开发者
"""

import sys
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))


def find_wechat_window():
    from pywinauto import Desktop
    desktop = Desktop(backend="uia")
    for title_pattern in ["微信", "WeChat"]:
        try:
            wins = desktop.windows(title=title_pattern)
            if wins:
                return wins[0]
        except Exception:
            pass
    raise RuntimeError("未找到微信窗口")


def main():
    print("=" * 60)
    print("  微信搜索框调试工具")
    print("=" * 60)
    print()

    print("[1] 查找微信窗口...")
    win = find_wechat_window()
    rect = win.rectangle()
    print(f"  窗口位置: ({rect.left},{rect.top},{rect.right},{rect.bottom})")
    print(f"  尺寸: {rect.width()}x{rect.height()}")
    print()

    print("[2] 激活窗口...")
    try:
        if win.is_minimized():
            win.restore()
        win.set_focus()
        time.sleep(1.5)
    except Exception as e:
        print(f"  警告: {e}")
    print()

    print("[3] 列出所有 Edit 控件 (搜索框通常是 Edit)...")
    print("-" * 60)
    try:
        edits = win.descendants(control_type="Edit")
        print(f"找到 {len(edits)} 个 Edit 控件:")
        for i, e in enumerate(edits):
            try:
                r = e.rectangle()
                info = win.element_info
                e_info = e.element_info
                visible = "?"
                try:
                    visible = e.is_visible()
                except Exception:
                    pass
                print(f"  [{i}] {e_info.control_type} '{e_info.name}'")
                print(f"      位置: ({r.left},{r.top},{r.right},{r.bottom}) {r.width()}x{r.height()}")
                print(f"      auto_id={e_info.automation_id}, class={e_info.class_name}")
                print(f"      visible={visible}")
            except Exception as ex:
                print(f"  [{i}] 读取失败: {ex}")
    except Exception as e:
        print(f"  找 Edit 控件失败: {e}")
    print()

    print("[4] 列出顶部 100px 内的所有控件 (搜索框在顶部)...")
    print("-" * 60)
    try:
        all_controls = win.descendants()
        top_y = rect.top + 100
        top_controls = []
        for c in all_controls:
            try:
                r = c.rectangle()
                if r.top < top_y and r.top >= rect.top:
                    top_controls.append((c, r))
            except Exception:
                continue

        print(f"找到 {len(top_controls)} 个顶部控件:")
        for i, (c, r) in enumerate(top_controls[:30]):
            try:
                info = c.element_info
                print(f"  [{i}] {info.control_type} '{info.name[:50] if info.name else ''}'")
                print(f"      位置: ({r.left},{r.top},{r.right},{r.bottom}) {r.width()}x{r.height()}")
                print(f"      auto_id={info.automation_id}, class={info.class_name}")
            except Exception as ex:
                print(f"  [{i}] 读取失败: {ex}")
    except Exception as e:
        print(f"  找顶部控件失败: {e}")
    print()

    print("[5] 尝试用各种方式找搜索框...")
    print("-" * 60)
    attempts = [
        {"auto_id": "SearchInput"},
        {"auto_id": "search_input"},
        {"auto_id": "SearchBox"},
        {"auto_id": "fnSearchEdit"},
        {"class_name": "mmui::SearchLineEdit"},
        {"class_name": "SearchLineEdit"},
        {"control_type": "Edit"},
    ]
    for kwargs in attempts:
        try:
            found = win.child_window(**kwargs)
            if found.exists(timeout=0.5):
                r = found.rectangle()
                print(f"  ✓ 找到: {kwargs}")
                print(f"    位置: ({r.left},{r.top},{r.right},{r.bottom}) {r.width()}x{r.height()}")
            else:
                print(f"  ✗ 不存在: {kwargs}")
        except Exception as e:
            print(f"  ✗ 错误: {kwargs} -> {e}")
    print()

    print("=" * 60)
    print("  调试完成")
    print("=" * 60)
    print()
    print("请把上面的输出全部复制粘贴给开发者")
    print("开发者会根据这些信息调整搜索框定位方式")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"执行失败: {e}")
        import traceback
        traceback.print_exc()
    input("\n按回车键退出...")
