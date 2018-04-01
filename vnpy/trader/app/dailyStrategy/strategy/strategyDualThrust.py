# encoding: UTF-8

"""
DualThrust交易策略
"""

from datetime import datetime, time,timedelta
from vnpy.trader.vtObject import VtBarData
from vnpy.trader.vtConstant import EMPTY_STRING
from vnpy.trader.app.dailyStrategy.dailyTemplate import  DailyTemplate
from ..dailyBase import *
from vnpy.trader.app.barManager import BarManager
import talib
import numpy as np

DAY_END_PRE = time(22, 50)
DAY_END_LAT = time(23, 20)

DAY_AM_START = time(8,58)
DAY_AM_START_END = time(9,2)

DAY_NIGHT_START = time(20,58)
DAY_NIGHT_START_END = time(21,2)

########################################################################
class DualThrustStrategy(DailyTemplate):
    """DualThrust交易策略"""
    className = 'DualThrustStrategy'
    author = u'用Python的交易员'

    # 策略参数
    fixedSize = 100
    k1 = 0.7
    k2 = 0.7

    initDays = 10

    # 策略变量
    barList = []                # K线对象的列表

    dayOpen = 0
    dayHigh = 0
    dayLow = 0
    dayCloseHigh = 0
    dayCloseLow = 0

    dayHighList = []
    dayLowList = []
    dayCloseHighList = []
    dayCloseLowList = []


    range = 0
    longEntry = 0
    shortEntry = 0
    exitTime = time(hour=14, minute=55)

    longEntered = False
    shortEntered = False

    TICK_MODE = 'tick'
    BAR_MODE = 'bar'



    # 参数列表，保存了参数的名称
    paramList = ['name',
                 'className',
                 'author',
                 'vtSymbol',
                 'k1',
                 'k2']    

    # 变量列表，保存了变量的名称
    varList = ['inited',
               'trading',
               'pos',
               'range',
               'longEntry',
               'shortEntry',
               'exitTime']  

    #----------------------------------------------------------------------
    def __init__(self, ctaEngine, setting):
        """Constructor"""
        super(DualThrustStrategy, self).__init__(ctaEngine, setting) 

        # 创建K线合成器对象
        cycleNumber = cycle_number[setting['strategyCycle']]
        if cycleNumber:
            self.bm = BarManager(self.onBar, cycleNumber, self.onXminBar)
        else:
            self.writeCtaLog(u'获取分钟失败')

        self.barList = []

        self.openList = []
        self.closeList = []
        self.highList = []
        self.lowList = []

        self.isMainSymbol = True  ##是否是主力
        self.strategyCycle =  setting['strategyCycle']

        self.mode = self.TICK_MODE    # 回测模式，默认为K线

        endTimeStr = self.dailyEngine.getSymbolEndTime(self.vtSymbol)
        self.endTime_pre = (datetime.strptime(endTimeStr,"%H:%M") - timedelta(minutes=10)).time()

    #----------------------------------------------------------------------
    def onInit(self):
        """初始化策略（必须由用户继承实现）"""
        self.writeCtaLog(u'%s策略初始化' %self.name)
    
        # 载入历史数据，并采用回放计算的方式初始化策略数值
        initData = self.dailyEngine.loadOptData(self.vtSymbol, self.strategyCycle)

        for bar in initData:
            self.highList.append(bar.high)
            self.lowList.append(bar.low)
            self.openList.append(bar.open)
            self.closeList.append(bar.close)

        self.putEvent()

    #----------------------------------------------------------------------
    def onStart(self):
        """启动策略（必须由用户继承实现）"""
        self.writeCtaLog(u'%s策略启动' %self.name)
        self.putEvent()

    #----------------------------------------------------------------------
    def onStop(self):
        """停止策略（必须由用户继承实现）"""
        self.writeCtaLog(u'%s策略停止' %self.name)
        self.putEvent()

    #----------------------------------------------------------------------
    def onTick(self, tick):
        """收到行情TICK推送（必须由用户继承实现）"""

        if tick.datetime.hour == 15: ##3点的先丢掉
            return

        self.bm.updateTick(tick)
        
    #----------------------------------------------------------------------
    def onBar(self, bar):
        """收到Bar推送（必须由用户继承实现）"""
        # 撤销之前发出的尚未成交的委托（包括限价单和停止单）

        self.bm.updateBar(bar)

        # 计算指标数值
        self.barList.append(bar)

        if len(self.barList) <= 4:
            return
        else:
            self.barList.pop(0)
        lastBar = self.barList[-2]

        if lastBar.datetime.time() > DAY_END_PRE:
            return

        # 新的一天
        if lastBar.datetime.date() != bar.datetime.date():
            # 如果已经初始化
            if self.dayHigh:

                self.range = self.dayHigh - self.dayLow



                self.longEntry = bar.open + self.k1 * self.range
                self.shortEntry = bar.open - self.k2 * self.range


            self.writeCtaLog("day start dayHigh:"+str(self.dayHigh)+" dayLow:"+str(self.dayLow)+" dayopen:"+str(bar.open))
            self.dayOpen = bar.open
            self.dayHigh = bar.high
            self.dayLow = bar.low
            self.dayCloseHigh = bar.close
            self.dayCloseLow = bar.close

            self.longEntered = False
            self.shortEntered = False
        else:
            self.dayHigh = max(self.dayHigh, bar.high)
            self.dayLow = min(self.dayLow, bar.low)
            self.dayCloseHigh = max(self.dayCloseHigh,bar.close)
            self.dayCloseLow = min(self.dayCloseLow,bar.close)


        # 收盘平仓

        # 尚未到收盘
        if not self.range:
            return
        self.cancelAll()

        ##计算kdj指标
        k,d =talib.STOCH(np.array(self.highList),np.array(self.lowList),np.array(self.closeList),
                       fastk_period=9,
                       slowk_period=3,
                       slowk_matype=0,
                       slowd_period=3,
                       slowd_matype=0)
        if bar.datetime.time() < self.exitTime:
            if self.pos == 0:
                if self.isMainSymbol == False:
                    return



                #self.k1 = 0.6
                #self.k2 = 0.6

                #if k[-1] > 50 and d[-1] > 50:
                #    self.k1 = 0.4
                #elif k[-1] < 50 and d[-1] < 50:
                #    self.k2 = 0.4

                if  k[-1] >  d[-1] :
                #if bar.close > self.dayOpen:
                    if not self.longEntered:
                        self.buy(bar.close, self.fixedSize,self.shortEntry,STOPDIRECTION_SOTP, False)
                        #self.buy(self.longEntry, self.fixedSize, stop=True)
                else:
                    if not self.shortEntered:
                        self.short(bar.close, self.fixedSize,self.longEntry,STOPDIRECTION_SOTP, False)
                        #self.short(self.shortEntry, self.fixedSize, stop=True)

            # 持有多头仓位
            elif self.pos > 0:
                self.longEntered = True

                if  k[-1] <  d[-1] :
                    self.sell(1, self.pos, STOPDIRECTION_SOTP, False)
                    return

                # 多头止损单
                self.sell(self.shortEntry, self.pos, STOPDIRECTION_LIMIT, True)
                #self.sell(self.shortEntry, self.fixedSize, stop=True)

                #止盈
                self.sell(self.dayOpen+self.range , self.pos, STOPDIRECTION_SOTP, True)

                # 空头开仓单
                #if not self.shortEntered:
                #    self.short(self.shortEntry, 1,self.longEntry,STOPDIRECTION_SOTP, True)
                    #self.short(self.shortEntry, self.fixedSize, stop=True)

            # 持有空头仓位
            elif self.pos < 0:
                self.shortEntered = True

                if  k[-1] >  d[-1] :
                    self.cover(99999, abs(self.pos), STOPDIRECTION_SOTP, False)
                    return

                # 空头止损单
                self.cover( self.longEntry , abs(self.pos), STOPDIRECTION_LIMIT, True)
                #self.cover(self.longEntry, self.fixedSize, stop=True)
                self.cover( self.dayOpen-self.range , abs(self.pos), STOPDIRECTION_SOTP, True)
                # 多头开仓单
                #if not self.longEntered:
                #    self.buy(self.longEntry, 1,self.shortEntry,STOPDIRECTION_SOTP, True)
                    #self.buy(self.longEntry, self.fixedSize, stop=True)
        else:
            if self.pos > 0:
                self.sell(1, self.pos, STOPDIRECTION_SOTP, False)
                #self.sell(bar.close * 0.99, abs(self.pos))
            elif self.pos < 0:
                self.cover(99999, abs(self.pos), STOPDIRECTION_SOTP, False)
                #self.cover(bar.close * 1.01, abs(self.pos))


    ##使用于日间
    def nDayRange(self):
        self.dayHighList.append(self.dayHigh)
        self.dayLowList.append(self.dayLow)
        self.dayCloseLowList.append(self.dayCloseLow)
        self.dayCloseHighList.append(self.dayCloseHigh)

        if len(self.dayHighList) > 4:
            self.dayHighList.pop(0)

        if len(self.dayLowList) > 4:
            self.dayLowList.pop(0)

        if len(self.dayCloseLowList) > 4:
            self.dayCloseLowList.pop(0)

        if len(self.dayCloseHighList) > 4:
            self.dayCloseHighList.pop(0)

        HH = max(self.dayHighList) #N日HIGH的最高价
        HC = max(self.dayCloseHighList)#//N日CLOSE的最高价
        LC = min(self.dayCloseLowList)#//N日CLOSE的最低价
        LL = min(self.dayLowList)#//N日LOW的最低价

        return max(HH-LC,HC-LL)



    def onXminBar(self, bar):


        self.openList.append(bar.open)
        self.closeList.append(bar.close)
        self.highList.append(bar.high)
        self.lowList.append(bar.low)





        # 发出状态更新事件
        self.putEvent()

    #----------------------------------------------------------------------
    def onOrder(self, order):
        """收到委托变化推送（必须由用户继承实现）"""
        pass

    #----------------------------------------------------------------------
    def onTrade(self, trade):
        # 发出状态更新事件
        self.putEvent()

    #----------------------------------------------------------------------
    def onStopOrder(self, so):
        """停止单推送"""
        pass

    def setIsMainSymbol(self,isMainSymbol):
        self.isMainSymbol = isMainSymbol

    def setMode(self, mode):
        self.mode = mode

    ##每次成交手数
    def setFixSize(self,size):
        self.fixedSize = size