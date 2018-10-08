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