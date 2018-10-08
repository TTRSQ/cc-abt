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

# メインループ
for i in range(1800*24*2):
    trader = Trader(Exchange(BitFlyer()), Exchange(BitBank()))
    trader.parallel_shopping(1)
    time.sleep(2.0)

exit()
