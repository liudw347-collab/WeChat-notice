# Android 版 每日安全提醒自动化

> 适用场景：没有 PC 微信、只想用安卓手机自动完成。
>
> 技术栈：Termux + Python + uiautomator2（控制安卓微信 UI） + cron 定时。

---

## 一、原理

Android 上控制微信发消息的最佳方案是 [uiautomator2](https://github.com/openatx/uiautomator2)：
- 它通过 Android 系统自带的 UIAutomator 框架操作 APP 界面，**不需要 root**；
- 可以模拟点击、输入、截图、滑动等操作；
- 配合 Termux 内的 cron，每天 7:30 自动唤醒手机、启动微信、发消息、截图、转发。

---

## 二、准备工作

### 1. 安装 Termux（关键！）

⚠️ **不要用应用商店版的 Termux**（已停止更新），必须用 F-Droid 版：

- 打开 <https://f-droid.org/packages/com.termux/>
- 下载 APK 安装

同时安装 **Termux:API**（用于通知）：
- <https://f-droid.org/packages/com.termux.api/>

### 2. 安装 ATX agent

uiautomator2 需要一个名叫 "ATX" 的辅助 APP 安装到手机上：
- 打开 Termux，运行 `pkg install python`
- 运行 `pip install uiautomator2`
- 运行 `python -m uiautomator2 init`
- 手机会自动安装 "ATX" 应用，**保持它启用**

### 3. 关闭 Termux 电池优化（最关键）

否则手机进入睡眠后 cron 不会运行：

- **设置 → 应用 → Termux → 电池 → 不受限**
- **设置 → 应用 → Termux:API → 电池 → 不受限**
- **设置 → 应用 → ATX → 电池 → 不受限**
- 在 Termux 通知栏长按 → **锁定**（防止被系统清理）
- **手机自启动管理**中允许 Termux 自启动（小米/红米在安全中心，华为/荣耀在设置→应用启动管理）

### 3.5 获取 Termux wake-lock（防睡眠关键）

install.sh 会自动执行 `termux-wake-lock`，但**手机重启后需要重新获取**。

手动获取/释放：
```bash
termux-wake-lock      # 获取唤醒锁 (Termux 保持唤醒)
termux-wake-unlock    # 释放唤醒锁 (Termux 可被睡眠)
```

让 wake-lock 开机自动获取，编辑 `~/.bashrc`（每次打开 Termux 自动执行）：
```bash
echo "termux-wake-lock 2>/dev/null" >> ~/.bashrc
```

或在 cron 中加一条开机任务：
```bash
crontab -e
# 添加: 每分钟检查一次, 没有就获取
* * * * * pgrep -f "termux-wake-lock" > /dev/null || termux-wake-lock
```

### 4. 屏幕锁设置

脚本只会上滑解锁，**无法输入密码**。建议：
- 早晨 7:30 时手机不锁密码（智能解锁：到家/连蓝牙耳机时保持解锁）
- 或临时关闭锁屏密码（不推荐）
- 或使用 Tasker 配合，在脚本运行前自动解锁（高级）

---

## 三、部署步骤

### 1. 把项目文件复制到手机

把整个 `WeChat-notice` 文件夹复制到手机存储根目录：
- 路径应为 `/storage/emulated/0/WeChat-notice/`
- 用 USB 数据线 / 微信文件传输助手 / OTG U盘 都可以

### 2. 在 Termux 中执行安装脚本

```bash
# 进入项目 android 目录
cd /storage/emulated/0/WeChat-notice/android

# 赋予执行权限
chmod +x install.sh

# 执行安装
./install.sh
```

脚本会自动：
- 安装 Python、cron、termux-api 等依赖
- 安装 uiautomator2、Pillow
- 初始化 ATX agent
- 添加 cron 定时任务（每天 7:30）
- 获取 Termux wake-lock（防止手机睡眠杀掉 Termux）
- 启动 cron 服务

### 3. 修改配置

```bash
# 用 nano 或 vim 编辑 config.json
nano /storage/emulated/0/WeChat-notice/android/config.json
```

把 `class_group_name` 和 `teacher_group_name` 改成你真实的微信群名。

### 4. 测试运行

```bash
# 测试模式：发到文件传输助手，不污染真实群
python /storage/emulated/0/WeChat-notice/android/wechat_daily_android.py --test
```

观察手机：
- 屏幕亮起
- 微信自动打开
- 切到文件传输助手
- 发出测试文字 + 截图

### 5. 等待自动执行

第二天 7:30，cron 会自动唤醒手机执行脚本。

---

## 四、常用命令

```bash
# 立即手动执行
python /storage/emulated/0/WeChat-notice/android/wechat_daily_android.py

# 指定日期补发
python /storage/emulated/0/WeChat-notice/android/wechat_daily_android.py --date 2026-07-24

# 模拟运行（不实际发送）
python /storage/emulated/0/WeChat-notice/android/wechat_daily_android.py --dry-run

# 查看今天的日志
cat /storage/emulated/0/WeChat-notice/android/logs/run_$(date +%F).log

# 查看 cron 日志
cat /storage/emulated/0/WeChat-notice/android/logs/cron.log

# 查看 cron 任务
crontab -l

# 编辑 cron 任务
crontab -e

# 卸载定时任务
crontab -l | grep -v wechat_daily_android.py | crontab -

# 重启 cron 服务
pkill crond && crond
```

---

## 五、定时任务管理

cron 表达式格式：`分 时 日 月 周 命令`

当前配置（每天 7:30 执行）：
```
30 7 * * * /data/data/com.termux/files/usr/bin/python /storage/emulated/0/WeChat-notice/android/wechat_daily_android.py >> /storage/emulated/0/WeChat-notice/android/logs/cron.log 2>&1
```

修改发送时间示例：
- 改为 7:00：`0 7 * * * ...`
- 改为工作日 7:30：`30 7 * * 1-5 ...`
- 改为周末 8:00：`0 8 * * 0,6 ...`

修改后必须重启 cron：`pkill crond && crond`

---

## 六、失败处理

| 场景 | 处理 |
|------|------|
| 微信未启动 | 脚本会自动 `app_start` 启动微信 |
| 屏幕锁未解 | 脚本上滑解锁，但若需要密码会失败 → 告警震动 |
| 群名搜索不到 | 立即失败 + 长震动告警 |
| Termux 被系统清理 | cron 不执行，需手动补发 |
| 手机睡眠 | wake-lock + 关闭电池优化可解决 99% 情况 |
| 微信弹窗（如更新提示）挡住 | 失败重试 3 次 |
| 手机重启 | wake-lock 失效，需打开 Termux 重新获取 |

### 告警方式
- **长震动**：5 次 800ms 震动
- **Termux 通知**：通知栏弹出"安全提醒发送失败"

---

## 七、常见问题

**Q1：cron 没在 7:30 执行**
A：① 检查 Termux 是否被电池优化清理：设置 → 应用 → Termux → 电池 → 不受限；② 锁定 Termux 后台；③ 用 `crond -x` 查看调试输出；④ 确认 `termux-wake-lock` 已获取（通知栏会有 Termux 持续运行图标）；⑤ 重启手机后需重新打开 Termux 触发 wake-lock（或写入 .bashrc）。

**Q2：脚本提示"无法连接设备"**
A：打开 ATX 应用，确认显示"已启动"；运行 `python -m uiautomator2 init` 重新初始化。

**Q3：搜索群名时找不到**
A：① 群名拼写错误，检查 config.json；② 微信版本更新后 UI 变化，可能需要更新 uiautomator2 (`pip install -U uiautomator2`)。

**Q4：截图是黑屏**
A：脚本运行时屏幕必须亮起。检查 `screen_on()` 是否生效。如手机有"防截屏"模式请关闭。

**Q5：图片没有发出，只发了文字**
A：微信相册的图片选择界面 UI 可能在不同版本有差异。手动在微信里发送一张图，观察界面元素，调整 `send_image_in_chat` 中的 resource ID。

**Q6：手机没有 root 可以用吗？**
A：完全可以，uiautomator2 不需要 root。

**Q7：插着电过夜安全吗？**
A：现代手机有过充保护，长期插电对电池损耗略大但无安全风险。如担心可使用智能插座定时通电。

---

## 八、与 Windows 版的对比

| 维度 | Windows 版 | Android 版 |
|------|-----------|-----------|
| 设备 | 一台常开电脑 | 一台安卓手机 |
| 成本 | 需要电脑 24 小时开机 | 旧手机即可 |
| 稳定性 | ⭐⭐⭐⭐⭐ 高 | ⭐⭐⭐ 中（手机易被清理） |
| 群名识别 | 精确 | 通过搜索可能模糊匹配 |
| 截图清晰度 | 高 | 中 |
| 失败恢复 | 任务计划+开机补发 | 需手动重启 |
| 推荐场景 | 家里有电脑 | 仅手机可用 |

**建议**：优先用 Windows 版；如果用 Android 版，建议用一台**专门**的旧手机，长期插电、关闭省电模式、锁定 Termux 后台。

---

## 九、卸载

```bash
# 移除定时任务
crontab -l | grep -v wechat_daily_android.py | crontab -

# 停止 cron
pkill crond

# 卸载 Termux 相关 APP（在手机设置里）
# 卸载 ATX 应用
```
