#!/data/data/com.termux/files/usr/bin/bash
# ============================================================
#  定州市第八中学 每日安全提醒 - 一键安装引导 (Android)
#
#  老师使用步骤:
#    1. 安装 Termux + Termux:API 两个 APP (F-Droid 版)
#    2. 打开 Termux, 复制下面整段命令粘贴回车:
#
#       curl -fsSL https://raw.githubusercontent.com/liudw347-collab/WeChat-notice/main/android/easy-install/bootstrap.sh | bash
#
#    3. 按提示完成配置 (会弹出网页表单填群名/时间)
#
#  本脚本会自动完成:
#    - 安装 Python / cron / termux-api 等依赖
#    - 下载项目代码
#    - 初始化 ATX
#    - 启动配置向导
#    - 注册定时任务
#    - 获取 wake-lock
# ============================================================
set -e

PROJECT_DIR="/storage/emulated/0/WeChat-notice"
ANDROID_DIR="$PROJECT_DIR/android"
REPO_URL="https://github.com/liudw347-collab/WeChat-notice.git"
MIRROR_REPO="https://ghproxy.com/https://github.com/liudw347-collab/WeChat-notice.git"

# ANSI 颜色
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
RED='\033[0;31m'
NC='\033[0m'

print_step() {
    echo -e "${CYAN}[$1]${NC} $2"
}
print_ok() {
    echo -e "${GREEN}[OK]${NC} $1"
}
print_warn() {
    echo -e "${YELLOW}[警告]${NC} $1"
}
print_err() {
    echo -e "${RED}[错误]${NC} $1"
}

echo "============================================================"
echo "  定州市第八中学 每日安全提醒 - 一键安装"
echo "  适合不会用电脑的老师, 在手机上完成所有配置"
echo "============================================================"
echo

# 检查 Termux
if [ ! -d "/data/data/com.termux" ]; then
    print_err "请在 Termux 中运行本脚本"
    exit 1
fi

# 检查存储权限
print_step "1/8" "检查存储权限..."
if [ ! -d "/storage/emulated/0" ]; then
    print_warn "需要存储权限, 正在请求..."
    termux-setup-storage
    sleep 3
    if [ ! -d "/storage/emulated/0" ]; then
        print_err "未获取存储权限, 请在系统设置中授予 Termux 存储权限后重试"
        exit 1
    fi
fi
print_ok "存储权限已获取"

# 更新包管理器
print_step "2/8" "更新 Termux 软件源..."
pkg update -y >/dev/null 2>&1 || {
    print_warn "更新失败, 尝试使用国内镜像..."
    sed -i 's@^\(deb.*stable main\)$@#\1\ndeb https://mirrors.tuna.tsinghua.edu.cn/termux/apt/termux-main stable main@' /data/data/com.termux/files/usr/etc/apt/sources.list
    pkg update -y
}

# 安装依赖
print_step "3/8" "安装基础软件包 (Python / cron / git / termux-api)..."
pkg install -y python git tsu openssl termux-api cronie wget openssh

print_step "4/8" "安装 Python 依赖..."
pip install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple
pip install uiautomator2 pillow requests -i https://pypi.tuna.tsinghua.edu.cn/simple

# 下载项目
print_step "5/8" "下载项目代码..."
mkdir -p "$PROJECT_DIR"
if [ -d "$PROJECT_DIR/.git" ]; then
    cd "$PROJECT_DIR"
    git pull --rebase || print_warn "更新失败, 继续使用现有版本"
else
    cd /storage/emulated/0
    rm -rf WeChat-notice
    print_step "5/8" "尝试从 GitHub 克隆..."
    if ! git clone --depth 1 "$REPO_URL" WeChat-notice; then
        print_warn "GitHub 直连失败, 尝试镜像..."
        git clone --depth 1 "$MIRROR_REPO" WeChat-notice || {
            print_err "下载失败, 请检查网络"
            exit 1
        }
    fi
fi
print_ok "项目已下载到 $PROJECT_DIR"

# 初始化 ATX
print_step "6/8" "初始化 ATX 辅助应用..."
python -m uiautomator2 init || print_warn "ATX 初始化失败, 你可以稍后手动运行 python -m uiautomator2 init"

# 获取 wake-lock
print_step "7/8" "获取 wake-lock (防止手机睡眠杀掉 Termux)..."
termux-wake-lock
# 持久化: 写入 .bashrc
if ! grep -q "termux-wake-lock" ~/.bashrc 2>/dev/null; then
    echo "termux-wake-lock 2>/dev/null" >> ~/.bashrc
fi
print_ok "wake-lock 已获取"

# 启动配置向导
print_step "8/8" "启动配置向导..."
echo
echo "============================================================"
echo "  接下来会启动配置向导"
echo "  请按提示输入:"
echo "    - 班级微信群名 (必填, 必须与微信中显示完全一致)"
echo "    - 班主任工作群名 (必填)"
echo "    - 每日发送时间 (默认 07:30)"
echo "============================================================"
echo
read -p "按回车开始配置向导..." _

python "$ANDROID_DIR/easy-install/config_wizard.py"

# 启动 cron
print_step "完成" "启动定时任务服务..."
pkill crond 2>/dev/null || true
crond
print_ok "cron 服务已启动"

echo
echo "============================================================"
echo -e "${GREEN}  安装完成！${NC}"
echo "============================================================"
echo
echo "最后一步 - 关闭电池优化 (最关键, 否则手机睡眠会停止运行):"
echo "  1. 设置 -> 应用 -> Termux -> 电池 -> 不受限"
echo "  2. 设置 -> 应用 -> Termux:API -> 电池 -> 不受限"
echo "  3. 设置 -> 应用 -> ATX -> 电池 -> 不受限"
echo "  4. 在 Termux 通知栏长按 -> 锁定"
echo "  5. 在手机自启动管理中允许 Termux (小米/华为/荣耀尤其重要)"
echo
echo "测试发送 (发到文件传输助手, 不影响真实群):"
echo "  python $ANDROID_DIR/wechat_daily_android.py --test"
echo
echo "立即手动触发一次:"
echo "  python $ANDROID_DIR/wechat_daily_android.py"
echo
echo "查看日志:"
echo "  cat $ANDROID_DIR/logs/run_\$(date +%F).log"
echo
echo "修改配置 (重新运行配置向导):"
echo "  python $ANDROID_DIR/easy-install/config_wizard.py"
echo
echo "卸载:"
echo "  crontab -l | grep -v wechat_daily_android.py | crontab -"
echo "  termux-wake-unlock"
echo
read -p "按回车键退出..."
