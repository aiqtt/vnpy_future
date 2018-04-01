# encoding: UTF-8

from __future__ import division

from math import floor
from datetime import datetime

from vnpy.trader.vtConstant import (EMPTY_INT, EMPTY_FLOAT, 
                                    EMPTY_STRING, EMPTY_UNICODE)
from vnpy.trader.vtObject import VtTickData



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

##停止单方向 止盈  止损    只有在平仓的时候有用
STOPDIRECTION_LOSS = u"止损"
STOPDIRECTION_PROFIT = u"止盈"


# 本地停止单前缀
STOPORDERPREFIX = 'DailyStopOrder.'



EVENT_SPREADTRADING_TICK = 'eSpreadTradingTick.'
EVENT_SPREADTRADING_POS = 'eSpreadTradingPos.'
EVENT_SPREADTRADING_LOG = 'eSpreadTradingLog'
EVENT_SPREADTRADING_ALGO = 'eSpreadTradingAlgo.'
EVENT_SPREADTRADING_ALGOLOG = 'eSpreadTradingAlgoLog'


SPREAD_LONG  = 1  ##多
SPREAD_SHORT = 2 ##空

# 引擎类型，用于区分当前策略的运行环境
ENGINETYPE_BACKTESTING = 'backtesting'  # 回测
ENGINETYPE_TRADING = 'trading'          # 实盘

# 组合仓位状态
POSITION_OPENING  = u'开仓中'
POSITION_OPEN     = u'开仓'
POSITION_CLOSING  = u'平仓中'
POSITION_CLOSE    = u'平仓'


########################################################################
class StLeg(VtTickData):
    """"""

    #----------------------------------------------------------------------
    def __init__(self,contract):
        """Constructor"""
        super(StLeg, self).__init__()

        self.tickInited = False

        # 初始化合约信息
        self.symbol = contract.symbol
        self.exchange = contract.exchange
        self.vtSymbol = contract.vtSymbol

        self.size = contract.size
        self.priceTick = contract.priceTick
        self.gatewayName = contract.gatewayName

        self.ratio = EMPTY_INT          # 实际交易时的比例
        self.multiplier = EMPTY_FLOAT   # 计算价差时的乘数
        self.payup = EMPTY_INT          # 对冲时的超价tick


        ##一下属性用于成交
        self.tradeVolume = EMPTY_INT
        self.tradePrice  = EMPTY_FLOAT

    #----------------------------------------------------------------------
    def newTick(self, tick):
        """行情更新"""
        if not self.tickInited:
            self.date = tick.date
            self.openPrice = tick.openPrice
            self.upperLimit = tick.upperLimit
            self.lowerLimit = tick.lowerLimit
            self.tickInited = True

        self.lastPrice = tick.lastPrice
        self.volume = tick.volume
        self.openInterest = tick.openInterest
        self.time = tick.time

        self.bidPrice1 = tick.bidPrice1
        self.askPrice1 = tick.askPrice1
        self.bidVolume1 = tick.bidVolume1
        self.askVolume1 = tick.askVolume1


########################################################################
class StSpread(object):
    """"""

    #----------------------------------------------------------------------
    def __init__(self):
        """Constructor"""
        self.name = EMPTY_UNICODE       # 名称
        self.symbol = EMPTY_STRING      # 代码（基于组成腿计算）
        
        self.activeLeg = None           # 主动腿
        self.passiveLegs = []           # 被动腿（支持多条）
        self.allLegs = {}               # 所有腿

        self.datetime = None
        
        self.longPos = EMPTY_INT
        self.shortPos = EMPTY_INT
        self.netPos = EMPTY_INT
        self.tickInited = False

        ##下面用于成交的
        self.direction = EMPTY_INT             ##多空
        self.status = EMPTY_UNICODE
        self.portfolioOpenPrice = EMPTY_FLOAT  #开仓价
        self.portfolioClosePrice = EMPTY_FLOAT  #成交价
        
    #----------------------------------------------------------------------
    def initSpread(self):
        """初始化价差"""
        # 价差最少要有一条主动腿
        if not self.activeLeg:
            return
        
        # 生成所有腿列表
        self.allLegs[self.activeLeg.vtSymbol] = self.activeLeg
        for leg in self.passiveLegs:
            self.allLegs[leg.vtSymbol] = leg

        
        # 生成价差代码
        legSymbolList = []
        legSymbolList.append(self.activeLeg.vtSymbol)
        for leg in self.passiveLegs:
            #if leg.multiplier >= 0:
            #    legSymbol = '+%s*%s' %(leg.multiplier, leg.vtSymbol)
            #else:
            #    legSymbol = '%s*%s' %(leg.multiplier, leg.vtSymbol)
            legSymbol = leg.vtSymbol
            legSymbolList.append(legSymbol)
        
        self.symbol = ''.join(legSymbolList)


    #----------------------------------------------------------------------
    def newTick(self, tick):
        """行情推送"""
        symbol = tick.symbol
        hasUpdate = False

        if symbol in self.allLegs:
            leg = self.allLegs[tick.symbol]
            leg.newTick(tick)
            if not self.datetime or self.datetime < tick.datetime:  ##组合时间以最新时间为准
                self.datetime = tick.datetime

            hasUpdate = True


        if not self.tickInited:
            ret = True
            for leg in self.allLegs.values():
                 if not leg.tickInited:
                     ret = False
            self.tickInited = ret

        return hasUpdate


    def calculateLastPrice(self):

        # 遍历价差腿列表
        price = 0.0
        for  leg in self.allLegs.values():
            # 计算价格
            if leg.multiplier > 0:
                price += leg.lastPrice * leg.multiplier

            else:
                price += leg.lastPrice * leg.multiplier

        return price

    def calculateTradePrice(self):

        # 遍历价差腿列表
        price = 0.0
        for  leg in self.allLegs.values():
            # 计算价格
            if leg.multiplier > 0:
                price += leg.tradePrice*leg.tradeVolume * leg.multiplier

            else:
                price += leg.tradePrice*leg.tradeVolume * leg.multiplier

        return price

    def calculateClosePrice(self):  ##组合平仓价格
        price = 0.0
        for  leg in self.allLegs.values():
            # 计算价格
            if leg.multiplier > 0:  #平仓 卖
                price +=  leg.askPrice1 * leg.multiplier

            else:
                price +=  leg.bidPrice1 * leg.multiplier

        return price



    def clearOptionTrade(self):

        for  leg in self.allLegs.values():
            leg.tradeVolume = EMPTY_INT
            leg.tradePrice  = EMPTY_FLOAT

    #----------------------------------------------------------------------
    def calculatePrice(self):
        """计算价格"""
        # 清空价格和委托量数据
        self.bidPrice = EMPTY_FLOAT
        self.askPrice = EMPTY_FLOAT
        self.askVolume = EMPTY_INT
        self.bidVolume = EMPTY_INT
        
        # 遍历价差腿列表
        for n, leg in enumerate(self.allLegs):
            # 计算价格
            if leg.multiplier > 0:
                self.bidPrice += leg.bidPrice * leg.multiplier
                self.askPrice += leg.askPrice * leg.multiplier
            else:
                self.bidPrice += leg.askPrice * leg.multiplier
                self.askPrice += leg.bidPrice * leg.multiplier
                
            # 计算报单量
            if leg.ratio > 0:
                legAdjustedBidVolume = floor(leg.bidVolume / leg.ratio)
                legAdjustedAskVolume = floor(leg.askVolume / leg.ratio)
            else:
                legAdjustedBidVolume = floor(leg.askVolume / abs(leg.ratio))
                legAdjustedAskVolume = floor(leg.bidVolume / abs(leg.ratio))
            
            if n == 0:
                self.bidVolume = legAdjustedBidVolume                           # 对于第一条腿，直接初始化
                self.askVolume = legAdjustedAskVolume
            else:
                self.bidVolume = min(self.bidVolume, legAdjustedBidVolume)      # 对于后续的腿，价差可交易报单量取较小值
                self.askVolume = min(self.askVolume, legAdjustedAskVolume)
                
        # 更新时间
        self.time = datetime.now().strftime('%H:%M:%S.%f')[:-3]
        

    #----------------------------------------------------------------------
    def addActiveLeg(self, leg):
        """添加主动腿"""
        self.activeLeg = leg
    
    #----------------------------------------------------------------------
    def addPassiveLeg(self, leg):
        """添加被动腿"""
        self.passiveLegs.append(leg)
        
        
    
    