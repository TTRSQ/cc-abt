# coding: utf-8
import time
import os
import mysql.connector
import urllib.request
import json
from datetime import datetime

# 取引所に命令を送るためのクラス(状態保有あり)
class Exchange:
    def __init__(self, exchange):
        self.exchange = exchange
        self.board = {}
        self.balance = {}

    def get_board(self):
        command = 'board'
        self.board = self.exchange.format(command, self.exchange.hit_api(command))

    def get_balance(self):
        command = 'balance'
        self.balance = self.exchange.format(command, self.exchange.hit_api(command))

    def order(self, param):
        command = 'order'
        self.exchange.hit_api(command, param)


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
        for command in self.api_list.keys():
            self.formatter[command] = self.formatter_default

    def make_request(self):
        pass

    def hit_api(self, command, param={}):
        request = self.make_request(command, param)
        response_dic = {}
        with urllib.request.urlopen(request) as response:
            response_dic = json.loads( response.read().decode("utf-8") )
        return response_dic

    @staticmethod
    def formatter_default(values):
        return values

    def format(self, command, values):
        pass


class Bitflyer(ExchangeCharacterBase):
    def __init__(self):
        self.name = 'Bitflyer'
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
                }
            }
        }
        super().__init__(default)


    def make_request(self, command, param):
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
                raw_sign += str(json.dumps(param).encode("utf-8"))
            header['ACCESS-SIGN'] = hmac.new(bytes(self.api_key_s, 'ascii'), bytes(raw_sign, 'ascii'), hashlib.sha256).hexdigest()

        return urllib.request.Request(url, method=method, headers=header)

    def format(self, command, values):
        return self.formatter[command](values)




# class ApiFormatter:
#     EXCHANGE_INFO = {
#         'bitflyer' : {
#             'exchange_id'      : 1,
#             'api_public_base'  : 'https://api.bitflyer.com/v1',
#             'api_private_base' : 'https://api.bitflyer.com/v1'
#         },
#         'bitbank' : {
#             'exchange_id'      : 2,
#             'api_public_base'  : 'https://public.bitbank.cc',
#             'api_private_base' : 'https://api.bitbank.cc/v1'
#         },
#         'coincheck' : {
#             'exchange_id'      : 3,
#             'api_public_base'  : 'https://coincheck.com',
#             'api_private_base' : 'https://coincheck.com'
#         }
#     }
#
#     API_END_PINT = {
#         'board' : {
#             'bitflyer'  : '/getboard',
#             'bitbank'   : '/btc_jpy/depth',
#             'coincheck' : '/api/order_books'
#         },
#         'ticker' : {
#             'bitflyer'  : '/ticker',
#             'bitbank'   : '/btc_jpy/ticker',
#             'coincheck' : '/api/ticker'
#         }
#     }
#
#     COMMISSIONS = {
#         # JPY
#         'deposit_jpy' : {
#             'bitflyer'  : 324,
#             'bitbank'   : 0,
#             'coincheck' : 0
#         },
#
#         # %
#         'trade_commission' : {
#             'bitflyer'  : 0.0015,
#             'bitbank'   : 0,
#             'coincheck' : 0.002
#         },
#
#         # BTC
#         'transfer_commission' : {
#             'bitflyer'  : 0.0004,
#             'bitbank'   : 0.0004,
#             'coincheck' : 0.001
#         }
#     }
#
#
#     @staticmethod
#     def get_config():
#         for name in ApiFormatter.EXCHANGE_INFO.keys():
#             print(name)
#             for element in ApiFormatter.EXCHANGE_INFO[name]:
#                 print('\t', element, ': ', ApiFormatter.EXCHANGE_INFO[name][element])
#
#     @staticmethod
#     def get_board(name):
#         # 差分を吸収して asks: {price : val, size : val}, bids: {price : val, size : val}のリストを返す
#         response_body = {}
#         with urllib.request.urlopen(ApiFormatter.EXCHANGE_INFO[name]['api_public_base'] + ApiFormatter.API_END_PINT['board'][name]) as res:
#             response_body = json.loads( res.read().decode('utf-8') )
#
#         if name == 'bitflyer':
#             return response_body
#
#         elif name == 'bitbank':
#             dic = {}
#             dic['asks'] = []
#             dic['bids'] = []
#             for bid in response_body['data']['bids']:
#                 element = {'price': float(bid[0]), 'size': float(bid[1])}
#                 dic['bids'].append(element)
#             for ask in response_body['data']['asks']:
#                 element = {'price': float(ask[0]), 'size': float(ask[1])}
#                 dic['asks'].append(element)
#             return dic
#         elif name == 'coincheck':
#             dic = {}
#             dic['asks'] = []
#             dic['bids'] = []
#             for bid in response_body['bids']:
#                 element = {'price': float(bid[0]), 'size': float(bid[1])}
#                 dic['bids'].append(element)
#             for ask in response_body['asks']:
#                 element = {'price': float(ask[0]), 'size': float(ask[1])}
#                 dic['asks'].append(element)
#             return dic
#
#         else:
#             return response_body
#
# # 取引所単体に関する操作
# class Exchange:
#     def __init__(self, exchange_name):
#
#         self.exchange_name = exchange_name
#         self.board = ApiFormatter.get_board(exchange_name)
#
#     def update_board(self):
#         self.board = ApiFormatter.get_board(self.exchange_name)
#
#     # private
#     def __get_value_from_size(self, size, side):
#         anchor = 0.0
#         sum = 0.0
#         for element in self.board[side]:
#             if size - anchor >= element['size']:
#                 anchor += element['size']
#                 sum += element['size']*element['price']
#             else:
#                 sum += (size - anchor)*element['price']
#                 break
#         return sum/size
#
#     def get_mean_bid_from_size(self, size):
#         return self.__get_value_from_size(size, 'bids')
#
#     def get_mean_ask_from_size(self, size):
#         return self.__get_value_from_size(size, 'asks')
#
# # 複数の取引所の間の相互的なハンドリング
# class Trader:
#     def __init__(self, exchange_name1, exchange_name2):
#         self.exchange1 = Exchange(exchange_name1)
#         self.exchange2 = Exchange(exchange_name2)
#
#     def update_board(self):
#         self.exchange1.update_board()
#         self.exchange2.update_board()
#
#     # スプレッドがnagativeになる最大取引サイズを求める(positive状態なら0返る)
#     def __get_nagative_size(self, exchange1, exchange2):
#         print('hello')
#
#     # return [float(1買 2売), float(2買 1売)]
#     def get_active_size(self):
#         print('hello')
#
#
#
# class SqlController:
#
#     def __init__(self):
#         self.connection = mysql.connector.connect(
#             host = 'localhost',
#             port = '3306',
#             user = os.environ['CL_SQL_USER'],
#             password = os.environ['CL_SQL_PASS'],
#             database = os.environ['CL_USE_DB']
#         )
#
#     def __del__(self):
#         self.connection.close()
#
#     def begin_cursor(self):
#         self.cursor = self.connection.cursor(buffered=True)
#
#     def execute(self, query):
#         self.cursor.execute(query)
#
#     def commit(self):
#         self.connection.commit()
#
#     def quit_cursor(self):
#         self.cursor.close()
#
# def insert(db, table, dic):
#     db.begin_cursor()
#     query  = 'insert into %s ' %(table)
#     keys = list(dic.keys())
#     values = map(str, list(dic.values()))
#     query += '(' + ', '.join(keys) + ') values '
#     query += '(' + ', '.join(values) + ')'
#     db.execute(query)
#     db.commit()
#     db.quit_cursor()



bitflyer = Exchange(Bitflyer())


for i in range(10):
    start = time.time()
    bitflyer.get_board()
    end = time.time()
    print(end - start)
    time.sleep(1)

exit()
