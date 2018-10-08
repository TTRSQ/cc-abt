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
        if command == "order":
            f = open("/home/tatsuya/tmp/log", "a")
            f.write(json.dumps(response_dic)+"\n")
            f.close()
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