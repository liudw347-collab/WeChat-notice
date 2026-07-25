# -*- coding: utf-8 -*-
"""
资源清理模块
- 自动清理超过 N 天的旧日志文件
- 自动清理超过 N 天的旧截图文件
- 防止长期累积占用磁盘

清理策略:
    - logs/run_YYYY-MM-DD.log       保留最近 30 天
    - screenshots/screenshot_*.png  保留最近 30 天
    - sent_records.json             仅保留最近 60 天的记录
"""

import json
import logging
import os
from datetime import date, timedelta
from pathlib import Path

log = logging.getLogger("cleanup")

DEFAULT_RETENTION_DAYS = 30
RECORDS_RETENTION_DAYS = 60


def cleanup_old_files(base_dir: Path, retention_days: int = DEFAULT_RETENTION_DAYS) -> dict:
    """清理旧日志、截图, 返回清理统计"""
    base_dir = Path(base_dir)
    logs_dir = base_dir / "logs"
    screenshots_dir = base_dir / "screenshots"
    records_file = base_dir / "sent_records.json"

    stats = {"logs_deleted": 0, "screenshots_deleted": 0, "records_pruned": 0,
             "freed_bytes": 0}

    cutoff_date = date.today() - timedelta(days=retention_days)
    cutoff_str = cutoff_date.isoformat()

    # 1. 清理日志 (文件名格式: run_YYYY-MM-DD.log)
    if logs_dir.exists():
        for f in logs_dir.glob("run_*.log"):
            try:
                # 从文件名提取日期
                name = f.stem  # run_2026-07-25
                date_str = name.replace("run_", "")
                file_date = date.fromisoformat(date_str)
                if file_date < cutoff_date:
                    size = f.stat().st_size
                    f.unlink()
                    stats["logs_deleted"] += 1
                    stats["freed_bytes"] += size
                    log.info(f"删除旧日志: {f.name}")
            except Exception as e:
                log.warning(f"无法解析日志文件日期 {f.name}: {e}")

    # 2. 清理截图 (文件名格式: screenshot_YYYY-MM-DD_attempt*.png)
    if screenshots_dir.exists():
        for f in screenshots_dir.glob("screenshot_*.png"):
            try:
                name = f.stem  # screenshot_2026-07-25_attempt1
                # 提取日期部分
                parts = name.split("_")
                if len(parts) >= 2:
                    date_str = parts[1]
                    file_date = date.fromisoformat(date_str)
                    if file_date < cutoff_date:
                        size = f.stat().st_size
                        f.unlink()
                        stats["screenshots_deleted"] += 1
                        stats["freed_bytes"] += size
                        log.info(f"删除旧截图: {f.name}")
            except Exception as e:
                log.warning(f"无法解析截图文件日期 {f.name}: {e}")

    # 3. 精简已发送记录 (保留最近 60 天)
    if records_file.exists():
        try:
            with open(records_file, "r", encoding="utf-8") as f:
                records = json.load(f)
            original_count = len(records)
            cutoff_records = (date.today() - timedelta(days=RECORDS_RETENTION_DAYS)).isoformat()
            records = {k: v for k, v in records.items() if k >= cutoff_records}
            if len(records) < original_count:
                with open(records_file, "w", encoding="utf-8") as f:
                    json.dump(records, f, ensure_ascii=False, indent=2)
                stats["records_pruned"] = original_count - len(records)
                log.info(f"精简记录: {original_count} → {len(records)}")
        except Exception as e:
            log.warning(f"清理记录文件失败: {e}")

    if stats["logs_deleted"] + stats["screenshots_deleted"] + stats["records_pruned"] > 0:
        freed_kb = stats["freed_bytes"] / 1024
        log.info(
            f"清理完成: 日志 {stats['logs_deleted']} 个, "
            f"截图 {stats['screenshots_deleted']} 个, "
            f"记录 {stats['records_pruned']} 条, "
            f"释放 {freed_kb:.1f} KB"
        )
    else:
        log.info("无需清理")

    return stats


def print_disk_usage(base_dir: Path) -> dict:
    """打印项目目录占用情况"""
    base_dir = Path(base_dir)
    total_size = 0
    file_count = 0
    for root, dirs, files in os.walk(base_dir):
        # 跳过 __pycache__
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for f in files:
            fp = Path(root) / f
            try:
                total_size += fp.stat().st_size
                file_count += 1
            except Exception:
                pass

    usage = {
        "total_files": file_count,
        "total_size_bytes": total_size,
        "total_size_mb": round(total_size / (1024 * 1024), 2),
    }
    log.info(f"项目磁盘占用: {usage['total_files']} 个文件, {usage['total_size_mb']} MB")
    return usage


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    import sys
    base = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    print_disk_usage(base)
    cleanup_old_files(base)
    print_disk_usage(base)
