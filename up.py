import time
from datetime import datetime, timedelta


#手数料の取得のためにインスタンスを作成して破棄
trader = Trader(Exchange(BitFlyer()), Exchange(BitBank()))
trader.get_commission()
trader = None
time.sleep(2.0)

# メインループ発火
while(True):
    now = datetime.now() + timedelta(hours=9)

    if now.hour == 4 and 0 <= now.minute and now.minute <= 10:
        # 04:00 - 4:10の期間は bitflyer がメンテ中
        pass
    elif now.hour == 0 and 0 <= now.minute and now.minute <= 9:
        # プログラムを終了する
        break
    else:
        # 通常
        trader = Trader(Exchange(BitFlyer()), Exchange(BitBank()))
        trader.parallel_shopping(1)
    time.sleep(2.0)

