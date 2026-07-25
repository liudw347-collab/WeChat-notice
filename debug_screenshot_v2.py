# -*- coding: utf-8 -*-
"""
截图当前状态自检 - 看看 wechat_daily.py 当前用的截图逻辑是什么

用法:
    1. 打开 PC 微信, 进入任意一个群聊
    2. 运行: python debug_screenshot_v2.py
    3. 工具会:
       - 用 wechat_daily.py 里真实的 screenshot_wechat_window 函数截一张图
       - 同时打印当前的裁剪参数 (top_offset, sidebar_x 等)
       - 把截图保存到 debug/screenshot_actual.png
"""

import sys
import time
import logging
from pathlib import Path
from datetime import date

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

# 配置日志输出到控制台
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)

# 创建 debug 目录
DEBUG_DIR = BASE_DIR / "debug"
DEBUG_DIR.mkdir(exist_ok=True)


def main():
    print("=" * 60)
    print("  截图自检工具 - 看当前 wechat_daily.py 截出来的图")
    print("=" * 60)
    print()

    # 1. 查找微信窗口
    print("[1/4] 查找微信窗口...")
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
        print("  未找到微信窗口, 请先打开 PC 微信并登录")
        return
    rect = win.rectangle()
    print(f"  窗口位置: ({rect.left},{rect.top},{rect.right},{rect.bottom})")
    print(f"  尺寸: {rect.width()}x{rect.height()}")
    print()

    # 2. 激活窗口
    print("[2/4] 激活微信窗口...")
    try:
        if win.is_minimized():
            win.restore()
        win.set_focus()
        time.sleep(1.5)
    except Exception as e:
        print(f"  警告: {e}")
    print()

    # 3. 调用 wechat_daily.py 里的真实截图函数
    print("[3/4] 调用 wechat_daily.screenshot_wechat_window() 截图...")
    print("  (用的就是定时任务跑的时候用的那个截图函数)")
    print()

    from wechat_daily import screenshot_wechat_window, log

    output_path = str(DEBUG_DIR / f"screenshot_actual_{date.today().isoformat()}.png")
    success = screenshot_wechat_window(win, output_path)

    if not success:
        print("  截图失败!")
        return

    print()
    print(f"  截图已保存: {output_path}")
    print()

    # 4. 分析截图
    print("[4/4] 分析截图...")
    from PIL import Image
    import numpy as np
    img = Image.open(output_path)
    print(f"  尺寸: {img.width}x{img.height}")

    arr = np.array(img)
    h, w = arr.shape[:2]

    # 检查四角和中心
    print(f"  四角颜色 (RGB):")
    print(f"    左上角 (0,0): {arr[5, 5, :3]}")
    print(f"    右上角 (5,w-5): {arr[5, w-5, :3]}")
    print(f"    左下角 (h-5,5): {arr[h-5, 5, :3]}")
    print(f"    右下角 (h-5,w-5): {arr[h-5, w-5, :3]}")
    print(f"    正中间: {arr[h//2, w//2, :3]}")

    # 判断截图是否正确
    print()
    print("=" * 60)
    print("  判断结果")
    print("=" * 60)
    print()

    # 顶部应该能看到群名标题栏 (颜色通常较深或与聊天区不同)
    top_color = arr[2, w//2, :3]
    mid_color = arr[h//2, w//2, :3]
    print(f"  顶部颜色: {top_color}")
    print(f"  中间颜色: {mid_color}")

    # 如果顶部和中间颜色相近, 可能顶部被裁掉了
    color_diff = abs(int(top_color.mean()) - int(mid_color.mean()))
    if color_diff < 10:
        print(f"  颜色差异 {color_diff} 很小, 顶部可能没保留群名标题栏")
    else:
        print(f"  颜色差异 {color_diff}, 顶部应该能看到群名")

    print()
    print("=" * 60)
    print("  请打开截图查看:")
    print(f"  {output_path}")
    print()
    print("  如果截图正确 (顶部能看到群名, 左侧无聊天列表), 就完美!")
    print("  如果有问题, 请把:")
    print("    1. 上面的输出")
    print("    2. screenshot_actual_*.png 这张图")
    print("  贴给开发者调整")
    print("=" * 60)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"执行失败: {e}")
        import traceback
        traceback.print_exc()
    input("\n按回车键退出...")
