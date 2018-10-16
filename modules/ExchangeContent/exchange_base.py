import json
import urllib.request
from datetime import datetime, timedelta, timezone
from Logger import Logger

# グローバル変数
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
JST = timezone(timedelta(hours=+9), 'JST')

# 固有取引所カセットが継承するクラス
class ExchangeCharacterBase:
    commission = 0

    def __init__(self, default):
        self.logger = Logger('/home/tatsuya/tmp/log')
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
            self.logger.log(json.dumps(response_dic))
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