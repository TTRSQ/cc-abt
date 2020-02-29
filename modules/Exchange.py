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