# encoding: UTF-8

'''
本文件中包含了CTA模块中用到的一些基础设置、类和常量等。
'''

# CTA引擎中涉及的数据类定义
from vnpy.trader.vtConstant import EMPTY_UNICODE, EMPTY_STRING, EMPTY_FLOAT, EMPTY_INT

# 常量定义
# CTA引擎中涉及到的交易方向类型
CTAORDER_BUY = u'买开'
CTAORDER_SELL = u'卖平'
CTAORDER_SHORT = u'卖开'
CTAORDER_COVER = u'买平'

# 本地停止单状态
STOPORDER_WAITING = u'等待中'
STOPORDER_CANCELLED = u'已撤销'
STOPORDER_TRIGGERED = u'已触发'

##停止单方向 STOP  limit  开仓的时候 stop是追涨 limit 等回落  平仓 stop 是止盈， limit止损
STOPDIRECTION_SOTP =  "stop"
STOPDIRECTION_LIMIT = "limit"


# 本地停止单前缀
STOPORDERPREFIX = 'DailyStopOrder.'

# 数据库名称
SETTING_DB_NAME = 'VnTrader_Setting_Db'
POSITION_DB_NAME = 'VnTrader_Position_Db'

TICK_DB_NAME = 'VnTrader_Tick_Db'
DAILY_DB_NAME = 'VnTrader_Daily_Db'

MINUTE_DB_NAME = 'VnTrader_1Min_Db'
MINUTE_3_DB_NAME = 'VnTrader_3Min_Db'
MINUTE_5_DB_NAME = 'VnTrader_5Min_Db'
MINUTE_6_DB_NAME = 'VnTrader_6Min_Db'
MINUTE_7_DB_NAME = 'VnTrader_7Min_Db'
MINUTE_8_DB_NAME = 'VnTrader_8Min_Db'
MINUTE_9_DB_NAME = 'VnTrader_9Min_Db'
MINUTE_10_DB_NAME = 'VnTrader_10Min_Db'
MINUTE_15_DB_NAME = 'VnTrader_15Min_Db'
MINUTE_30_DB_NAME = 'VnTrader_30Min_Db'
MINUTE_60_DB_NAME = 'VnTrader_60Min_Db'

WEEK_DB_NAME  = 'VnTrader_Week_Db'
DAY_DB_NAME   = 'VnTrader_Day_Db'

# 引擎类型，用于区分当前策略的运行环境
ENGINETYPE_BACKTESTING = 'backtesting'  # 回测
ENGINETYPE_TRADING = 'trading'          # 实盘

# CTA模块事件
EVENT_DAILY_LOG = 'eDailyLog'               # daily相关的日志事件
EVENT_DAILY_STRATEGY = 'eDailyStrategy.'    # daily策略状态变化事件

cycle_db = {"3min":MINUTE_3_DB_NAME,"5min":MINUTE_5_DB_NAME,"6min":MINUTE_6_DB_NAME,"7min":MINUTE_7_DB_NAME,"8min":MINUTE_8_DB_NAME,
            "9min":MINUTE_9_DB_NAME,"10min":MINUTE_10_DB_NAME,"15min":MINUTE_15_DB_NAME,"30min":MINUTE_30_DB_NAME,"60min":MINUTE_60_DB_NAME,"day":DAY_DB_NAME}

cycle_number =  {"3min":3,"5min":5,"6min":6,"7min":7,"8min":8,
            "9min":9,"10min":10,"15min":15,"30min":30,"60min":60}



########################################################################
class StopOrder(object):
    """本地停止单"""

    #----------------------------------------------------------------------
    def __init__(self):
        """Constructor"""
        self.vtSymbol = EMPTY_STRING
        self.orderType = EMPTY_UNICODE
        self.direction = EMPTY_UNICODE
        self.offset = EMPTY_UNICODE
        self.price = EMPTY_FLOAT
        self.volume = EMPTY_INT

        self.strategyName = EMPTY_STRING #策略名
        self.strategy = None             # 下停止单的策略对象
        self.stopOrderID = EMPTY_STRING  # 停止单的本地编号 
        self.status = EMPTY_STRING       # 停止单状态

        self.stopDirection = EMPTY_STRING  ## 停止单方向 止盈  止损    只有在平仓的时候有用





