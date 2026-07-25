# -*- coding: utf-8 -*-
"""
搜索后控件调试 - 用 uiautomation 打印搜索后微信窗口的所有控件

使用方法:
    1. 打开 PC 微信, 回到主界面
    2. 运行: python debug_search_uia.py
    3. 工具会:
       - 让你输入群名
       - Ctrl+F 搜索
       - 打印微信窗口的所有 Text/Edit 控件 (uiautomation 视角)
       - 截图保存
       - 让你看搜索框当前内容是什么
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
    print("  搜索后 uiautomation 控件调试")
    print("=" * 60)
    print()
    print("  本工具会:")
    print("    1. 让你输入群名")
    print("    2. Ctrl+F 搜索 (用 PowerShell SendKeys)")
    print("    3. 打印搜索后微信窗口的所有 Text/Edit 控件")
    print("    4. 截图保存")
    print("    5. 让你看搜索框当前内容是什么")
    print()
    name = input("请输入要搜索的群名: ").strip()
    if not name:
        return

    # 找微信窗口 (pywinauto)
    print()
    print("[1/5] 查找并激活微信窗口...")
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

    # 用 uiautomation 找微信窗口
    print("[2/5] 用 uiautomation 找微信窗口...")
    try:
        import uiautomation as uia
    except ImportError:
        print("  未安装 uiautomation, 请运行: pip install uiautomation")
        return

    wechat_win = uia.WindowControl(Name="微信")
    if not wechat_win.Exists(1):
        wechat_win = uia.WindowControl(SubName="微信")
        if not wechat_win.Exists(1):
            print("  uiautomation 找不到微信窗口")
            return
    print(f"  找到: {wechat_win.Name}")
    print()

    # Ctrl+F 搜索 (用 PowerShell SendKeys)
    print("[3/5] Ctrl+F 搜索...")
    import subprocess
    subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         "Add-Type -AssemblyName System.Windows.Forms; "
         "[System.Windows.Forms.SendKeys]::SendWait('^f')"],
        capture_output=True, timeout=5
    )
    time.sleep(1.0)

    # 设置剪贴板 + 粘贴
    tmp = Path(BASE_DIR) / "logs" / "_debug_search.txt"
    tmp.parent.mkdir(exist_ok=True)
    tmp.write_text(name, encoding="utf-8")
    subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         f"$text = Get-Content -LiteralPath '{tmp}' -Raw -Encoding UTF8; "
         "Set-Clipboard -Value $text"],
        capture_output=True, timeout=5
    )
    time.sleep(0.5)
    subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         "Add-Type -AssemblyName System.Windows.Forms; "
         "[System.Windows.Forms.SendKeys]::SendWait('^v')"],
        capture_output=True, timeout=5
    )
    print(f"  已粘贴群名: {name}")
    time.sleep(3.0)  # 等搜索结果加载
    print()

    # 截图
    print("[4/5] 截图保存当前界面...")
    try:
        from PIL import ImageGrab
        rect = win.rectangle()
        bbox = (rect.left, rect.top, rect.right, rect.bottom)
        img = ImageGrab.grab(bbox=bbox)
        shot_path = DEBUG_DIR / f"search_uia_{date.today().isoformat()}.png"
        img.save(str(shot_path))
        print(f"  已保存: {shot_path}")
    except Exception as e:
        print(f"  截图失败: {e}")
    print()

    # 打印所有 Edit 控件 (找搜索框)
    print("[5/5] 打印所有 Edit 控件 (搜索框是 Edit)...")
    print("-" * 60)
    try:
        edits = wechat_win.GetChildren()
        print(f"微信窗口的直接子控件: {len(edits)} 个")
        for i, child in enumerate(edits):
            try:
                print(f"  [{i}] {child.ControlTypeName} '{child.Name}'")
            except Exception:
                pass
        print()

        # 深度遍历找 Edit
        print("深度遍历找 Edit 控件 (搜索框):")
        edit_count = 0
        for ctrl in wechat_win.GetChildren()[0].GetChildren() if wechat_win.GetChildren() else []:
            try:
                if ctrl.ControlTypeName == "EditControl":
                    edit_count += 1
                    print(f"  Edit: '{ctrl.Name}' value='{ctrl.GetValuePattern().Value if ctrl.GetValuePattern().Exists() else '?'}'")
            except Exception:
                pass
        print(f"找到 {edit_count} 个 Edit")
        print()

        # 找所有 Text 控件
        print("所有 Text 控件 (找搜索结果, 包括 <em> 标记):")
        text_count = 0
        for ctrl in wechat_win.GetChildren():
            try:
                _walk_text(ctrl, 0, 5)
            except Exception as e:
                print(f"  遍历失败: {e}")
    except Exception as e:
        print(f"  遍历失败: {e}")

    print()
    print("-" * 60)
    print("请把上面的输出全部复制粘贴给开发者")
    print(f"同时把截图 {DEBUG_DIR}/search_uia_*.png 也给开发者")


def _walk_text(ctrl, depth, max_depth):
    """递归遍历打印 Text 控件"""
    if depth > max_depth:
        return
    try:
        if ctrl.ControlTypeName == "TextControl":
            name = ctrl.Name
            if name and len(name) < 200:
                # 标记 <em>
                marker = " <<< <em>标记!" if "<em>" in name else ""
                print(f"  {'  ' * depth}Text: '{name}'{marker}")
    except Exception:
        pass
    try:
        for child in ctrl.GetChildren():
            _walk_text(child, depth + 1, max_depth)
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
