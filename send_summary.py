from email import message
import json
import smtplib
import sys
sys.path.append('/home/tatsuya/app/modules')
sys.path.append('/home/tatsuya/app/modules/Util')
sys.path.append('/home/tatsuya/app/modules/ExchangeContent')
from Exchange import Exchange
from BitFlyer import BitFlyer
from BitBank  import BitBank
from datetime import datetime, timedelta, timezone

bf = Exchange(BitFlyer())
bb = Exchange(BitBank())

bf.get_balance()
bf.get_commission()
bb.get_balance()

pre_val = int((bb.balance['btc'] + bf.balance['btc'])*720000 + (bb.balance['jpy'] + bf.balance['jpy']))

# 本文作成
TEXT = '''
BitFlyer手数料 : {commission}.
資産
BTC : {btc}
JPY : {jpy}
btc72とした総資産 : {val}
この辺にいい感じに明日のbiasとその根拠書く
'''.format(
    commission = str(bf.my_commission()),
    btc = str(bb.balance['btc'] + bf.balance['btc']),
    jpy = str(bb.balance['jpy'] + bf.balance['jpy']),
    val = str(pre_val)
).strip()


##　後始末
################################################################################
# 1日前に戻すために1時間ずらしている
deltazone = timezone(timedelta(hours=+8))
today = datetime.now(deltazone).strftime('%Y-%m-%d')
const = {}
with open('/home/tatsuya/app/mail.secret','r') as f:
    const = json.load( f )
msg = message.EmailMessage()
msg.set_content(TEXT) # メールの本文
msg['Subject'] = today+'のcoin_logサマリ' # 件名
msg['From'] = const['from_email'] # メール送信元
msg['To'] = const['to_email'] #メール送信先

# メールサーバーへアクセス
server = smtplib.SMTP(const['smtp_host'], const['smtp_port'])
server.ehlo()
server.starttls()
server.ehlo()
server.login(const['username'], const['password'])
server.send_message(msg)
server.quit()