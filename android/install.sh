#!/data/data/com.termux/files/usr/bin/bash
# ============================================================
#  Android 一键安装脚本 (在 Termux 中执行)
#  定州市第八中学 每日安全提醒自动化
# ============================================================
set -e

PROJECT_DIR="/storage/emulated/0/WeChat-notice"
ANDROID_DIR="$PROJECT_DIR/android"

echo "============================================================"
echo "  定州市第八中学 每日安全提醒 - Android 安装"
echo "============================================================"
echo

# 检查 Termux:API (可选, 用于通知)
echo "[1/7] 安装 Termux 基础包..."
pkg update -y
pkg install -y python git tsu openssl termux-api cronie
echo

# 安装 Python 依赖
echo "[2/7] 安装 Python 依赖..."
pip install --upgrade pip
pip install uiautomator2 pillow
echo

# 初始化 ATX agent
echo "[3/7] 初始化 ATX agent (会在手机上安装 ATX 应用)..."
python -m uiautomator2 init
echo

# 准备项目目录
echo "[4/7] 准备项目目录..."
mkdir -p "$PROJECT_DIR"
mkdir -p "$ANDROID_DIR/logs"
mkdir -p "$ANDROID_DIR/screenshots"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cp "$SCRIPT_DIR/wechat_daily_android.py" "$ANDROID_DIR/"
cp "$SCRIPT_DIR/config.json" "$ANDROID_DIR/"
cp "../message_builder.py" "$PROJECT_DIR/" 2>/dev/null || \
  cp "$SCRIPT_DIR/../message_builder.py" "$PROJECT_DIR/" 2>/dev/null || true
echo "项目文件已复制到 $ANDROID_DIR"
echo

# 获取 Termux wake-lock, 防止手机睡眠时杀掉 Termux
echo "[5/7] 获取 Termux wake-lock (防止手机睡眠杀掉 Termux)..."
termux-wake-lock
echo "  已获取 wake-lock, Termux 将保持唤醒"
echo "  (退出 Termux 时仍会保持, 输入 termux-wake-unlock 可手动释放)"
echo

# 配置 cron
echo "[6/7] 配置 cron 定时任务 (每天 7:30 执行)..."
PYTHON_BIN="$(which python)"
CRON_LINE="30 7 * * * $PYTHON_BIN $ANDROID_DIR/wechat_daily_android.py >> $ANDROID_DIR/logs/cron.log 2>&1"

# 移除旧任务, 添加新任务
crontab -l 2>/dev/null | grep -v "wechat_daily_android.py" > /tmp/crontab.new || true
echo "$CRON_LINE" >> /tmp/crontab.new
crontab /tmp/crontab.new
echo "  已添加 cron: $CRON_LINE"
echo

# 启动 cron 服务
echo "[7/7] 启动 cron 服务..."
pkill crond 2>/dev/null || true
crond
echo "  cron 服务已启动"
echo

echo "============================================================"
echo "  安装完成！"
echo "============================================================"
echo
echo "接下来你需要做："
echo "  1. 编辑 $ANDROID_DIR/config.json, 修改群名"
echo "  2. 测试运行: python $ANDROID_DIR/wechat_daily_android.py --test"
echo "  3. 关闭 Termux 电池优化:"
echo "     设置 -> 应用 -> Termux -> 电池 -> 不受限"
echo "     设置 -> 应用 -> Termux:API -> 电池 -> 不受限"
echo "     设置 -> 应用 -> ATX -> 电池 -> 不受限"
echo "  4. 锁定 Termux 后台 (通知栏长按 Termux 通知 -> 锁定)"
echo "  5. 在手机自启动管理中, 允许 Termux 自启动"
echo "     (小米/红米: 安全中心 -> 应用管理 -> 自启动管理)"
echo "     (华为/荣耀: 设置 -> 应用启动管理 -> Termux -> 手动管理)"
echo
echo "查看日志: cat $ANDROID_DIR/logs/run_*.log"
echo "手动触发: python $ANDROID_DIR/wechat_daily_android.py"
echo "卸载定时: crontab -l | grep -v wechat_daily_android.py | crontab -"
echo "释放唤醒: termux-wake-unlock"
