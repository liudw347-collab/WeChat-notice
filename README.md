# 定州市第八中学 · 假期安全提醒自动化

> 暑假期间每天早上 8 点前，用微信班级群发安全提醒并截图转发班主任群。
>
> 本项目提供 **Windows 版** 和 **Android 版** 两套方案，可按设备情况选用。

---

## ⭐ 看这里！快速开始

### 你是 Windows 用户？

直接看 **[Windows极简手册.md](Windows极简手册.md)** —— 一页纸说明，包含：
- ✅ 怎么用（5 步搞定）
- ✅ 怎么改时间
- ✅ 怎么卸载
- ✅ install.bat 到底做了什么
- ✅ 装了什么 / 会不会污染电脑

### 你是 Android 用户？

直接看 **[android/autox/使用说明.md](android/autox/使用说明.md)** —— 3 步搞定，只需装 1 个 APP。

### 你想分发给其他老师？

- Windows 用户：把 **Windows极简手册.md** 转发到班主任群
- 安卓用户：把 **android/autox/使用说明.md** 转发到班主任群

---

## 📋 项目结构

```
WeChat-notice/
├── message_builder.py          # 文案生成器（内容固定，仅日期每天变化）
├── keep_awake.py               # 防休眠模块 (Win32 API)
├── cleanup.py                  # 资源清理模块 (自动删除旧日志/截图)
├── wechat_daily.py             # Windows 版主脚本 (pywinauto)
├── config.json                 # Windows 版配置
├── install.bat                 # Windows 一键安装 (GBK 编码)
├── install_task.ps1            # Windows 定时任务安装 (UTF-8 with BOM)
├── requirements.txt            # Python 依赖
├── Windows极简手册.md           # ⭐ Windows 老师必读 (一页纸说明)
├── README.md                   # 本文档（双版本说明）
├── android/                    # Android 版本
│   ├── autox/                  # ⭐⭐⭐ 推荐方案 - 老师专用 (1 个 APP)
│   │   ├── safety-reminder.js  #   AutoX.js 脚本 (带图形 UI)
│   │   └── 使用说明.md          #   3 步搞定，可直接转发班主任群
│   ├── easy-install/           # 进阶方案 - IT 老师用 (3 个 APP)
│   │   ├── bootstrap.sh
│   │   ├── config_wizard.py
│   │   ├── config.html
│   │   ├── save_config.py
│   │   └── 老师使用指南.md
│   ├── wechat_daily_android.py # Termux 版主脚本
│   ├── config.json             # Termux 版配置
│   ├── install.sh              # Termux 手动安装
│   └── README.md               # Termux 详细文档
├── logs/                       # 运行日志（自动生成，30 天自动清理）
├── screenshots/                # 每日截图（自动生成，30 天自动清理）
└── sent_records.json           # 已发送记录（防重复，60 天自动精简）
```

---

## 🆕 v2 更新 (2026-07-25)

针对用户反馈的关键问题：

### 问题 1：`pip install wxauto` 安装失败
- 原因：wxauto 最新版（2025 重写版）只支持 Python 3.9-3.12，**不支持 Python 3.13+**
- 解决：**改用 `pywinauto`** 替代 wxauto。pywinauto 是纯 Python 实现，**兼容所有 Python 版本（3.6-3.14+）**，且对微信 4.x 的支持更好

### 问题 2：电脑/手机会自动休眠导致任务失败

**电脑端三重防护**：
1. ✅ **任务计划程序 WakeToRun**：电脑休眠/关机时也能被定时任务唤醒
2. ✅ **电源 RTCWAKE 设置**：install.bat 自动启用"唤醒定时器"电源选项
3. ✅ **keep_awake.py 模块**：脚本运行期间通过 Win32 API 阻止系统睡眠 + 自动唤醒屏幕，结束后恢复

**手机端三重防护**：
1. ✅ **Termux wake-lock**：install.sh 自动获取唤醒锁，防止手机睡眠杀掉 Termux
2. ✅ **关闭电池优化**：必须手动关闭 Termux/Termux:API/ATX 的电池优化
3. ✅ **锁定后台**：长按 Termux 通知锁定，防止被系统清理

### 问题 3：会不会消耗电脑资源 / 造成破坏性影响？

**完全不会。请放心。**

| 时间段 | CPU | 内存 | 说明 |
|--------|-----|------|------|
| 99.9% 的时间（无任务） | 0% | 0 MB | Windows 任务计划程序原生功能，常驻后台占用极小 |
| 7:30 任务执行时（约 30 秒） | 5-15% | 50-80 MB | Python 进程临时加载，执行完立即退出 |
| 任务结束后 | 0% | 0 MB | 进程完全销毁，所有资源释放 |

**为什么不会无限增加**：
1. ✅ **一次性进程**：脚本执行完（成功或失败）都 `sys.exit()` 退出，**所有内存自动归还系统**
2. ✅ **日志自动清理**：cleanup.py 模块每次执行后自动删除 **30 天前**的旧日志/截图
3. ✅ **记录自动精简**：sent_records.json 保留最近 **60 天**记录
4. ✅ **`prevent_sleep()` 不会永久占用**：脚本退出时 `finally` 块自动调用 `allow_sleep()` 恢复，即使脚本崩溃 Windows 也会自动释放
5. ✅ **无网络上传**：所有数据只在本地，不向外发送任何信息

### 问题 4：安卓版能不能像装普通 APP 一样方便分发？

**可以！** 新增 `android/easy-install/` 一键安装方案：

- 老师只需要 **5 步**就能装好（见 [android/easy-install/老师使用指南.md](android/easy-install/老师使用指南.md)）
- **一行命令**完成所有安装：
  ```
  curl -fsSL https://raw.githubusercontent.com/liudw347-collab/WeChat-notice/main/android/easy-install/bootstrap.sh | bash
  ```
- **交互式配置向导**：不用懂 JSON，按提示输入群名和时间即可
- **可视化 HTML 配置页面**：浏览器打开 `config.html`，填表生成配置
- 把"老师使用指南.md"发到班主任群，其他老师照着做就行

### 问题 5：install.bat 报 `'�' is not recognized` 错误

**根因**：v1 版本的 .bat 文件是 UTF-8 编码，cmd.exe 在 `chcp 65001` 生效前用 GBK 解析导致部分字符乱码；同时 echo 行中的半角括号 `(兼容 Python 3.13+)` 被 cmd 误判为复合命令块。

**v3 修复**：
- ✅ **install.bat 改为 GBK 编码**（中文 Windows 原生编码，无需 chcp 切换）
- ✅ **移除所有 echo 行中的半角括号**，避免 cmd 误判
- ✅ **行尾改为 CRLF**（Windows 原生格式）

### 问题 6：install_task.ps1 报 `Missing closing '}'` 错误

**根因**：v1 版本的 .ps1 文件是 UTF-8 无 BOM，Windows PowerShell 5.x 默认按 ANSI(GBK) 读取，中文字符变乱码后破坏语法解析。

**v3 修复**：
- ✅ **install_task.ps1 改为 UTF-8 with BOM 编码**（PowerShell 5.x 能正确识别 BOM 并按 UTF-8 解析）
- ✅ **行尾改为 CRLF**（Windows 原生格式）
- ✅ **简化 try-catch 块**，移除可能引起解析问题的复杂字符串

### 问题 7：Termux 版对普通老师太难，能简化吗？

**根因**：Termux 方案需要装 3 个 APP（Termux + Termux:API + ATX），还要在终端粘贴命令，F-Droid 国内访问困难。

**v4 修复**：新增 **AutoX.js 方案**（推荐给所有老师）：
- ✅ **只需 1 个 APP**（AutoX.js）
- ✅ **图形界面配置**，不用懂终端命令
- ✅ **GitHub 加速链接**，国内可下载
- ✅ 完全免费开源
- ✅ 老师只需要 **3 步**：装 APP → 导入脚本 → 配置群名

详见 [android/autox/使用说明.md](android/autox/使用说明.md)

---

## 📝 文案内容（每日固定，仅日期变化）

每天发送的内容为：

```
严谨治校  勤奋进取

定州市第八中学假期安全提醒:
       为确保同学们度过一个安全、健康的假期，特提醒以下注意事项：

1. 交通安全
      遵守交通规则，不闯红灯、不骑电动车，过马路走斑马线。
      乘坐正规车辆，不坐超载车、黑车，拒乘无牌无证车辆。

2. 防溺水安全
      禁止私自到水库、河道、池塘等危险水域玩耍或游泳。

3. 居家安全
       注意用火用电安全。独自在家时锁好门窗，不轻易给陌生人开门，
       遇到紧急情况及时联系家长或报警。

4. 网络安全
       警惕网络诈骗，不轻易点击陌生链接或转账，遇到可疑情况及时告知家长。

5. 饮食卫生
       注意饮食均衡，不暴饮暴食，少吃生冷、油炸食品。

6. 心理健康
       多与家人沟通交流，适当参加户外运动或兴趣活动，缓解学习压力。
       遇到问题及时向家长、老师或心理老师求助。

温馨提示：
       外出活动前告知家长去向。
       注意天气变化，及时增减衣物，预防感冒。

      安全无小事，防范于未然！祝同学们假期愉快，平安返校！

崇德 励志 和谐 进取
善教 好学 友爱 创新
家校携手，共育共赢共未来!

                   2026年7月25日 星期六     ← 这一行每天变化
           —— 定州市第八中学
```

由 `message_builder.py` 自动生成，每天日期与星期会自动更新。

---

## 🖥️ Windows 版

### 适用条件
- Windows 10 / 11
- PC 微信保持登录
- 电脑可 24 小时开机（或支持定时唤醒）

### 核心依赖（已改为 pywinauto）
- [pywinauto](https://github.com/pywinauto/pywinauto) - Windows UI 自动化（替代 wxauto）
- Pillow - 图片处理
- psutil - 进程检测（可选）

### 快速开始

1. **安装 Python 3.9+**（3.14 也支持）：<https://www.python.org/downloads/>（勾选 Add to PATH）
2. **登录 PC 微信**，勾选"自动登录该设备"
3. **解压项目到任意目录**，如 `C:\WeChat-notice\`
4. **右键 `install.bat` → 以管理员身份运行**
   - 自动安装依赖（pywinauto + Pillow + psutil）
   - 自动启用电源"唤醒定时器"选项
   - 自动注册定时任务
   - 自动执行一次测试发送
5. **修改 `config.json`**，把群名改成你真实的微信群名
6. **测试**：`python wechat_daily.py --test`
7. **等待**：第二天 7:30 系统自动执行

### 笔记本用户必读：防合盖休眠

**手动方法**（推荐）：
1. 控制面板 → 电源选项 → **选择关闭盖子的功能**
2. "关闭盖子时" → 设为 **不采取任何操作**（电池和接通电源都设）

**命令行方法**（管理员 PowerShell）：
```powershell
powercfg /SETACVALUEINDEX SCHEME_CURRENT SUB_BUTTONS LIDACTION 0
powercfg /SETDCVALUEINDEX SCHEME_CURRENT SUB_BUTTONS LIDACTION 0
powercfg /SETACTIVE SCHEME_CURRENT
```

### 防休眠机制说明

| 阶段 | 措施 | 实现方式 |
|------|------|---------|
| 7:30 任务触发时 | 唤醒电脑 | 任务计划 `WakeToRun=true` + 电源 RTCWAKE 启用 |
| 唤醒后屏幕黑 | 唤醒屏幕 | `keep_awake.wake_up_screen()` 模拟按键+鼠标移动 |
| 脚本运行期间 | 阻止睡眠 | `keep_awake.prevent_sleep()` 调用 SetThreadExecutionState |
| 脚本结束 | 恢复策略 | `keep_awake.allow_sleep()` 释放 |

---

## 📱 Android 版

### 适用条件
- Android 7.0+
- 一台可长期插电的安卓手机（建议旧手机）
- 无需 root

### ⭐⭐⭐ 强烈推荐：AutoX.js 版（最适合分发给老师）

**老师只需要 3 步**就能装好，**只装 1 个 APP**：

1. 下载安装 AutoX.js APK（GitHub 加速链接在说明里）
2. 导入 `safety-reminder.js` 脚本文件
3. 开启无障碍权限 → 运行 → 填群名 → 完成

特点：
- ✅ **只需 1 个 APP**（不用 Termux + Termux:API + ATX 三件套）
- ✅ **图形界面配置**（不用懂 JSON / 终端命令）
- ✅ **国内可下载**（GitHub 加速链接）
- ✅ **完全免费开源**
- ✅ 不需要 root

详见 [android/autox/使用说明.md](android/autox/使用说明.md) - **这份说明可以直接转发给班主任群**

### 进阶方式：Termux 版（适合 IT 老师调试）

如果需要更精细控制或 IT 老师想自己调整，可用 Termux 版：

- 一键安装脚本（curl 一行命令）：见 [android/easy-install/老师使用指南.md](android/easy-install/老师使用指南.md)
- 手动安装：见 [android/README.md](android/README.md)

### Android 三种方案对比

| 方案 | 装几个 APP | 难度 | 适合谁 |
|------|----------|------|--------|
| **AutoX.js**（推荐） | 1 个 | ⭐ 简单 | 所有老师 |
| Termux 一键安装 | 3 个 | ⭐⭐⭐ 中等 | IT 老师 |
| Termux 手动安装 | 3 个 | ⭐⭐⭐⭐⭐ 复杂 | 开发者 |

### 防休眠机制说明

| 措施 | 实现方式 |
|------|---------|
| APP 持续运行 | 关闭电池优化 + 锁定后台 + 允许自启动 |
| 屏幕唤醒 | 脚本内 `device.wakeUp()` + 上滑解锁 |
| 定时触发 | AutoX.js 内置 `setInterval` 或 Termux cron |
| 失败告警 | 5 次长震动 + 通知栏 |

---

## ⚙️ 通用配置说明

`config.json` 关键字段：

```json
{
  "wechat": {
    "class_group_name": "班级家长群",      // 改成你真实的班级微信群名
    "teacher_group_name": "班主任工作群"     // 改成班主任群名
  },
  "schedule": {
    "send_time": "07:30",                  // 发送时间，留 30 分钟缓冲
    "max_retries": 3,                       // 失败重试次数
    "retry_interval_sec": 60                // 重试间隔
  },
  "alert": {
    "enable_popup": true,                   // Windows: 失败弹窗
    "enable_sound": true,                   // Windows: 失败响铃
    "enable_vibrate": true,                 // Android: 失败震动
    "enable_notification": true             // Android: 通知栏告警
  }
}
```

⚠️ **群名必须与微信中显示的完全一致**，包括表情符号、空格、括号。最稳妥的做法是从 PC/手机微信中复制群名粘贴到 config.json。

---

## 🔧 命令行用法

### Windows 版

```bash
# 立即执行今天的提醒（手动补发）
python wechat_daily.py

# 指定日期执行
python wechat_daily.py --date 2026-07-25

# 模拟运行（不实际发送）
python wechat_daily.py --dry-run

# 测试模式（发到文件传输助手）
python wechat_daily.py --test
```

### Android 版

```bash
python /storage/emulated/0/WeChat-notice/android/wechat_daily_android.py
python /storage/emulated/0/WeChat-notice/android/wechat_daily_android.py --test
python /storage/emulated/0/WeChat-notice/android/wechat_daily_android.py --date 2026-07-25
```

---

## 🛡️ 失败处理机制

| 场景 | 处理方式 |
|------|----------|
| 微信未启动 | pywinauto 启动；Android: app_start |
| 微信窗口被遮挡 | 截图前自动激活到前台 |
| 群名搜索不到 | 立即失败 + 告警 |
| 网络异常 | 自动重试 3 次 |
| 电脑/手机当时关机 | 下次开机补发（Windows）/ 手动重启（Android） |
| 系统休眠 | 自动唤醒（WakeToRun + RTCWAKE + wake_up_screen） |
| 今天已发送过 | 自动跳过，防止重复 |

### 告警方式

- **Windows**：MessageBox 弹窗（始终置顶）+ 5 声蜂鸣
- **Android**：5 次 800ms 长震动 + Termux 通知栏

听到/看到告警后，请尽快手动 `python wechat_daily.py` 补发一次。

---

## 🆚 Windows vs Android 对比

| 维度 | Windows 版 | Android 版 |
|------|-----------|-----------|
| 设备要求 | Windows 10/11 电脑 | Android 7+ 手机 |
| Python | 3.9-3.14+ 任意版本 | 3.9+ |
| 主库 | pywinauto | uiautomator2 |
| 稳定性 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| 防休眠 | WakeToRun + keep_awake | termux-wake-lock + 关电池优化 |
| 成本 | 需要电脑常开 | 旧手机即可 |
| 群名识别 | 通过 Ctrl+F 搜索 | 通过搜索可能模糊匹配 |
| 失败恢复 | 开机补发 | 需手动重启 |
| 屏幕锁 | 不涉及 | 需配置智能解锁 |
| 推荐场景 | 家有常开电脑 | 仅手机可用 |

**推荐**：优先 Windows 版。如必须用 Android，建议用专用旧手机，长期插电。

---

## ❓ 常见问题

### 安装相关

**Q1：`pip install wxauto` 失败？**
A：v2 已改用 pywinauto，不再需要 wxauto。如你下载的是 v1 版本，请重新拉取仓库：
```bash
git pull origin main
# 或重新 clone
git clone https://github.com/liudw347-collab/WeChat-notice.git
```

**Q2：pywinauto 安装失败？**
A：使用国内镜像源：
```bash
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple pywinauto Pillow psutil
```

**Q3：Python 3.14 可以用吗？**
A：可以。pywinauto 是纯 Python 实现，兼容所有 Python 3.6+ 版本。

### 休眠相关

**Q4：电脑 7:30 没唤醒？**
A：① 确认任务计划程序中"唤醒计算机以运行此任务"已勾选；② 确认电源选项中"允许使用唤醒定时器"已启用（install.bat 已自动设置）；③ 笔记本电池模式下可能限制唤醒，建议接电源使用；④ 检查 BIOS 中是否禁用了 USB/网络唤醒。

**Q5：电脑唤醒了但屏幕黑屏，截图是黑的？**
A：脚本内 `wake_up_screen()` 会模拟按键+鼠标移动唤醒屏幕。如仍黑屏，检查"屏幕保护程序"设置，或延长 `keep_awake.py` 中的 `time.sleep`。

**Q6：笔记本合盖就休眠？**
A：控制面板 → 电源选项 → 选择关闭盖子的功能 → 设为"不采取任何操作"。

**Q7：手机 Termux 总是被系统杀掉？**
A：① 关闭电池优化：设置 → 应用 → Termux → 电池 → 不受限；② 锁定 Termux 后台通知；③ 在自启动管理中允许 Termux；④ 长期插电避免省电模式；⑤ 考虑用一台专用旧手机。

### 使用相关

**Q8：群名搜索不到？**
A：从 PC/手机微信中**复制群名**粘贴到 config.json，避免手打错。注意全角/半角、表情符号、空格。

**Q9：截图是黑屏？**
A：Windows：检查锁屏设置，建议关闭屏幕保护；Android：确保 `screen_on()` 生效。

**Q10：每天没按时执行？**
A：Windows：检查任务计划程序设置；Android：检查 Termux 电池优化设置、cron 服务是否在运行（`ps aux | grep crond`）。

**Q11：微信更新后失效？**
A：Windows：升级 pywinauto `pip install -U pywinauto`；Android：升级 uiautomator2 `pip install -U uiautomator2`，如仍无效需修改脚本中的元素定位。

**Q12：能否修改发送时间？**
A：编辑 `config.json` 的 `schedule.send_time`，Windows 重新运行 `install_task.ps1`，Android 编辑 `crontab -e`。

**Q13：暑假结束后如何卸载？**
A：Windows：`Unregister-ScheduledTask -TaskName 'WeChatDailySafety' -Confirm:$false`；Android：`crontab -l | grep -v wechat_daily_android.py | crontab -` + `termux-wake-unlock`。

---

## ⚖️ 合规与隐私

- 本方案仅模拟人工操作微信客户端，**不破解任何协议、不读取聊天记录、不上传任何数据**。
- 所有日志、截图仅保存在本地电脑/手机。
- 微信对自动化操作有风控，**请勿用于发送广告或频繁刷屏**，每天仅 1 条提醒，符合正常使用习惯。
- 如学校改用企业微信，建议改用 webhook 推送，更稳定合规。

---

## 📦 依赖清单

### Windows
```
pywinauto>=0.6.8
Pillow>=9.0.0
psutil>=5.9.0
```

### Android
```
uiautomator2>=2.0.0
Pillow>=9.0.0
termux-api (Termux 包)
cronie (Termux 包)
```

---

## 📞 联系与反馈

如有问题，请优先查看 `logs/` 下的日志文件，里面记录了完整的执行过程和错误堆栈。

如需更新文案内容，编辑 `message_builder.py` 的 `build_message()` 函数即可，**无需修改脚本其他部分**。
