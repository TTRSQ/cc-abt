from email import message
import json
import smtplib

const = {}
with open('/home/tatsuya/app/mail.secret','r') as f:
    const = json.load( f )

# メールの内容を作成
msg = message.EmailMessage()
msg.set_content('test mail') # メールの本文
msg['Subject'] = 'test mail(sub)' # 件名
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