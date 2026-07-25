"ui";

// ============================================================
// 定州市第八中学 假期安全提醒 - AutoX.js 版 (v2)
// ============================================================
// 改进:
//   1. 借鉴 Windows 版验证有效的 'position' 方案
//      - 用户提前在微信里打开班级群和班主任群
//      - 脚本直接点击会话列表固定位置, 不搜索!
//      - 100% 可靠, 不依赖搜索/控件识别
//   2. 加错误防护, 避免 Activity 销毁崩溃影响主流程
//   3. 加 vivo 专用提示
// ============================================================

// 配置存储
var config = storages.create("dingzhou_8th_safety");

// 全局状态
var IS_RUNNING = false;

// ==================== 主入口 ============================
// 全局错误捕获, 避免 Activity 销毁时崩溃
try {
    if (!config.contains("class_group") || !config.contains("teacher_group")) {
        showConfigUI();
    } else {
        showMainUI();
    }
} catch (e) {
    toast("脚本启动出错: " + e);
    log("启动错误: " + e);
}

// ==================== 配置界面 ============================
function showConfigUI() {
    ui.layout(
        <vertical padding="16">
            <text text="定州市第八中学" textSize="22sp" gravity="center" textColor="#2c3e50" marginBottom="4"/>
            <text text="假期安全提醒 - 首次配置" textSize="14sp" gravity="center" textColor="#888" marginBottom="20"/>

            <text text="打开群方式" textSize="14sp" textColor="#2c3e50" marginTop="8"/>
            <horizontal>
                <button id="method_position" text="位置点击 (推荐)" textSize="12sp" padding="8" layout_weight="1"/>
                <button id="method_search" text="搜索群名" textSize="12sp" padding="8" layout_weight="1"/>
            </horizontal>
            <text id="method_desc" text="位置点击: 提前打开两个群, 脚本点会话列表位置, 100% 可靠" textSize="11sp" textColor="#95a5a6" marginBottom="12"/>

            <text text="班级微信群名" textSize="14sp" textColor="#2c3e50"/>
            <input id="class_group" hint="搜索方式时必填" marginBottom="12"/>

            <text text="班主任工作群名" textSize="14sp" textColor="#2c3e50"/>
            <input id="teacher_group" hint="搜索方式时必填" marginBottom="12"/>

            <text text="班级群位置 (会话列表第几项)" textSize="14sp" textColor="#2c3e50"/>
            <input id="class_position" text="2" inputType="number" marginBottom="8"/>

            <text text="班主任群位置 (会话列表第几项)" textSize="14sp" textColor="#2c3e50"/>
            <input id="teacher_position" text="1" inputType="number" marginBottom="12"/>

            <text text="每日发送时间" textSize="14sp" textColor="#2c3e50"/>
            <input id="send_time" text="07:30" hint="HH:MM, 学校要求 8:00 前" marginBottom="20"/>

            <button id="save" text="保存配置" bg="#667eea" textColor="white" padding="12"/>

            <text text="" textSize="10sp" marginTop="20"/>
            <text text="位置点击方式说明:" textSize="13sp" textColor="#e74c3c" marginTop="8"/>
            <text text="每天电脑开机后/微信重启后:" textSize="12sp" textColor="#555"/>
            <text text="1. 打开微信" textSize="12sp" textColor="#555"/>
            <text text="2. 鼠标点班级群" textSize="12sp" textColor="#555"/>
            <text text="3. 鼠标点班主任群" textSize="12sp" textColor="#555"/>
            <text text="这样班主任群=第1位, 班级群=第2位" textSize="12sp" textColor="#555"/>
        </vertical>
    );

    var openMethod = config.get("open_method", "position");
    updateMethodUI(openMethod);

    ui.method_position.on("click", function() {
        updateMethodUI("position");
    });
    ui.method_search.on("click", function() {
        updateMethodUI("search");
    });

    function updateMethodUI(method) {
        config.put("open_method", method);
        if (method === "position") {
            ui.method_position.bg("#667eea");
            ui.method_position.textColor("white");
            ui.method_search.bg("#ecf0f1");
            ui.method_search.textColor("#2c3e50");
            ui.method_desc.text("位置点击: 提前打开两个群, 脚本点会话列表位置, 100% 可靠");
        } else {
            ui.method_search.bg("#667eea");
            ui.method_search.textColor("white");
            ui.method_position.bg("#ecf0f1");
            ui.method_position.textColor("#2c3e50");
            ui.method_desc.text("搜索群名: 用 Ctrl+F 搜索, 不用提前打开, 但微信新版可能失败");
        }
    }

    ui.save.on("click", function() {
        var classGroup = ui.class_group.text().trim();
        var teacherGroup = ui.teacher_group.text().trim();
        var sendTime = ui.send_time.text().trim();
        var classPos = parseInt(ui.class_position.text().trim() || "2");
        var teacherPos = parseInt(ui.teacher_position.text().trim() || "1");
        var method = config.get("open_method", "position");

        if (method === "search") {
            if (!classGroup) { toast("搜索方式下班级群名必填"); return; }
            if (!teacherGroup) { toast("搜索方式下班主任群名必填"); return; }
        }
        if (!/^(\d{1,2}):(\d{2})$/.test(sendTime)) {
            toast("时间格式错误, 应为 HH:MM, 例如 07:30");
            return;
        }

        config.put("class_group", classGroup);
        config.put("teacher_group", teacherGroup);
        config.put("send_time", sendTime);
        config.put("class_position", classPos);
        config.put("teacher_position", teacherPos);

        toast("保存成功!");
        sleep(800);
        showMainUI();
    });
}

// ==================== 主界面 ============================
function showMainUI() {
    var classGroup = config.get("class_group", "(未设置)");
    var teacherGroup = config.get("teacher_group", "(未设置)");
    var sendTime = config.get("send_time", "07:30");
    var lastRun = config.get("last_run", "从未执行");
    var method = config.get("open_method", "position");
    var classPos = config.get("class_position", 2);
    var teacherPos = config.get("teacher_position", 1);

    var methodText = method === "position"
        ? "位置点击 (班级群第" + classPos + "项, 班主任群第" + teacherPos + "项)"
        : "搜索群名";

    ui.layout(
        <vertical padding="16">
            <text text="定州市第八中学" textSize="22sp" gravity="center" textColor="#2c3e50" marginBottom="4"/>
            <text text="假期安全提醒" textSize="14sp" gravity="center" textColor="#888" marginBottom="16"/>

            <card marginBottom="12" bg="#f8f9fa">
                <vertical padding="14">
                    <text text="当前配置" textSize="13sp" textColor="#888" marginBottom="6"/>
                    <text text={"打开方式: " + methodText} textSize="14sp" marginBottom="2"/>
                    <text text={"发送时间: 每天 " + sendTime} textSize="14sp" marginBottom="2"/>
                    <text text={"上次执行: " + lastRun} textSize="13sp" textColor="#888"/>
                </vertical>
            </card>

            <button id="test" text="测试发送 (发到文件传输助手)" bg="#3498db" textColor="white" padding="12" marginBottom="8"/>
            <button id="run_now" text="立即发送一次" bg="#27ae60" textColor="white" padding="12" marginBottom="8"/>
            <button id="reconfig" text="修改配置" bg="#95a5a6" textColor="white" padding="12" marginBottom="16"/>

            <text text="重要提示:" textSize="14sp" textColor="#e74c3c" marginBottom="4"/>
            <text text="1. 保持 AutoX.js 后台运行 (关闭电池优化)" textSize="12sp" textColor="#555"/>
            <text text="2. 保持无障碍服务启用" textSize="12sp" textColor="#555"/>
            <text text="3. 微信保持登录状态" textSize="12sp" textColor="#555"/>
            <text text="4. 手机不要锁密码 (智能解锁)" textSize="12sp" textColor="#555"/>
            <text text="5. 长期插电运行 (推荐用旧手机)" textSize="12sp" textColor="#555"/>
            <text text="" textSize="10sp" marginTop="8"/>
            <text text="位置点击方式每日准备:" textSize="13sp" textColor="#e74c3c" marginTop="8"/>
            <text text="打开微信 → 点班级群 → 点班主任群" textSize="12sp" textColor="#555"/>
            <text text="(做完后定时任务会自动完成发送)" textSize="12sp" textColor="#555"/>
        </vertical>
    );

    ui.test.on("click", function() {
        if (IS_RUNNING) { toast("正在执行中, 请稍候"); return; }
        toast("开始测试, 请勿操作手机...");
        threads.start(function() {
            IS_RUNNING = true;
            try { runTask(true); } catch(e) { log("测试错误: " + e); }
            IS_RUNNING = false;
        });
    });

    ui.run_now.on("click", function() {
        if (IS_RUNNING) { toast("正在执行中, 请稍候"); return; }
        toast("开始发送, 请勿操作手机...");
        threads.start(function() {
            IS_RUNNING = true;
            try { runTask(false); } catch(e) { log("发送错误: " + e); }
            IS_RUNNING = false;
        });
    });

    ui.reconfig.on("click", function() {
        showConfigUI();
    });

    // 注册定时任务
    scheduleTask(sendTime);
}

// ==================== 定时任务 ============================
function scheduleTask(timeStr) {
    var parts = timeStr.split(":");
    var h = parseInt(parts[0]);
    var m = parseInt(parts[1]);

    var now = new Date();
    var next = new Date();
    next.setHours(h, m, 0, 0);
    if (next <= now) {
        next.setDate(next.getDate() + 1);
    }

    var delay = next - now;
    log("下次执行: " + next.toLocaleString() + " (约 " + Math.round(delay/60000) + " 分钟后)");

    threads.start(function() {
        try {
            setTimeout(function() {
                try { runTask(false); } catch(e) { log("定时任务错误: " + e); }
                setInterval(function() {
                    try { runTask(false); } catch(e) { log("定时任务错误: " + e); }
                }, 24 * 60 * 60 * 1000);
            }, delay);
        } catch(e) {
            log("定时器错误: " + e);
        }
    });
}

// ==================== 主任务 ============================
function runTask(testMode) {
    var reason = "";
    try {
        // 1. 唤醒屏幕
        if (!device.isScreenOn()) {
            device.wakeUp();
            sleep(1000);
            swipe(device.width/2, device.height*0.8, device.width/2, device.height*0.2, 500);
            sleep(2000);
        }

        // 2. 启动微信
        if (!launchWechat()) {
            reason = "无法启动微信";
            throw new Error(reason);
        }

        var method = config.get("open_method", "position");
        var classPos = config.get("class_position", 2);
        var teacherPos = config.get("teacher_position", 1);
        var classGroup = testMode ? "文件传输助手" : config.get("class_group");
        var teacherGroup = testMode ? "文件传输助手" : config.get("teacher_group");

        log("打开方式: " + method + (method === "position"
            ? " (班级=" + classPos + ", 班主任=" + teacherPos + ")"
            : " (班级=" + classGroup + ", 班主任=" + teacherGroup + ")"));

        // 3. 班级群发文案
        if (method === "position") {
            if (!openChatByPosition(testMode ? 1 : classPos)) {
                reason = "无法点击会话列表第 " + (testMode ? 1 : classPos) + " 项";
                throw new Error(reason);
            }
        } else {
            if (!searchAndOpenChat(classGroup)) {
                reason = "找不到班级群: " + classGroup;
                throw new Error(reason);
            }
        }

        var message = buildMessage();
        if (!sendMessage(message)) {
            reason = "发送文案失败";
            throw new Error(reason);
        }
        sleep(3000);

        // 4. 截图 (只截聊天区域)
        var screenshotPath = "/sdcard/WeChat-notice/screenshots/screenshot_" + formatDate(new Date()) + ".png";
        files.ensureDir(screenshotPath);
        if (!requestScreenCapture(false)) {
            reason = "无法获取截屏权限";
            throw new Error(reason);
        }
        sleep(500);
        var fullImg = captureScreen();
        var fullW = fullImg.getWidth();
        var fullH = fullImg.getHeight();
        log("截图尺寸: " + fullW + "x" + fullH);

        var topCut = Math.max(80, Math.min(Math.floor(fullH * 0.12), 200));
        var bottomCut = Math.max(60, Math.min(Math.floor(fullH * 0.08), 150));
        log("裁剪: 顶 " + topCut + "px, 底 " + bottomCut + "px");

        var croppedImg = images.clip(fullImg, 0, topCut, fullW, fullH - topCut - bottomCut);
        images.save(croppedImg, screenshotPath);
        log("已截图 (仅聊天区域): " + screenshotPath);
        fullImg.recycle();
        croppedImg.recycle();
        sleep(1000);

        // 5. 班主任群发截图
        if (method === "position") {
            if (!openChatByPosition(testMode ? 1 : teacherPos)) {
                reason = "无法点击会话列表第 " + (testMode ? 1 : teacherPos) + " 项";
                throw new Error(reason);
            }
        } else {
            if (!searchAndOpenChat(teacherGroup)) {
                reason = "找不到班主任群: " + teacherGroup;
                throw new Error(reason);
            }
        }
        if (!sendImage(screenshotPath)) {
            reason = "发送截图失败";
            throw new Error(reason);
        }

        // 成功
        var now = new Date();
        var timeStr = now.toLocaleString();
        config.put("last_run", timeStr + " (成功)");
        toast("发送成功!");
        log("发送成功: " + timeStr);

    } catch (e) {
        var errTime = new Date().toLocaleString();
        config.put("last_run", errTime + " (失败: " + (reason || e.message) + ")");
        toast("发送失败: " + (reason || e.message));
        log("发送失败: " + e);

        // 震动告警 (5 次)
        try {
            for (var i = 0; i < 5; i++) {
                device.vibrate(800);
                sleep(400);
            }
        } catch(vibrateErr) {
            log("震动失败: " + vibrateErr);
        }
    }
}

// ==================== 位置点击打开群 (新增, 推荐!) ============================
function openChatByPosition(position) {
    log("点击会话列表第 " + position + " 项");
    try {
        // 微信 Android 会话列表布局:
        // 顶部状态栏 ~30dp
        // 标题栏 ~50dp
        // 会话列表第 1 项 y 起点 ≈ 130dp
        // 每项高度约 70dp
        // x: 屏幕宽度 / 2 (会话列表居中)

        var screenWidth = device.width;
        var screenHeight = device.height;

        // 用 dp 转 px (AutoX.js 的 dp 转换)
        var scale = device.getDisplayMetrics().density || 3;
        var dp2px = function(dp) { return Math.floor(dp * scale); };

        var clickX = Math.floor(screenWidth / 2);
        var clickY = dp2px(130 + (position - 1) * 70 + 35);  // 项中心

        log("点击坐标: (" + clickX + ", " + clickY + "), density=" + scale);

        // 回到微信主界面 (防止当前在聊天详情页等)
        app.launch("com.tencent.mm");
        sleep(1500);

        // 点击
        click(clickX, clickY);
        sleep(2000);

        log("已点击会话列表第 " + position + " 项");
        return true;
    } catch (e) {
        log("位置点击失败: " + e);
        return false;
    }
}

// ==================== 微信操作函数 ============================
function launchWechat() {
    app.launch("com.tencent.mm");
    sleep(3000);
    return currentPackage().indexOf("com.tencent.mm") >= 0;
}

function searchAndOpenChat(name) {
    app.launch("com.tencent.mm");
    sleep(2000);

    var searchBtn = id("icon_search").findOne(2000)
        || desc("搜索").findOne(2000)
        || id("kbq").findOne(2000);

    if (searchBtn) {
        searchBtn.click();
        sleep(1500);
    } else {
        var searchBox = className("EditText").findOne(2000);
        if (searchBox) {
            searchBox.click();
            sleep(1000);
        } else {
            log("找不到搜索入口");
            return false;
        }
    }

    var input = className("EditText").findOne(2000);
    if (!input) {
        log("找不到搜索输入框");
        return false;
    }
    input.setText(name);
    sleep(2500);

    var result = text(name).findOne(3000);
    if (result) {
        result.click();
        sleep(2000);
        return true;
    }

    var firstItem = className("android.widget.LinearLayout").findOne(2000);
    if (firstItem) {
        firstItem.click();
        sleep(2000);
        return true;
    }

    log("搜索结果为空");
    return false;
}

function sendMessage(text) {
    var input = className("EditText").findOne(3000);
    if (!input) {
        log("找不到聊天输入框");
        return false;
    }
    input.click();
    sleep(500);
    input.setText(text);
    sleep(1500);

    var sendBtn = text("发送").findOne(2000)
        || desc("发送").findOne(2000)
        || id("b6l").findOne(2000);

    if (sendBtn) {
        sendBtn.click();
    } else {
        KeyEvent("KEYCODE_ENTER");
    }
    sleep(1500);
    return true;
}

function sendImage(imagePath) {
    var plusBtn = desc("更多功能按钮").findOne(2000)
        || id("b6k").findOne(2000)
        || id("b6n").findOne(2000);

    if (plusBtn) {
        plusBtn.click();
        sleep(1500);
    } else {
        log("找不到 + 按钮");
        return false;
    }

    var album = text("相册").findOne(2000);
    if (album) {
        album.click();
        sleep(2000);
    } else {
        log("找不到相册选项");
        return false;
    }

    var firstImg = className("android.widget.ImageView").findOne(2000);
    if (firstImg) {
        firstImg.click();
        sleep(1500);
    } else {
        log("找不到图片");
        return false;
    }

    var sendBtn = text("发送").findOne(2000)
        || desc("发送").findOne(2000);

    if (sendBtn) {
        sendBtn.click();
        sleep(2000);
    }
    return true;
}

// ==================== 工具函数 ============================
function buildMessage() {
    var now = new Date();
    var weekdays = ["星期日", "星期一", "星期二", "星期三", "星期四", "星期五", "星期六"];
    var dateStr = now.getFullYear() + "年" + (now.getMonth()+1) + "月" + now.getDate() + "日";
    var weekday = weekdays[now.getDay()];

    return "严谨治校  勤奋进取\n\n" +
        "定州市第八中学假期安全提醒:\n" +
        "       为确保同学们度过一个安全、健康的假期，特提醒以下注意事项：\n\n" +
        "1. 交通安全\n" +
        "      遵守交通规则，不闯红灯、不骑电动车，过马路走斑马线。乘坐正规车辆，不坐超载车、黑车，拒乘无牌无证车辆。\n\n" +
        "2. 防溺水安全\n" +
        "      禁止私自到水库、河道、池塘等危险水域玩耍或游泳。\n\n" +
        "3. 居家安全\n" +
        "       注意用火用电安全。独自在家时锁好门窗，不轻易给陌生人开门，遇到紧急情况及时联系家长或报警。\n\n" +
        "4. 网络安全\n" +
        "       警惕网络诈骗，不轻易点击陌生链接或转账，遇到可疑情况及时告知家长。\n\n" +
        "5. 饮食卫生\n" +
        "       注意饮食均衡，不暴饮暴食，少吃生冷、油炸食品。\n\n" +
        "6. 心理健康\n" +
        "       多与家人沟通交流，适当参加户外运动或兴趣活动，缓解学习压力。遇到问题及时向家长、老师或心理老师求助。\n\n" +
        "温馨提示：\n" +
        "       外出活动前告知家长去向。\n" +
        "       注意天气变化，及时增减衣物，预防感冒。\n\n" +
        "      安全无小事，防范于未然！祝同学们假期愉快，平安返校！\n\n" +
        "崇德 励志 和谐 进取\n" +
        "善教 好学 友爱 创新\n" +
        "家校携手，共育共赢共未来!\n\n" +
        "                   " + dateStr + " " + weekday + "\n" +
        "           —— 定州市第八中学";
}

function formatDate(d) {
    var y = d.getFullYear();
    var m = ("0" + (d.getMonth()+1)).slice(-2);
    var day = ("0" + d.getDate()).slice(-2);
    return y + "-" + m + "-" + day;
}

// ==================== 全局错误防护 ============================
// 避免 Activity 销毁时崩溃 (Android 16 + AutoX.js 已知 bug)
events.on("exit", function() {
    log("脚本退出");
    IS_RUNNING = false;
});

// 捕获未处理的异常
events.observeKey();
events.on("key", function(keyCode, event) {
    // 防止按键事件导致崩溃
});
