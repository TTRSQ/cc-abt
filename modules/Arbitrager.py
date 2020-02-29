import threading
from Exchange import Exchange
from Logger import Logger

class Arbitrager:

    def __init__(self, exchange0, exchange1):
        self.logger = Logger('/home/tatsuya/tmp/log')
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
        if exec:
            exchange.order({
                'size' : size,
                'side' : side
            })

            price = self.get_mean_value_from_size(size ,exchange)
            bid_ask = 'bid' if side == 'sell' else 'ask'

            # 指値でリトライ
            if exchange.last_order['success'] == 0 and exchange.last_order['retry']:
                exchange.order({
                    'size'  : size,
                    'price' : (price[bid_ask]*1.1 if side == 'buy' else price[bid_ask]*0.9),
                    'side'  : side
                })


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
        return {1: t1*rate, 2: t2*rate, 'extra': {'ex0': et0, 'ex1': et1}}

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
            mes = self.max_effective_size(self.threshold['price'], self.threshold['bias'], 1.0)
            if mes[1] > mes[2]:
                if mes[1] > self.threshold['size']:
                    mta = self.max_trade_amount(mes[1], 1.0)
                    size = min(mta[1]*0.5, mes[1]*0.8)
                    if size < self.threshold['size']:
                        return
                    self.trade(1, size, exec)
                    self.logger.log('dir:1, size:' + str(size) + ', price:' + str(mta['extra']['ex0']['ask']) + ' -> ' + str(mta['extra']['ex1']['bid']))
            else:
                if mes[2] > self.threshold['size']:
                    mta = self.max_trade_amount(mes[2], 1.0)
                    size = min(mta[2]*0.5, mes[2]*0.8)
                    if size < self.threshold['size']:
                        return
                    self.trade(2, size, exec)
                    self.logger.log('dir:2, size:' + str(size) + ', price:' + str(mta['extra']['ex1']['ask']) + ' -> ' + str(mta['extra']['ex0']['bid']))


    def parallel_shopping(self, exec):
        self.th0 = threading.Thread(name="ex0", target=self.shopping, args=(self.ex0, exec, ))
        self.th1 = threading.Thread(name="ex1", target=self.shopping, args=(self.ex1, exec, ))
        self.th0.start()
        self.th1.start()

