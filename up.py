# coding: utf-8
import time
import os
import mysql.connector
import urllib.request
import json
from datetime import datetime

class ApiFormatter:
    EXCHANGE_INFO = {
        'bitflyer' : {
            'exchange_id'      : 1,
            'api_public_base'  : 'https://api.bitflyer.com/v1',
            'api_private_base' : 'https://api.bitflyer.com/v1'
        },
        'bitbank' : {
            'exchange_id'      : 2,
            'api_public_base'  : 'https://public.bitbank.cc',
            'api_private_base' : 'https://api.bitbank.cc/v1'
        },
        'coincheck' : {
            'exchange_id'      : 3,
            'api_public_base'  : 'https://coincheck.com',
            'api_private_base' : 'https://coincheck.com'
        }
    }

    API_END_PINT = {
        'board' : {
            'bitflyer'  : '/getboard',
            'bitbank'   : '/btc_jpy/depth',
            'coincheck' : '/api/order_books'
        },
        'ticker' : {
            'bitflyer'  : '/ticker',
            'bitbank'   : '/btc_jpy/ticker',
            'coincheck' : '/api/ticker'
        }
    }

    COMMISSIONS = {
        # JPY
        'deposit_jpy' : {
            'bitflyer'  : 324,
            'bitbank'   : 0,
            'coincheck' : 0
        },

        # %
        'trade_commission' : {
            'bitflyer'  : 0.0015,
            'bitbank'   : 0,
            'coincheck' : 0.002
        },

        # BTC
        'transfer_commission' : {
            'bitflyer'  : 0.0004,
            'bitbank'   : 0.0004,
            'coincheck' : 0.001
        }
    }


    @staticmethod
    def get_config():
        for name in ApiFormatter.EXCHANGE_INFO.keys():
            print(name)
            for element in ApiFormatter.EXCHANGE_INFO[name]:
                print('\t', element, ': ', ApiFormatter.EXCHANGE_INFO[name][element])

    @staticmethod
    def get_board(name):
        # 差分を吸収して asks: {price : val, size : val}, bids: {price : val, size : val}のリストを返す
        response_body = {}
        with urllib.request.urlopen(ApiFormatter.EXCHANGE_INFO[name]['api_public_base'] + ApiFormatter.API_END_PINT['board'][name]) as res:
            response_body = json.loads( res.read().decode('utf-8') )

        if name == 'bitflyer':
            return response_body

        elif name == 'bitbank':
            dic = {}
            dic['asks'] = []
            dic['bids'] = []
            for bid in response_body['data']['bids']:
                element = {'price': float(bid[0]), 'size': float(bid[1])}
                dic['bids'].append(element)
            for ask in response_body['data']['asks']:
                element = {'price': float(ask[0]), 'size': float(ask[1])}
                dic['asks'].append(element)
            return dic
        elif name == 'coincheck':
            dic = {}
            dic['asks'] = []
            dic['bids'] = []
            for bid in response_body['bids']:
                element = {'price': float(bid[0]), 'size': float(bid[1])}
                dic['bids'].append(element)
            for ask in response_body['asks']:
                element = {'price': float(ask[0]), 'size': float(ask[1])}
                dic['asks'].append(element)
            return dic

        else:
            return response_body

# 取引所単体に関する操作
class Exchange:
    def __init__(self, exchange_name):

        self.exchange_name = exchange_name
        self.board = ApiFormatter.get_board(exchange_name)

    def update_board(self):
        self.board = ApiFormatter.get_board(self.exchange_name)

    # private
    def __get_value_from_size(self, size, side):
        anchor = 0.0
        sum = 0.0
        for element in self.board[side]:
            if size - anchor >= element['size']:
                anchor += element['size']
                sum += element['size']*element['price']
            else:
                sum += (size - anchor)*element['price']
                break
        return sum/size

    def get_mean_bid_from_size(self, size):
        return self.__get_value_from_size(size, 'bids')

    def get_mean_ask_from_size(self, size):
        return self.__get_value_from_size(size, 'asks')

# 複数の取引所の間の相互的なハンドリング
class Trader:
    def __init__(self, exchange_name1, exchange_name2):
        self.exchange1 = Exchange(exchange_name1)
        self.exchange2 = Exchange(exchange_name2)

    def update_board(self):
        self.exchange1.update_board()
        self.exchange2.update_board()

    # スプレッドがnagativeになる最大取引サイズを求める(positive状態なら0返る)
    def __get_nagative_size(self, exchange1, exchange2):
        print('hello')

    # return [float(1買 2売), float(2買 1売)]
    def get_active_size(self):
        print('hello')



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


db = SqlController()
bitflyer = Exchange('bitflyer')
coincheck = Exchange('coincheck')
bitbank = Exchange('bitbank')

for i in range(4*3600):
    size = 0.25
    timestamp = int(datetime.now().timestamp())

    bf_meanbid = bitflyer.get_mean_bid_from_size(size)
    bf_meanask = bitflyer.get_mean_ask_from_size(size)
    insert(db, 'bitflyer_log', {
        'mean_bid'   : bf_meanbid,
        'mean_ask'   : bf_meanask,
        'size'       : size,
        'created_at' : timestamp
    })

    cc_meanbid = coincheck.get_mean_bid_from_size(size)
    cc_meanask = coincheck.get_mean_ask_from_size(size)
    insert(db, 'coincheck_log', {
        'mean_bid'   : cc_meanbid,
        'mean_ask'   : cc_meanask,
        'size'       : size,
        'created_at' : timestamp
    })

    bb_meanbid = bitbank.get_mean_bid_from_size(size)
    bb_meanask = bitbank.get_mean_ask_from_size(size)
    insert(db, 'bitbank_log', {
        'mean_bid'   : bb_meanbid,
        'mean_ask'   : bb_meanask,
        'size'       : size,
        'created_at' : timestamp
    })

    bitflyer.update_board()
    coincheck.update_board()
    bitbank.update_board()
    time.sleep(5)

db = None

exit()
