import time
import sys
sys.path.append('/home/tatsuya/app/modules')
sys.path.append('/home/tatsuya/app/modules/Util')
sys.path.append('/home/tatsuya/app/modules/ExchangeContent')
from datetime import datetime, timedelta
from Arbitrager import Arbitrager
from Exchange import Exchange
from BitFlyer import BitFlyer
from BitBank  import BitBank


#手数料の取得のためにインスタンスを作成して破棄
arbitrager = Arbitrager(Exchange(BitFlyer()), Exchange(BitBank()))
arbitrager.get_commission()
arbitrager = None
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
        arbitrager = Arbitrager(Exchange(BitFlyer()), Exchange(BitBank()))
        arbitrager.parallel_shopping(1)
    time.sleep(2.0)

