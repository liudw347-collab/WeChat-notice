# 每日安全提醒自动化

> 定州市第八中学 暑假每日安全提醒自动发送项目。
>
> 每天早上 7:30 自动通过微信向班级群发送安全提醒，并截图转发到班主任工作群。

## 快速开始

- **Windows 用户**：见 [README.md](README.md) 的 "Windows 版" 章节
- **Android 用户**：见 [android/README.md](android/README.md)

## 文案说明

每天发送的内容固定为定州市第八中学假期安全提醒全文，仅末尾的"日期 + 星期"每天变化。
文案由 `message_builder.py` 自动生成，无需手动维护。

## 项目结构

```
WeChat-notice/
├── message_builder.py          # 文案生成器
├── wechat_daily.py             # Windows 主脚本
├── config.json                 # Windows 配置
├── install.bat / install_task.ps1
├── android/                    # Android 版本
│   ├── wechat_daily_android.py
│   ├── config.json
│   └── install.sh
└── README.md
```

## 卸载

- Windows: `Unregister-ScheduledTask -TaskName 'WeChatDailySafety' -Confirm:$false`
- Android: `crontab -l | grep -v wechat_daily_android.py | crontab -`
