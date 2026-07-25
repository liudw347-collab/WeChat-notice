# -*- coding: utf-8 -*-
"""
搜索结果调试工具 - 看微信搜索后到底显示了哪些分类和群

使用方法:
    1. 打开 PC 微信, 回到主界面 (不要进入任何聊天)
    2. 运行: python debug_search_result.py
    3. 工具会:
       - 提示你输入群名
       - 自动 Ctrl+F 搜索
       - 把搜索后界面的所有 Text 和 ListItem 按位置打印出来
       - 标记出"群聊"分类及下方的项
       - 告诉你脚本会点击哪个
"""

import sys
import time
import logging
from pathlib import Path
from datetime import date

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

DEBUG_DIR = BASE_DIR / "debug"
DEBUG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)

log = logging.getLogger("debug")


def main():
    print("=" * 60)
    print("  搜索结果调试工具")
    print("=" * 60)
    print()
    print("  这个工具会:")
    print("    1. 让你输入群名")
    print("    2. 自动在微信中 Ctrl+F 搜索")
    print("    3. 打印搜索结果中的所有项 (按位置排序)")
    print("    4. 标记 '群聊' 分类下的所有项")
    print("    5. 告诉你脚本会点击哪个 (完全匹配的)")
    print()
    name = input("请输入要搜索的群名 (回车确认): ").strip()
    if not name:
        print("未输入群名, 退出")
        return

    print()
    print("[1/3] 查找并激活微信窗口...")
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

    print("[2/3] Ctrl+F 搜索...")
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
        print("  等待 5 秒让搜索结果加载...")
        time.sleep(5.0)  # 加长等待
    except Exception as e:
        print(f"  搜索失败: {e}")
        return
    print("  搜索完成")
    print()

    # 先截图保存
    print("[3/4] 截图保存当前界面...")
    try:
        from PIL import ImageGrab
        rect = win.rectangle()
        bbox = (rect.left, rect.top, rect.right, rect.bottom)
        img = ImageGrab.grab(bbox=bbox)
        shot_path = DEBUG_DIR / f"debug_search_{date.today().isoformat()}.png"
        img.save(str(shot_path))
        print(f"  已保存: {shot_path}")
    except Exception as e:
        print(f"  截图失败: {e}")
    print()

    print("[4/4] 收集搜索结果中的所有项...")
    print("-" * 60)

    # 收集所有 Text 和 ListItem
    items = []

    # 多种方式找控件, 微信 4.x 可能用不同的 control_type
    print("  尝试多种控件类型查找...")
    found_types = set()

    for ctrl_type in ["Text", "ListItem", "Button", "Edit",
                       "Custom", "Group", "Pane", "DataItem",
                       "TreeItem", "MenuItem", "Hyperlink"]:
        try:
            ctrls = win.descendants(control_type=ctrl_type)
            if ctrls:
                found_types.add(ctrl_type)
                print(f"    {ctrl_type}: {len(ctrls)} 个")
            for c in ctrls:
                try:
                    if not c.is_visible():
                        continue
                    r = c.rectangle()
                    if r.height() < 5 or r.width() < 5:
                        continue
                    text = (c.window_text() or "").strip()
                    if text:
                        items.append({
                            "type": ctrl_type,
                            "y": r.top,
                            "x": r.left,
                            "text": text,
                        })
                except Exception:
                    continue
        except Exception:
            continue

    print()
    print(f"  找到 {len(items)} 个有文字的项, 涉及控件类型: {found_types}")
    print()
    items.sort(key=lambda a: a["y"])

    # 已知分类
    known_categories = {
        "搜一搜", "搜索网络结果", "网络结果",
        "聊天", "聊天记录", "群聊",
        "联系人", "群组", "好友",
        "公众号", "小程序", "朋友圈",
        "群公告", "收藏", "文件",
    }

    # 找到"群聊"分类的位置
    qunliao_idx = None
    for i, item in enumerate(items):
        if item["text"] == "群聊":
            qunliao_idx = i
            break

    # 打印所有项
    print(f"共找到 {len(items)} 个项 (按 y 坐标排序):")
    print()
    for i, item in enumerate(items):
        is_category = item["text"] in known_categories
        is_qunliao = (i == qunliao_idx)
        in_qunliao = (qunliao_idx is not None and qunliao_idx < i
                      and item["text"] not in known_categories)

        marker = "  "
        if is_qunliao:
            marker = ">>"  # 群聊分类标题
        elif in_qunliao:
            marker = "QQ"  # 群聊分类下的项

        cat_mark = " [分类]" if is_category else ""
        match_mark = ""
        if item["text"] == name:
            match_mark = " <<< 完全匹配!"
        elif name in item["text"]:
            match_mark = f" <<< 包含 '{name}'"

        print(f"{marker} [{item['type']:9}] y={item['y']:4} '{item['text']}'{cat_mark}{match_mark}")

    print()
    print("-" * 60)
    print()
    print("图例:")
    print("  >>  = '群聊' 分类标题")
    print("  QQ  = '群聊' 分类下的项 (脚本只会从这些里选)")
    print("  <<< 完全匹配 = 脚本会点击这个")
    print()

    if qunliao_idx is None:
        print("[警告] 没找到 '群聊' 分类标题!")
        print("可能原因:")
        print("  1. 微信搜索结果界面还没加载完")
        print("  2. '群聊' 这两个字在微信里被显示为其他文字")
        print("  3. 该群不存在或微信没识别为群聊")
    else:
        # 列出群聊分类下的所有项
        qunliao_items = []
        for item in items[qunliao_idx + 1:]:
            if item["text"] in known_categories:
                break
            qunliao_items.append(item)

        print(f"'群聊' 分类下共 {len(qunliao_items)} 个项:")
        for it in qunliao_items:
            match_mark = " ✓ 完全匹配!" if it["text"] == name else ""
            print(f"  - '{it['text']}'{match_mark}")

        print()
        # 找完全匹配
        exact_match = next((it for it in qunliao_items if it["text"] == name), None)
        if exact_match:
            print(f"✓ 脚本会点击: '{exact_match['text']}'")
        else:
            print(f"✗ 脚本不会点击任何项 (没有完全匹配 '{name}')")
            print()
            print("可能原因:")
            print(f"  - config.json 里的群名是 '{name}'")
            print(f"  - 但微信里'群聊'分类下没有完全等于这个名字的群")
            print("  - 请检查:")
            print("    1. config.json 里的群名是否与微信中显示完全一致")
            print("    2. 注意全角/半角, 表情符号, 空格")
            print("    3. 群名末尾不要带 '(32)' 这种成员数, 脚本会自动识别")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"执行失败: {e}")
        import traceback
        traceback.print_exc()
    input("\n按回车键退出...")
