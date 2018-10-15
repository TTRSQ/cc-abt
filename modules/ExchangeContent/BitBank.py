import exchange_base

class BitBank(ExchangeCharacterBase):
    def __init__(self):
        self.name = 'BitBank'
        with open("/home/tatsuya/app/config.secret", "r") as f:
            key_data = json.load(f)[self.name]
            self.api_key = key_data['KEY']
            self.api_key_s = key_data['S_KEY']
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