# -*- coding: utf-8 -*-
"""
每日安全提醒文案生成器
- 内容固定为「定州市第八中学假期安全提醒」全文
- 仅"日期"与"日期对应的星期"每天变化
"""

from datetime import datetime, date

WEEKDAY_MAP = {
    0: "星期一",
    1: "星期二",
    2: "星期三",
    3: "星期四",
    4: "星期五",
    5: "星期六",
    6: "星期日",
}


def build_message(target_date: date) -> str:
    """生成指定日期的安全提醒文案。"""
    date_str = f"{target_date.year}年{target_date.month}月{target_date.day}日"
    weekday_str = WEEKDAY_MAP[target_date.weekday()]

    text = f"""严谨治校  勤奋进取

定州市第八中学假期安全提醒:
       为确保同学们度过一个安全、健康的假期，特提醒以下注意事项：

1. 交通安全
      遵守交通规则，不闯红灯、不骑电动车，过马路走斑马线。乘坐正规车辆，不坐超载车、黑车，拒乘无牌无证车辆。

2. 防溺水安全
      禁止私自到水库、河道、池塘等危险水域玩耍或游泳。

3. 居家安全
       注意用火用电安全。独自在家时锁好门窗，不轻易给陌生人开门，遇到紧急情况及时联系家长或报警。

4. 网络安全
       警惕网络诈骗，不轻易点击陌生链接或转账，遇到可疑情况及时告知家长。

5. 饮食卫生
       注意饮食均衡，不暴饮暴食，少吃生冷、油炸食品。

6. 心理健康
       多与家人沟通交流，适当参加户外运动或兴趣活动，缓解学习压力。遇到问题及时向家长、老师或心理老师求助。

温馨提示：
       外出活动前告知家长去向。
       注意天气变化，及时增减衣物，预防感冒。

      安全无小事，防范于未然！祝同学们假期愉快，平安返校！

崇德 励志 和谐 进取
善教 好学 友爱 创新
家校携手，共育共赢共未来!

                   {date_str} {weekday_str}
           —— 定州市第八中学"""
    return text


if __name__ == "__main__":
    # 自测：打印今天与明天、后天的文案结尾
    from datetime import timedelta
    for d in [date.today(), date.today() + timedelta(days=1), date.today() + timedelta(days=2)]:
        msg = build_message(d)
        print(f"=== {d.isoformat()} ===")
        print(msg[-120:])
        print()
