# encoding: UTF-8

import sys
import json
from datetime import datetime
from time import time, sleep

from pymongo import MongoClient, ASCENDING

from vnpy.trader.vtObject import VtBarData


import tushare as ts


# 数据库名称
SETTING_DB_NAME = 'VnTrader_Setting_Db'
TICK_DB_NAME = 'VnTrader_Tick_Db'
DAILY_DB_NAME = 'VnTrader_Daily_Db'
MINUTE_DB_NAME = 'VnTrader_1Min_Db'
MINUTE_3_DB_NAME = 'VnTrader_3Min_Db'
MINUTE_5_DB_NAME = 'VnTrader_5Min_Db'
MINUTE_15_DB_NAME = 'VnTrader_15Min_Db'
MINUTE_30_DB_NAME = 'VnTrader_30Min_Db'
MINUTE_60_DB_NAME = 'VnTrader_60Min_Db'

DAY_DB_NAME   = 'VnTrader_Day_Db'
WEEK_DB_NAME  = 'VnTrader_Week_Db'

# 加载配置
config = open('config.json')
setting = json.load(config)

MONGO_HOST = setting['MONGO_HOST']
MONGO_PORT = setting['MONGO_PORT']
SYMBOLS = setting['SYMBOLS']

mc = MongoClient(MONGO_HOST, MONGO_PORT)        # Mongo连接
db = mc[MINUTE_DB_NAME]                         # 数据库


#----------------------------------------------------------------------
def generateExchange(symbol):
    """生成VT合约代码"""
    exchange = ''
    if symbol[0:2] in ['60', '51']:
        exchange = 'SSE'
    elif symbol[0:2] in ['00', '15', '30']:
        exchange = 'SZSE'
    return exchange

#----------------------------------------------------------------------
def generateVtBar(row):
    """生成K线"""
    bar = VtBarData()
    
    bar.symbol = row['code']
    bar.exchange = generateExchange(bar.symbol)
    bar.vtSymbol = '.'.join([bar.symbol, bar.exchange])
    bar.open = row['open']
    bar.high = row['high']
    bar.low = row['low']
    bar.close = row['close']
    bar.volume = row['vol']
    bar.datetime = row.name
    bar.date = bar.datetime.strftime("%Y%m%d")
    bar.time = bar.datetime.strftime("%H:%M:%S")
    
    return bar

#----------------------------------------------------------------------
def downMinuteBarBySymbol(symbol,freq):
    """下载某一合约的分钟线数据"""
    start = time()


    cl = db[symbol]
    cl.ensure_index([('datetime', ASCENDING)], unique=True)         # 添加索引

    df = ts.bar(symbol, ts.get_apis(),freq=freq, asset='X')
    #df = ts.bar(symbol, ktype='1min')
    df = df.sort_index()
    
    for ix, row in df.iterrows():
        bar = generateVtBar(row)
        d = bar.__dict__
        #有的合约字母变成大写，可以自己放开这个地方
        #d['symbol'] = d['symbol'].lower()

        flt = {'datetime': bar.datetime}
        cl.replace_one(flt, d, True)            

    end = time()
    cost = (end - start) * 1000

    print u'合约%s数据下载完成%s - %s，耗时%s毫秒' %(symbol, df.index[0], df.index[-1], cost)

    
#----------------------------------------------------------------------
def downloadAllMinuteBar(db_name):
    """下载所有配置中的合约的分钟线数据"""
    print '-' * 50
    print u'开始下载合约分钟线数据'
    print '-' * 50


    #KTYPE_LOW_COLS = ['D', 'XD', 'W', 'M', 'Q', 'Y']
    #KTYPE_ARR = ['1MIN', '5MIN', '15MIN', '30MIN', '60MIN']
    freq = "D"
    if db_name == MINUTE_DB_NAME:
        freq = '1MIN'
    if db_name == MINUTE_60_DB_NAME:
        freq = '60MIN'

    if db_name == MINUTE_30_DB_NAME:
        freq = '30MIN'

    if db_name == MINUTE_5_DB_NAME:
        freq = '5MIN'

    if db_name == DAY_DB_NAME:
        freq = 'D'

    global  db
    db = mc[db_name]


    # 添加下载任务
    for symbol in SYMBOLS:
        try:
            downMinuteBarBySymbol(str(symbol),freq)
        except :
            print("symbol download error")

    print '-' * 50
    print u'合约分钟线数据下载完成'
    print '-' * 50
    


    