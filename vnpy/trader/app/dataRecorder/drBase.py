# encoding: UTF-8

'''
本文件中包含的数据格式和CTA模块通用，用户有必要可以自行添加格式。
'''

from __future__ import division

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

MINUTE_TO_DB_NAME = {3: MINUTE_3_DB_NAME, 5: MINUTE_5_DB_NAME, 15: MINUTE_15_DB_NAME, 30: MINUTE_30_DB_NAME, 60: MINUTE_60_DB_NAME}


# 行情记录模块事件
EVENT_DATARECORDER_LOG = 'eDataRecorderLog'     # 行情记录日志更新事件

# CTA引擎中涉及的数据类定义
from vnpy.trader.vtConstant import EMPTY_UNICODE, EMPTY_STRING, EMPTY_FLOAT, EMPTY_INT
