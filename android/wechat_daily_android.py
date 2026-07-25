# -*- coding: utf-8 -*-
"""
每日安全提醒自动化 (Android 版) - 核心执行脚本
项目: WeChat-notice / 定州市第八中学假期安全提醒

运行环境:
    - 安卓手机 (Android 7.0+)
    - Termux 终端 (F-Droid 版, 不要用 Play Store 版)
    - Python 3 (Termux 内安装)
    - uiautomator2 (Python 库)
    - ATX agent (uiautomator2 自动安装)

依赖安装 (Termux 内执行):
    pkg update && pkg upgrade -y
    pkg install python git tsu openssl -y
    pip install --upgrade pip
    pip install uiautomator2 pillow
    python -m uiautomator2 init   # 给手机安装 ATX agent APP

工作流程:
    1. 通过 message_builder 生成本日文案
    2. 唤醒手机 + 解锁 (需配置屏幕锁)
    3. 通过 uiautomator2 启动微信
    4. 在班级群发送文案
    5. 截图
    6. 在班主任群发送截图
    7. 失败重试 3 次, 仍失败则震动 + 通知栏告警

定时:
    使用 Termux 内的 cron 实现每天 7:30 自动执行
    pkg install cronie -y
    crontab -e
    添加: 30 7 * * * /data/data/com.termux/files/usr/bin/python /storage/emulated/0/WeChat-notice/android/wechat_daily_android.py >> /storage/emulated/0/WeChat-notice/logs/cron.log 2>&1

命令行用法:
    python wechat_daily_android.py                  # 立即执行今日提醒
    python wechat_daily_android.py --date 2026-07-25  # 指定日期
    python wechat_daily_android.py --dry-run        # 模拟
    python wechat_daily_android.py --test           # 测试 (发文件传输助手)
"""

import argparse
import json
import logging
import os
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

# 把父目录加入 sys.path, 复用 message_builder
sys.path.insert(0, str(BASE_DIR.parent))
from message_builder import build_message

for d in [LOGS_DIR, SCREENSHOTS_DIR]:
    d.mkdir(exist_ok=True)


def setup_logger():
    log_file = LOGS_DIR / f"run_{date.today().isoformat()}.log"
    logger = logging.getLogger("wechat_daily_android")
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


# ----------------- 设备操作 -----------------

def wake_unlock_device():
    """唤醒屏幕并上滑解锁(不输入密码,适用于无密码或智能解锁场景)"""
    try:
        import uiautomator2 as u2
        d = u2.connect()
        log.info("设备已连接")
        # 屏幕亮起
        d.screen_on()
        time.sleep(1)
        # 上滑解锁
        d.swipe(0.5, 0.8, 0.5, 0.2, 0.3)
        time.sleep(1)
        return d
    except Exception as e:
        log.error(f"唤醒/连接设备失败: {e}")
        raise


def launch_wechat(d):
    """启动微信"""
    package = "com.tencent.mm"
    try:
        d.app_start(package, wait=True)
        time.sleep(3)
        log.info("微信已启动")
    except Exception as e:
        log.error(f"启动微信失败: {e}")
        raise


def open_chat_by_search(d, name: str):
    """通过搜索打开指定群/联系人"""
    # 点击搜索按钮 (微信主界面右上角放大镜)
    # 由于微信 UI 在不同版本有差异, 这里用资源 ID 定位更可靠
    try:
        # 点击搜索入口
        d(resourceId="com.tencent.mm:id/icon_search").click_exists(timeout=3) or \
        d(description="搜索").click_exists(timeout=3) or \
        d(className="android.widget.ImageView", instance=0).click_exists(timeout=3)
        time.sleep(1.5)
        # 输入群名
        search_edit = d(resourceId="com.tencent.mm:id/b4m") or \
                      d(resourceId="com.tencent.mm:id/kbq") or \
                      d(className="android.widget.EditText")
        search_edit.set_text(name)
        time.sleep(2)
        # 点击搜索结果第一条 (通常是"群聊"分类下)
        # 找到包含该名称的 TextView 并点击
        target = d(text=name)
        if target.exists:
            target.click()
            time.sleep(2)
            log.info(f"已进入会话: {name}")
            return True
        # 如果精确匹配找不到, 点击列表第一项
        d(className="android.widget.LinearLayout", instance=2).click_exists(timeout=3)
        time.sleep(2)
        log.info(f"已进入搜索结果首项 (可能不是精确匹配 {name})")
        return True
    except Exception as e:
        log.error(f"搜索会话失败: {e}")
        return False


def send_text_in_chat(d, text: str):
    """在当前会话窗口输入并发送文字"""
    try:
        # 输入框
        edit = d(resourceId="com.tencent.mm:id/bkk") or \
               d(resourceId="com.tencent.mm:id/b4a") or \
               d(className="android.widget.EditText")
        edit.set_text(text)
        time.sleep(1.5)
        # 发送按钮
        send_btn = d(resourceId="com.tencent.mm:id/b6l") or \
                   d(text="发送") or \
                   d(description="发送")
        send_btn.click()
        time.sleep(1.5)
        log.info("文字消息已发送")
        return True
    except Exception as e:
        log.error(f"发送文字失败: {e}")
        return False


def take_screenshot(d, save_path: str):
    """截图并保存 - 只截微信聊天区域, 裁掉顶部状态栏/标题栏和左侧聊天列表

    微信 Android 界面结构:
        ┌────────────────────────────┐
        │ 状态栏 (电量/时间)           │  顶部 ~30dp
        ├────────────────────────────┤
        │ 标题栏 (群名 + 成员数 + ...)  │  ~50dp
        ├────────────────────────────┤
        │                            │
        │   聊天消息区域 (我们要截的)   │
        │                            │
        ├────────────────────────────┤
        │ 输入框 / + 按钮 / 发送       │  底部 ~50dp
        └────────────────────────────┘
    """
    try:
        # 获取屏幕尺寸
        info = d.info
        screen_w = info["displayWidth"]
        screen_h = info["displayHeight"]
        log.info(f"屏幕尺寸: {screen_w}x{screen_h}")

        # 截全屏
        full_img = d.screenshot()
        full_w, full_h = full_img.size
        log.info(f"截图尺寸: {full_w}x{full_h}")

        # 计算裁剪区域:
        # - 顶部裁掉状态栏 + 标题栏 (约屏幕高度的 12%, 至少 80px, 至多 200px)
        # - 底部裁掉输入框 (约屏幕高度的 8%, 至少 60px, 至多 150px)
        # - 横向保留全部 (聊天内容通常占满宽度)
        top_cut = max(80, min(int(full_h * 0.12), 200))
        bottom_cut = max(60, min(int(full_h * 0.08), 150))

        # 裁剪
        from PIL import Image
        cropped = full_img.crop((0, top_cut, full_w, full_h - bottom_cut))
        cropped.save(save_path)
        log.info(f"已截图 (仅聊天区域): {save_path}, "
                 f"尺寸 {cropped.width}x{cropped.height} "
                 f"(裁掉顶部 {top_cut}px + 底部 {bottom_cut}px)")
        return True
    except Exception as e:
        log.error(f"裁剪截图失败, 兜底截全屏: {e}")
        try:
            img = d.screenshot()
            img.save(save_path)
            log.warning(f"已截全屏 (兜底): {save_path}")
            return True
        except Exception as e2:
            log.error(f"截图失败: {e2}")
            return False


def send_image_in_chat(d, image_path: str):
    """在当前会话发送图片"""
    try:
        # 点击 "+" 按钮
        d(resourceId="com.tencent.mm:id/b6k").click_exists(timeout=3) or \
        d(description="更多功能按钮").click_exists(timeout=3) or \
        d(className="android.widget.ImageView", instance=2).click_exists(timeout=3)
        time.sleep(1.5)
        # 点击 "相册"
        d(text="相册").click_exists(timeout=3)
        time.sleep(2)
        # 选择第一张图 (刚截图的图会在最前)
        # 一般第一张是缩略图网格, 点击 instance=0
        d(className="android.widget.ImageView", instance=0).click_exists(timeout=3)
        time.sleep(1.5)
        # 点击发送
        d(resourceId="com.tencent.mm:id/lns").click_exists(timeout=3) or \
        d(text="发送").click_exists(timeout=3) or \
        d(description="发送").click_exists(timeout=3)
        time.sleep(2)
        log.info(f"图片已发送: {image_path}")
        return True
    except Exception as e:
        log.error(f"发送图片失败: {e}")
        return False


# ----------------- 告警 -----------------

def alert_failure(reason: str, config):
    log.error(f"告警触发: {reason}")
    alert_cfg = config.get("alert", {})
    try:
        import uiautomator2 as u2
        d = u2.connect()
        # 长震动
        for _ in range(5):
            d.shell("cmd vibration vibrate 800")
            time.sleep(0.4)
        # 通知栏
        d.shell(
            f'am broadcast -a com.android.server.action.NOTIFY -e title "安全提醒失败" '
            f'-e text "{reason[:100]}"'
        )
        # termux-notification 更明显
        d.shell(
            f'termux-notification --title "安全提醒发送失败" '
            f'--content "{reason[:200]}" --priority high'
        )
    except Exception as e:
        log.error(f"告警执行失败: {e}")


# ----------------- 主流程 -----------------

def run_once(today: date, dry_run: bool = False, test_mode: bool = False):
    log.info(f"=== 开始执行 {today.isoformat()} 安全提醒任务 ===")
    config = load_config()

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

    last_error = None
    for attempt in range(1, max_retries + 1):
        log.info(f"--- 第 {attempt}/{max_retries} 次尝试 ---")
        try:
            if dry_run:
                log.info(f"[DRY-RUN] 模拟向「{class_group}」发送文案")
                log.info(f"[DRY-RUN] 模拟截图")
                log.info(f"[DRY-RUN] 模拟向「{teacher_group}」发送截图")
                return True

            d = wake_unlock_device()
            launch_wechat(d)

            # 1. 班级群发文案
            if not open_chat_by_search(d, class_group):
                raise RuntimeError(f"无法打开班级群「{class_group}」")
            if not send_text_in_chat(d, text):
                raise RuntimeError("发送文案失败")
            time.sleep(3)

            # 2. 截图
            shot_path = str(
                SCREENSHOTS_DIR / f"screenshot_{today.isoformat()}_attempt{attempt}.png"
            )
            if not take_screenshot(d, shot_path):
                raise RuntimeError("截图失败")

            # 3. 班主任群发截图
            if not open_chat_by_search(d, teacher_group):
                raise RuntimeError(f"无法打开班主任群「{teacher_group}」")
            if not send_image_in_chat(d, shot_path):
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

            # 回到桌面, 关闭微信以节省电量
            try:
                d.app_stop("com.tencent.mm")
            except Exception:
                pass
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


def main():
    parser = argparse.ArgumentParser(
        description="定州市第八中学 每日安全提醒自动化 (Android)"
    )
    parser.add_argument("--date", help="指定日期 YYYY-MM-DD")
    parser.add_argument("--dry-run", action="store_true", help="模拟运行")
    parser.add_argument("--test", action="store_true", help="测试模式（发文件传输助手）")
    args = parser.parse_args()

    today = datetime.strptime(args.date, "%Y-%m-%d").date() if args.date else date.today()
    success = run_once(today, dry_run=args.dry_run, test_mode=args.test)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
