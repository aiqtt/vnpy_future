# encoding: UTF-8

'''
本文件中包含的是价差模块的回测引擎
'''
from __future__ import division

from datetime import datetime, timedelta, date
from collections import OrderedDict
from itertools import product
import multiprocessing
import copy
import random

import pandas as pd
import numpy as np
from vnpy.trader.vtFunction import *




from vnpy.trader.vtGlobal import globalSetting
from vnpy.trader.vtObject import VtTickData, VtBarData,VtPositionData,VtContractData
from vnpy.trader.vtConstant import *
from vnpy.trader.vtGateway import VtOrderData, VtTradeData

from .stBase import *
from .strategy.strategyCrossSpecies import  *
import matplotlib.pyplot as plt

import sys
reload(sys)
sys.setdefaultencoding('utf8')

########################################################################
class BacktestingEngine(object):
    """
    spread 回测引擎
    函数接口和策略引擎保持一样，
    从而实现同一套代码从回测到实盘。
    """


    portfolioFileName = 'etf_portfolio.json'
    portfoliofilePath = getJsonPath(portfolioFileName, __file__)


    TICK_MODE = 'tick'
    BAR_MODE = 'bar'
    FIX_SIZE_AUDO = -1  ##设置为-1，表示volume需要根据资金使用率等来计算

    #----------------------------------------------------------------------
    def __init__(self):
        """Constructor"""
        # 本地停止单
        self.stopOrderCount = 0     # 编号计数：stopOrderID = STOPORDERPREFIX + str(stopOrderCount)

        # 本地停止单字典, key为stopOrderID，value为stopOrder对象
        self.stopOrderDict = {}             # 停止单撤销后不会从本字典中删除
        self.workingStopOrderDict = {}      # 停止单撤销后会从本字典中删除

        self.engineType = ENGINETYPE_BACKTESTING    # 引擎类型为回测

        self.mode = self.BAR_MODE   # 回测模式，默认为K线

        self.startDate = ''
        self.initDays = 0
        self.endDate = ''
        self.curDate = None  ##回测当前日期

        self.capital = 1000000      # 回测时的起始本金（默认100万）
        self.slippage = 0           # 回测时假设的滑点
        self.rate = 0               # 回测时假设的佣金比例（适用于百分比佣金）
        self.commission = 2         #1手 手续费  （适用于固定手数佣金）
        self.size = 1               # 合约大小，默认为1
        self.priceTick = 0          # 价格最小变动


        self.capitalUseRat = 0.5    #整体资金使用率
        self.riskRate      = 0.02   #单笔风险敞口
        self.superPricePoint = 1    #超价档位
        self.contactInfo = None
        self.portfolioInfo = None  ##组合
        self.setting  = None

        self.dbClient = None        # 数据库客户端
        self.dbCursor = None        # 数据库指针

        self.changeMainSymbol = 'rb0000'            # 回测产品
        self.mainSymbol = ''        # 主力合约
        self.secSymbol = ''         #次主力合约

        self.positionManager = None
        self.accountManager = None

        self.portfolioList = {}   ##价差组合
        self.algoList      = {}   ##算法列表
        self.strategy = {}



        self.symbolFile = {}     #日线文件句柄  每天开始更新一下bar，小时线直接合成
        self.symbolData = {}

        self.portfolioCurTimeList = {}

        #判断主力合约
        self.dayMainSymbolFile = {}  #判断主力合约的日线文件句柄
        self.dayMainSymbolData = {}     #日线文件读取的当前K线数据,跟dayMainSymbolFile配合使用


        self.dataStartDate = None       # 回测数据开始日期，datetime对象
        self.dataEndDate = None         # 回测数据结束日期，datetime对象


        self.limitOrderCount = 0                    # 限价单编号
        self.limitOrderDict = OrderedDict()         # 限价单字典
        self.workingLimitOrderDict = OrderedDict()  # 活动限价单字典，用于进行撮合用

        self.workingOrderToPortfolio = {}  ##订单ID，组合id


        self.portfolioOrderList = {}         ##所有portfolio订单
        self.workingPortfolioOrderList = {}  ##活动的portfolio订单



        self.tradeCount = 0             # 成交编号
        self.tradeDict = OrderedDict()  # 成交字典

        self.logList = []               # 日志记录

        # 当前最新数据，用于模拟成交用
        self.tick = None
        self.bar = None
        self.dt = None      # 最新的时间

        self.FilePath = 'D:/data/'



    #------------------------------------------------
    # 通用功能
    #------------------------------------------------

    #----------------------------------------------------------------------
    def roundToPriceTick(self, price):
        """取整价格到合约最小价格变动"""
        if not self.priceTick:
            return price

        newPrice = round(price/self.priceTick, 0) * self.priceTick
        return newPrice

    #----------------------------------------------------------------------
    def output(self, content):
        """输出内容"""
        print str(self.dt) + "\t" + content

    #------------------------------------------------
    # 参数设置相关
    #------------------------------------------------

    #----------------------------------------------------------------------
    def setStartDate(self, startDate='20100416', initDays=10):
        """设置回测的启动日期"""
        self.startDate = startDate
        self.initDays = initDays

        self.dataStartDate = datetime.strptime(startDate, '%Y%m%d')

        #initTimeDelta = timedelta(initDays)
        #self.strategyStartDate = self.dataStartDate + initTimeDelta

    #----------------------------------------------------------------------
    def setEndDate(self, endDate=''):
        """设置回测的结束日期"""
        self.endDate = endDate

        if endDate:
            self.dataEndDate = datetime.strptime(endDate, '%Y%m%d')

            # 若不修改时间则会导致不包含dataEndDate当天数据
            self.dataEndDate = self.dataEndDate.replace(hour=23, minute=59)

    #----------------------------------------------------------------------
    def setBacktestingMode(self, mode):
        """设置回测模式"""
        self.mode = mode



    def setDataPath(self,path):
        self.FilePath = path

    #----------------------------------------------------------------------
    def setCapital(self, capital):
        """设置资本金"""
        self.capital = capital

    #----------------------------------------------------------------------
    def setSlippage(self, slippage):
        """设置滑点点数"""
        self.slippage = slippage

    #----------------------------------------------------------------------
    def setSize(self, size):
        """设置合约大小"""
        self.size = size

    #----------------------------------------------------------------------
    def setRate(self, rate):
        """设置佣金比例"""
        self.rate = rate

    #----------------------------------------------------------------------
    def setPriceTick(self, priceTick):
        """设置价格最小变动"""
        self.priceTick = priceTick

    def getContactValues(self, symbol):
        for key, value in self.contactInfo.items():
            if len(symbol) == value["length"] and symbol.startswith(value["pre"]):
                return value

        return None

    ### 获取合约最大volume
    def getSymbolVolume(self, symbol,price,stopPrice):
        ##判断资金使用率
        if self.accountManager.getAvailableRate() > self.capitalUseRat:
            return 0

        maxSymbolVol = self.getContactValues(symbol)["maxVolume"]


        maxRiskVol = int(self.accountManager.getAvailable()*self.riskRate/abs(price - stopPrice)/self.getContactValues(symbol)["volumeMultiple"])

        ##每次开最大    仓保证金为 权益资金的2层
        marginVolume = self.positionManager.getVolumeByMargin(   self.accountManager.getCapital()*0.2, price,symbol)
        marginVolume = int(marginVolume)

        return min(maxSymbolVol, maxRiskVol,marginVolume)

    def getSymbolPrePosition(self, symbol):
        return self.positionManager.preContactPosition(symbol)




    ## 文件行转对象
    def loadTickData(self, strLine):

        lineArray = strLine.split(",")
        tickData = VtTickData()
        tickData.symbol = lineArray[2]
        tickData.exchange = lineArray[3]
        tickData.vtSymbol = lineArray[4]

        tickData.lastPrice = float(lineArray[5])
        tickData.lastVolume = int(lineArray[6])
        tickData.volume = int(lineArray[7])
        tickData.openInterest = int(lineArray[8])
        tickData.time = lineArray[9]
        tickData.date = lineArray[10]
        tickData.datetime = datetime.strptime(' '.join([tickData.date, tickData.time]), '%Y%m%d %H:%M:%S.%f')

        tickData.openPrice = float(lineArray[12])
        tickData.highPrice = float(lineArray[13])
        tickData.lowPrice = float(lineArray[14])
        tickData.preClosePrice = float(lineArray[15])

        tickData.upperLimit = float(lineArray[16])
        tickData.lowerLimit = float(lineArray[17])

        tickData.bidPrice1 = float(lineArray[18])
        tickData.askPrice1 = float(lineArray[23])
        tickData.bidVolume1 = int(lineArray[28])
        tickData.askVolume1 = int(lineArray[33])



        return tickData

    def loadBarData(self,strLine):
        lineArray = strLine.split(",")
        barData = VtBarData()
        barData.vtSymbol = lineArray[0]
        barData.symbol = lineArray[1]
        barData.exchange = lineArray[2]
        barData.open = float(lineArray[3])
        barData.high = float(lineArray[4])
        barData.low = float(lineArray[5])
        barData.close = float(lineArray[6])
        barData.date = lineArray[7]
        barData.time = lineArray[8]
        barData.datetime =  datetime.strptime(lineArray[9], '%Y-%m-%d %H:%M:%S')
        barData.volume = int(lineArray[10])
        barData.openInterest = int(lineArray[11])

        return barData

    ##读取策略组合price的k线
    def loadPortfolioPriceData(self,name,strategyCycle):
        filePath = self.FilePath+'portfolio/'+name+".txt"

        return self.loadFileData(filePath, self.dataStartDate)

    def loadOptData(self,symbol, strategyCycle,days=None):
        fileName = "5min"
        if strategyCycle == "5min":
            fileName = "5min"
        elif strategyCycle == "6min":
            fileName = "6min"
        elif strategyCycle == "7min":
            fileName = "7min"
        elif strategyCycle == "8min":
            fileName = "8min"
        elif strategyCycle == "9min":
            fileName = "9min"
        elif strategyCycle == "3min":
            fileName = "3min"
        elif strategyCycle == "10min":
            fileName = "10min"
        elif strategyCycle == "15min":
            fileName = "15min"
        elif strategyCycle == "30min":
            fileName = "30min"
        elif strategyCycle == "60min":
            fileName = "60min"
        elif strategyCycle == "day":
            fileName = "day"
        else:
            return None

        return self.loadFileData(self.FilePath+fileName+"/"+symbol+".txt",self.curDate)


    ##读取日线文件到那天的数据
    def readDayFileData(self, dateTime,contract ):
        if not self.dayMainSymbolFile.has_key(contract):
            try:
                self.dayMainSymbolFile[contract] = open(self.FilePath+'day/'+contract+".txt", 'r')
            except :
                return None


        dateTimeStr = dateTime.strftime("%Y%m%d")

        while True:
            if not self.dayMainSymbolData.has_key(contract):
                line = self.dayMainSymbolFile[contract].readline()
                if line == '':
                    break
                self.dayMainSymbolData[contract] = self.loadBarData(line)
            if self.dayMainSymbolData[contract].date == dateTimeStr:
                return self.dayMainSymbolData[contract]

            if self.dayMainSymbolData[contract].date < dateTimeStr:
                line = self.dayMainSymbolFile[contract].readline()
                if line == '':
                    break
                self.dayMainSymbolData[contract] = self.loadBarData(line)
                continue
            if self.dayMainSymbolData[contract].date > dateTimeStr:
                return self.dayMainSymbolData[contract]  ## 如果出现某天没有数据，可以返回后一天的。

        return None


    #------------------------------------------------
    # 数据回放相关
    #------------------------------------------------
    def getProductContractList(self, startTime):
        """  合约前缀+当前日期后12个月  """
        number_0 = self.changeMainSymbol.count('0')
        listContract = []
        for i in range(11):
            time_aaa = startTime + pd.tseries.offsets.DateOffset(months=i,days=0)
            if number_0 == 3:
                listContract.append(self.changeMainSymbol[0:len(self.changeMainSymbol)-number_0] +str(time_aaa.year)[3:4]+str(time_aaa.month).zfill(2))
            if number_0 == 4:
                listContract.append(self.changeMainSymbol[0:len(self.changeMainSymbol)-number_0] +str(time_aaa.year)[2:4]+str(time_aaa.month).zfill(2))

        return listContract

    ## 判断主力合约
    def getMainContact(self, dateTime , listContract):
        mianSymbol = None
        volume = 0
        for contract in listContract:
            #print contract
             #加载日线file
            kData = self.readDayFileData(dateTime,contract)
            if  kData and kData.volume > volume:
                mianSymbol = kData.symbol
                volume = kData.volume

        return mianSymbol

    #----------------------------------------------------------------------
    def changeMainContact(self, date):
        """"""
        listContract = self.getProductContractList(date)

        mainSymbol = self.getMainContact(date, listContract)

        if not mainSymbol:
            return None             ### 没有读取到合约数据，可能是休息日

        if cmp(self.mainSymbol , mainSymbol) < 0:
            self.secSymbol = self.mainSymbol
            self.mainSymbol = mainSymbol

            if self.secSymbol != '' and self.strategy.has_key(self.secSymbol):
                #self.strategy[self.secSymbol].setIsMainSymbol(False)

                ##次主力合约不处理，跟趋势策略不一样
                del self.strategy[self.secSymbol]
                self.secSymbol = ''


        return self.mainSymbol

    #----------------------------------------------------------------------
    def runBacktesting(self):
        """运行回测"""


        self.curDate = self.dataStartDate
        isExit = self.changeMainContact(self.dataStartDate)
        while not isExit:
            self.curDate = self.curDate +  timedelta(1)
            isExit = self.changeMainContact(self.curDate)

        #self.loadHistoryData()

        # 首先根据回测模式，确认要使用的数据类
        if self.mode == self.BAR_MODE:
            dataClass = VtBarData
            func = self.newBar
        else:
            dataClass = VtTickData
            func = self.newTick

        self.output(u'开始回测')


        while True:
            ##### 1天1个循环
            print( u"======开始新的一天=="+self.mainSymbol+"==="+self.curDate.strftime("%Y-%m-%d  %H:%M:%S") )

            #开始获取主力合约
            if not self.strategy.has_key(self.mainSymbol):
                print(u'切换合约==='+self.mainSymbol+self.curDate.strftime("%Y%m%d"))
                ##初始化组合

                spread = self.initPortfolio(self.mainSymbol)

                s = {"name":spread.symbol,"strategyCycle":self.setting["strategyCycle"]}
                ##初始化算法
                stra = self.strategyClass(self,spread,s)
                stra.setMode(self.mode)

                stra.onInit()
                stra.inited = True
                self.output(u'策略初始化完成')

                stra.trading = True
                stra.onStart()
                self.output(u'策略启动完成')

                self.algoList[stra.name] = stra
                self.strategy[self.mainSymbol] = stra

                for symbol in spread.allLegs:
                    self.seekFileToDate(symbol,"tick/",self.curDate)


            #for strategy in self.algoList.values():
            #    lower, upper = self.getUpperLower(strategy.protforlio.symbol)
            #    strategy.frencyUpper = upper
            #    strategy.frencyLower = lower

            #    print "frency:"+str(lower) + str(upper)


            ##回放数据 1天
            while True:
                ##### 1天1个循环

                ##取最大时间的合约tick
                #self.symbolData.sort()
                #tickData = self.symbolData[0]
                #elf.symbolData.remove(tickData)


                #for key,value in tickData.items():
                #    tickData = value

                keys = self.symbolData.keys()
                keys.sort()

                tickData = self.symbolData[keys[0]]
                del self.symbolData[keys[0]]

                self.readFileLine(tickData.vtSymbol)


                #self.output(tickData.symbol+str(tickData.datetime))
                func(tickData)

                if tickData.datetime > self.curDate:
                    #新的一天，
                    break



            if self.curDate > self.dataEndDate:
                self.output(u'数据回放结束')
                break

            isExit = None
            while not isExit:
                self.curDate = self.curDate +  timedelta(1)

                isExit = self.changeMainContact(self.curDate)






    def initPortfolio(self,activeSymbol):

        spread = StSpread()
        spread.name = self.portfolioInfo["name"]


        contract = VtContractData()
        contract.symbol = activeSymbol
        contract.exchange = ""
        contract.vtSymbol =activeSymbol
        contract.size = self.size
        contract.priceTick = self.priceTick
        contract.gatewayName = "CTP"

        activeLeg = StLeg(contract)
        activeLeg.ratio =  self.portfolioInfo["activeLeg"]["ratio"]
        activeLeg.multiplier = self.portfolioInfo["activeLeg"]["multiplier"]
        activeLeg.payup  =  self.portfolioInfo["activeLeg"]["payup"]
        spread.addActiveLeg(activeLeg)


        for passiveLegInfo in self.portfolioInfo["passiveLegs"]:

            passiveLegSymbol = passiveLegInfo["vtSymbol"]+activeSymbol[2:]

            contract = VtContractData()
            contract.symbol = passiveLegSymbol
            contract.exchange = ""
            contract.vtSymbol =passiveLegSymbol
            contract.size = self.size
            contract.priceTick = self.priceTick
            contract.gatewayName = "CTP"

            passiveLeg = StLeg(contract)
            passiveLeg.ratio =  passiveLegInfo["ratio"]
            passiveLeg.multiplier = passiveLegInfo["multiplier"]
            passiveLeg.payup  =  passiveLegInfo["payup"]
            spread.addPassiveLeg(passiveLeg)

        spread.initSpread()

        self.portfolioList[spread.symbol] = spread

        return spread


    def loadOptBar_tick(self, fileHandle, dateTimePreStr,dateTimeLastStr, seekStart, seedEnd):
        ##用seek，到curDate前面差不多位置
        #fsize = os.path.getsize(optFilePath)

        seekMiddle = (seekStart + seedEnd)/2

        fileHandle.seek(seekMiddle)
        fileHandle.readline()
        line = fileHandle.readline()

        #print line
        data_tick = self.loadTickData(line)

        if data_tick.date >= dateTimePreStr and data_tick.date <=  dateTimeLastStr:
            return

        if data_tick.date > dateTimeLastStr:
            self.loadOptBar_tick(fileHandle, dateTimePreStr,dateTimeLastStr, seekStart, seekMiddle)
        elif data_tick.date < dateTimePreStr:
            self.loadOptBar_tick(fileHandle, dateTimePreStr, dateTimeLastStr,seekMiddle, seedEnd)


        if seekStart == seedEnd:
            return


    ##加载操作周期bar
    def seekFileToDate(self, symbol,optFilePath,  curDate):

        dateTimeStr = curDate.strftime("%Y%m%d")

        isEnd = False
        if not self.symbolFile.has_key(symbol):
            self.symbolFile[symbol] = open(self.FilePath+optFilePath+symbol+".txt", 'r')
            ##第一次seek到当天的位置

            if self.mode == self.TICK_MODE:
                ##先seek到那一天前
                fsize = os.path.getsize(self.FilePath+optFilePath+symbol+".txt")

                dateTimePreStr = (curDate-timedelta(7)).strftime("%Y%m%d")
                dateTimeLastStr = (curDate - timedelta(1)).strftime("%Y%m%d")
                #print dateTimePreStr

                self.loadOptBar_tick(self.symbolFile[symbol],dateTimePreStr,dateTimeLastStr,0,fsize)


            while True:
                line = self.symbolFile[symbol].readline()
                if line == '':
                    isEnd = True
                    break

                if self.mode == self.BAR_MODE:
                    symbolData_t = self.loadBarData(line)
                else:
                   symbolData_t = self.loadTickData(line)

                if symbolData_t.date == dateTimeStr or symbolData_t.date > dateTimeStr:

                    ##读到了
                    #self.symbolData.append({str(symbolData_t.datetime)+symbol: symbolData_t})
                    self.symbolData[symbolData_t.date + symbolData_t.time + symbol] = symbolData_t

                    break;

        return isEnd


    def readFileLine(self, symbol):
        isEnd = False
        line = self.symbolFile[symbol].readline()
        if line == '':
            isEnd = True

        if self.mode == self.BAR_MODE:
            symbolData_t = self.loadBarData(line)
        else:
           symbolData_t = self.loadTickData(line)

        #self.symbolData.append({str(symbolData_t.datetime)+symbol: symbolData_t})
        self.symbolData[symbolData_t.date + symbolData_t.time +symbol] = symbolData_t

        return isEnd







    #----------------------------------------------------------------------
    def newBar(self, bar):
        """新的K线"""
        self.bar = bar
        self.currentSymbol = bar.symbol
        self.dt = bar.datetime
        self.positionManager.updateBarPrice(bar)


        self.crossStopOrder()       # 再撮合停止单

        for portfolio in  self.portfolioList.values():
            portfolio.newTick(bar)

            if self.portfolioCurTimeList.has_key(bar.vtSymbol):
                if portfolio.datetime > self.portfolioCurTimeList[bar.vtSymbol]:
                    ##组合新的时间，计算组合，并推送
                    lastPrice = portfolio.calculateLastPrice()

                    portfolioTick = VtTickData()
                    portfolioTick.datetime = bar.datatime
                    portfolioTick.lastPrice = lastPrice

                    self.algoList[portfolio.name].updateSpreadTick(portfolioTick)


                    self.portfolioCurTimeList[bar.vtSymbol] =  portfolio.datetime
            else:
                self.portfolioCurTimeList[bar.vtSymbol] =  portfolio.datetime


        self.crossLimitOrder()      # 先撮合限价单   bar来信号在当前bar成交  sar趋势跟一般的趋势策略有区别

        self.updateDailyClose(bar.datetime, bar.close)

    #----------------------------------------------------------------------
    def newTick(self, tick):
        """新的Tick"""
        self.tick = tick
        self.currentSymbol = tick.symbol
        self.dt = tick.datetime
        #print  str(self.dt) + str(tick.symbol)
        self.positionManager.updateTickPrice(tick)

        self.crossStopOrder()
        self.crossLimitOrder()


        for portfolio in  self.portfolioList.values():

            if self.portfolioCurTimeList.has_key(portfolio.symbol):

                portfolio.newTick(tick)

                #and portfolio.datetime < tick.datetime
                if portfolio.datetime  \
                        and portfolio.tickInited == True:

                    ##组合新的时间，计算组合，并推送
                    lastPrice = portfolio.calculateLastPrice()

                    portfolioTick = VtTickData()
                    portfolioTick.datetime = tick.datetime
                    portfolioTick.lastPrice = lastPrice
                    portfolioTick.askPrice1 = portfolio.calculateClosePrice()
                    portfolioTick.bidPrice1 = portfolioTick.askPrice1

                    self.algoList[portfolio.symbol].updatePortfolioTick(portfolioTick)



            if self.currentSymbol in portfolio.allLegs.keys():
                self.portfolioCurTimeList[portfolio.symbol] =  portfolio.datetime


        #self.updateDailyClose(tick.datetime, tick.lastPrice)

    #----------------------------------------------------------------------
    def initStrategy(self, strategyClass, setting=None):
        """
        初始化策略
        setting是策略的参数设置，如果使用类中写好的默认设置则可以不传该参数
        """
        self.strategyClass = strategyClass

        self.riskRate      = setting["riskRate"]
        self.capitalUseRat = setting["capitalUseRat"]
        self.commission    = setting["commission"]

        self.positionManager = PositionManager(setting["contactInfo"])
        self.accountManager = AccountManager(self.positionManager, setting["capital"])

        self.positionManager.setRate(self.rate)

        self.contactInfo = setting["contactInfo"]
        self.portfolioInfo = setting["spread"]
        self.setting = setting


    #----------------------------------------------------------------------
    def crossLimitOrder(self):
        """基于最新数据撮合限价单"""
        # 先确定会撮合成交的价格
        if self.mode == self.BAR_MODE:
            buyCrossPrice = self.bar.low        # 若买入方向限价单价格高于该价格，则会成交
            sellCrossPrice = self.bar.high      # 若卖出方向限价单价格低于该价格，则会成交
            buyBestCrossPrice = self.bar.open   # 在当前时间点前发出的买入委托可能的最优成交价
            sellBestCrossPrice = self.bar.open  # 在当前时间点前发出的卖出委托可能的最优成交价
        else:
            buyCrossPrice = self.tick.askPrice1
            sellCrossPrice = self.tick.bidPrice1
            buyBestCrossPrice = self.tick.askPrice1
            sellBestCrossPrice = self.tick.bidPrice1


        jumpPrice = self.getContactValues(self.currentSymbol)["priceTick"]*self.slippage

        # 遍历限价单字典中的所有限价单
        for orderID, order in self.workingLimitOrderDict.items():
            # 推送委托进入队列（未成交）的状态更新

            portfolioID = self.workingOrderToPortfolio[orderID]

            if not self.workingPortfolioOrderList.has_key(portfolioID):
                self.output("cross   orderId:"+str(orderID))


            strategy = self.algoList[self.workingPortfolioOrderList[portfolioID].symbol]

            option = self.workingPortfolioOrderList[portfolioID].allLegs[self.currentSymbol]


            if order.vtSymbol != self.currentSymbol:
                continue

            if not order.status:
                order.status = STATUS_NOTTRADED
                strategy.onOrder(order)

            # 判断是否会成交
            buyCross = (order.direction==DIRECTION_LONG and
                        order.price>=buyCrossPrice and
                        buyCrossPrice > 0)      # 国内的tick行情在涨停时askPrice1为0，此时买无法成交

            sellCross = (order.direction==DIRECTION_SHORT and
                         order.price<=sellCrossPrice and
                         sellCrossPrice > 0)    # 国内的tick行情在跌停时bidPrice1为0，此时卖无法成交

            # 如果发生了成交
            if buyCross or sellCross:



                # 推送成交数据
                self.tradeCount += 1            # 成交编号自增1
                tradeID = str(self.tradeCount)
                trade = VtTradeData()
                trade.vtSymbol = order.vtSymbol
                trade.tradeID = tradeID
                trade.vtTradeID = tradeID
                trade.orderID = order.orderID
                trade.vtOrderID = order.orderID
                trade.direction = order.direction
                trade.offset = order.offset



                # 以买入为例：
                # 1. 假设当根K线的OHLC分别为：100, 125, 90, 110
                # 2. 假设在上一根K线结束(也是当前K线开始)的时刻，策略发出的委托为限价105
                # 3. 则在实际中的成交价会是100而不是105，因为委托发出时市场的最优价格是100
                if buyCross:
                    trade.price = min(order.price, buyBestCrossPrice)  #bar  order.price
                    #self.strategy[self.currentSymbol].pos += order.totalVolume

                    trade.price += jumpPrice
                else:
                    trade.price = max(order.price, sellBestCrossPrice) #bar  order.price
                    #self.strategy[self.currentSymbol].pos -= order.totalVolume

                    trade.price -= jumpPrice

                option.tradeVolume = order.totalVolume
                option.tradePrice = trade.price


                trade.volume = order.totalVolume
                trade.tradeTime = self.dt.strftime('%H:%M:%S')
                trade.dt = self.dt
                strategy.onTrade(trade)

                self.tradeDict[tradeID] = trade

                self.accountManager.updatePositionByTrade(trade)
                trade.profit = self.accountManager.getCapital()
                trade.margin = self.accountManager.getMargin()

                trade.symbol =  self.tick.symbol

                # 推送委托数据
                order.tradedVolume = order.totalVolume
                order.status = STATUS_ALLTRADED
                strategy.onOrder(order)

                # 从字典中删除该限价单
                del self.workingLimitOrderDict[orderID]
                del self.workingOrderToPortfolio[orderID]

                self.output("cross del  orderId:"+str(orderID))

                ##看期权组合是否全部成交
                self.checkPortfolioTrade(self.workingPortfolioOrderList[portfolioID],strategy)

    ##检查开平是否结束，结束做相应的操作
    def checkPortfolioTrade(self,portfolio,strategy):
        isEnd = True
        for option in  portfolio.allLegs.values():
            if option.tradeVolume != 1:
                isEnd = False

        if isEnd == True:
            if portfolio.status == POSITION_OPENING:
                ##计算open利润
                portfolio.portfolioOpenPrice = portfolio.calculateTradePrice()

                portfolio.status = POSITION_OPEN
                portfolio.clearOptionTrade()  ##情况成交，为close做准备


            if portfolio.status == POSITION_CLOSING:
                portfolio.status = POSITION_CLOSE
                portfolio.portfolioClosePrice = portfolio.calculateTradePrice()

                del self.workingPortfolioOrderList[portfolio.portfolioOrderId]
                del strategy.protforlioPosList[portfolio.portfolioOrderId]

    #----------------------------------------------------------------------
    def crossStopOrder(self):
        """基于最新数据撮合停止单"""
        # 先确定会撮合成交的价格，这里和限价单规则相反
        if self.mode == self.BAR_MODE:
            buyCrossPrice = self.bar.high    # 若买入方向停止单价格低于该价格，则会成交
            sellCrossPrice = self.bar.low    # 若卖出方向限价单价格高于该价格，则会成交
            bestCrossPrice = self.bar.open   # 最优成交价，买入停止单不能低于，卖出停止单不能高于
        else:
            buyCrossPrice = self.tick.lastPrice
            sellCrossPrice = self.tick.lastPrice
            bestCrossPrice = self.tick.lastPrice


        #jumpPrice = 5*1 #self.volumeMultiple * self.priceTick  ##目前下单是直接下，只有平仓下的是停止单，平仓加滑点
        jumpPrice = self.getContactValues(self.currentSymbol)["priceTick"]*self.slippage


        # 遍历停止单字典中的所有停止单
        for stopOrderID, so in self.workingStopOrderDict.items():



            if so.vtSymbol != self.currentSymbol:
                continue

            # 判断是否会成交
            buyCross = so.direction==DIRECTION_LONG and so.price<=buyCrossPrice
            sellCross = so.direction==DIRECTION_SHORT and so.price>=sellCrossPrice

            # 如果发生了成交
            if buyCross or sellCross:

                if self.bar.date == "20150611":
                    aaa =3


                # 更新停止单状态，并从字典中删除该停止单
                so.status = STOPORDER_TRIGGERED
                if stopOrderID in self.workingStopOrderDict:
                    del self.workingStopOrderDict[stopOrderID]

                # 推送成交数据
                self.tradeCount += 1            # 成交编号自增1
                tradeID = str(self.tradeCount)
                trade = VtTradeData()
                trade.vtSymbol = so.vtSymbol
                trade.tradeID = tradeID
                trade.vtTradeID = tradeID

                if so.offset == OFFSET_CLOSE and so.direction == DIRECTION_LONG :
                    ## 如果是平仓
                    if (self.strategy[self.currentSymbol].pos + so.volume) > 0:
                        ## 多 平仓 大于0，有问题
                        return

                if so.offset == OFFSET_CLOSE and so.direction == DIRECTION_SHORT :
                    ## 如果是平仓
                    if (self.strategy[self.currentSymbol].pos - so.volume) < 0:
                        ## 多 平仓 大于0，有问题
                        return


                if buyCross:
                    self.strategy[self.currentSymbol].pos += so.volume
                    trade.price = so.price +jumpPrice #max(bestCrossPrice, so.price)
                else:
                    self.strategy[self.currentSymbol].pos -= so.volume
                    trade.price = so.price - jumpPrice #min(bestCrossPrice, so.price)




                self.limitOrderCount += 1
                orderID = str(self.limitOrderCount)
                trade.orderID = orderID
                trade.vtOrderID = orderID
                trade.direction = so.direction
                trade.offset = so.offset
                trade.volume = so.volume
                trade.tradeTime = self.dt.strftime('%H:%M:%S')
                trade.dt = self.dt

                self.tradeDict[tradeID] = trade
                self.accountManager.updatePositionByTrade(trade)
                trade.profit = self.accountManager.getCapital()
                trade.margin = self.accountManager.getMargin()
                trade.symbol = self.symbol

                # 推送委托数据
                order = VtOrderData()
                order.vtSymbol = so.vtSymbol
                order.symbol = so.vtSymbol
                order.orderID = orderID
                order.vtOrderID = orderID
                order.direction = so.direction
                order.offset = so.offset
                order.price = so.price
                order.totalVolume = so.volume
                order.tradedVolume = so.volume
                order.status = STATUS_ALLTRADED
                order.orderTime = trade.tradeTime

                self.limitOrderDict[orderID] = order

                # 按照顺序推送数据
                self.strategy[self.currentSymbol].onStopOrder(so)
                self.strategy[self.currentSymbol].onOrder(order)
                self.strategy[self.currentSymbol].onTrade(trade)


    ##组合开仓
    def protforlioOpen(self,strategy, direction):

        protforlio = copy.deepcopy(strategy.protforlio)
        protforlio.portfolioOrderId = str(datetime.now())+str(random.randint(1,100))+strategy.protforlio.symbol
        protforlio.direction = direction
        protforlio.status = POSITION_OPENING

        self.writeCtaLog(" protforlioOpen " + direction)

        strategy.protforlioPosList[protforlio.portfolioOrderId] = protforlio

        self.portfolioOrderList[protforlio.portfolioOrderId] = protforlio
        self.workingPortfolioOrderList[protforlio.portfolioOrderId] = protforlio

        ##所有合约下单
        for leg in protforlio.allLegs.values():
            ##市价下单
            #if leg.lowerLimit == 0.0:
            leg.lowerLimit = 0.000001
            #if leg.upperLimit == 0.0:
            leg.upperLimit = 9999.0

            if (leg.multiplier < 0 and protforlio.direction == DIRECTION_LONG) or \
                 (leg.multiplier > 0 and protforlio.direction == DIRECTION_SHORT):
                orderId = self.sendOrder(leg.vtSymbol,CTAORDER_SHORT, leg.lowerLimit, 1  ,strategy)
            else:
                orderId = self.sendOrder(leg.vtSymbol,CTAORDER_BUY, leg.upperLimit, 1  ,strategy)

            self.workingOrderToPortfolio[orderId[0]] = protforlio.portfolioOrderId

            self.writeOptionLog("getavalal:"+ str(self.accountManager.getCapital()) + " avalil:"+str(self.accountManager.getAvailable()))
            self.output("open  orderId:"+str(orderId)+"  portfolioOrderId:"+protforlio.portfolioOrderId)


    def protforlioCloseOne(self,strategy, protforlio):

            if protforlio.status != POSITION_OPEN:
                return

            closePrice = strategy.protforlio.calculateClosePrice()

            #if protforlio.direction == DIRECTION_LONG:
            #    prof = closePrice - protforlio.portfolioOpenPrice
            #else:
            #    prof = protforlio.portfolioOpenPrice - closePrice

            #if prof  > strategy.commission or \
            #        prof < -30:  ##达到-30平仓
                ##不亏就平仓
                ##所有合约下单

            self.output(u"平仓：openPrice："+str(protforlio.portfolioOpenPrice)+" close:"+str(closePrice))

            protforlio.status = POSITION_CLOSING
            for leg in protforlio.allLegs.values():
                ##市价下单
                #if leg.lowerLimit == 0.0:
                leg.lowerLimit = 0.000001
                #if leg.upperLimit == 0.0:
                leg.upperLimit = 9999.0

                if (leg.multiplier < 0 and protforlio.direction == DIRECTION_LONG) or \
                       (leg.multiplier > 0 and protforlio.direction == DIRECTION_SHORT)  :
                    orderId = self.sendOrder(leg.vtSymbol,CTAORDER_COVER, leg.upperLimit, 1  ,strategy)
                else:
                    orderId = self.sendOrder(leg.vtSymbol,CTAORDER_SELL, leg.lowerLimit, 1  ,strategy)

                self.workingOrderToPortfolio[orderId[0]] = protforlio.portfolioOrderId

                self.output("close  orderId:"+str(orderId)+"  portfolioOrderId:"+protforlio.portfolioOrderId)



    #组合平仓
    def protforlioClose(self,strategy):

        for protforlio in strategy.protforlioPosList.values():

            if protforlio.status != POSITION_OPEN:
                continue

            closePrice = strategy.protforlio.calculateClosePrice()

            if protforlio.direction == DIRECTION_LONG:
                prof = closePrice - protforlio.portfolioOpenPrice
            else:
                prof = protforlio.portfolioOpenPrice - closePrice

            if prof  > strategy.commission or \
                    prof < -30:  ##达到-30平仓
                ##不亏就平仓
                ##所有合约下单

                self.output(u"平仓：openPrice："+str(protforlio.portfolioOpenPrice)+" close:"+str(closePrice))

                protforlio.status = POSITION_CLOSING
                for leg in protforlio.allLegs.values():
                    ##市价下单
                    #if leg.lowerLimit == 0.0:
                    leg.lowerLimit = 0.000001
                    #if leg.upperLimit == 0.0:
                    leg.upperLimit = 9999.0

                    if (leg.multiplier < 0 and protforlio.direction == DIRECTION_LONG) or \
                           (leg.multiplier > 0 and protforlio.direction == DIRECTION_SHORT)  :
                        orderId = self.sendOrder(leg.vtSymbol,CTAORDER_COVER, leg.upperLimit, 1  ,strategy)
                    else:
                        orderId = self.sendOrder(leg.vtSymbol,CTAORDER_SELL, leg.lowerLimit, 1  ,strategy)

                    self.workingOrderToPortfolio[orderId[0]] = protforlio.portfolioOrderId

                    self.output("close  orderId:"+str(orderId)+"  portfolioOrderId:"+protforlio.portfolioOrderId)

    #------------------------------------------------
    # 策略接口相关
    #------------------------------------------------

    #----------------------------------------------------------------------
    def sendOrder(self, vtSymbol, orderType, price, volume, strategy):

        """发单"""
        self.limitOrderCount += 1
        orderID = str(self.limitOrderCount)

        order = VtOrderData()
        order.vtSymbol = vtSymbol
        order.price = self.roundToPriceTick(price)
        order.totalVolume = volume
        order.orderID = orderID
        order.vtOrderID = orderID
        order.orderTime = self.dt.strftime('%H:%M:%S')

        # CTA委托类型映射
        if orderType == CTAORDER_BUY:
            order.direction = DIRECTION_LONG
            order.offset = OFFSET_OPEN
        elif orderType == CTAORDER_SELL:
            order.direction = DIRECTION_SHORT
            order.offset = OFFSET_CLOSE
        elif orderType == CTAORDER_SHORT:
            order.direction = DIRECTION_SHORT
            order.offset = OFFSET_OPEN
        elif orderType == CTAORDER_COVER:
            order.direction = DIRECTION_LONG
            order.offset = OFFSET_CLOSE

        # 保存到限价单字典中
        self.workingLimitOrderDict[orderID] = order
        self.limitOrderDict[orderID] = order

        return [orderID]

    #----------------------------------------------------------------------
    def cancelOrder(self, vtOrderID):
        """撤单"""
        if vtOrderID in self.workingLimitOrderDict:
            order = self.workingLimitOrderDict[vtOrderID]

            order.status = STATUS_CANCELLED
            order.cancelTime = self.dt.strftime('%H:%M:%S')

            self.strategy[self.currentSymbol].onOrder(order)

            del self.workingLimitOrderDict[vtOrderID]

    #----------------------------------------------------------------------
    def sendStopOrder(self, vtSymbol, orderType, price, volume, strategy):



        """发停止单（本地实现）"""
        self.stopOrderCount += 1
        stopOrderID = STOPORDERPREFIX + str(self.stopOrderCount)

        so = StopOrder()
        so.vtSymbol = vtSymbol
        so.price = self.roundToPriceTick(price)
        so.volume = volume
        so.strategy = strategy
        so.status = STOPORDER_WAITING
        so.stopOrderID = stopOrderID

        if orderType == CTAORDER_BUY:
            so.direction = DIRECTION_LONG
            so.offset = OFFSET_OPEN
        elif orderType == CTAORDER_SELL:
            so.direction = DIRECTION_SHORT
            so.offset = OFFSET_CLOSE
        elif orderType == CTAORDER_SHORT:
            so.direction = DIRECTION_SHORT
            so.offset = OFFSET_OPEN
        elif orderType == CTAORDER_COVER:
            so.direction = DIRECTION_LONG
            so.offset = OFFSET_CLOSE

        # 保存stopOrder对象到字典中
        self.stopOrderDict[stopOrderID] = so
        self.workingStopOrderDict[stopOrderID] = so

        # 推送停止单初始更新
        if self.mode == self.BAR_MODE:
            self.strategy[self.bar.symbol].onStopOrder(so)
        else:
            self.strategy[self.tick.symbol].onStopOrder(so)



        return [stopOrderID]

    #----------------------------------------------------------------------
    def cancelStopOrder(self, stopOrderID):
        """撤销停止单"""
        # 检查停止单是否存在
        if stopOrderID in self.workingStopOrderDict:
            so = self.workingStopOrderDict[stopOrderID]
            so.status = STOPORDER_CANCELLED
            del self.workingStopOrderDict[stopOrderID]
            if self.mode == self.BAR_MODE:
                self.strategy[self.bar.symbol].onStopOrder(so)
            else:
                self.strategy[self.tick.symbol].onStopOrder(so)

    #----------------------------------------------------------------------
    def putStrategyEvent(self, name):
        """发送策略更新事件，回测中忽略"""
        pass

    #----------------------------------------------------------------------
    def insertData(self, dbName, collectionName, data):
        """考虑到回测中不允许向数据库插入数据，防止实盘交易中的一些代码出错"""
        pass

    #----------------------------------------------------------------------
    def loadBar(self, dbName, collectionName, startDate):
        """直接返回初始化数据列表中的Bar"""
        return self.initData

    def loadFileData(self,filePath,curData):

        file_day = open(filePath, 'r')
        lineNum  = 0
        curNum   = 0

        initData = []

        while True:  ##获取一共多少行
            line = file_day.readline()
            if line == '':
                break
            lineTime =  datetime.strptime(line.split(",")[9], '%Y-%m-%d %H:%M:%S')

            if lineTime > curData:
                break;

            curNum += 1

        lineNum = curNum-1  ##读取到当前时间的前一条记录
        curNum = 0
        file_day.seek(0, 0)

        while True :  ###取前100行
            curNum += 1
            line = file_day.readline()
            if line == '':
                break
            if curNum > lineNum:
                break;

            initData.append(self.loadBarData(line))

        file_day.close()


        return initData


    def loadDayData(self,symbol,curData):
        return self.loadFileData(self.FilePath+'day/'+symbol+".txt",curData)

    def loadWeekData(self,symbol,curData):
        return self.loadFileData(self.FilePath+'week/'+self.symbol+".txt",curData)

    def loadHalfHourData(self, symbol, curData):
        return self.loadFileData(self.FilePath+'30min/'+symbol+".txt",curData)

    def loadHourData(self, symbol, curData):
        return self.loadFileData(self.FilePath+'60min/'+symbol+".txt",curData)


    #----------------------------------------------------------------------
    def loadTick(self, dbName, collectionName, startDate):
        """直接返回初始化数据列表中的Tick"""
        return self.initData

    #----------------------------------------------------------------------
    def writeCtaLog(self, content):
        """记录日志"""
        log = str(self.dt) + ' ' + content
        self.logList.append(log)

        print  log

    def writeOptionLog(self,content):
        """记录日志"""
        log = str(self.dt) + ' ' + content
        self.logList.append(log)

        print  log

        #----------------------------------------------------------------------
    def cancelAllStop(self, vsymbol):
        """全部撤单"""

        # 撤销停止单
        for stopOrderID in self.workingStopOrderDict.keys():
            so = self.workingStopOrderDict[stopOrderID]
            if so.vtSymbol == vsymbol:
                self.cancelStopOrder(stopOrderID)


    def cancleAllLimit(self,day):
        for orderID in self.workingLimitOrderDict.keys():
            order = self.workingLimitOrderDict[orderID]
            print("day start cancle limit %s  %s  %s %s"%(day,order.vtSymbol,order.price,order.orderTime))
            self.cancelOrder(orderID)

    #----------------------------------------------------------------------
    def cancelAll(self, name):
        """全部撤单"""
        # 撤销限价单
        for orderID in self.workingLimitOrderDict.keys():
            self.cancelOrder(orderID)

        # 撤销停止单
        for stopOrderID in self.workingStopOrderDict.keys():
            self.cancelStopOrder(stopOrderID)


    ##更加频率分布计算上下限
    def getUpperLower(self,name):

        price_tick = pd.read_csv(self.FilePath+'portfolio/'+name+"_tick.txt",index_col =0,header = None)
        price_tick = price_tick.dropna()
        price_tick = price_tick.set_index(pd.DatetimeIndex(pd.to_datetime(price_tick.index)))

        startData = self.curDate -  timedelta(5)
        price_tick = price_tick[(price_tick.index >= startData) & (price_tick.index <= self.curDate )]

        price_tick.sort_values(by=[1],ascending=0,inplace=True)

        data_index = price_tick.reset_index(drop=True)

        len = data_index.count()

        upper = data_index[1][int(len*0.2)]
        lower = data_index[1][int(len*0.8)]

        return lower, upper



    #------------------------------------------------
    # 交易写入文件
    #------------------------------------------------
    def protforlioToFile(self):
        tradePath = getTempPath("protforlio.csv")
        if os.path.exists(tradePath):
            os.remove(tradePath)

        import csv
        import codecs


        fieldnames = ['name','status', 'direction', 'portfolioOrderId', 'portfolioClosePrice', 'symbol', 'datetime', 'portfolioOpenPrice']



        trade_file = open(tradePath, 'wb+')
        trade_file.write(codecs.BOM_UTF8)
        dict_writer = csv.DictWriter(trade_file, fieldnames=fieldnames)
        dict_writer.writeheader()
        for trade in self.portfolioOrderList.values():

            dict = {}
            dict["status"] = trade.status
            dict["direction"] = trade.direction
            dict["name"] = trade.name
            dict["portfolioOrderId"] = trade.portfolioOrderId
            dict["portfolioClosePrice"] = trade.portfolioClosePrice
            dict["symbol"] = trade.symbol
            dict["datetime"] = trade.datetime
            dict["portfolioOpenPrice"] = trade.portfolioOpenPrice


            dict_writer.writerow(dict)  # rows就是表单提交的数据
        trade_file.close()



    #------------------------------------------------
    # 交易写入文件
    #------------------------------------------------
    def tradeToFile(self):
        tradePath = getTempPath("trade.csv")
        if os.path.exists(tradePath):
            os.remove(tradePath)

        import csv
        import codecs


        fieldnames = ['dt','symbol', 'exchange', 'vtSymbol', 'tradeID', 'vtTradeID', 'orderID', 'vtOrderID',
                      'direction','offset','price','volume','tradeTime',"gatewayName","rawData","profit","margin"]



        trade_file = open(tradePath, 'wb+')
        trade_file.write(codecs.BOM_UTF8)
        dict_writer = csv.DictWriter(trade_file, fieldnames=fieldnames)
        dict_writer.writeheader()
        for trade in self.tradeDict.values():

            dicta = trade.__dict__
            j = json.dumps(dicta, cls=CJsonEncoder)
            dict2 = j.decode("unicode-escape")
            dict3 = json.loads(dict2)

            dict_writer.writerow(dict3)  # rows就是表单提交的数据
        trade_file.close()


    ##获取合约最后一次下单
    def getSymbolLastTrade(self, symbol):
        lastTrade = None
        for trade in self.tradeDict.values():
            if trade.vtSymbol == symbol:
                lastTrade = trade

        return lastTrade


    def calculateBortfolioResult(self):
        """
        计算回测结果
        """
        self.output(u'计算回测结果')

        # 首先基于回测后的成交记录，计算每笔交易的盈亏
        resultList = []             # 交易结果列表

        longTradeList = {}        # 合约对应的longtrade
        shortTradeList = {}

        longTrade = []              # 未平仓的多头交易
        shortTrade = []             # 未平仓的空头交易

        tradeTimeList = []          # 每笔成交时间戳
        posList = [0]               # 每笔成交后的持仓情况


        for portfolio in self.portfolioOrderList.values():
            for k,v in portfolio.__dict__.items():
                if  isinstance(v, basestring) or isinstance(v, int) or isinstance(v, float) or isinstance(v, datetime):
                    print k,v,
            print ''

        for trade in self.tradeDict.values():
            for k,v in trade.__dict__.items():
                print k,v,
            print ''

        self.protforlioToFile()
        self.tradeToFile()


        # 然后基于每笔交易的结果，我们可以计算具体的盈亏曲线和最大回撤等
        capital = self.capital           # 资金
        maxCapital = 0          # 资金最高净值
        drawdown = 0            # 回撤
        maxDrawDownRat = 0.0      #最大回测率

        totalResult = 0         # 总成交数量
        totalTurnover = 0       # 总成交金额（合约面值）
        totalCommission = 0     # 总手续费
        totalSlippage = 0       # 总滑点

        timeList = []           # 时间序列
        pnlList = []            # 每笔盈亏序列
        capitalList = []        # 盈亏汇总的时间序列
        drawdownList = []       # 回撤的时间序列
        drawdownRateList = []   # 回撤率的时间序列

        winningResult = 0       # 盈利次数
        losingResult = 0        # 亏损次数
        totalWinning = 0        # 总盈利金额
        totalLosing = 0         # 总亏损金额


        keys = self.portfolioOrderList.keys()
        keys.sort()

        for key in keys:
            portfolio = self.portfolioOrderList[key]

            if portfolio.direction == DIRECTION_LONG:
                pnl = portfolio.portfolioClosePrice - portfolio.portfolioOpenPrice

            elif portfolio.direction == DIRECTION_SHORT:
                pnl = portfolio.portfolioOpenPrice - portfolio.portfolioClosePrice

            pnl = pnl * 10

            commission = 14  ##3500*10*2*0.0001

            pnl -= commission

            capital += pnl
            maxCapital = max(capital, maxCapital)
            drawdown = capital - maxCapital

            if drawdown != 0 and maxCapital > 0: #有策略 计算回测率
                drawdownRate = abs(drawdown) / maxCapital
                maxDrawDownRat = max(maxDrawDownRat,drawdownRate)
                drawdownRateList.append(drawdownRate)
            else:
                drawdownRateList.append(0.0)


            pnlList.append(pnl)
            timeList.append(portfolio.datetime)      # 交易的时间戳使用平仓时间
            capitalList.append(capital)
            drawdownList.append(drawdown)

            totalResult += 1
            totalTurnover += 0
            totalCommission += commission
            totalSlippage += 0

            if pnl >= 0:
                winningResult += 1
                totalWinning += pnl
            else:
                losingResult += 1
                totalLosing += pnl

        # 计算盈亏相关数据
        winningRate = winningResult/totalResult*100         # 胜率

        averageWinning = 0                                  # 这里把数据都初始化为0
        averageLosing = 0
        profitLossRatio = 0

        if winningResult:
            averageWinning = totalWinning/winningResult     # 平均每笔盈利
        if losingResult:
            averageLosing = totalLosing/losingResult        # 平均每笔亏损
        if averageLosing:
            profitLossRatio = -averageWinning/averageLosing # 盈亏比

        # 返回回测结果
        d = {}
        d['capital'] = capital
        d['maxCapital'] = maxCapital
        d['drawdown'] = drawdown
        d['maxDrawDownRat'] = maxDrawDownRat
        d['totalResult'] = totalResult
        d['totalTurnover'] = totalTurnover
        d['totalCommission'] = totalCommission
        d['totalSlippage'] = totalSlippage
        d['timeList'] = timeList
        d['pnlList'] = pnlList
        d['capitalList'] = capitalList
        d['drawdownList'] = drawdownList
        d['drawdownRateList'] = drawdownRateList
        d['winningRate'] = winningRate
        d['averageWinning'] = averageWinning
        d['averageLosing'] = averageLosing
        d['profitLossRatio'] = profitLossRatio
        d['posList'] = posList
        d['tradeTimeList'] = tradeTimeList

        return d




    #----------------------------------------------------------------------
    def calculateBacktestingResult(self):
        """
        计算回测结果
        """
        self.output(u'计算回测结果')

        # 首先基于回测后的成交记录，计算每笔交易的盈亏
        resultList = []             # 交易结果列表

        longTradeList = {}        # 合约对应的longtrade
        shortTradeList = {}

        longTrade = []              # 未平仓的多头交易
        shortTrade = []             # 未平仓的空头交易

        tradeTimeList = []          # 每笔成交时间戳
        posList = [0]               # 每笔成交后的持仓情况

        #打印
        for portfolio in self.portfolioOrderList.values():
            for k,v in portfolio.__dict__.items():
                if  isinstance(v, basestring) or isinstance(v, int) or isinstance(v, float) or isinstance(v, datetime):
                    print k,v,
            print ''

        for trade in self.tradeDict.values():
            for k,v in trade.__dict__.items():
                print k,v,
            print ''

        self.protforlioToFile()
        self.tradeToFile()

        for trade in self.tradeDict.values():
            # 复制成交对象，因为下面的开平仓交易配对涉及到对成交数量的修改
            # 若不进行复制直接操作，则计算完后所有成交的数量会变成0
            trade = copy.copy(trade)

            if shortTradeList.has_key(trade.vtSymbol):
                shortTrade = shortTradeList[trade.vtSymbol]
            else:
                shortTrade = []
                shortTradeList[trade.vtSymbol] = shortTrade

            if longTradeList.has_key(trade.vtSymbol):
                longTrade = longTradeList[trade.vtSymbol]
            else:
                longTrade = []
                longTradeList[trade.vtSymbol] = longTrade

            # 多头交易
            if trade.direction == DIRECTION_LONG:


                # 如果尚无空头交易
                if not shortTrade:
                    longTrade.append(trade)
                # 当前多头交易为平空
                else:
                    while True:
                        entryTrade = shortTrade[0]
                        exitTrade = trade

                        # 清算开平仓交易
                        closedVolume = min(exitTrade.volume, entryTrade.volume)
                        result = TradingResult(entryTrade.price, entryTrade.dt,
                                               exitTrade.price, exitTrade.dt,
                                               -closedVolume, self.rate, self.slippage, self.size)
                        resultList.append(result)

                        posList.extend([-1,0])
                        tradeTimeList.extend([result.entryDt, result.exitDt])

                        # 计算未清算部分
                        entryTrade.volume -= closedVolume
                        exitTrade.volume -= closedVolume

                        # 如果开仓交易已经全部清算，则从列表中移除
                        if not entryTrade.volume:
                            shortTrade.pop(0)

                        # 如果平仓交易已经全部清算，则退出循环
                        if not exitTrade.volume:
                            break

                        # 如果平仓交易未全部清算，
                        if exitTrade.volume:
                            # 且开仓交易已经全部清算完，则平仓交易剩余的部分
                            # 等于新的反向开仓交易，添加到队列中
                            if not shortTrade:
                                longTrade.append(exitTrade)
                                break
                            # 如果开仓交易还有剩余，则进入下一轮循环
                            else:
                                pass

            # 空头交易
            else:
                # 如果尚无多头交易
                if not longTrade:
                    shortTrade.append(trade)
                # 当前空头交易为平多
                else:
                    while True:
                        entryTrade = longTrade[0]
                        exitTrade = trade

                        # 清算开平仓交易
                        closedVolume = min(exitTrade.volume, entryTrade.volume)
                        result = TradingResult(entryTrade.price, entryTrade.dt,
                                               exitTrade.price, exitTrade.dt,
                                               closedVolume, self.rate, self.slippage, self.size)
                        resultList.append(result)

                        posList.extend([1,0])
                        tradeTimeList.extend([result.entryDt, result.exitDt])

                        # 计算未清算部分
                        entryTrade.volume -= closedVolume
                        exitTrade.volume -= closedVolume

                        # 如果开仓交易已经全部清算，则从列表中移除
                        if not entryTrade.volume:
                            longTrade.pop(0)

                        # 如果平仓交易已经全部清算，则退出循环
                        if not exitTrade.volume:
                            break

                        # 如果平仓交易未全部清算，
                        if exitTrade.volume:
                            # 且开仓交易已经全部清算完，则平仓交易剩余的部分
                            # 等于新的反向开仓交易，添加到队列中
                            if not longTrade:
                                shortTrade.append(exitTrade)
                                break
                            # 如果开仓交易还有剩余，则进入下一轮循环
                            else:
                                pass

        # 到最后交易日尚未平仓的交易，则以最后价格平仓
        if self.mode == self.BAR_MODE:
            endPrice = self.bar.close
        else:
            endPrice = self.tick.lastPrice



        for longTrade_temp in longTradeList.values():
            for trade in longTrade_temp:
                result = TradingResult(trade.price, trade.dt, endPrice, self.dt,
                                       trade.volume, self.rate, self.slippage, self.size)
                resultList.append(result)
        for shortTrade_temp in shortTradeList.values():
            for trade in shortTrade_temp:
                result = TradingResult(trade.price, trade.dt, endPrice, self.dt,
                                       -trade.volume, self.rate, self.slippage, self.size)
                resultList.append(result)



        # 检查是否有交易
        if not resultList:
            self.output(u'无交易结果')
            return {}



        # 然后基于每笔交易的结果，我们可以计算具体的盈亏曲线和最大回撤等
        capital = self.capital           # 资金
        maxCapital = 0          # 资金最高净值
        drawdown = 0            # 回撤
        maxDrawDownRat = 0.0      #最大回测率

        totalResult = 0         # 总成交数量
        totalTurnover = 0       # 总成交金额（合约面值）
        totalCommission = 0     # 总手续费
        totalSlippage = 0       # 总滑点

        timeList = []           # 时间序列
        pnlList = []            # 每笔盈亏序列
        capitalList = []        # 盈亏汇总的时间序列
        drawdownList = []       # 回撤的时间序列
        drawdownRateList = []   # 回撤率的时间序列

        winningResult = 0       # 盈利次数
        losingResult = 0        # 亏损次数
        totalWinning = 0        # 总盈利金额
        totalLosing = 0         # 总亏损金额


        #for resu_ in resultList:
        #    for k,v in resu_.__dict__.items():
        #        print k,v,
        #    print ''


        for result in resultList:

            capital += result.pnl
            maxCapital = max(capital, maxCapital)
            drawdown = capital - maxCapital

            if drawdown != 0 and maxCapital > 0: #有策略 计算回测率
                drawdownRate = abs(drawdown) / maxCapital
                maxDrawDownRat = max(maxDrawDownRat,drawdownRate)
                drawdownRateList.append(drawdownRate)
            else:
                drawdownRateList.append(0.0)


            pnlList.append(result.pnl)
            timeList.append(result.exitDt)      # 交易的时间戳使用平仓时间
            capitalList.append(capital)
            drawdownList.append(drawdown)

            totalResult += 1
            totalTurnover += result.turnover
            totalCommission += result.commission
            totalSlippage += result.slippage

            if result.pnl >= 0:
                winningResult += 1
                totalWinning += result.pnl
            else:
                losingResult += 1
                totalLosing += result.pnl

        # 计算盈亏相关数据
        winningRate = winningResult/totalResult*100         # 胜率

        averageWinning = 0                                  # 这里把数据都初始化为0
        averageLosing = 0
        profitLossRatio = 0

        if winningResult:
            averageWinning = totalWinning/winningResult     # 平均每笔盈利
        if losingResult:
            averageLosing = totalLosing/losingResult        # 平均每笔亏损
        if averageLosing:
            profitLossRatio = -averageWinning/averageLosing # 盈亏比

        # 返回回测结果
        d = {}
        d['capital'] = capital
        d['maxCapital'] = maxCapital
        d['drawdown'] = drawdown
        d['maxDrawDownRat'] = maxDrawDownRat
        d['totalResult'] = totalResult
        d['totalTurnover'] = totalTurnover
        d['totalCommission'] = totalCommission
        d['totalSlippage'] = totalSlippage
        d['timeList'] = timeList
        d['pnlList'] = pnlList
        d['capitalList'] = capitalList
        d['drawdownList'] = drawdownList
        d['drawdownRateList'] = drawdownRateList
        d['winningRate'] = winningRate
        d['averageWinning'] = averageWinning
        d['averageLosing'] = averageLosing
        d['profitLossRatio'] = profitLossRatio
        d['posList'] = posList
        d['tradeTimeList'] = tradeTimeList

        return d


    ##只获取trade result list
    def getBacktestingResult_trade(self):

        self.tradeToFile()

        return self.tradeDict.values()


    ##只获取trade result list
    def getBacktestingResult_result(self):
        """
        计算回测结果
        """
        self.output(u'计算回测结果')

        # 首先基于回测后的成交记录，计算每笔交易的盈亏
        resultList = []             # 交易结果列表

        longTradeList = {}        # 合约对应的longtrade
        shortTradeList = {}

        longTrade = []              # 未平仓的多头交易
        shortTrade = []             # 未平仓的空头交易

        tradeTimeList = []          # 每笔成交时间戳
        posList = [0]               # 每笔成交后的持仓情况

        ##打印

        for trade in self.tradeDict.values():
            for k,v in trade.__dict__.items():
                print k,v,
            print ''

        self.tradeToFile()

        for trade in self.tradeDict.values():
            # 复制成交对象，因为下面的开平仓交易配对涉及到对成交数量的修改
            # 若不进行复制直接操作，则计算完后所有成交的数量会变成0
            trade = copy.copy(trade)

            if shortTradeList.has_key(trade.vtSymbol):
                shortTrade = shortTradeList[trade.vtSymbol]
            else:
                shortTrade = []
                shortTradeList[trade.vtSymbol] = shortTrade

            if longTradeList.has_key(trade.vtSymbol):
                longTrade = longTradeList[trade.vtSymbol]
            else:
                longTrade = []
                longTradeList[trade.vtSymbol] = longTrade

            # 多头交易
            if trade.direction == DIRECTION_LONG:


                # 如果尚无空头交易
                if not shortTrade:
                    longTrade.append(trade)
                # 当前多头交易为平空
                else:
                    while True:
                        entryTrade = shortTrade[0]
                        exitTrade = trade

                        # 清算开平仓交易
                        closedVolume = min(exitTrade.volume, entryTrade.volume)
                        result = TradingResult(entryTrade.price, entryTrade.dt,
                                               exitTrade.price, exitTrade.dt,
                                               -closedVolume, self.rate, self.slippage, self.size)
                        resultList.append(result)

                        posList.extend([-1,0])
                        tradeTimeList.extend([result.entryDt, result.exitDt])

                        # 计算未清算部分
                        entryTrade.volume -= closedVolume
                        exitTrade.volume -= closedVolume

                        # 如果开仓交易已经全部清算，则从列表中移除
                        if not entryTrade.volume:
                            shortTrade.pop(0)

                        # 如果平仓交易已经全部清算，则退出循环
                        if not exitTrade.volume:
                            break

                        # 如果平仓交易未全部清算，
                        if exitTrade.volume:
                            # 且开仓交易已经全部清算完，则平仓交易剩余的部分
                            # 等于新的反向开仓交易，添加到队列中
                            if not shortTrade:
                                longTrade.append(exitTrade)
                                break
                            # 如果开仓交易还有剩余，则进入下一轮循环
                            else:
                                pass

            # 空头交易
            else:
                # 如果尚无多头交易
                if not longTrade:
                    shortTrade.append(trade)
                # 当前空头交易为平多
                else:
                    while True:
                        entryTrade = longTrade[0]
                        exitTrade = trade

                        # 清算开平仓交易
                        closedVolume = min(exitTrade.volume, entryTrade.volume)
                        result = TradingResult(entryTrade.price, entryTrade.dt,
                                               exitTrade.price, exitTrade.dt,
                                               closedVolume, self.rate, self.slippage, self.size)
                        resultList.append(result)

                        posList.extend([1,0])
                        tradeTimeList.extend([result.entryDt, result.exitDt])

                        # 计算未清算部分
                        entryTrade.volume -= closedVolume
                        exitTrade.volume -= closedVolume

                        # 如果开仓交易已经全部清算，则从列表中移除
                        if not entryTrade.volume:
                            longTrade.pop(0)

                        # 如果平仓交易已经全部清算，则退出循环
                        if not exitTrade.volume:
                            break

                        # 如果平仓交易未全部清算，
                        if exitTrade.volume:
                            # 且开仓交易已经全部清算完，则平仓交易剩余的部分
                            # 等于新的反向开仓交易，添加到队列中
                            if not longTrade:
                                shortTrade.append(exitTrade)
                                break
                            # 如果开仓交易还有剩余，则进入下一轮循环
                            else:
                                pass

        # 到最后交易日尚未平仓的交易，则以最后价格平仓
        if self.mode == self.BAR_MODE:
            endPrice = self.bar.close
        else:
            endPrice = self.tick.lastPrice

        for trade in longTrade:
            result = TradingResult(trade.price, trade.dt, endPrice, self.dt,
                                   trade.volume, self.rate, self.slippage, self.size)
            resultList.append(result)

        for trade in shortTrade:
            result = TradingResult(trade.price, trade.dt, endPrice, self.dt,
                                   -trade.volume, self.rate, self.slippage, self.size)
            resultList.append(result)

        # 检查是否有交易
        if not resultList:
            self.output(u'无交易结果')
            return {}

        return resultList

    def calculateResult_result(self,resultList):


        # 然后基于每笔交易的结果，我们可以计算具体的盈亏曲线和最大回撤等
        capital = self.capital           # 资金
        maxCapital = 0          # 资金最高净值
        drawdown = 0            # 回撤
        maxDrawDownRat = 0.0      #最大回测率

        totalResult = 0         # 总成交数量
        totalTurnover = 0       # 总成交金额（合约面值）
        totalCommission = 0     # 总手续费
        totalSlippage = 0       # 总滑点

        timeList = []           # 时间序列
        pnlList = []            # 每笔盈亏序列
        capitalList = []        # 盈亏汇总的时间序列
        drawdownList = []       # 回撤的时间序列
        drawdownRateList = []   # 回撤率的时间序列

        winningResult = 0       # 盈利次数
        losingResult = 0        # 亏损次数
        totalWinning = 0        # 总盈利金额
        totalLosing = 0         # 总亏损金额




        for result in resultList:

            capital += result.pnl
            maxCapital = max(capital, maxCapital)
            drawdown = capital - maxCapital

            if drawdown != 0 and maxCapital > 0: #有策略 计算回测率
                drawdownRate = abs(drawdown) / maxCapital
                maxDrawDownRat = max(maxDrawDownRat,drawdownRate)
                drawdownRateList.append(drawdownRate)
            else:
                drawdownRateList.append(0.0)


            pnlList.append(result.pnl)
            timeList.append(result.exitDt)      # 交易的时间戳使用平仓时间
            capitalList.append(capital)
            drawdownList.append(drawdown)

            totalResult += 1
            totalTurnover += result.turnover
            totalCommission += result.commission
            totalSlippage += result.slippage

            if result.pnl >= 0:
                winningResult += 1
                totalWinning += result.pnl
            else:
                losingResult += 1
                totalLosing += result.pnl

        # 计算盈亏相关数据
        winningRate = winningResult/totalResult*100         # 胜率

        averageWinning = 0                                  # 这里把数据都初始化为0
        averageLosing = 0
        profitLossRatio = 0

        if winningResult:
            averageWinning = totalWinning/winningResult     # 平均每笔盈利
        if losingResult:
            averageLosing = totalLosing/losingResult        # 平均每笔亏损
        if averageLosing:
            profitLossRatio = -averageWinning/averageLosing # 盈亏比

        # 返回回测结果
        d = {}
        d['capital'] = capital
        d['maxCapital'] = maxCapital
        d['drawdown'] = drawdown
        d['maxDrawDownRat'] = maxDrawDownRat
        d['totalResult'] = totalResult
        d['totalTurnover'] = totalTurnover
        d['totalCommission'] = totalCommission
        d['totalSlippage'] = totalSlippage
        d['timeList'] = timeList
        d['pnlList'] = pnlList
        d['capitalList'] = capitalList
        d['drawdownList'] = drawdownList
        d['drawdownRateList'] = drawdownRateList
        d['winningRate'] = winningRate
        d['averageWinning'] = averageWinning
        d['averageLosing'] = averageLosing
        d['profitLossRatio'] = profitLossRatio


        return d


    def calculateResult_trade(self,resultList, capital_, capitalSymbolList):


        # 然后基于每笔交易的结果，我们可以计算具体的盈亏曲线和最大回撤等
        capital = capital_           # 资金
        maxCapital = 0          # 资金最高净值
        drawdown = 0            # 回撤
        maxDrawDownRat = 0.0      #最大回测率
        maxMargin = 0.0

        totalResult = 0         # 总成交数量
        totalTurnover = 0       # 总成交金额（合约面值）
        totalCommission = 0     # 总手续费
        totalSlippage = 0       # 总滑点

        timeList = []           # 时间序列
        pnlList = []            # 每笔盈亏序列
        capitalList = []        # 盈亏汇总的时间序列
        drawdownList = []       # 回撤的时间序列
        drawdownRateList = []   # 回撤率的时间序列
        marginRateList = []         ##保证金占用


        winningResult = 0       # 盈利次数
        losingResult = 0        # 亏损次数
        totalWinning = 0        # 总盈利金额
        totalLosing = 0         # 总亏损金额



        #for resu_ in resultList:
        #    for k,v in resu_.__dict__.items():
        #        print k,v,
        #    print ''

        profitList = {}
        marginList = {}

        for trade in resultList:


            profitList[trade.symbol] = trade.profit-capital_  ##这里保存是当时账号净值
            marginList[trade.symbol] = trade.margin

            allPrifit = 0
            for pro_t in profitList:
                allPrifit += profitList[pro_t]

            allMargin = 0
            for margin_t in marginList:
                allMargin += marginList[margin_t]


            capital  = capital_ + allPrifit
            maxCapital = max(capital, maxCapital)
            drawdown = capital - maxCapital

            if drawdown != 0 and maxCapital > 0: #有策略 计算回测率
                drawdownRate = abs(drawdown) / maxCapital
                maxDrawDownRat = max(maxDrawDownRat,drawdownRate)
                drawdownRateList.append(drawdownRate)
            else:
                drawdownRateList.append(0.0)


            marginRate = allMargin/capital
            maxMargin = max(maxMargin, marginRate)


            timeList.append(trade.dt)      # 交易的时间戳使用平仓时间
            capitalList.append(capital)
            for key in capitalSymbolList:
                if profitList.has_key(key):
                    capitalSymbolList[key].append(profitList[key]+capital_)
                else:
                    capitalSymbolList[key].append(capital_)

            drawdownList.append(drawdown)
            marginRateList.append(marginRate)


            totalResult += 1



        # 计算盈亏相关数据
        #winningRate = winningResult/totalResult*100         # 胜率

        averageWinning = 0                                  # 这里把数据都初始化为0
        averageLosing = 0
        profitLossRatio = 0



        # 返回回测结果
        d = {}
        d['capital'] = capital
        d['maxCapital'] = maxCapital
        d['drawdown'] = drawdown
        d['maxDrawDownRat'] = maxDrawDownRat
        d['maxMargin'] = maxMargin
        d['totalResult'] = totalResult
        d['totalTurnover'] = totalTurnover
        d['totalCommission'] = totalCommission
        d['totalSlippage'] = totalSlippage
        d['timeList'] = timeList
        d['pnlList'] = pnlList
        d['capitalList'] = capitalList
        d['drawdownList'] = drawdownList
        d['drawdownRateList'] = drawdownRateList
        d['winningRate'] = 0
        d['averageWinning'] = averageWinning
        d['averageLosing'] = averageLosing
        d['profitLossRatio'] = profitLossRatio
        d["marginRateList"] = marginRateList


        return d


    ##这个是使用仓位管理来统计仓位占比等
    def showMultiResult_Margin(self,resultList,capital, capitalSymbolList):
        """显示回测结果"""
        d = self.calculateResult_trade(resultList,capital,capitalSymbolList)


        # 输出
        self.output('-' * 30)
        self.output(u'第一笔交易：\t%s' % d['timeList'][0])
        self.output(u'最后一笔交易：\t%s' % d['timeList'][-1])

        #self.output(u'总交易次数：\t%s' % formatNumber(d['totalResult']))
        self.output(u'总盈亏：\t%s' % formatNumber(d['capital']))
        self.output(u'最大回撤: \t%s' % formatNumber(min(d['drawdownList'])))
        self.output(u'最大回撤率：\t%s' % formatNumber(d['maxDrawDownRat']))
        self.output(u'最大资金占用：\t%s' % formatNumber(d['maxMargin']))


        #self.output(u'平均每笔盈利：\t%s' %formatNumber(d['capital']/d['totalResult']))



        # 绘图
        fig = plt.figure(figsize=(10, 16))

        pCapital = plt.subplot(5, 1, 1)
        pCapital.set_ylabel("capital")
        pCapital.plot(d['capitalList'], color='r', lw=0.8)
        for key in capitalSymbolList:
            pCapital.plot(capitalSymbolList[key],   color='g', lw=0.8 )


        pDD = plt.subplot(5, 1, 2)
        pDD.set_ylabel("DD")
        pDD.bar(range(len(d['drawdownList'])), d['drawdownList'], color='g')

        pDD1 = plt.subplot(5, 1, 3)
        pDD1.set_ylabel("DD")
        pDD1.bar(range(len(d['drawdownRateList'])), d['drawdownRateList'], color='g')




        tradeTimeIndex = [item.strftime("%Y/%m/%d %H:%M:%S") for item in d['timeList']]
        xindex = np.arange(0, len(tradeTimeIndex), np.int(len(tradeTimeIndex)/10))
        tradeTimeIndex = map(lambda i: tradeTimeIndex[i], xindex)


        plt.tight_layout()
        plt.xticks(xindex, tradeTimeIndex, rotation=30)  # 旋转15

        plt.show()


    #----------------------------------------------------------------------
    def showBacktestingResult(self):
        """显示回测结果"""
        #d = self.calculateResult_result(result_list)

        #d = self.calculateBacktestingResult()

        d = self.calculateBortfolioResult()

        # 输出
        self.output('-' * 30)
        self.output(u'第一笔交易：\t%s' % d['timeList'][0])
        self.output(u'最后一笔交易：\t%s' % d['timeList'][-1])

        self.output(u'总交易次数：\t%s' % formatNumber(d['totalResult']))
        self.output(u'总盈亏：\t%s' % formatNumber(d['capital']))
        self.output(u'最大回撤: \t%s' % formatNumber(min(d['drawdownList'])))
        self.output(u'最大回撤率：\t%s' % formatNumber(d['maxDrawDownRat']))


        self.output(u'平均每笔盈利：\t%s' %formatNumber(d['capital']/d['totalResult']))
        self.output(u'平均每笔滑点：\t%s' %formatNumber(d['totalSlippage']/d['totalResult']))
        self.output(u'平均每笔佣金：\t%s' %formatNumber(d['totalCommission']/d['totalResult']))

        self.output(u'胜率\t\t%s%%' %formatNumber(d['winningRate']))
        self.output(u'盈利交易平均值\t%s' %formatNumber(d['averageWinning']))
        self.output(u'亏损交易平均值\t%s' %formatNumber(d['averageLosing']))
        self.output(u'盈亏比：\t%s' %formatNumber(d['profitLossRatio']))

        return d

        """
        # 绘图
        fig = plt.figure(figsize=(10, 16))

        pCapital = plt.subplot(5, 1, 1)
        pCapital.set_ylabel("capital")
        pCapital.plot(d['capitalList'], color='r', lw=0.8)


        pDD = plt.subplot(5, 1, 2)
        pDD.set_ylabel("DD")
        pDD.bar(range(len(d['drawdownList'])), d['drawdownList'], color='g')

        pDD1 = plt.subplot(5, 1, 3)
        pDD1.set_ylabel("DD")
        pDD1.bar(range(len(d['drawdownRateList'])), d['drawdownRateList'], color='g')

        pPnl = plt.subplot(5, 1, 4)
        pPnl.set_ylabel("pnl")
        pPnl.hist(d['pnlList'], bins=50, color='c')




        tradeTimeIndex = [item.strftime("%Y/%m/%d %H:%M:%S") for item in d['timeList']]
        xindex = np.arange(0, len(tradeTimeIndex), np.int(len(tradeTimeIndex)/10))
        tradeTimeIndex = map(lambda i: tradeTimeIndex[i], xindex)




        plt.tight_layout()
        plt.xticks(xindex, tradeTimeIndex, rotation=30)  # 旋转15

        plt.show()
    """

    #----------------------------------------------------------------------
    def clearBacktestingResult(self):
        """清空之前回测的结果"""
        # 清空限价单相关
        self.limitOrderCount = 0
        self.limitOrderDict.clear()
        self.workingLimitOrderDict.clear()

        # 清空停止单相关
        self.stopOrderCount = 0
        self.stopOrderDict.clear()
        self.workingStopOrderDict.clear()

        # 清空成交相关
        self.tradeCount = 0
        self.tradeDict.clear()

#----------------------------------------------------------------------
def formatNumber(n):
    """格式化数字到字符串"""
    rn = round(n, 2)        # 保留两位小数
    return format(rn, ',')  # 加上千分符

########################################################################
class TradingResult(object):
    """每笔交易的结果"""

    #----------------------------------------------------------------------
    def __init__(self, entryPrice, entryDt, exitPrice,
                 exitDt, volume, rate, slippage, size,commission=2):
        """Constructor"""
        self.entryPrice = entryPrice    # 开仓价格
        self.exitPrice = exitPrice      # 平仓价格

        self.entryDt = entryDt          # 开仓时间datetime
        self.exitDt = exitDt            # 平仓时间

        self.volume = volume    # 交易数量（+/-代表方向）

        self.turnover = (self.entryPrice+self.exitPrice)*size*abs(volume)   # 成交金额
        self.commission = abs(volume)*commission                                # 手续费成本
        self.slippage = 0##slippage*2*size*abs(volume)                         # 滑点成本
        self.pnl = ((self.exitPrice - self.entryPrice) * volume * size
                    - self.commission - self.slippage)                      # 净盈亏




class CJsonEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.strftime('%Y-%m-%d %H:%M:%S')
        elif isinstance(obj, date):
            return obj.strftime("%Y-%m-%d")
        else:
            return json.JSONEncoder.default(self, obj)

##模拟仓位
class PositionManager(object):
    def __init__(self,symbolSetting={}):
        self.positionList = []  ##仓位列表
        self.symbolPrice = {}   ##实时合约价格
        self.symbolSetting = symbolSetting ##合约参数信息 手数  保证金率  {"rb1205":{"maxVolume":50,"margin":0.1,volumeMultiple:10}}


        self.rate = 0

    def setRate(self,rate):
        self.rate = rate

    def updateBarPrice(self,bar):
        self.symbolPrice[bar.symbol] = bar.open

    def updateTickPrice(self,tick):
        self.symbolPrice[tick.symbol] = tick.lastPrice



    def updatePositionByTrade(self,trade):
        positionData = VtPositionData()
        positionData.symbol = trade.vtSymbol
        positionData.exchange = trade.exchange
        positionData.vtSymbol = trade.vtSymbol
        positionData.direction = trade.direction
        positionData.position = trade.volume
        positionData.frozen = 0
        positionData.price = trade.price
        positionData.positionProfit = 0.0

        return  self.updatePosition(positionData, trade.offset)


    def updatePosition(self,positionData, offset):
        ##看开仓还是平仓  开仓直接加入列表   平仓时候返回盈亏
        if offset == OFFSET_OPEN:
            self.positionList.append(positionData)
            return 0.0
        elif offset == OFFSET_CLOSE:
            Profit = 0.0

            position_index = 0
            while position_index < len(self.positionList):

                position = self.positionList[position_index]
                if positionData.vtSymbol == position.vtSymbol and positionData.direction != position.direction:
                    ##平仓
                    minPosition = min( positionData.position,position.position )

                    pnl = (positionData.price - position.price) * minPosition * self.getContactValues(positionData.vtSymbol)["volumeMultiple"]

                    if position.direction == DIRECTION_SHORT:
                        pnl = -pnl

                    Profit += pnl

                    #Profit -= self.getContactValues(positionData.vtSymbol)["commission"]*minPosition  ##手续费

                    ##手续费
                    turnover = (positionData.price + position.price) * minPosition * self.getContactValues(position.vtSymbol)["volumeMultiple"]   # 成交金额
                    commission = turnover*self.rate                            # 手续费成本

                    Profit -= commission

                    # 计算未清算部分
                    positionData.position -= minPosition
                    position.position -= minPosition

                    if position.position == 0:
                        self.positionList.pop(position_index)
                        #position_index -= 1
                        continue

                    if positionData.position == 0:
                        break

                position_index += 1

            return Profit



    ##获取合约上次开仓数
    def preContactPosition(self,symbol):
        for i in range(0,  self.positionList.__len__())[::-1]:
           if self.positionList[i].vtSymbol == symbol:
               return self.positionList[i].position

        return 0


    ##获取盈亏
    def getProfit(self):
        profit = 0.0
        for position in self.positionList:
            pnl = (self.symbolPrice[position.vtSymbol] - position.price) * position.position * self.getContactValues(position.vtSymbol)["volumeMultiple"]

            if position.direction == DIRECTION_SHORT:
                pnl = -pnl

            profit += pnl

        return profit



    ##获取保证金
    def getMargin(self):
        margin = 0.0
        for position in self.positionList:
            margin_tmp = self.symbolPrice[position.vtSymbol] * position.position \
                         * self.getContactValues(position.vtSymbol)["volumeMultiple"]*self.getContactValues(position.vtSymbol)["margin"]
            margin += margin_tmp

        return margin

    ##根据保证金算最大手数
    def getVolumeByMargin(self,margin,price, symbol):
            return margin/self.getContactValues(symbol)["volumeMultiple"]/self.getContactValues(symbol)["margin"]/price


    def getContactValues(self, symbol):
        for key, value in self.symbolSetting.items():
            if len(symbol) == value["length"] and symbol.startswith(value["pre"]):
                return value

        return None

##模拟账户信息
class AccountManager(object):
    def __init__(self, positionManager, capital=1000000):
        self.capital = capital                 # 启始资金

        ##下面每次获取算，不用每个tick或者bar去算
        #self.balance = EMPTY_FLOAT              # 账户净值
        #self.available = EMPTY_FLOAT            # 可用资金
        #self.margin = EMPTY_FLOAT               # 保证金占用
        #self.closeProfit = EMPTY_FLOAT          # 平仓盈亏
        #self.positionProfit = EMPTY_FLOAT       # 持仓盈亏

        self.positionManager = positionManager


    def updatePositionByTrade(self,trade):
        prifit = self.positionManager.updatePositionByTrade(trade)

        self.capital += prifit

    ##获取盈亏
    def getProfit(self):
        return  self.positionManager.getProfit()

    def getCapital(self):
        return  self.positionManager.getProfit()+ self.capital

    ##获取保证金
    def getMargin(self):
        return self.positionManager.getMargin()

    ##获取可用资金
    def getAvailable(self):
        profit = self.positionManager.getProfit()
        margin = self.positionManager.getMargin()

        return self.capital + profit - margin

    ##资金使用率  保证金/权益
    def getAvailableRate(self):
        profit = self.positionManager.getProfit()
        margin = self.positionManager.getMargin()

        return margin/(self.capital + profit)

