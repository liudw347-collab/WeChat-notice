# Windows 版 · 老师极简手册

> 这一页就够了。看完就知道怎么用、怎么改、怎么删。

---

## ❓ 5 个最常见的问题

### Q1：我运行 install.bat 之后还要做什么？

**答：只做 1 件事——改群名。**

具体来说：
1. 双击 `install.bat`（右键以管理员身份运行）
   - 它会自动装好依赖
   - 自动注册定时任务（每天 7:30 触发）
   - 自动配置电源选项
   - 自动测试发送一次（发到"文件传输助手"，不影响真实群）
2. **打开 `config.json`**（用记事本）
3. **选择打开群的方式**（推荐用 `position` 方式，100% 可靠）：
   - **`position` 方式（推荐）**：完全不搜索，直接点会话列表
     ```json
     "open_method": "position",
     "class_group_position": 2,
     "teacher_group_position": 1
     ```
     使用前需要每天：① 打开微信 → ② 鼠标点班级群 → ③ 鼠标点班主任群
     这样班主任群 = 第 1 位，班级群 = 第 2 位，脚本会自动点击
   - **`search` 方式（备选）**：用 Ctrl+F 搜索群名
     ```json
     "open_method": "search",
     "class_group_name": "改成你的班级群名",
     "teacher_group_name": "改成你的班主任群名"
     ```
     不需要提前打开，但微信 4.x 上可能搜不到
4. **测试位置点击方案**（如果选了 position）：
   ```
   python test_position_click.py
   ```
   按提示操作，确认能正确切换群

#### position 方式的每日准备（重要！）

如果用了 `position` 方式，**每天电脑开机后/微信重启后**必须做一次：
1. 打开 PC 微信
2. 鼠标点击**班级群**（进入班级群聊天界面）
3. 鼠标点击**班主任群**（进入班主任群聊天界面）

这样会话列表里班主任群是第 1 个，班级群是第 2 个，脚本才能正确点击。

> 💡 这个操作**只需每天做一次**，做完后定时任务会自动完成剩下的发送工作。

5. **再运行一次测试**：在文件夹里打开命令行（地址栏输入 `cmd` 回车），输入：
   ```
   python wechat_daily.py --test
   ```
   如果"文件传输助手"收到了测试消息+截图，就成功了！

**就这些，不用再做别的。** 第二天 7:30 系统自动执行。

---

### Q2：怎么改发送时间？（比如从 7:30 改成 7:00）

**3 步搞定：**

1. 用记事本打开 `config.json`
2. 找到这一行：
   ```json
   "send_time": "07:30",
   ```
   改成你想要的时间，比如：
   ```json
   "send_time": "07:00",
   ```
3. **重新运行一次 `install.bat`**（让新时间生效）

完成。下次 7:00 就会执行。

---

### Q3：不想用了怎么卸载？

**3 步彻底删除：**

#### 第 1 步：删除定时任务

按 `Win + R` → 输入 `powershell` → 回车，粘贴下面命令回车：

```powershell
Unregister-ScheduledTask -TaskName 'WeChatDailySafety' -Confirm:$false
```

看到没有报错就成功了。验证一下：
```powershell
Get-ScheduledTask -TaskName 'WeChatDailySafety'
```
如果提示"找不到任务"，说明已删除。

#### 第 2 步：删除项目文件夹

直接把整个 `WeChat-notice` 文件夹删除（右键 → 删除）。

#### 第 3 步：（可选）恢复电源设置

如果你想恢复电源设置，按 `Win + R` → 输入 `powershell` → 回车，粘贴：

```powershell
powercfg /SETACVALUEINDEX SCHEME_CURRENT SUB_SLEEP RTCWAKE 0
powercfg /SETDCVALUEINDEX SCHEME_CURRENT SUB_SLEEP RTCWAKE 0
powercfg /SETACTIVE SCHEME_CURRENT
```

**卸载完成。** Python 和已安装的库（pywinauto 等）可以保留，不影响其他用途；如果想彻底清理，去"设置 → 应用"卸载 Python。

---

### Q4：定时任务是怎么注册的？

`install.bat` 调用 `install_task.ps1` 在 Windows **任务计划程序**里注册了一个名叫 `WeChatDailySafety` 的任务。

**查看方法：**
- 按 `Win + R` → 输入 `taskschd.msc` → 回车，打开"任务计划程序"
- 在左侧"任务计划程序库"里找到 `WeChatDailySafety`
- 双击可以看到详细配置

**这个任务做了什么：**
- 每天 7:30 自动触发
- 如果电脑当时休眠，会被唤醒（WakeToRun）
- 如果当时关机，下次开机时自动补发（StartWhenAvailable）
- 运行 `python wechat_daily.py`

**手动触发一次**（不等 7:30）：
```powershell
Start-ScheduledTask -TaskName 'WeChatDailySafety'
```

---

### Q5：到底装了什么？会不会污染我电脑？

| 项目 | 装在哪 | 占用 | 卸载方式 |
|------|-------|------|---------|
| Python 库 pywinauto | Python 的 site-packages | ~20MB | `pip uninstall pywinauto` |
| Python 库 Pillow | Python 的 site-packages | ~10MB | `pip uninstall pillow` |
| Python 库 psutil | Python 的 site-packages | ~3MB | `pip uninstall psutil` |
| Windows 定时任务 | 系统任务计划程序 | 0（仅一个 XML 描述） | 上面的 Q3 第 1 步 |
| 项目文件 | 你解压的文件夹 | <1MB | 直接删文件夹 |

**没有装任何：**
- ❌ 后台服务
- ❌ 开机自启
- ❌ 系统级钩子
- ❌ 注册表修改
- ❌ 网络监听

**所有运行都靠定时任务触发**，没有任务运行的时候不消耗任何资源（CPU 0%、内存 0MB）。

---

## 🚀 完整使用流程（一图流）

```
   ┌─────────────────────────────────────────┐
   │  1. 解压项目到 D:\sth\pro\WeChat-notice  │
   └────────────────┬────────────────────────┘
                    ↓
   ┌─────────────────────────────────────────┐
   │  2. 右键 install.bat → 以管理员身份运行  │
   │     （自动装依赖 + 注册定时任务 + 测试）  │
   └────────────────┬────────────────────────┘
                    ↓
   ┌─────────────────────────────────────────┐
   │  3. 用记事本打开 config.json             │
   │     把两个群名改成真实的微信群名          │
   └────────────────┬────────────────────────┘
                    ↓
   ┌─────────────────────────────────────────┐
   │  4. 在文件夹地址栏输入 cmd 回车          │
   │     输入: python wechat_daily.py --test  │
   │     检查文件传输助手是否收到消息          │
   └────────────────┬────────────────────────┘
                    ↓
   ┌─────────────────────────────────────────┐
   │  5. 完成！第二天 7:30 自动执行            │
   └─────────────────────────────────────────┘
```

---

## 🛠️ 常用命令速查

打开命令行：在项目文件夹地址栏输入 `cmd` 回车。

| 想做什么 | 命令 |
|---------|------|
| 手动发一次今天的提醒 | `python wechat_daily.py` |
| 测试发送（发到文件传输助手） | `python wechat_daily.py --test` |
| 补发昨天的 | `python wechat_daily.py --date 2026-07-24` |
| 模拟运行（不实际发送） | `python wechat_daily.py --dry-run` |
| 修改群名 | 用记事本打开 `config.json` 改 |
| 修改发送时间 | 改 `config.json` 的 `send_time` 后**重新运行 install.bat** |
| 立即触发定时任务 | `Start-ScheduledTask -TaskName 'WeChatDailySafety'`（PowerShell） |
| 查看定时任务状态 | `Get-ScheduledTask -TaskName 'WeChatDailySafety'`（PowerShell） |
| **快速测试定时任务**（X 分钟后自动触发） | `python test_schedule.py 3`（3 分钟后触发） |
| **截图调试工具**（看截图裁剪是否正确） | `python debug_screenshot.py` |
| 卸载 | 见上面 Q3 |

---

## 🧪 测试定时任务能不能正常触发

如果你想验证"7:30 真的会自动执行"而不想等到 7:30，用快速测试工具：

### 方法 1：管理员身份运行（推荐）

1. 按 `Win + X` → 选 **"Windows PowerShell (管理员)"** 或 **"终端 (管理员)"**
2. 切到项目目录：
   ```
   cd /d D:\sth\pro\WeChat-notice
   ```
3. 运行（3 分钟后触发）：
   ```
   python test_schedule.py 3
   ```

### 方法 2：普通身份运行（会自动弹 UAC 提示）

直接双击或在普通 PowerShell 里运行：
```
python test_schedule.py 3
```

脚本会检测到没管理员权限，提示你按回车弹 UAC，点"是"后自动以管理员身份重跑。

### 注意：删除已注册的任务必须管理员权限

Windows 安全限制：**只有管理员才能删除/修改已注册的定时任务**。所以 `install.bat` 和 `test_schedule.py` 都需要管理员权限。

如果你看到这种报错：
```
Unregister-ScheduledTask : 拒绝访问
```

就是权限不够，请按方法 1 操作。

### 测试流程

脚本会自动：
1. 修改 `config.json` 的 `send_time` 为 N 分钟后的时间
2. 重新注册定时任务
3. 到点后自动执行（发到班级群 + 截图 + 发到班主任群）

**测试完别忘了恢复时间**：
1. 用记事本打开 `config.json`
2. 把 `send_time` 改回原来的时间（比如 `07:30`）
3. **以管理员身份重新运行 `install.bat`**

---

## 📸 截图调试

如果截图裁剪不对（比如左侧栏被截进来、或顶部群名被切掉），运行调试工具：

```
python debug_screenshot.py
```

会在 `debug\` 文件夹下生成：
- `debug_full_*.png`：完整微信窗口截图
- `debug_cropped_*.png`：按算法裁剪后的图

把这两张图 + 控制台输出贴给开发者，能精准调整裁剪参数。

**当前裁剪策略**：
- 左右：自动检测聊天区边界（裁掉左侧功能栏 + 聊天列表）
- 上下：**不裁剪**，保留顶部群名标题栏（能看到是哪个群）

---

## ❓ 还有疑问？

### 测试发送失败了怎么办？

1. **检查微信是否登录**：PC 微信必须保持登录状态（建议勾选"自动登录"）
2. **检查群名是否对**：从 PC 微信里**右键复制群名**，粘贴到 config.json，**不要手打**
3. **看日志**：打开 `logs\run_2026-07-25.log`（日期换成今天），看具体错误信息

### 笔记本电脑合盖就休眠怎么办？

控制面板 → 电源选项 → 选择关闭盖子的功能 → 设为"不采取任何操作"

或者管理员 PowerShell 运行：
```powershell
powercfg /SETACVALUEINDEX SCHEME_CURRENT SUB_BUTTONS LIDACTION 0
powercfg /SETDCVALUEINDEX SCHEME_CURRENT SUB_BUTTONS LIDACTION 0
powercfg /SETACTIVE SCHEME_CURRENT
```

### 改了群名后要重新运行 install.bat 吗？

**不需要。** 改 `config.json` 直接保存即可，下次 7:30 自动用新群名。

只有改 `send_time`（发送时间）才需要重新运行 `install.bat`，因为时间要写入任务计划。

### 暑假结束后想暂停但保留怎么办？

最简单：用 PowerShell 删除定时任务（Q3 第 1 步），项目文件保留。明年暑假重新运行 `install.bat` 即可恢复。

### 重装电脑或换电脑怎么办？

直接在新电脑上：
1. 安装 Python 3.9+
2. 把 `WeChat-notice` 文件夹复制过去
3. 运行 `install.bat`
4. 改群名（如果新电脑微信登录的是同一个账号，群名不用改）

### 忘了项目文件夹在哪怎么办？

打开 PowerShell，运行：
```powershell
Get-ScheduledTask -TaskName 'WeChatDailySafety' | Select-Object -ExpandProperty Actions | Select-Object -ExpandProperty WorkingDirectory
```

会显示项目文件夹路径。
