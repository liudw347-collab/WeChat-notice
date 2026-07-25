# -*- coding: utf-8 -*-
"""
每日安全提醒自动化 (Windows 版) - 核心执行脚本
项目: WeChat-notice / 定州市第八中学假期安全提醒

依赖:
    pip install pywinauto pillow psutil

特点:
    - 不依赖 wxauto (wxauto 不支持 Python 3.13+)
    - 用 pywinauto + Win32 API 直接控制 PC 微信窗口
    - 内置 keep_awake 模块, 运行期间防止系统休眠 + 自动唤醒屏幕
    - 失败重试 3 次, 弹窗+响铃告警

命令行用法:
    python wechat_daily.py                  # 立即执行今日提醒
    python wechat_daily.py --date 2026-07-25  # 指定日期执行（补发）
    python wechat_daily.py --dry-run        # 仅模拟，不实际发送
    python wechat_daily.py --test           # 发测试消息到文件传输助手
"""

import argparse
import json
import logging
import os
import re
import sys
import time
import traceback
from datetime import datetime, date
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.json"
LOGS_DIR = BASE_DIR / "logs"
SCREENSHOTS_DIR = BASE_DIR / "screenshots"
SENT_RECORDS_PATH = BASE_DIR / "sent_records.json"

LOGS_DIR.mkdir(exist_ok=True)
SCREENSHOTS_DIR.mkdir(exist_ok=True)

# 引入文案生成器与防休眠模块
sys.path.insert(0, str(BASE_DIR))
from message_builder import build_message
from keep_awake import prevent_sleep, allow_sleep, wake_up_screen
from cleanup import cleanup_old_files, print_disk_usage


def setup_logger():
    log_file = LOGS_DIR / f"run_{date.today().isoformat()}.log"
    logger = logging.getLogger("wechat_daily")
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()
    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)
    logger.addHandler(fh)
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)
    logger.addHandler(ch)
    return logger


log = setup_logger()


def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def load_sent_records():
    if not SENT_RECORDS_PATH.exists():
        return {}
    try:
        with open(SENT_RECORDS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_sent_records(records: dict):
    with open(SENT_RECORDS_PATH, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)


# ----------------- 微信自动化 (pywinauto 实现) -----------------

def find_wechat_window():
    """查找 PC 微信主窗口, 返回窗口对象"""
    try:
        from pywinauto import Desktop
    except ImportError:
        log.error("未安装 pywinauto, 请执行: pip install pywinauto")
        raise

    desktop = Desktop(backend="uia")
    # 微信 3.x 标题为 "微信", 4.x 标题为 "WeChat" 或 "微信"
    candidates = []
    for title_pattern in ["微信", "WeChat"]:
        try:
            wins = desktop.windows(title=title_pattern)
            candidates.extend(wins)
        except Exception:
            pass

    if not candidates:
        log.error("未找到 PC 微信窗口, 请确认微信已登录")
        raise RuntimeError("微信窗口未找到")

    # 取第一个非最小化的, 否则取第一个
    for w in candidates:
        try:
            if w.is_enabled() and w.is_visible():
                return w
        except Exception:
            continue
    return candidates[0]


def bring_wechat_to_front(win):
    """将微信窗口激活到前台"""
    try:
        if win.is_minimized():
            win.restore()
        win.set_focus()
        time.sleep(1.0)
    except Exception as e:
        log.warning(f"激活窗口失败 (忽略): {e}")


def open_chat_by_session_position(win, position: int = 1) -> bool:
    """通过点击会话列表的指定位置打开群聊 (无需搜索!)

    原理:
        用户提前在微信里打开班级群和班主任群
        这样这两个群就在会话列表的最前面 (微信按最近活动排序)
        脚本直接点击会话列表的第 N 个项即可

    位置计算:
        微信窗口左侧栏结构 (4.x):
            顶部: 功能按钮栏 (微信/通讯录/朋友圈等) ~60px
            顶部: 搜索框 ~40px
            下方: 会话列表 (每个会话约 64px 高)

        所以第 1 个会话的 y 坐标 ≈ 窗口顶部 + 100 + 32 = 132 (相对)
        第 N 个会话的 y 坐标 ≈ 132 + (N-1) * 64

    参数:
        position: 会话列表中的位置 (1=第一个, 2=第二个)
                  用户提前打开班级群后再打开班主任群
                  班主任群是第 1 个 (最近打开), 班级群是第 2 个

    使用前提:
        用户必须按以下顺序操作 (每天电脑开机后/微信重启后只需做一次):
        1. 打开 PC 微信
        2. 鼠标点击班级群 (进入班级群聊天界面)
        3. 鼠标点击班主任群 (进入班主任群聊天界面)
        这样班主任群 = 第1位, 班级群 = 第2位

    优点:
        - 完全不依赖搜索功能
        - 完全不依赖控件识别 (pywinauto/uiautomation 都读不到自绘控件)
        - 完全不依赖 OCR
        - 100% 可靠, 只要用户提前打开过两个群

    缺点:
        - 需要用户配合 (每天提前点一下两个群)
        - 会话顺序可能受其他消息影响 (如果有新消息进来到这两个群前面)
    """
    try:
        bring_wechat_to_front(win)
        rect = win.rectangle()
        win_left = rect.left
        win_top = rect.top
        win_width = rect.width()

        # 微信 4.x 左侧栏结构:
        # - 功能按钮栏: 60px (最左边一列图标)
        # - 会话列表区: 从 x=60 开始, 宽度约 250px
        # - 会话列表第 1 项的 y 起点 ≈ 窗口顶部 + 100 (跳过搜索框)

        # 点击位置: 会话列表第 N 项的中心
        # x: 左侧栏中心 = 窗口左 + 60 + 125 = 窗口左 + 185
        # y: 窗口顶 + 100 + (position - 1) * 64 + 32 (项中心)

        click_x = win_left + 185
        click_y = win_top + 100 + (position - 1) * 64 + 32

        log.info(f"点击会话列表第 {position} 项, 坐标 ({click_x}, {click_y})")

        # 用 win32api 点击 (最可靠, 不依赖任何库)
        import ctypes
        # 移动鼠标
        ctypes.windll.user32.SetCursorPos(click_x, click_y)
        time.sleep(0.3)
        # 鼠标左键按下 + 抬起
        ctypes.windll.user32.mouse_event(0x0002, 0, 0, 0, 0)  # LEFTDOWN
        ctypes.windll.user32.mouse_event(0x0004, 0, 0, 0, 0)  # LEFTUP
        time.sleep(1.5)  # 等待会话切换

        log.info(f"已点击会话列表第 {position} 项")
        return True

    except Exception as e:
        log.error(f"点击会话列表失败: {e}")
        return False


def search_and_open_chat(win, name: str):
    """在微信中通过搜索打开指定群聊 (借鉴 wxauto 方案)

    关键技巧 (来自 wxauto 源码):
        微信搜索结果里, 完全匹配的群名会被 <em>标签包裹 (HTML 高亮)
        所以可以用 TextControl(Name=f"<em>{name}</em>") 精确定位完全匹配项
        这是 pywinauto 找不到的, 但 uiautomation 能找到

    分工:
        - 键盘操作 (Ctrl+F, Ctrl+V): 用 pywinauto.keyboard (一直能工作)
        - 找搜索结果控件: 用 uiautomation (能读 <em> 标记)

    流程:
        1. 优先从会话列表找 (不搜索!) - 群名已在列表里就直接点击
        2. 找不到才 Ctrl+F 搜索
        3. 搜索后找 <em>群名</em> 标记的完全匹配项
        4. 找不到完全匹配, 就失败 (不再兜底)
    """
    try:
        import uiautomation as uia
    except ImportError:
        log.error("未安装 uiautomation, 请运行: pip install uiautomation")
        return False

    bring_wechat_to_front(win)

    # === 1. 找微信主窗口的 uiautomation 控件 ===
    wechat_win = uia.WindowControl(ClassName="WeChatMainWndForPC", Name="微信")
    if not wechat_win.Exists(1):
        # 微信 4.x 用不同的 ClassName
        wechat_win = uia.WindowControl(Name="微信")
        if not wechat_win.Exists(1):
            wechat_win = uia.WindowControl(SubName="微信")
            if not wechat_win.Exists(1):
                log.error("uiautomation 找不到微信窗口")
                return False

    log.info(f"uiautomation 找到微信窗口: {wechat_win.Name}")

    # === 2. 优先从会话列表找 (不搜索!) ===
    # 微信主窗口结构: NavigationBox | SessionBox | ChatBox (三个子控件)
    try:
        children = wechat_win.GetChildren()
        if len(children) >= 3:
            session_box = children[1]  # SessionBox
            # 在会话列表里找完全匹配的项
            list_item = session_box.ListItemControl(RegexName=f"^{re.escape(name)}($|\\s|\\()")
            if list_item.Exists(0.5):
                log.info(f"会话列表里找到 '{name}', 直接点击 (无需搜索)")
                list_item.Click(simulateMove=False)
                time.sleep(1.5)
                return True
            # 模糊匹配 (名字包含目标群名)
            list_item = session_box.ListItemControl(RegexName=re.escape(name))
            if list_item.Exists(0.5):
                log.info(f"会话列表里找到包含 '{name}' 的项, 点击")
                list_item.Click(simulateMove=False)
                time.sleep(1.5)
                return True
    except Exception as e:
        log.warning(f"从会话列表查找失败: {e}")

    # === 3. Ctrl+F 搜索 ===
    # 用 send_keys_safe (PowerShell 优先, 失败回退 pywinauto)
    log.info(f"会话列表未找到, 用 Ctrl+F 搜索 '{name}'")
    if not send_keys_safe("^f"):
        log.error("Ctrl+F 失败")
        return False
    time.sleep(1.0)

    # === 4. 输入群名 (剪贴板粘贴) ===
    # 用 PowerShell 设置剪贴板, 用 paste_via_clipboard 粘贴
    # 避免 pywinauto '^v' 字面字符问题
    try:
        import subprocess
        tmp = Path(BASE_DIR) / "logs" / "_search_buffer.txt"
        tmp.write_text(name, encoding="utf-8")
        ps_cmd = (
            f"$text = Get-Content -LiteralPath '{tmp}' -Raw -Encoding UTF8; "
            "Set-Clipboard -Value $text"
        )
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_cmd],
            capture_output=True, timeout=5
        )
        time.sleep(0.5)  # 等剪贴板就绪

        # 用 paste_via_clipboard 粘贴 (PowerShell SendKeys 优先)
        paste_via_clipboard()
        time.sleep(2.5)  # 等待搜索结果加载
    except Exception as e:
        log.error(f"输入群名失败: {e}")
        return False

    # === 5. 找完全匹配项 (关键: <em>群名</em> 标记) ===
    # 这是 wxauto 的核心技巧: 微信搜索结果完全匹配的项会被 <em> 标签包裹
    try:
        target = wechat_win.TextControl(Name=f"<em>{name}</em>")
        if target.Exists(2):
            log.info(f"找到完全匹配项 (<em>{name}</em>), 点击")
            target.Click(simulateMove=False)
            time.sleep(2.0)
            return True
        log.info(f"未找到 <em>{name}</em> 标记的完全匹配项")
    except Exception as e:
        log.warning(f"找 <em> 标记失败: {e}")

    # === 6. 备用: 找带 <em> 的, 但 RegexName 模糊匹配 ===
    try:
        target = wechat_win.TextControl(RegexName=f"<em>{re.escape(name)}</em>")
        if target.Exists(2):
            log.info(f"通过 RegexName 找到完全匹配项, 点击")
            target.Click(simulateMove=False)
            time.sleep(2.0)
            return True
    except Exception as e:
        log.warning(f"RegexName 匹配失败: {e}")

    # === 6.5 备用: 找搜索结果中的 ListItem (微信4.x 可能用这种结构) ===
    try:
        # 微信4.x 搜索结果可能是 ListItem, 找包含群名的
        list_items = wechat_win.ListItemControl(RegexName=re.escape(name))
        if list_items.Exists(2):
            log.info(f"找到 ListItem 包含 '{name}', 点击")
            list_items.Click(simulateMove=False)
            time.sleep(2.0)
            return True
    except Exception as e:
        log.warning(f"ListItem 匹配失败: {e}")

    # === 6.6 备用: 遍历所有 Text 控件, 找完全匹配的 (排除搜一搜) ===
    # 微信4.x 可能不用 <em> 标记, 直接显示群名
    # 搜一搜下也会有"群名"字样 (作为搜索建议), 要排除
    log.info("尝试遍历所有 Text 控件找完全匹配")
    try:
        # 收集所有 Text 控件, 按位置 (y 坐标) 排序
        all_texts = []
        for text_ctrl in wechat_win.GetChildren():
            _collect_texts(text_ctrl, all_texts, depth=0, max_depth=8)
        all_texts.sort(key=lambda x: x["y"])

        log.info(f"共找到 {len(all_texts)} 个 Text 控件")
        # 打印前 30 个, 方便调试
        for i, t in enumerate(all_texts[:30]):
            log.info(f"  [{i}] y={t['y']} '{t['name'][:60]}'")

        # 已知分类标题 (遇到就跳过其下方的项)
        known_categories = {
            "搜一搜", "搜索网络结果", "网络结果",
            "聊天", "聊天记录", "群聊", "群组",
            "联系人", "好友",
            "公众号", "小程序", "朋友圈",
            "群公告", "收藏", "文件",
        }

        # 找"群聊"分类下的完全匹配项
        in_qunliao = False
        for t in all_texts:
            text = t["name"].strip()
            if text in known_categories:
                in_qunliao = (text in ["群聊", "群组"])
                continue
            if in_qunliao and text == name:
                log.info(f"在 '群聊' 分类下找到完全匹配: '{text}'")
                try:
                    t["control"].Click(simulateMove=False)
                    time.sleep(2.0)
                    return True
                except Exception as click_err:
                    log.warning(f"点击失败: {click_err}")
    except Exception as e:
        log.warning(f"遍历 Text 控件失败: {e}")

    # === 6.7 最后备用: 键盘导航 (按 ↓ 进入结果, 多次 ↓ 跳过搜一搜, Enter) ===
    log.info("尝试键盘导航方案: 按 ↓ 跳过搜一搜, 再按 Enter")
    try:
        # 按 5 次 ↓ 跳过搜一搜 + 网络结果项 + 进入群聊分类
        for i in range(5):
            send_keys_safe("{DOWN}")
            time.sleep(0.3)
        # 按 Enter 进入当前选中项
        send_keys_safe("{ENTER}")
        time.sleep(2.0)
        log.info("键盘导航完成, 验证是否进入了正确的群...")

        # 验证: 看当前聊天窗口标题是否包含群名
        try:
            current_chat = wechat_win.TextControl(Name=name)
            if current_chat.Exists(2):
                log.info(f"键盘导航成功, 当前在 '{name}' 群")
                return True
            else:
                log.warning(f"键盘导航后当前聊天不是 '{name}', 可能进错群")
                send_keys_safe("{ESC}")
                time.sleep(1.0)
        except Exception as verify_err:
            log.warning(f"验证当前群失败: {verify_err}")
    except Exception as e:
        log.warning(f"键盘导航失败: {e}")

    # === 7. 严格策略: 找不到完全匹配就失败, 不再兜底 ===
    log.error(f"未找到完全匹配 '{name}' 的群")
    log.error(f"请检查 config.json 里的群名是否与微信中显示完全一致")
    return False


def click_item(control) -> bool:
    """点击控件, 失败时尝试点击父级 (保留, 部分代码可能用到)"""
    try:
        control.click_input()
        return True
    except Exception as e:
        log.warning(f"点击失败, 尝试点击父级: {e}")
        try:
            parent = control.parent()
            if parent:
                parent.click_input()
                return True
        except Exception:
            pass
    return False


def _collect_texts(ctrl, result, depth=0, max_depth=8):
    """递归收集所有 Text 控件, 返回 [{name, y, control}, ...]"""
    if depth > max_depth:
        return
    try:
        if ctrl.ControlTypeName == "TextControl":
            name = ctrl.Name or ""
            if name and len(name) < 200:
                try:
                    rect = ctrl.BoundingRectangle
                    result.append({
                        "name": name,
                        "y": rect.top,
                        "x": rect.left,
                        "control": ctrl,
                    })
                except Exception:
                    pass
    except Exception:
        pass
    try:
        for child in ctrl.GetChildren():
            _collect_texts(child, result, depth + 1, max_depth)
    except Exception:
        pass


def paste_via_clipboard():
    """通过剪贴板粘贴 (Ctrl+V)

    使用 PowerShell SendKeys 而不是 pywinauto.keyboard.send_keys
    原因: pywinauto 的 '^v' 有时会把字面字符 ^v 输入到搜索框/输入框
    PowerShell 的 SendKeys 更底层, 更稳定
    """
    import subprocess
    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Add-Type -AssemblyName System.Windows.Forms; "
             "[System.Windows.Forms.SendKeys]::SendWait('^v')"],
            capture_output=True, timeout=5
        )
        return True
    except Exception as e:
        log.warning(f"PowerShell SendKeys 粘贴失败, 回退到 pywinauto: {e}")
        try:
            import pywinauto.keyboard as kb
            kb.send_keys("^v")
            return True
        except Exception:
            return False


def send_keys_safe(keys: str):
    """安全的 send_keys, 优先用 PowerShell, 失败回退到 pywinauto

    用于关键的键盘操作 (Enter, Ctrl+A, DEL 等)
    """
    import subprocess
    # PowerShell SendKeys 语法和 pywinauto 不同, 需要转换
    # pywinauto: '{ENTER}' -> PowerShell: '{ENTER}'
    # pywinauto: '^a' -> PowerShell: '^a'
    # pywinauto: '{DEL}' -> PowerShell: '{DELETE}'
    ps_keys = keys.replace('{DEL}', '{DELETE}')

    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"Add-Type -AssemblyName System.Windows.Forms; "
             f"[System.Windows.Forms.SendKeys]::SendWait('{ps_keys}')"],
            capture_output=True, timeout=5
        )
        return True
    except Exception as e:
        log.warning(f"PowerShell SendKeys 失败, 回退到 pywinauto: {e}")
        try:
            import pywinauto.keyboard as kb
            kb.send_keys(keys)
            return True
        except Exception:
            return False


def send_text_in_chat(win, text: str):
    """在当前会话中发送文字

    微信的输入框无法用 pywinauto 直接定位 (UIA 树里是 Edit 控件),
    但只要窗口在前台, 直接 send_keys 就会进到输入框.

    使用 PowerShell SendKeys 粘贴, 避免 pywinauto '^v' 字面字符问题
    """
    try:
        bring_wechat_to_front(win)
        import subprocess
        # 通过剪贴板粘贴, 解决中文输入和长文本问题
        # 写到临时文件再用 PowerShell 读取 (更可靠)
        tmp = Path(BASE_DIR) / "logs" / "_msg_buffer.txt"
        tmp.write_text(text, encoding="utf-8")
        ps_cmd = (
            f"$text = Get-Content -LiteralPath '{tmp}' -Raw -Encoding UTF8; "
            "Set-Clipboard -Value $text"
        )
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_cmd],
            capture_output=True, timeout=10
        )
        time.sleep(0.5)

        # Ctrl+V 粘贴 (用 PowerShell SendKeys, 避免 ^v 字面问题)
        paste_via_clipboard()
        time.sleep(1.0)

        # Enter 发送
        send_keys_safe("{ENTER}")
        time.sleep(1.0)
        log.info(f"已发送文本消息 ({len(text)} 字符)")
        return True
    except Exception as e:
        log.error(f"发送文字失败: {e}")
        return False


def screenshot_wechat_window(win, image_path: str) -> bool:
    """对微信窗口截图 - 只截聊天区域, 不要左侧栏

    微信窗口结构:
        ┌────────┬──────────────────────────┐
        │ 左侧栏  │                          │
        │ 微信    │                          │
        │ 通讯录  │     聊天区域              │
        │ 朋友圈  │   （我们要截这部分）      │
        │ 聊天列表 │                          │
        │        │                          │
        └────────┴──────────────────────────┘

    截图策略 (按优先级):
        1. pywinauto 找聊天区域子控件 (最精确, 但依赖微信版本)
        2. 像素颜色检测自动找左侧栏边界 (推荐, 适应各种微信版本)
        3. 启发式裁剪 (兜底)
        4. 截全窗口 (最后兜底)
    """
    try:
        from PIL import ImageGrab, Image
        import numpy as np
        bring_wechat_to_front(win)
        time.sleep(1.0)

        # 整个微信窗口的位置
        full_rect = win.rectangle()
        full_bbox = (full_rect.left, full_rect.top, full_rect.right, full_rect.bottom)

        # 先截一张完整图, 后续基于它裁剪
        full_img = ImageGrab.grab(bbox=full_bbox)
        log.info(f"已截全窗口: {full_img.width}x{full_img.height}")

        chat_bbox = None

        # === 方法 1: pywinauto 找聊天区域子控件 (仅明确控件名, 不再"找最大子控件") ===
        # 注意: 微信 4.x 的 mmui::MainView 控件覆盖整个窗口, 不能用"最大子控件"兜底
        # 否则会把整个窗口当成聊天区域, 截图就不会裁掉左侧栏了
        try:
            chat_candidates = []
            # 只用明确的聊天区域控件名, 不要 MainView 这种主容器
            for class_name in ["ChatView", "WeChatMainWndForGPS", "ChatWnd",
                                "SessionView", "ChatPanel", "ChatWidget"]:
                try:
                    found = win.child_window(class_name=class_name)
                    if found.exists(timeout=0.5):
                        # 排除"覆盖整个窗口"的控件 (它是主容器不是聊天区)
                        r = found.rectangle()
                        if r.width() < full_rect.width() * 0.95 or \
                           r.height() < full_rect.height() * 0.95:
                            chat_candidates.append(found)
                            log.info(f"方法1: 找到 {class_name}, 大小 {r.width()}x{r.height()}")
                        else:
                            log.info(f"方法1: 跳过 {class_name} (覆盖整个窗口, 是主容器)")
                except Exception:
                    continue

            for auto_id in ["ChatView", "ChatPanel", "SessionPanel", "main_chat_panel"]:
                try:
                    found = win.child_window(auto_id=auto_id)
                    if found.exists(timeout=0.5):
                        r = found.rectangle()
                        if r.width() < full_rect.width() * 0.95 or \
                           r.height() < full_rect.height() * 0.95:
                            chat_candidates.append(found)
                            log.info(f"方法1: 找到 auto_id={auto_id}, 大小 {r.width()}x{r.height()}")
                except Exception:
                    continue

            # 注意: 已移除"找最大子控件"的兜底逻辑
            # 原因: 微信4.x 的 mmui::MainView 覆盖整个窗口, 会被错误识别为聊天区域

            if chat_candidates:
                chat_rect = chat_candidates[0].rectangle()
                if chat_rect.width() > 100 and chat_rect.height() > 100:
                    chat_bbox = (chat_rect.left, chat_rect.top,
                                  chat_rect.right, chat_rect.bottom)
                    log.info(f"方法1成功: 找到聊天区域控件, 大小 {chat_rect.width()}x{chat_rect.height()}")
        except Exception as e:
            log.warning(f"方法1失败 (找控件): {e}")

        # === 方法 2: 像素颜色检测找聊天区边界 (推荐) ===
        # 微信窗口结构 (从左到右):
        #   [功能按钮栏 ~60px] [聊天列表 ~240px] [聊天消息区]
        #   颜色:  浅绿灰         浅灰            近白色
        # 我们要找的是 聊天列表 → 聊天区 的边界 (颜色从灰变白)
        if chat_bbox is None:
            try:
                arr = np.array(full_img)
                h, w = arr.shape[:2]
                # 取中间区域 (避开顶部标题栏和底部输入框)
                sample_top = min(150, h // 4)
                sample_bottom = h - min(150, h // 4)
                if sample_bottom <= sample_top:
                    sample_top, sample_bottom = h // 4, h * 3 // 4

                # 每一列的平均颜色 (RGB)
                col_means = arr[sample_top:sample_bottom, :, :3].mean(axis=0)  # shape (w, 3)

                # 计算每一列的"亮度" (平均 RGB)
                col_brightness = col_means.mean(axis=1)  # shape (w,)

                # 策略: 找最右侧的"亮度从低变高"的边界
                # 聊天列表区是灰色 (亮度 ~230), 聊天区是近白 (亮度 ~250)
                # 我们要找最后一个 "亮度 < 245 → 亮度 >= 245" 的过渡点
                sidebar_x = None

                # 在窗口左侧 60% 范围内扫描 (聊天区一定在右侧)
                scan_range = min(int(w * 0.6), 800)
                for i in range(scan_range - 1, 100, -1):  # 从右往左找
                    # 连续 5 列都 < 245, 且后面 5 列都 >= 245
                    if i + 5 < w and i - 5 > 0:
                        before = col_brightness[i-5:i].mean()
                        after = col_brightness[i:i+5].mean()
                        if before < 245 and after >= 245 and (after - before) > 5:
                            sidebar_x = i
                            break

                # 备用: 如果上面没找到, 用最大突变法 (但限制在 100px 以后)
                if sidebar_x is None:
                    diffs = np.abs(np.diff(col_means, axis=0)).sum(axis=1)
                    # 只在 x > 100 的范围找 (跳过功能按钮栏边界)
                    threshold_x = min(int(w * 0.6), 800)
                    sidebar_candidates = []
                    for i in range(100, threshold_x):
                        if diffs[i] > 30:
                            sidebar_candidates.append((i + 1, float(diffs[i])))
                    if sidebar_candidates:
                        # 取最右侧的强突变点
                        sidebar_candidates.sort(key=lambda x: x[0], reverse=True)
                        sidebar_x = sidebar_candidates[0][0]

                if sidebar_x:
                    # 顶部不裁剪, 保留聊天窗口顶部的群名标题栏 (能看到这是哪个群)
                    top_offset = 0
                    chat_bbox = (
                        full_rect.left + sidebar_x,
                        full_rect.top + top_offset,
                        full_rect.right,
                        full_rect.bottom,
                    )
                    log.info(f"方法2成功: 像素检测聊天区边界 x={sidebar_x}, "
                             f"顶 {top_offset}px (保留群名标题栏), "
                             f"聊天区域 {chat_bbox[2]-chat_bbox[0]}x{chat_bbox[3]-chat_bbox[1]}")
                else:
                    log.warning("方法2: 未检测到聊天区边界")
            except Exception as e:
                log.warning(f"方法2失败 (像素检测): {e}")

        # === 方法 3: 启发式裁剪 (兜底) ===
        if chat_bbox is None:
            log.info("使用方法3: 启发式裁剪")
            width = full_rect.width()
            sidebar_width = min(int(width * 0.28), 350)
            sidebar_width = max(200, sidebar_width)
            top_offset = 60
            chat_bbox = (
                full_rect.left + sidebar_width,
                full_rect.top + top_offset,
                full_rect.right,
                full_rect.bottom,
            )
            log.info(f"方法3: 左 {sidebar_width}px, 顶 {top_offset}px, "
                     f"聊天区域 {chat_bbox[2]-chat_bbox[0]}x{chat_bbox[3]-chat_bbox[1]}")

        # 裁剪并保存
        # chat_bbox 是屏幕坐标, 转成相对于 full_img 的坐标
        crop_box = (
            chat_bbox[0] - full_rect.left,
            chat_bbox[1] - full_rect.top,
            chat_bbox[2] - full_rect.left,
            chat_bbox[3] - full_rect.top,
        )
        cropped = full_img.crop(crop_box)
        cropped.save(image_path)
        log.info(f"已截图 (仅聊天区域): {image_path}, 尺寸 {cropped.width}x{cropped.height}")
        return True
    except Exception as e:
        log.error(f"截图失败: {e}")
        # 兜底: 截整个窗口
        try:
            full_img.save(image_path)
            log.warning(f"截图失败, 兜底截全窗口: {image_path}")
            return True
        except Exception as e2:
            log.error(f"兜底截图也失败: {e2}")
            return False


def send_image_in_chat(win, image_path: str):
    """在当前会话中发送图片

    实现: 通过剪贴板粘贴图片到微信输入框, 然后 Enter 发送
    使用 PowerShell SendKeys 粘贴, 避免 pywinauto '^v' 字面字符问题
    """
    import subprocess

    try:
        bring_wechat_to_front(win)

        # 用 PowerShell 把图片放到剪贴板
        ps_cmd = (
            "Add-Type -AssemblyName System.Windows.Forms; "
            "Add-Type -AssemblyName System.Drawing; "
            f"$img = [System.Drawing.Image]::FromFile('{image_path}'); "
            "[System.Windows.Forms.Clipboard]::SetImage($img); "
            "$img.Dispose()"
        )
        subprocess.run(
            ["powershell", "-NoProfile", "-STA", "-Command", ps_cmd],
            capture_output=True, timeout=10
        )
        time.sleep(0.5)

        # Ctrl+V 粘贴图片 (微信会显示预览)
        # 用 PowerShell SendKeys, 避免 ^v 字面字符问题
        paste_via_clipboard()
        time.sleep(2.0)  # 等图片预览加载

        # Enter 发送
        send_keys_safe("{ENTER}")
        time.sleep(1.5)
        log.info(f"已发送图片: {image_path}")
        return True
    except Exception as e:
        log.error(f"发送图片失败: {e}")
        return False


# ----------------- 告警 -----------------

def alert_failure(reason: str, config):
    log.error(f"告警触发: {reason}")
    alert_cfg = config.get("alert", {})
    if alert_cfg.get("enable_popup", True):
        try:
            import ctypes
            # MB_TOPMOST 让弹窗始终在前
            ctypes.windll.user32.MessageBoxW(
                0,
                f"【每日安全提醒】发送失败！\n\n原因：{reason}\n\n请尽快手动补发，并检查脚本。",
                "班主任安全提醒 - 失败告警",
                0x10 | 0x0 | 0x40000,  # MB_ICONERROR | MB_OK | MB_TOPMOST
            )
        except Exception as e:
            log.error(f"弹窗告警失败: {e}")
    if alert_cfg.get("enable_sound", True):
        try:
            import winsound
            for _ in range(5):
                winsound.Beep(2000, 600)
                time.sleep(0.3)
        except Exception as e:
            log.error(f"响铃告警失败: {e}")
    if alert_cfg.get("enable_email", False):
        try:
            send_email_alert(reason, config)
        except Exception as e:
            log.error(f"邮件告警失败: {e}")


def send_email_alert(reason: str, config):
    import smtplib
    from email.mime.text import MIMEText
    e = config["alert"]["email"]
    msg = MIMEText(
        f"【班主任安全提醒】发送失败\n时间: {datetime.now()}\n原因: {reason}",
        "plain",
        "utf-8",
    )
    msg["Subject"] = "【告警】班主任安全提醒发送失败"
    msg["From"] = e["smtp_user"]
    msg["To"] = e["to_addr"]
    with smtplib.SMTP_SSL(e["smtp_server"], e["smtp_port"]) as s:
        s.login(e["smtp_user"], e["smtp_password"])
        s.sendmail(e["smtp_user"], [e["to_addr"]], msg.as_string())
    log.info("邮件告警已发送")


# ----------------- 主流程 -----------------

def run_once(today: date, dry_run: bool = False, test_mode: bool = False):
    log.info(f"=== 开始执行 {today.isoformat()} 安全提醒任务 ===")
    config = load_config()

    # 防重复
    if not dry_run and not test_mode:
        records = load_sent_records()
        key = today.isoformat()
        if records.get(key, {}).get("success"):
            log.warning(f"{key} 已发送过，跳过本次执行")
            return True

    if test_mode:
        text = "【测试消息】班主任安全提醒脚本测试，请忽略此消息。"
        class_group = "文件传输助手"
        teacher_group = "文件传输助手"
    else:
        text = build_message(today)
        log.info(f"今日文案长度: {len(text)} 字符")
        class_group = config["wechat"]["class_group_name"]
        teacher_group = config["wechat"]["teacher_group_name"]

    max_retries = config["schedule"]["max_retries"]
    retry_interval = config["schedule"]["retry_interval_sec"]

    # === 防休眠: 整个执行期间阻止系统睡眠 ===
    prevent_sleep()
    wake_up_screen()

    # 打印项目磁盘占用 (方便监控资源)
    print_disk_usage(BASE_DIR)

    try:
        last_error = None
        for attempt in range(1, max_retries + 1):
            log.info(f"--- 第 {attempt}/{max_retries} 次尝试 ---")
            try:
                if dry_run:
                    log.info(f"[DRY-RUN] 模拟向「{class_group}」发送文案")
                    log.info(f"[DRY-RUN] 模拟截图")
                    log.info(f"[DRY-RUN] 模拟向「{teacher_group}」发送截图")
                    return True

                win = find_wechat_window()
                bring_wechat_to_front(win)

                # 获取打开群的方式
                open_method = config.get("wechat", {}).get(
                    "open_method", "search")  # search 或 position
                class_position = config.get("wechat", {}).get(
                    "class_group_position", 2)  # 班级群在会话列表的位置
                teacher_position = config.get("wechat", {}).get(
                    "teacher_group_position", 1)  # 班主任群在会话列表的位置

                log.info(f"打开群方式: {open_method}")
                if open_method == "position":
                    log.info(f"  班级群位置: 第 {class_position} 项")
                    log.info(f"  班主任群位置: 第 {teacher_position} 项")
                    log.info("  提醒: 请确认已提前打开班级群和班主任群!")

                # 1. 班级群发文案
                if open_method == "position":
                    if not open_chat_by_session_position(win, class_position):
                        raise RuntimeError(f"无法打开班级群 (位置 {class_position})")
                else:
                    if not search_and_open_chat(win, class_group):
                        raise RuntimeError(f"无法打开班级群「{class_group}」")
                if not send_text_in_chat(win, text):
                    raise RuntimeError("发送文案失败")
                time.sleep(3)

                # 2. 截图
                shot_path = str(
                    SCREENSHOTS_DIR / f"screenshot_{today.isoformat()}_attempt{attempt}.png"
                )
                if not screenshot_wechat_window(win, shot_path):
                    raise RuntimeError("微信窗口截图失败")

                # 3. 班主任群发截图
                if open_method == "position":
                    if not open_chat_by_session_position(win, teacher_position):
                        raise RuntimeError(f"无法打开班主任群 (位置 {teacher_position})")
                else:
                    if not search_and_open_chat(win, teacher_group):
                        raise RuntimeError(f"无法打开班主任群「{teacher_group}」")
                if not send_image_in_chat(win, shot_path):
                    raise RuntimeError("发送截图失败")

                log.info("本次发送成功")
                records = load_sent_records()
                records[today.isoformat()] = {
                    "success": True,
                    "time": datetime.now().isoformat(),
                    "attempts": attempt,
                    "screenshot": shot_path if not test_mode else None,
                }
                save_sent_records(records)
                return True

            except Exception as e:
                last_error = f"第 {attempt} 次失败: {e}\n{traceback.format_exc()[-300:]}"
                log.error(last_error)
                if attempt < max_retries:
                    log.info(f"等待 {retry_interval}s 后重试...")
                    time.sleep(retry_interval)

        alert_failure(last_error or "未知错误", config)
        records = load_sent_records()
        records[today.isoformat()] = {
            "success": False,
            "time": datetime.now().isoformat(),
            "error": last_error,
        }
        save_sent_records(records)
        return False
    finally:
        # === 恢复休眠策略 ===
        allow_sleep()
        # === 资源清理: 自动删除 30 天前的旧日志/截图, 防止长期累积 ===
        try:
            cleanup_old_files(BASE_DIR, retention_days=30)
        except Exception as e:
            log.warning(f"资源清理失败 (忽略): {e}")


def main():
    parser = argparse.ArgumentParser(
        description="定州市第八中学 每日安全提醒自动化 (Windows, pywinauto 版)"
    )
    parser.add_argument("--date", help="指定日期 YYYY-MM-DD")
    parser.add_argument("--dry-run", action="store_true", help="模拟运行")
    parser.add_argument("--test", action="store_true", help="测试模式（发文件传输助手）")
    args = parser.parse_args()

    # 检测是否在 Microsoft Store 版 Python 下运行 (任务计划程序里可能有问题)
    import sys as _sys
    if "WindowsApps" in _sys.executable:
        log.warning("=" * 60)
        log.warning("警告: 你正在使用 Microsoft Store 版 Python!")
        log.warning("路径: " + _sys.executable)
        log.warning("这个版本在 Windows 任务计划程序里可能无法正常运行")
        log.warning("建议: 卸载这个版本, 从 https://www.python.org/downloads/")
        log.warning("      下载安装官方版 Python (勾选 Add to PATH)")
        log.warning("=" * 60)

    today = datetime.strptime(args.date, "%Y-%m-%d").date() if args.date else date.today()
    success = run_once(today, dry_run=args.dry_run, test_mode=args.test)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
