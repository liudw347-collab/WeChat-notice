# -*- coding: utf-8 -*-
"""
防休眠模块 (Windows)
功能:
    1. prevent_sleep(): 进入临界区, 临时阻止系统休眠/屏保 (脚本运行期间)
    2. allow_sleep():   退出临界区, 恢复系统原有策略
    3. wake_up_screen(): 唤醒屏幕 (用于定时任务执行时屏幕已黑的情况)
    4. disable_screensaver_temporarily(): 临时关闭屏保

原理:
    - 调用 Win32 API SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED)
      告诉系统"我正在干活, 别睡"
    - 这比改电源设置更优雅, 因为退出脚本后系统自动恢复

用法:
    from keep_awake import prevent_sleep, allow_sleep, wake_up_screen

    prevent_sleep()      # 脚本开始时调用
    try:
        ... 你的逻辑 ...
    finally:
        allow_sleep()    # 脚本结束时调用 (务必放 finally)

    # 如果定时任务触发时屏幕是黑的, 单独调用:
    wake_up_screen()
"""

import ctypes
import logging
import time
from ctypes import wintypes

log = logging.getLogger("keep_awake")

# SetThreadExecutionState 标志位
ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001
ES_DISPLAY_REQUIRED = 0x00000002
ES_AWAYMODE_REQUIRED = 0x00000040

# 加载 Win32 API (只在 Windows 上有 windll, Linux/Mac 上跳过)
_is_windows = hasattr(ctypes, 'windll')
if _is_windows:
    _kernel32 = ctypes.windll.kernel32
    _user32 = ctypes.windll.user32

    # SetThreadExecutionState 返回值类型
    _kernel32.SetThreadExecutionState.restype = wintypes.DWORD
    _kernel32.SetThreadExecutionState.argtypes = [wintypes.DWORD]
else:
    _kernel32 = None
    _user32 = None


def prevent_sleep():
    """阻止系统休眠/关闭屏幕, 直到调用 allow_sleep()"""
    try:
        # ES_CONTINUOUS 表示持续生效, 直到下次调用改变状态
        # ES_SYSTEM_REQUIRED 系统保持工作
        # ES_DISPLAY_REQUIRED 显示器保持开启
        _kernel32.SetThreadExecutionState(
            ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED
        )
        log.info("已阻止系统休眠 (持续生效)")
    except Exception as e:
        log.warning(f"prevent_sleep 失败: {e}")


def allow_sleep():
    """恢复系统原有的休眠策略"""
    try:
        _kernel32.SetThreadExecutionState(ES_CONTINUOUS)
        log.info("已恢复系统休眠策略")
    except Exception as e:
        log.warning(f"allow_sleep 失败: {e}")


def wake_up_screen():
    """唤醒屏幕 (用于定时任务执行时屏幕已黑的情况)

    实现: 模拟一次无关按键 (Shift), 触发系统唤醒
    """
    try:
        # 1. 通过 keybd_event 模拟按 Shift 键 (不会影响任何输入)
        #   VK_SHIFT = 0x10
        _user32.keybd_event(0x10, 0, 0x0000, 0)        # key down
        _user32.keybd_event(0x10, 0, 0x0002, 0)        # key up (KEYEVENTF_KEYUP)
        # 2. 移动鼠标 1 像素再移回, 唤醒屏幕
        #   GetCursorPos / SetCursorPos
        class POINT(ctypes.Structure):
            _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]
        pt = POINT()
        _user32.GetCursorPos(ctypes.byref(pt))
        _user32.SetCursorPos(pt.x + 1, pt.y + 1)
        time.sleep(0.05)
        _user32.SetCursorPos(pt.x, pt.y)
        log.info("已唤醒屏幕")
        time.sleep(1.0)  # 等待屏幕亮起
    except Exception as e:
        log.warning(f"wake_up_screen 失败: {e}")


def keep_awake_context():
    """上下文管理器用法

    示例:
        with keep_awake_context():
            send_wechat_message()
    """
    class _Ctx:
        def __enter__(self):
            prevent_sleep()
            wake_up_screen()
            return self
        def __exit__(self, *exc):
            allow_sleep()
            return False
    return _Ctx()


if __name__ == "__main__":
    # 自测: 5 秒不睡眠
    import sys
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    print("5 秒内不会睡眠, 屏幕保持亮...")
    prevent_sleep()
    wake_up_screen()
    for i in range(5, 0, -1):
        print(f"  {i}...")
        time.sleep(1)
    allow_sleep()
    print("已恢复, 测试结束")
