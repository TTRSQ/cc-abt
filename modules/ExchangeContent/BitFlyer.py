from exchange_base import ExchangeCharacterBase

class BitFlyer(ExchangeCharacterBase):
    def __init__(self):
        self.name = 'BitFlyer'
        with open("/home/tatsuya/app/config.secret", "r") as f:
            key_data = json.load(f)[self.name]
            self.api_key = key_data['KEY']
            self.api_key_s = key_data['S_KEY']
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
