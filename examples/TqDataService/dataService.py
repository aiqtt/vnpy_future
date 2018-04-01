# encoding: UTF-8

import sys
import json
from datetime import datetime
from time import sleep

from pymongo import MongoClient, ASCENDING

from vnpy.data.tq.vntq import TqApi
from vnpy.trader.vtObject import VtBarData

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

api = TqApi()   # 历史行情服务API对象
api.connect()   # 连接
taskList = []   # 下载任务列表


#----------------------------------------------------------------------
def generateVtBar(symbol, d):
    """生成K线"""
    bar = VtBarData()
    
    bar.symbol = symbol
    bar.vtSymbol = symbol
    bar.open = float(d['open'])
    bar.high = float(d['high'])
    bar.low = float(d['low'])
    bar.close = float(d['close'])
    bar.volume = d['volume']
    bar.openInterest = d['open_oi']
    bar.datetime = datetime.fromtimestamp(d['datetime']/1000000000)
    bar.date = bar.datetime.strftime("%Y%m%d")
    bar.time = bar.datetime.strftime("%H:%M:%S")
    
    return bar

#----------------------------------------------------------------------
def onChart(symbol, seconds):
    """K线更新处理函数"""    
    # 避免重复记录已经完成的任务
    if symbol not in taskList:
        return 
    
    serial = api.get_kline_serial(symbol, seconds)
    
    cl = db[symbol]                                                 # 集合
    cl.ensure_index([('datetime', ASCENDING)], unique=True)         # 添加索引
    
    l = serial.values()
    for d in l:
        bar = generateVtBar(symbol, d)
        d = bar.__dict__
        flt = {'datetime': bar.datetime}
        cl.replace_one(flt, d, True)
    
    start = datetime.fromtimestamp(l[0]['datetime']/1000000000)
    end = datetime.fromtimestamp(l[-1]['datetime']/1000000000)
    print u'合约%s下载完成%s - %s' %(symbol, start, end)
    
    # 移除已经完成的任务
    if symbol in taskList:
        taskList.remove(symbol)

#----------------------------------------------------------------------
def downMinuteBarBySymbol(symbol, num,duration_seconds=60):
    """下载某一合约的分钟线数据"""
    api.subscribe_chart(symbol, duration_seconds, num, onChart)



def downloadAllBar(num, db_name):
    """下载所有配置中的合约的分钟线数据"""
    print '-' * 50
    print u'开始下载合约bar线数据'+db_name
    print '-' * 50

    # 添加下载任务
    taskList.extend(SYMBOLS)

    duration_seconds = 60
    if db_name == MINUTE_DB_NAME:
        duration_seconds = 60
    if db_name == MINUTE_60_DB_NAME:
        duration_seconds = 60*60

    if db_name == MINUTE_30_DB_NAME:
        duration_seconds = 30*60

    if db_name == MINUTE_5_DB_NAME:
        duration_seconds = 5*60

    if db_name == DAY_DB_NAME:
        duration_seconds = 60*60*24

    global  db
    db = mc[db_name]


    for symbol in SYMBOLS:
        downMinuteBarBySymbol(str(symbol), num,duration_seconds)


    while True:
        sleep(2)

        # 如果任务列表为空，则说明数据已经全部下载完成
        if not taskList:
            print '-' * 50
            print u'合约分钟线数据下载完成'
            print '-' * 50
            return

#----------------------------------------------------------------------
def downloadAllMinuteBar(num):
    """下载所有配置中的合约的分钟线数据"""
    print '-' * 50
    print u'开始下载合约分钟线数据'
    print '-' * 50
    
    # 添加下载任务
    taskList.extend(SYMBOLS)
    
    for symbol in SYMBOLS:
        downMinuteBarBySymbol(str(symbol), num)
    
    while True:
        sleep(2)

        # 如果任务列表为空，则说明数据已经全部下载完成
        if not taskList:
            print '-' * 50
            print u'合约分钟线数据下载完成'
            print '-' * 50
            return       
    


    