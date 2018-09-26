# coding: utf-8
import time
import os
import mysql.connector
import urllib.request
import json
from datetime import datetime
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

    def get_board(self):
        command = 'board'
        self.board = self.exchange.format(command, self.exchange.hit_api(command))

    def get_balance(self):
        command = 'balance'
        self.balance = self.exchange.format(command, self.exchange.hit_api(command))

    def order(self, param):
        command = 'order'
        self.last_order = self.exchange.format(command, self.exchange.hit_api(command, param))

    def order_list(self):
        command = 'order_list'
        print(self.exchange.hit_api(command))

    def get_permission(self):
        command = 'permissions'
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
        return response_dic

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
                'permissions' : {
                    'path'   : '/v1/me/getpermissions',
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
            'created_at' : int(datetime.now().timestamp()*1000)
        }
        return ret_value

    def prepare(self, command, params):
        return self.prepare_dic[command](params)

    def prepare_order(self, params):
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
            unix_stamp = str(int(datetime.now().timestamp()))
            header['ACCESS-NONCE'] = unix_stamp
            raw_sign = unix_stamp
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
        ret_value = {
            'side'       : values['data']['side'],
            'size'       : values['data']['start_amount'],
            'created_at' : values['data']['ordered_at'],
            'success'    : values['success'],
        }
        return ret_value


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

class myThread(threading.Thread):
    def __init__(self, exchange):
        super(myThread, self).__init__()
        self.exchange = exchange

    def run(self):
        start = time.time()
        self.exchange.get_board()
        end = time.time()
        print(end - start)

bitflyer = Exchange(BitFlyer())
bitbank = Exchange(BitBank())

start = time.time()

bitflyer.order({
    'side'  : 'buy',
    'size'  : 0.005,
})
bitbank.order({
    'side'  : 'buy',
    'size'  : 0.005,
})

print(bitbank.last_order, bitflyer.last_order)



end = time.time()
print(end - start)

exit()
