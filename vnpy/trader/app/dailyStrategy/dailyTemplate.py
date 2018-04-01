# encoding: UTF-8

'''
本文件包含了日内引擎中的策略开发用模板，开发策略时需要继承dailyTemplate类。
'''

import numpy as np
import talib
import copy
from vnpy.trader.vtConstant import *
from vnpy.trader.vtObject import VtBarData

from .dailyBase  import *
from math import ceil

########################################################################
class DailyTemplate(object):
    """日内策略模板"""
    
    # 策略类的名称和作者
    className = 'DailyTemplate'
    author = EMPTY_UNICODE
    
    # MongoDB数据库的名称，K线数据库默认为1分钟
    tickDbName = TICK_DB_NAME
    barDbName = MINUTE_DB_NAME
    
    # 策略的基本参数
    name = EMPTY_UNICODE           # 策略实例名称
    vtSymbol = EMPTY_STRING        # 交易的合约vt系统代码    
    productClass = EMPTY_STRING    # 产品类型（只有IB接口需要）
    currency = EMPTY_STRING        # 货币（只有IB接口需要）
    
    # 策略的基本变量，由引擎管理
    inited = False                 # 是否进行了初始化
    trading = False                # 是否启动交易，由引擎管理
    pos = 0                        # 持仓情况

    volumeMultiple = 1       #跳价的点位
    priceTick = 1.0           # 价格最小变动
    
    # 参数列表，保存了参数的名称
    paramList = ['name',
                 'className',
                 'author',
                 'vtSymbol']
    
    # 变量列表，保存了变量的名称
    varList = ['inited',
               'trading',
               'pos']

    #----------------------------------------------------------------------
    def __init__(self, dailyEngine, setting):
        """Constructor"""
        self.dailyEngine = dailyEngine

        # 设置策略的参数
        if setting:
            d = self.__dict__
            for key in self.paramList:
                if key in setting:
                    d[key] = setting[key]
    
    #----------------------------------------------------------------------
    def onInit(self):
        """初始化策略（必须由用户继承实现）"""
        raise NotImplementedError
    
    #----------------------------------------------------------------------
    def onStart(self):
        """启动策略（必须由用户继承实现）"""
        raise NotImplementedError

    def setPriceTick(self , volumeMultiple, priceTick):
        self.volumeMultiple =  volumeMultiple
        self.priceTick      =  priceTick

    #----------------------------------------------------------------------
    def onStop(self):
        """停止策略（必须由用户继承实现）"""
        raise NotImplementedError

    #----------------------------------------------------------------------
    def onTick(self, tick):
        """收到行情TICK推送（必须由用户继承实现）"""
        raise NotImplementedError

    #----------------------------------------------------------------------
    def onOrder(self, order):
        """收到委托变化推送（必须由用户继承实现）"""
        raise NotImplementedError
    
    #----------------------------------------------------------------------
    def onTrade(self, trade):
        """收到成交推送（必须由用户继承实现）"""
        raise NotImplementedError
    
    #----------------------------------------------------------------------
    def onBar(self, bar):
        """收到Bar推送（必须由用户继承实现）"""
        raise NotImplementedError
    
    #----------------------------------------------------------------------
    def onStopOrder(self, so):
        """收到停止单推送（必须由用户继承实现）"""
        raise NotImplementedError

    ##判断是否加仓  如果是看多判断止损点是否比上一次开仓价高，高就开仓
    def isScaleIn(self, stopPrice,direction):
        trade = self.dailyEngine.getSymbolLastTrade(self.vtSymbol)
        if trade:
            if direction == DIRECTION_LONG and stopPrice <  trade.price:
                return False

            if direction == DIRECTION_SHORT and stopPrice > trade.price:
                return False


        return True




    #----------------------------------------------------------------------
    def buy(self, price, volume,stopPrice, stopDirection,stop=False,isMargin = False):
        """买开  isMargin 是否考虑保证金 """

        ##判断涨铁停
        if self.dailyEngine.isUpperOrLowerLimit.has_key(self.vtSymbol)  and self.dailyEngine.isUpperOrLowerLimit[self.vtSymbol]== True:
            self.writeCtaLog(u"涨跌停板了")
            return []

        ##计算volume
        if volume == self.dailyEngine.FIX_SIZE_AUDO:
            if price == stopPrice:
                return []
            #volume = self.dailyEngine.getSymbolVolume(self.vtSymbol,price ,stopPrice)
            if isMargin == False:
                volume = self.dailyEngine.getSymbolVolume(self.vtSymbol,price ,stopPrice)
            else: ##反手
                volume = self.dailyEngine.getSymbolVolumeNotMargin(self.vtSymbol,price ,stopPrice)

        #preVolume = self.dailyEngine.getSymbolPrePosition(self.vtSymbol)

        #if preVolume != 0:
        #    volume = min(preVolume,volume)

        self.writeCtaLog("volume="+str(volume))
        if volume == 0:
            return []

        #if stop == False: ##停止单不加超价
        #    price += self.priceTick  ##加上1档超价

        return self.sendOrder(CTAORDER_BUY, price, volume,stopDirection, stop)
    
    #----------------------------------------------------------------------
    def sell(self, price, volume,stopDirection, stop=False):
        """卖平"""


        return self.sendOrder(CTAORDER_SELL, price, volume, stopDirection, stop)

    #----------------------------------------------------------------------
    def short(self, price, volume,stopPrice, stopDirection,stop=False ,isMargin = False):
        """卖开"""

        ##判断涨铁停
        if self.dailyEngine.isUpperOrLowerLimit.has_key(self.vtSymbol)  and self.dailyEngine.isUpperOrLowerLimit[self.vtSymbol]== True:
            self.writeCtaLog(u"涨跌停板了")
            return []

        ##计算volume
        if volume == self.dailyEngine.FIX_SIZE_AUDO:
            if price == stopPrice:
                return []
            if isMargin == False:
                volume = self.dailyEngine.getSymbolVolume(self.vtSymbol,price ,stopPrice)
            else:
                volume = self.dailyEngine.getSymbolVolumeNotMargin(self.vtSymbol,price ,stopPrice)


        #preVolume = self.dailyEngine.getSymbolPrePosition(self.vtSymbol)

        #if preVolume != 0:
        #    volume = min(preVolume,volume)
        self.writeCtaLog("volume="+str(volume))
        if volume == 0:
            return []

        #if stop == False: ##停止单不加超价

        #    price -= self.priceTick  ##加上超价

        return self.sendOrder(CTAORDER_SHORT, price, volume, stopDirection, stop)
 
    #----------------------------------------------------------------------
    def cover(self, price, volume, stopDirection ,stop=False):
        """买平"""


        return self.sendOrder(CTAORDER_COVER, price, volume, stopDirection ,stop)
        
    #----------------------------------------------------------------------
    def sendOrder(self, orderType, price, volume,stopDirection,  stop=False):

        self.writeCtaLog(u"下单"+str(orderType)+str(price)+str(volume)+str(stop))
        if self.getEngineType() == ENGINETYPE_BACKTESTING:
            self.writeCtaLog("sendOrder getAvailable:"+ str(self.dailyEngine.accountManager.getAvailable()))

        """发送委托"""
        if self.trading:
            # 如果stop为True，则意味着发本地停止单
            if stop:
                vtOrderIDList = self.dailyEngine.sendStopOrder(self.vtSymbol, orderType, price, volume, self,stopDirection)
            else:
                vtOrderIDList = self.dailyEngine.sendOrder(self.vtSymbol, orderType, price, volume, self) 
            return vtOrderIDList
        else:
            # 交易停止时发单返回空字符串
            return []
        
    #----------------------------------------------------------------------
    def cancelOrder(self, vtOrderID):
        """撤单"""
        # 如果发单号为空字符串，则不进行后续操作
        if not vtOrderID:
            return
        
        if STOPORDERPREFIX in vtOrderID:
            self.dailyEngine.cancelStopOrder(vtOrderID)
        else:
            self.dailyEngine.cancelOrder(vtOrderID)
            
    #----------------------------------------------------------------------
    def cancelAllStop(self):
        """全部停止单"""
        self.dailyEngine.cancelAllStop(self.vtSymbol,self.className)

    def cancelAll(self):
        """全部撤单"""
        self.dailyEngine.cancelAll(self.vtSymbol,self.className)
    
    #----------------------------------------------------------------------
    def insertTick(self, tick):
        """向数据库中插入tick数据"""
        self.dailyEngine.insertData(self.tickDbName, self.vtSymbol, tick)
    
    #----------------------------------------------------------------------
    def insertBar(self, bar):
        """向数据库中插入bar数据"""
        self.dailyEngine.insertData(self.barDbName, self.vtSymbol, bar)
        
    #----------------------------------------------------------------------
    def loadTick(self, days):
        """读取tick数据"""
        return self.dailyEngine.loadTick(self.tickDbName, self.vtSymbol, days)
    
    #----------------------------------------------------------------------
    def loadBar(self, days):
        """读取bar数据"""
        return self.dailyEngine.loadBar(self.barDbName, self.vtSymbol, days)


    
    #----------------------------------------------------------------------
    def writeCtaLog(self, content):
        """记录CTA日志"""
        content = self.name + self.vtSymbol+ ':' + content
        self.dailyEngine.writeCtaLog(content)
        
    #----------------------------------------------------------------------
    def putEvent(self):
        """发出策略状态变化事件"""
        self.dailyEngine.putStrategyEvent(self.name)
        
    #----------------------------------------------------------------------
    def getEngineType(self):
        """查询当前运行的环境"""
        return self.dailyEngine.engineType
    

########################################################################
class TargetPosTemplate(DailyTemplate):
    """
    允许直接通过修改目标持仓来实现交易的策略模板
    
    开发策略时，无需再调用buy/sell/cover/short这些具体的委托指令，
    只需在策略逻辑运行完成后调用setTargetPos设置目标持仓，底层算法
    会自动完成相关交易，适合不擅长管理交易挂撤单细节的用户。    
    
    使用该模板开发策略时，请在以下回调方法中先调用母类的方法：
    onTick
    onBar
    onOrder
    
    假设策略名为TestStrategy，请在onTick回调中加上：
    super(TestStrategy, self).onTick(tick)
    
    其他方法类同。
    """
    
    className = 'TargetPosTemplate'
    author = u'量衍投资'
    
    # 目标持仓模板的基本变量
    tickAdd = 1             # 委托时相对基准价格的超价
    lastTick = None         # 最新tick数据
    lastBar = None          # 最新bar数据
    targetPos = EMPTY_INT   # 目标持仓
    orderList = []          # 委托号列表

    # 变量列表，保存了变量的名称
    varList = ['inited',
               'trading',
               'pos',
               'targetPos']

    #----------------------------------------------------------------------
    def __init__(self, dailyEngine, setting):
        """Constructor"""
        super(TargetPosTemplate, self).__init__(dailyEngine, setting)
        
    #----------------------------------------------------------------------
    def onTick(self, tick):
        """收到行情推送"""
        self.lastTick = tick
        
        # 实盘模式下，启动交易后，需要根据tick的实时推送执行自动开平仓操作
        if self.trading:
            self.trade()
        
    #----------------------------------------------------------------------
    def onBar(self, bar):
        """收到K线推送"""
        self.lastBar = bar
    
    #----------------------------------------------------------------------
    def onOrder(self, order):
        """收到委托推送"""
        if order.status == STATUS_ALLTRADED or order.status == STATUS_CANCELLED:
            self.orderList.remove(order.vtOrderID)
    
    #----------------------------------------------------------------------
    def setTargetPos(self, targetPos):
        """设置目标仓位"""
        self.targetPos = targetPos
        
        self.trade()
        
    #----------------------------------------------------------------------
    def trade(self):
        """执行交易"""
        # 先撤销之前的委托
        for vtOrderID in self.orderList:
            self.cancelOrder(vtOrderID)
        self.orderList = []
        
        # 如果目标仓位和实际仓位一致，则不进行任何操作
        posChange = self.targetPos - self.pos
        if not posChange:
            return
        
        # 确定委托基准价格，有tick数据时优先使用，否则使用bar
        longPrice = 0
        shortPrice = 0
        
        if self.lastTick:
            if posChange > 0:
                longPrice = self.lastTick.askPrice1 + self.tickAdd
            else:
                shortPrice = self.lastTick.bidPrice1 - self.tickAdd
        else:
            if posChange > 0:
                longPrice = self.lastBar.close + self.tickAdd
            else:
                shortPrice = self.lastBar.close - self.tickAdd
        
        # 回测模式下，采用合并平仓和反向开仓委托的方式
        if self.getEngineType() == ENGINETYPE_BACKTESTING:
            if posChange > 0:
                l = self.buy(longPrice, abs(posChange))
            else:
                l = self.short(shortPrice, abs(posChange))
            self.orderList.extend(l)
        
        # 实盘模式下，首先确保之前的委托都已经结束（全成、撤销）
        # 然后先发平仓委托，等待成交后，再发送新的开仓委托
        else:
            # 检查之前委托都已结束
            if self.orderList:
                return
            
            # 买入
            if posChange > 0:
                if self.pos < 0:
                    l = self.cover(longPrice, abs(self.pos))
                else:
                    l = self.buy(longPrice, abs(posChange))
            # 卖出
            else:
                if self.pos > 0:
                    l = self.sell(shortPrice, abs(self.pos))
                else:
                    l = self.short(shortPrice, abs(posChange))
            self.orderList.extend(l)
    

########################################################################
class ArrayManager(object):
    """
    K线序列管理工具，负责：
    1. K线时间序列的维护
    2. 常用技术指标的计算
    """

    #----------------------------------------------------------------------
    def __init__(self, size=100):
        """Constructor"""
        self.count = 0                      # 缓存计数
        self.size = size                    # 缓存大小
        self.inited = False                 # True if count>=size
        
        self.openArray = np.zeros(size)     # OHLC
        self.highArray = np.zeros(size)
        self.lowArray = np.zeros(size)
        self.closeArray = np.zeros(size)
        self.volumeArray = np.zeros(size)
        
    #----------------------------------------------------------------------
    def updateBar(self, bar):
        """更新K线"""


        self.count += 1
        if not self.inited and self.count >= self.size:
            self.inited = True
        
        self.openArray[0:self.size-1] = self.openArray[1:self.size]
        self.highArray[0:self.size-1] = self.highArray[1:self.size]
        self.lowArray[0:self.size-1] = self.lowArray[1:self.size]
        self.closeArray[0:self.size-1] = self.closeArray[1:self.size]
        self.volumeArray[0:self.size-1] = self.volumeArray[1:self.size]



        self.openArray[-1] = bar.open
        self.highArray[-1] = bar.high
        self.lowArray[-1] = bar.low        
        self.closeArray[-1] = bar.close
        self.volumeArray[-1] = bar.volume



    def updateLastBarValue(self,bar):


        self.openArray[-1] = bar.open
        self.highArray[-1] = bar.high
        self.lowArray[-1] = bar.low
        self.closeArray[-1] = bar.close
        self.volumeArray[-1] = bar.volume

    #----------------------------------------------------------------------
    @property
    def open(self):
        """获取开盘价序列"""
        return self.openArray
        
    #----------------------------------------------------------------------
    @property
    def high(self):
        """获取最高价序列"""
        return self.highArray
    
    #----------------------------------------------------------------------
    @property
    def low(self):
        """获取最低价序列"""
        return self.lowArray
    
    #----------------------------------------------------------------------
    @property
    def close(self):
        """获取收盘价序列"""
        return self.closeArray
    
    #----------------------------------------------------------------------
    @property    
    def volume(self):
        """获取成交量序列"""
        return self.volumeArray
    
    #----------------------------------------------------------------------
    def sma(self, n, array=False):
        """简单均线"""
        result = talib.SMA(self.close, n)
        if array:
            return result
        return result[-1]

    ##计算sar，上升赋值正，下降赋值负数
    def sar(self):
        abc = talib.SAR(self.highArray, self.lowArray)
        return abc



    #----------------------------------------------------------------------
    def std(self, n, array=False):
        """标准差"""
        result = talib.STDDEV(self.close, n)
        if array:
            return result
        return result[-1]
    
    #----------------------------------------------------------------------
    def cci(self, n, array=False):
        """CCI指标"""
        result = talib.CCI(self.high, self.low, self.close, n)
        if array:
            return result
        return result[-1]
        
    #----------------------------------------------------------------------
    def atr(self, n, array=False):
        """ATR指标"""
        result = talib.ATR(self.high, self.low, self.close, n)
        if array:
            return result
        return result[-1]
        
    #----------------------------------------------------------------------
    def rsi(self, n, array=False):
        """RSI指标"""
        result = talib.RSI(self.close, n)
        if array:
            return result
        return result[-1]
    
    #----------------------------------------------------------------------
    def macd(self, fastPeriod, slowPeriod, signalPeriod, array=False):
        """MACD指标"""
        macd, signal, hist = talib.MACD(self.close, fastPeriod,
                                        slowPeriod, signalPeriod)
        if array:
            return macd, signal, hist
        return macd[-1], signal[-1], hist[-1]
    
    #----------------------------------------------------------------------
    def adx(self, n, array=False):
        """ADX指标"""
        result = talib.ADX(self.high, self.low, self.close, n)
        if array:
            return result
        return result[-1]
    
    #----------------------------------------------------------------------
    def boll(self, n, dev, array=False):
        """布林通道"""
        mid = self.sma(n, array)
        std = self.std(n, array)
        
        up = mid + std * dev
        down = mid - std * dev
        
        return up, down    
    
    #----------------------------------------------------------------------
    def keltner(self, n, dev, array=False):
        """肯特纳通道"""
        mid = self.sma(n, array)
        atr = self.atr(n, array)
        
        up = mid + atr * dev
        down = mid - atr * dev
        
        return up, down
    
    #----------------------------------------------------------------------
    def donchian(self, n, array=False):
        """唐奇安通道"""
        up = talib.MAX(self.high, n)
        down = talib.MIN(self.low, n)
        
        if array:
            return up, down
        return up[-1], down[-1]