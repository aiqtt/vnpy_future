# encoding: UTF-8

"""

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
class MIStrategy(DailyTemplate):
    """DualThrust交易策略"""
    className = 'MIStrategy'
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
        super(MIStrategy, self).__init__(ctaEngine, setting)

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

        #endTimeStr = self.dailyEngine.getSymbolEndTime(self.vtSymbol)
        #self.endTime_pre = (datetime.strptime(endTimeStr,"%H:%M") - timedelta(minutes=10)).time()


        self.up_fractal_exists = False
        self.down_fractal_exists = False

        self.up_price = 0.0
        self.low_price = 0.0

        self.AOIndexList = []
        self.ACIndexList = []
        self.calACIndexList = []

        self.tradePrice = 0.0

        self.dayIsEndHandle = False

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

        if self.dayIsEndHandle == True:
            self.cancelAllStop()
            if self.pos > 0:
                self.sell(tick.lowerLimit, self.pos, STOPDIRECTION_SOTP, False)
            elif self.pos < 0:
                self.cover(tick.upperLimit, abs(self.pos), STOPDIRECTION_SOTP, False)

        if self.pos == 0:

            if self.shortEntered == True:
                self.cancelAll()
                self.shortEntered = False
                if tick.bidPrice1 != 0.0 and abs(tick.bidPrice1 - self.ma_line_13) < tick.bidPrice1*0.005:#0.03
                    self.short(tick.bidPrice1, self.fixedSize,self.ma_line_13,STOPDIRECTION_SOTP, False)
            elif self.longEntered == True:
                self.cancelAll()
                self.longEntered = False
                if tick.askPrice1 != 0.0 and abs(tick.askPrice1 - self.ma_line_13) < tick.askPrice1* 0.05:#0.03
                    self.buy(tick.askPrice1, self.fixedSize,self.ma_line_13,STOPDIRECTION_SOTP, False)


        self.bm.updateTick(tick)
        
    #----------------------------------------------------------------------
    def onBar(self, bar):
        """收到Bar推送（必须由用户继承实现）"""
        # 撤销之前发出的尚未成交的委托（包括限价单和停止单）

        self.bm.updateBar(bar)




    def onXminBar(self, bar):

        #self.writeCtaLog("onXminBar")
        self.openList.append(bar.open)
        self.closeList.append(bar.close)
        self.highList.append(bar.high)
        self.lowList.append(bar.low)


        hasExit = True

        if bar.datetime <  datetime(2014,12,26):
            if (bar.datetime.time() < self.exitTime and bar.datetime.time() > DAY_AM_START):
                hasExit = False
        elif bar.datetime > datetime(2014,12,26) and  bar.datetime < datetime(2016,05,01):
             if (bar.datetime.time() < time(0, 45) or bar.datetime.time() > DAY_AM_START):
                 hasExit = False
        elif bar.datetime > datetime(2016,05,01):
            if (bar.datetime.time() < DAY_END_PRE and bar.datetime.time() > DAY_AM_START):
                hasExit = False

        self.dayIsEndHandle = False
        if hasExit == True:
            self.dayIsEndHandle = True

        ma_line_13_list = self.MA(np.array(self.closeList[-200:]),34,True)  ##21
        ma_line_8_list = self.MA(np.array(self.closeList[-200:]),21,True)   ##13
        ma_line_5_list = self.MA(np.array(self.closeList[-200:]),13,True)   ##8

        self.ma_line_13 = ma_line_13_list[-1]
        self.ma_line_8 = ma_line_8_list [-1]
        self.ma_line_5 = ma_line_5_list[-1]

        self.cciValueList = talib.CCI(np.array(self.highList[-200:]),np.array(self.lowList[-200:]),np.array(self.closeList[-200:]),timeperiod=14)

        if self.pos > 0:
            self.cancelAllStop()
            self.sell(self.ma_line_13, self.pos, STOPDIRECTION_LIMIT, True)

        elif self.pos < 0:
            self.cancelAllStop()
            self.cover(self.ma_line_13, abs(self.pos), STOPDIRECTION_LIMIT, True)

        elif self.pos == 0:

            self.cancelAllStop()
            if self.dayIsEndHandle == True:
                return

            if self.isMainSymbol == False:
                return


            #多
            if self.ma_line_5 > self.ma_line_8  and self.ma_line_8 > self.ma_line_13 and bar.low > self.ma_line_8\
                    and self.cciValueList[-1] > 50:
                #找开始开口的地方
                for i in range(1,100):
                    index = -1*i
                    if ma_line_5_list[index] > ma_line_8_list[index] and ma_line_8_list[index] > ma_line_13_list[index]:
                            a = 3
                    else:
                        break

                price = self.closeList[-1*i]*1.005
                if price > bar.close:
                    self.buy(price, self.fixedSize, self.ma_line_13,STOPDIRECTION_SOTP, True)
                else:
                    self.longEntered = True


            if self.ma_line_5 < self.ma_line_8  and self.ma_line_8 < self.ma_line_13 and bar.high < self.ma_line_8 \
                     and self.cciValueList[-1] < -50:
                #找开始开口的地方
                for i in range(1,100):
                    index = -1*i
                    if ma_line_5_list[index] < ma_line_8_list[index] and ma_line_8_list[index] < ma_line_13_list[index]:
                            a = 3
                    else:
                        break

                price = self.closeList[-1*i]*(1 - 0.005)
                if price < bar.close:
                    self.short(price,self.fixedSize, self.ma_line_13,STOPDIRECTION_SOTP, True)
                else:
                    self.shortEntered = True


        # 发出状态更新事件
        self.putEvent()

    def MA(self,npArray,n, array=False):
        list = talib.EMA(npArray,timeperiod=n)

        if array == True:
            return list

        return list[-1]

    #----------------------------------------------------------------------
    def onOrder(self, order):
        """收到委托变化推送（必须由用户继承实现）"""
        pass

    #----------------------------------------------------------------------
    def onTrade(self, trade):
        # 发出状态更新事件

        self.writeCtaLog("onTrade order price:" + str(trade.price) + str(trade.tradeTime))

        self.tradePrice = trade.price

        if self.pos > 0:
            self.cancelAllStop()


            self.sell(self.ma_line_13, self.pos, STOPDIRECTION_LIMIT, True)

        elif self.pos < 0:
            self.cancelAllStop()

            self.cover(self.ma_line_13, abs(self.pos), STOPDIRECTION_LIMIT, True)

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




    #判断序列n日上行
    def is_up_going(self,alist,n):
        if len(alist) < n:
            return False
        for i in range(n-1):
            if alist[-(1+i)] <= alist[-(2+i)]:
                return False
        return True

    #判断序列n日下行
    def is_down_going(self,alist,n):
        if len(alist) < n:
            return False
        for i in range(n-1):
            if alist[-(1+i)] >= alist[-(2+i)]:
                return False
        return True