# coding: utf-8
import time
import os
import mysql.connector
import urllib.request
import json
from datetime import datetime, timedelta
import threading
import hmac
import hashlib

# 取引所に命令を送るためのクラス(状態保有あり)
class Exchange:
    def __init__(self, exchange):
        self.exchange = exchange
        self.board = {}
        self.balance = {}
        self.last_order = {}

    def get_commission(self):
        self.exchange.get_commission()

    def my_commission(self):
        return self.exchange.my_commission()

    def get_board(self):
        command = 'board'
        self.board = self.exchange.format(command, self.exchange.hit_api(command))

    def get_balance(self):
        command = 'balance'
        self.balance = self.exchange.format(command, self.exchange.hit_api(command))

    def round_order_size(self, size):
        return self.exchange.round_order_size(size)

    def order(self, param):
        command = 'order'

        # 丸め込みをする(小数点以下8桁)
        round = 100000000
        param['size'] = ( 1.0*int(param['size']*round) )/round

        self.last_order = self.exchange.format(command, self.exchange.hit_api(command, param))

    def order_list(self):
        command = 'order_list'
        print(self.exchange.hit_api(command))


api_config = {
    'method' : {
        'get'  : 1,
        'post' : 2
    },
    'type' : {
        'public'  : 1,
        'private' : 2
    }
}

# 固有取引所カセットが継承するクラス
class ExchangeCharacterBase:
    commission = 0

    def __init__(self, default):
        self.url_public  = default['url_public']
        self.url_private = default['url_private']
        self.api_list    = default['api_list']
        self.formatter   = {}
        self.prepare_dic = {}
        for command in self.api_list.keys():
            self.formatter[command] = self.formatter_default
            self.prepare_dic[command] = self.prepare_default

    def make_request(self):
        pass

    def hit_api(self, command, param={}):
        request = self.make_request(command, param)
        response_dic = {}
        with urllib.request.urlopen(request) as response:
            response_dic = json.loads( response.read().decode("utf-8") )
        if command == "order":
            f = open("/home/tatsuya/tmp/log", "a")
            f.write(json.dumps(response_dic)+"\n")
            f.close()
        return response_dic

    # 取引所ごとに扱える最小桁数が違う
    def round_order_size(self, size):
        return size

    # 手数料の取得(あればオーバーライド)
    def get_commission(self):
        ExchangeCharacterBase.commission = 0

    # 関数の返値を成形
    @staticmethod
    def formatter_default(values):
        return values

    # 関数の引数を整形
    @staticmethod
    def prepare_default(params):
        return params

    def format(self, command, values):
        pass

    def prepare(self, command, params):
        pass


class BitFlyer(ExchangeCharacterBase):
    def __init__(self):
        self.name = 'BitFlyer'
        self.api_key = os.environ['BF_KEY']
        self.api_key_s = os.environ['BF_KEY_S']
        default = {
            'url_public'  : 'https://api.bitflyer.com',
            'url_private' : 'https://api.bitflyer.com',
            'api_list' : {
                'board' : {
                    'path'   : '/v1/getboard',
                    'method' : api_config['method']['get'],
                    'type'   : api_config['type']['public']
                },
                'balance' : {
                    'path'   : '/v1/me/getbalance',
                    'method' : api_config['method']['get'],
                    'type'   : api_config['type']['private']
                },
                'order' : {
                    'path'   : '/v1/me/sendchildorder',
                    'method' : api_config['method']['post'],
                    'type'   : api_config['type']['private']
                },
                'commission' : {
                    'path'   : '/v1/me/gettradingcommission?product_code=BTC_JPY',
                    'method' : api_config['method']['get'],
                    'type'   : api_config['type']['private']
                }
            }
        }
        super().__init__(default)
        self.formatter["balance"] = self.format_balance
        self.formatter["order"] = self.format_order
        self.prepare_dic["order"] = self.prepare_order

    def make_request(self, command, param):
        param = self.prepare(command, param)
        header = {
            'Content-Type': 'application/json'
        }
        url = self.url_public + self.api_list[command]['path']
        method = 'GET' if self.api_list[command]['method'] == api_config['method']['get'] else 'POST'
        if self.api_list[command]['type'] == api_config['type']['private']:
            header['ACCESS-KEY'] = self.api_key
            unix_stamp = str(int(datetime.now().timestamp()))
            header['ACCESS-TIMESTAMP'] = unix_stamp
            raw_sign = unix_stamp + method + self.api_list[command]['path']
            # param が空出ない場合 raw_signにparamの文字列が追加される
            if len(param) != 0:
                raw_sign += str(json.dumps(param))
            header['ACCESS-SIGN'] = hmac.new(bytes(self.api_key_s, 'ascii'), bytes(raw_sign, 'ascii'), hashlib.sha256).hexdigest()
        if len(param) != 0:
            return urllib.request.Request(url, method=method, headers=header, data=json.dumps(param).encode('utf-8'))
        else:
            return urllib.request.Request(url, method=method, headers=header)

    def get_commission(self):
        res = self.hit_api('commission')
        BitFlyer.commission = res['commission_rate']

    def my_commission(self):
        return BitFlyer.commission

    def format(self, command, values):
        return self.formatter[command](values)

    def format_balance(self, values):
        ret_value = {}
        for element in values:
            if element['currency_code'] == 'JPY' or element['currency_code'] == 'BTC':
                code = 'jpy' if element['currency_code'] == 'JPY' else 'btc'
                ret_value[code] = element['available']
        return ret_value

    def format_order(self, values):
        ret_value = {
            'success'    : 1 if 'child_order_acceptance_id' else 0,
            'retry'      : 0,
            'created_at' : int(datetime.now().timestamp()*1000)
        }
        return ret_value

    def prepare(self, command, params):
        return self.prepare_dic[command](params)

    def prepare_order(self, params):
        # 手数料があるので購入は多く、売却は少なく
        if params['side'] == 'buy':
            params['size'] /= (1-BitFlyer.commission)
        else:
            params['size'] /= (1+BitFlyer.commission)

        round = 100000000
        params['size'] = ( 1.0*int(params['size']*round) )/round

        if 'price' in params:
            return {
                "product_code": "BTC_JPY",
                "child_order_type": "LIMIT",
                "side": ("BUY" if params['side'] == 'buy' else "SELL"),
                "size": params['size'],
                "price": params['price'],
                "minute_to_expire": 1,
                "time_in_force": "GTC"
            }
        else:
            return {
                "product_code": "BTC_JPY",
                "child_order_type": "MARKET",
                "side": ("BUY" if params['side'] == 'buy' else "SELL"),
                "size": params['size'],
                "minute_to_expire": 1,
                "time_in_force": "GTC"
            }


class BitBank(ExchangeCharacterBase):
    def __init__(self):
        self.name = 'BitBank'
        self.api_key = os.environ['BB_KEY']
        self.api_key_s = os.environ['BB_KEY_S']
        default = {
            'url_public'  : 'https://public.bitbank.cc',
            'url_private' : 'https://api.bitbank.cc',
            'api_list' : {
                'board' : {
                    'path'   : '/btc_jpy/depth',
                    'method' : api_config['method']['get'],
                    'type'   : api_config['type']['public']
                },
                'balance' : {
                    'path'   : '/v1/user/assets',
                    'method' : api_config['method']['get'],
                    'type'   : api_config['type']['private']
                },
                'order' : {
                    'path'   : '/v1/user/spot/order',
                    'method' : api_config['method']['post'],
                    'type'   : api_config['type']['private']
                },
                'order_list' : {
                    'path'   : '/v1/user/spot/orders_info',
                    'method' : api_config['method']['post'],
                    'type'   : api_config['type']['private']
                }
            }
        }
        super().__init__(default)
        self.formatter['board'] = self.format_board
        self.formatter['balance'] = self.format_balance
        self.formatter['order'] = self.format_order
        self.prepare_dic["order"] = self.prepare_order
        self.nonce = 0
        self.last_req_stamp = 0

    def make_request(self, command, param):
        param = self.prepare(command, param)
        is_get = self.api_list[command]['method'] == api_config['method']['get']
        is_public = self.api_list[command]['type'] == api_config['type']['public']
        header = {
            'Content-Type': 'application/json'
        }
        url = (self.url_public if is_public else self.url_private) + self.api_list[command]['path']
        method = 'GET' if is_get else 'POST'

        if not is_public:
            header['ACCESS-KEY'] = self.api_key
            unix_int = int(datetime.now().timestamp())
            # nonce が一桁である前提
            if self.last_req_stamp == unix_int:
                self.nonce += 1
            else:
                self.nonce = 0
            self.last_req_stamp = unix_int
            access_nonce = str(self.last_req_stamp)+str(self.nonce)
            header['ACCESS-NONCE'] = access_nonce
            raw_sign = access_nonce
            if is_get:
                raw_sign += self.api_list[command]['path']
            else:
                # param が空出ない場合 raw_signにparamの文字列が追加される
                if len(param) != 0:
                    raw_sign += str(json.dumps(param))

            header['ACCESS-SIGNATURE'] = hmac.new(bytes(self.api_key_s, 'ascii'), bytes(raw_sign, 'ascii'), hashlib.sha256).hexdigest()
        if len(param) != 0:
            return urllib.request.Request(url, method=method, headers=header, data=json.dumps(param).encode('utf-8'))
        else:
            return urllib.request.Request(url, method=method, headers=header)

    def my_commission(self):
        return BitBank.commission

    def format(self, command, values):
        return self.formatter[command](values)

    def format_board(self, values):
        ret_value = {'bids': [], 'asks': []}
        for element in values["data"]["bids"]:
            ret_value['bids'].append({'price': float(element[0]), 'size': float(element[1])})
        for element in values["data"]["asks"]:
            ret_value['asks'].append({'price': float(element[0]), 'size': float(element[1])})
        return ret_value

    def format_balance(self, values):
        ret_value = {}
        for element in values['data']['assets']:
            if element['asset'] == 'jpy' or element['asset'] == 'btc':
                ret_value[element['asset']] = float(element['free_amount'])
        return ret_value

    def format_order(self, values):
        if values['success']:
            ret_value = {
                'side'       : values['data']['side'],
                'size'       : values['data']['start_amount'],
                'created_at' : values['data']['ordered_at'],
                'success'    : values['success'],
            }
            return ret_value
        else:
            if values['data']['code'] == 70009:
                return {"success": 0 , "retry": 1}
            else:
                return {"success": 0 , "retry": 0}

    # bitbankは小数点以下4桁まで 以降切り捨て
    def round_order_size(self, size):
        # 丸め込みをする(小数点以下8桁)
        round = 10000
        return ( 1.0*int(size*round) )/round


    def prepare(self, command, params):
        return self.prepare_dic[command](params)

    def prepare_order(self, params):
        if 'price' in params:
            return {
                "pair"   : "btc_jpy",
                "amount" : params["size"],
                "side"   : params["side"],
                "price"  : params["price"],
                "type"   : "limit"
            }
        else:
            return {
                "pair"   : "btc_jpy",
                "amount" : params["size"],
                "side"   : params['side'],
                "type"   : "market"
            }


class SqlController:

    def __init__(self):
        self.connection = mysql.connector.connect(
            host = 'localhost',
            port = '3306',
            user = os.environ['CL_SQL_USER'],
            password = os.environ['CL_SQL_PASS'],
            database = os.environ['CL_USE_DB']
        )

    def __del__(self):
        self.connection.close()

    def begin_cursor(self):
        self.cursor = self.connection.cursor(buffered=True)

    def execute(self, query):
        self.cursor.execute(query)

    def commit(self):
        self.connection.commit()

    def quit_cursor(self):
        self.cursor.close()

def insert(db, table, dic):
    db.begin_cursor()
    query  = 'insert into %s ' %(table)
    keys = list(dic.keys())
    values = map(str, list(dic.values()))
    query += '(' + ', '.join(keys) + ') values '
    query += '(' + ', '.join(values) + ')'
    db.execute(query)
    db.commit()
    db.quit_cursor()

class Trader:

    def __init__(self, exchange0, exchange1):
        self.ex0 = exchange0
        self.ex1 = exchange1
        self.ex0.get_balance()
        self.ex1.get_balance()
        self.th0 = threading.Thread()
        self.th1 = threading.Thread()
        self.th00 = threading.Thread()
        self.th11 = threading.Thread()
        self.threshold = {'size': 0.001, 'price' : 1000, 'bias': 500}
        self.cart = 0
        self.f = open("/home/tatsuya/tmp/log", "a")

    def __del__(self):
        self.f.close()

    def disp_balance(self):
        print(self.ex0.exchange.name, self.ex0.balance)
        print(self.ex1.exchange.name, self.ex1.balance)

    def disp_commission(self):
        print(self.ex0.exchange.name, self.ex0.my_commission())
        print(self.ex1.exchange.name, self.ex1.my_commission())

    def update_balance(self, exchange):
        exchange.get_balance()

    def update_board(self, exchange):
        exchange.get_board()

    def update_board_parallel(self):
        self.board_is_new = 0

    def order(self, exchange, side, size, exec):
        now = (datetime.now() + timedelta(hours=9)).strftime("%Y/%m/%d %H:%M:%S")
        if size < self.threshold['size']:
            return
        if exec:
            exchange.order({
                'size' : size,
                'side' : side
            })

            self.f.write(now + ' ' + exchange.exchange.name + ' ' + side + ' ' + str(size) + '\n')
            price = self.get_mean_value_from_size(size ,exchange)
            bid_ask = 'bid' if side == 'sell' else 'ask'
            self.f.write(exchange.exchange.name + ' expect price:'+ str(price[bid_ask]) + '\n')

            # 指値でリトライ
            if exchange.last_order['success'] == 0 and exchange.last_order['retry']:
                exchange.order({
                    'size'  : size,
                    'price' : (price[bid_ask]*1.1 if side == 'buy' else price[bid_ask]*0.9),
                    'side'  : side
                })

        else:
            self.f.write(now + exchange.exchange.name + side + str(size) + '\n')

    def get_mean_value_from_size(self, size, exchange):
        calc_size = 0.0
        sum_bid = 0.0
        sum_ask = 0.0
        for element in exchange.board['bids']:
            if calc_size + element['size'] > size:
                sum_bid += element['price']*(size - calc_size)
                break
            else:
                sum_bid += element['price']*element['size']
                calc_size += element['size']
        calc_size = 0.0
        for element in exchange.board['asks']:
            if calc_size + element['size'] > size:
                sum_ask += element['price']*(size - calc_size)
                break
            else:
                sum_ask += element['price']*element['size']
                calc_size += element['size']
        return {'size':size, 'bid':sum_bid/size, 'ask':sum_ask/size}

    # サイズ = threshold におけるspreadを求める
    def get_negative_spread(self, size):
        et0 = self.get_mean_value_from_size(size, self.ex0)
        et1 = self.get_mean_value_from_size(size, self.ex1)
        # dir : spread
        return {1: et1['bid']-et0['ask'], 2: et0['bid']-et1['ask']}

    # 板情報を入手した直後に実行しないと意味ない
    def max_trade_amount(self, size, rate=1.0):
        et0 = self.get_mean_value_from_size(size, self.ex0)
        et1 = self.get_mean_value_from_size(size, self.ex1)
        t1 = min(self.ex0.balance['jpy']/et0['ask'], self.ex1.balance['btc'])
        t2 = min(self.ex1.balance['jpy']/et1['ask'], self.ex0.balance['btc'])
        return {1: t1*rate, 2: t2*rate}

    # 上の関数と似ているがこちらはどこまでのサイズなら有効なスプレッドであるかをさす。
    def max_effective_size(self, spread, bias, rate=1.0):
        return {1: self.get_mes(1, spread + bias)*rate, 2: self.get_mes(2, spread - bias)*rate}

    def get_mes(self, dir, spread):
        bids = []
        asks = []
        if dir == 1:
            asks = self.ex0.board['asks']
            bids = self.ex1.board['bids']
        else:
            asks = self.ex1.board['asks']
            bids = self.ex0.board['bids']

        size = 0.0
        bid_id = 0
        ask_id = 0
        bid_p = bids[0]['price']
        ask_p = asks[0]['price']
        bid_s = bids[0]['size']
        ask_s = asks[0]['size']
        while bid_p - ask_p > spread:
            if bid_s < ask_s:
                size += bid_s
                bid_id += 1
                if bid_id == len(bids):
                    break
                bid_s = bids[bid_id]['size']
                bid_p = bids[bid_id]['price']
            else:
                size += ask_s
                ask_id += 1
                if ask_id == len(asks):
                    break
                ask_s = asks[ask_id]['size']
                ask_p = asks[ask_id]['price']

        return size

    def get_commission(self):
        self.ex0.get_commission()
        self.ex1.get_commission()

    # dir = 1(ex0 -> ex1),2はその逆
    def trade(self, dir, size, exec):
        # より強く丸めた方を採用
        round_size0 = self.ex0.round_order_size(size)
        round_size1 = self.ex1.round_order_size(size)
        size = min(round_size0, round_size1)
        if dir == 1:
            self.th00 = threading.Thread(name="ex0", target=self.order, args=(self.ex0, 'buy' , size, exec, ))
            self.th11 = threading.Thread(name="ex1", target=self.order, args=(self.ex1, 'sell', size, exec, ))
        else:
            self.th00 = threading.Thread(name="ex0", target=self.order, args=(self.ex0, 'sell', size, exec, ))
            self.th11 = threading.Thread(name="ex1", target=self.order, args=(self.ex1, 'buy' , size, exec, ))
        self.th00.start()
        self.th11.start()

    def shopping(self, exchange, exec):
        self.update_board(exchange)
        self.cart += 1
        if self.cart == 2:
            self.cart = 0
            now = (datetime.now() + timedelta(hours=9)).strftime("%Y/%m/%d %H:%M:%S")
            mes = self.max_effective_size(self.threshold['price'], self.threshold['bias'], 1.0)
            if mes[1] > mes[2]:
                if mes[1] > self.threshold['size']:
                    mta = self.max_trade_amount(mes[1], 1.0)
                    self.f.write('\n'+now+' dir1 '+str(self.ex1.board['bids'][0]['price']-self.ex0.board['asks'][0]['price'])+'\n')
                    self.f.write('size: {mta:'+str(mta[1]*0.5)+', mes:'+str(mes[1]*0.8)+'}\n\n')
                    self.trade(1, min(mta[1]*0.5, mes[1]*0.8), exec)
            else:
                if mes[2] > self.threshold['size']:
                    mta = self.max_trade_amount(mes[2], 1.0)
                    self.f.write('\n'+now+' dir2 '+str(self.ex0.board['bids'][0]['price']-self.ex1.board['asks'][0]['price'])+'\n')
                    self.f.write('size: {mta:'+str(mta[2]*0.5)+', mes:'+str(mes[2]*0.8)+'}\n\n')
                    self.trade(2, min(mta[2]*0.5, mes[2]*0.8), exec)


    def parallel_shopping(self, exec):
        self.th0 = threading.Thread(name="ex0", target=self.shopping, args=(self.ex0, exec, ))
        self.th1 = threading.Thread(name="ex1", target=self.shopping, args=(self.ex1, exec, ))
        self.th0.start()
        self.th1.start()

# 手数料の取得のためにインスタンスを作成して破棄
trader = Trader(Exchange(BitFlyer()), Exchange(BitBank()))
trader.get_commission()
trader = None

time.sleep(2.0)

for i in range(1800*24*2):
    now = datetime.now() + timedelta(hours=9)

    if now.hour == 4 and 0 <= now.minute and now.minute <= 10:
        # 04:00 - 4:10の期間は bitflyer がメンテ中
        pass
    elif now.hour == 0 and 0 <= now.minute and now.minute <= 10:
        # この時間は手数料の更新が行われるので手数料を取得してから取引
        trader = Trader(Exchange(BitFlyer()), Exchange(BitBank()))
        trader.get_commission()
        time.sleep(2.0)
        trader.parallel_shopping(1)
    else:
        # 通常
        trader = Trader(Exchange(BitFlyer()), Exchange(BitBank()))
        trader.parallel_shopping(1)
    time.sleep(2.0)

exit()
