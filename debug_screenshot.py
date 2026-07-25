# -*- coding: utf-8 -*-
"""
截图调试工具 - 帮助分析微信窗口结构, 调整裁剪参数

使用方法:
    1. 打开 PC 微信, 进入任意一个聊天窗口
    2. 运行: python debug_screenshot.py
    3. 工具会:
       - 截一张完整的微信窗口图 (debug_full.png)
       - 打印微信窗口的所有子控件信息 (帮助定位聊天区域)
       - 用像素分析自动找左侧栏边界
       - 截一张裁剪后的图 (debug_cropped.png)
    4. 把这两张图 + 控制台输出贴给开发者
"""

import sys
import time
from pathlib import Path
from datetime import date

BASE_DIR = Path(__file__).resolve().parent
DEBUG_DIR = BASE_DIR / "debug"
DEBUG_DIR.mkdir(exist_ok=True)


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


def dump_control_tree(win, max_depth=4, indent=0):
    """打印控件树"""
    prefix = "  " * indent
    try:
        rect = win.rectangle()
        info = f"{prefix}- [{win.element_info.control_type}] '{win.element_info.name}' "
        info += f"({rect.left},{rect.top},{rect.right},{rect.bottom}) "
        info += f"{rect.width()}x{rect.height()}"
        if win.element_info.automation_id:
            info += f" auto_id={win.element_info.automation_id}"
        if win.element_info.class_name:
            info += f" class={win.element_info.class_name}"
        print(info)
    except Exception as e:
        print(f"{prefix}- (无法读取控件: {e})")
        return

    if indent >= max_depth:
        return

    try:
        children = win.children()
        for c in children[:30]:  # 限制每个层级最多 30 个, 避免太多
            dump_control_tree(c, max_depth, indent + 1)
    except Exception:
        pass


def detect_sidebar_by_color(img):
    """通过像素颜色检测聊天区边界 (与 wechat_daily.py 中方法2 保持一致)

    微信窗口结构 (从左到右):
        [功能按钮栏 ~60px] [聊天列表 ~240px] [聊天消息区]
        颜色:  浅绿灰         浅灰            近白色
    我们要找的是 聊天列表 → 聊天区 的边界 (颜色从灰变白)
    """
    from PIL import Image
    import numpy as np

    arr = np.array(img)
    h, w = arr.shape[:2]
    print(f"\n图像尺寸: {w}x{h}")

    sample_top = min(150, h // 4)
    sample_bottom = h - min(150, h // 4)
    if sample_bottom <= sample_top:
        sample_top, sample_bottom = h // 4, h * 3 // 4

    col_means = arr[sample_top:sample_bottom, :, :3].mean(axis=0)
    col_brightness = col_means.mean(axis=1)
    print(f"扫描行: y={sample_top} 到 y={sample_bottom}")

    # 策略: 找最右侧的"亮度从低变高"的边界 (聊天列表→聊天区)
    scan_range = min(int(w * 0.6), 800)
    sidebar_x = None
    for i in range(scan_range - 1, 100, -1):
        if i + 5 < w and i - 5 > 0:
            before = col_brightness[i-5:i].mean()
            after = col_brightness[i:i+5].mean()
            if before < 245 and after >= 245 and (after - before) > 5:
                sidebar_x = i
                break

    # 备用: 最大突变法 (x>100 范围)
    if sidebar_x is None:
        diffs = np.abs(np.diff(col_means, axis=0)).sum(axis=1)
        threshold_x = min(int(w * 0.6), 800)
        sidebar_candidates = []
        for i in range(100, threshold_x):
            if diffs[i] > 30:
                sidebar_candidates.append((i + 1, float(diffs[i])))
        if sidebar_candidates:
            sidebar_candidates.sort(key=lambda x: x[0], reverse=True)
            sidebar_x = sidebar_candidates[0][0]

    if sidebar_x:
        print(f"\n检测到聊天区边界: x={sidebar_x}")
        # 打印附近几列的颜色供参考
        print(f"边界附近颜色:")
        for x in [sidebar_x - 10, sidebar_x - 1, sidebar_x, sidebar_x + 1, sidebar_x + 10]:
            if 0 <= x < w:
                print(f"  x={x}: RGB={arr[h//2, x, :3]}")
        return sidebar_x
    else:
        print("\n未检测到聊天区边界")
        return None


def main():
    print("=" * 60)
    print("  微信截图调试工具")
    print("=" * 60)
    print()

    print("[1/5] 查找微信窗口...")
    win = find_wechat_window()
    rect = win.rectangle()
    print(f"  微信窗口位置: ({rect.left},{rect.top},{rect.right},{rect.bottom})")
    print(f"  尺寸: {rect.width()}x{rect.height()}")
    print()

    print("[2/5] 激活微信窗口...")
    try:
        if win.is_minimized():
            win.restore()
        win.set_focus()
        time.sleep(1.5)
    except Exception as e:
        print(f"  警告: {e}")
    print()

    print("[3/5] 截取完整微信窗口...")
    from PIL import ImageGrab
    full_path = DEBUG_DIR / f"debug_full_{date.today().isoformat()}.png"
    full_bbox = (rect.left, rect.top, rect.right, rect.bottom)
    full_img = ImageGrab.grab(bbox=full_bbox)
    full_img.save(str(full_path))
    print(f"  已保存: {full_path}")
    print(f"  尺寸: {full_img.width}x{full_img.height}")
    print()

    print("[4/5] 分析左侧栏边界 (像素颜色检测)...")
    sidebar_x = detect_sidebar_by_color(full_img)
    print()

    print("[5/5] 打印控件树 (帮助定位聊天区域)...")
    print("-" * 60)
    try:
        dump_control_tree(win, max_depth=3)
    except Exception as e:
        print(f"控件树打印失败: {e}")
    print("-" * 60)
    print()

    # 根据检测到的左侧栏边界裁剪一张示例图
    if sidebar_x:
        from PIL import Image
        # 顶部不裁剪, 保留群名标题栏
        top_cut = 0
        cropped = full_img.crop((sidebar_x, top_cut, full_img.width, full_img.height))
        cropped_path = DEBUG_DIR / f"debug_cropped_{date.today().isoformat()}.png"
        cropped.save(str(cropped_path))
        print(f"已生成裁剪示例: {cropped_path}")
        print(f"  裁剪参数: 左 {sidebar_x}px, 顶 {top_cut}px (保留群名标题栏)")
        print(f"  尺寸: {cropped.width}x{cropped.height}")
    else:
        print("未生成裁剪示例 (没检测到左侧栏边界)")

    print()
    print("=" * 60)
    print("  调试完成!")
    print("=" * 60)
    print()
    print("请把以下信息提供给开发者:")
    print(f"  1. 完整截图: {DEBUG_DIR}/debug_full_*.png")
    print(f"  2. 裁剪示例: {DEBUG_DIR}/debug_cropped_*.png (如果存在)")
    print(f"  3. 上面的控制台输出 (复制粘贴)")
    print()
    print("开发者会根据这些信息调整裁剪参数, 让截图只包含聊天区域。")


if __name__ == "__main__":
    main()
