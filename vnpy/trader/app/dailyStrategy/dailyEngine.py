# encoding: UTF-8

'''
本文件中实现了日内策略引擎，针对日内类型的策略，抽象简化了部分底层接口的功能。

关于平今和平昨规则：
1. 普通的平仓OFFSET_CLOSET等于平昨OFFSET_CLOSEYESTERDAY
2. 只有上期所的品种需要考虑平今和平昨的区别
3. 当上期所的期货有今仓时，调用Sell和Cover会使用OFFSET_CLOSETODAY，否则
   会使用OFFSET_CLOSE
4. 以上设计意味着如果Sell和Cover的数量超过今日持仓量时，会导致出错（即用户
   希望通过一个指令同时平今和平昨）
5. 采用以上设计的原因是考虑到vn.trader的用户主要是对TB、MC和金字塔类的平台
   感到功能不足的用户（即希望更高频的交易），交易策略不应该出现4中所述的情况
6. 对于想要实现4中所述情况的用户，需要实现一个策略信号引擎和交易委托引擎分开
   的定制化统结构（没错，得自己写）
'''

from __future__ import division

import json
import tushare as ts
import os
import  copy
import traceback
from collections import OrderedDict
from datetime import datetime, timedelta

from vnpy.event import Event
from vnpy.trader.vtEvent import *
from vnpy.trader.vtConstant import *
from vnpy.trader.vtObject import VtTickData, VtBarData
from vnpy.trader.vtGateway import VtSubscribeReq, VtOrderReq, VtCancelOrderReq, VtLogData
from vnpy.trader.vtFunction import todayDate, getJsonPath

from .dailyBase import *
from .strategy import STRATEGY_CLASS
from vnpy.trader.data.mysqlEngine import SQL_TABLENAME_POSITION, SQL_TABLENAME_STOP_ORDER,SQL_TABLENAME_TRADER
from vnpy.trader.app.gEntityObject import *
import pandas as pd



########################################################################
class DailyEngine(object):
    """Zzsd策略引擎"""
    settingFileName = 'Daily_setting.json'
    settingfilePath = getJsonPath(settingFileName, __file__)
    
    STATUS_FINISHED = set([STATUS_REJECTED, STATUS_CANCELLED, STATUS_ALLTRADED])
    FIX_SIZE_AUDO = -1
    #----------------------------------------------------------------------
    def __init__(self, mainEngine, eventEngine):
        """Constructor"""
        self.mainEngine = mainEngine
        self.eventEngine = eventEngine
        
        # 当前日期
        self.today = todayDate()

        self.symbolList = []        ##策略折行的产品，比如 ru0000  rb0000
        self.symbolInfoList = {}    ##产品信息 包括maxVolume
        self.mainSymbolList = []    ##主力合约


        self.account = None     ##账户
        self.capitalUseRat = 0.5  ##资金使用率 默认0.5
        self.riskRate   = 0.02    #单笔风险敞口


        self.isUpperOrLowerLimit = {}

        # 保存策略实例的字典
        # key为合约号+策略名，保证1个合约1个策略1个实例，value为策略实例
        self.strategyDict = {}
        
        # 保存vtSymbol和策略实例映射的字典（用于推送tick数据）
        # 由于可能多个strategy交易同一个vtSymbol，因此key为vtSymbol
        # value为包含所有相关strategy对象的list
        self.tickStrategyDict = {}
        
        # 保存vtOrderID和strategy对象映射的字典（用于推送order和trade数据）
        # key为vtOrderID，value为strategy对象
        self.orderStrategyDict = {}     

        self.lastOpenTrade = {}  ##最后一次开仓记录  key  symbol
        self.traderDict = {}     ##交易记录   key为vtOrderID


        # 本地停止单编号计数
        self.stopOrderCount = 0
        # stopOrderID = STOPORDERPREFIX + str(stopOrderCount)
        
        # 本地停止单字典
        # key为stopOrderID，value为stopOrder对象
        self.stopOrderDict = {}             # 停止单撤销后不会从本字典中删除
        self.workingStopOrderDict = {}      # 停止单撤销后会从本字典中删除

        ##用来记录停止单对应发送的委托
        self.orderToStopOrder = {}  ## key为order，交易id，value为stoporder

        # 保存策略名称和委托号列表的字典
        # key为symbol合约+策略名，value为保存orderID（限价+本地停止）的集合
        self.strategyOrderDict = {}
        
        # 成交号集合，用来过滤已经收到过的成交推送
        self.tradeSet = set()
        
        # 引擎类型为实盘
        self.engineType = ENGINETYPE_TRADING
        
        # 注册日式事件类型
        #self.mainEngine.registerLogEvent(EVENT_ZZSD_LOG)
        
        # 注册事件监听
        self.registerEvent()




    def checkPosition(self):
        print 'hello timer!'
        detailDict = self.mainEngine.dataEngine.getAllPositionDetail()
        for key in detailDict:
            print(key)
            if key != self.mainSymbol:
                return key   ##合约还有仓位，继续跟踪

        return ""


    def getSymbolEndTime(self,symbol):
        return self.mainEngine.getSymbolSetting(symbol)["nightEndTime"]



    ##获取仓位  暂不考虑同时有long和short的情况
    def getPos(self,symbol):
        detail = self.mainEngine.dataEngine.getPositionDetail(symbol)
        if detail.longPos > 0:
            return detail.longPos

        if detail.shortPos > 0:
            return -detail.shortPos

    #----------------------------------------------------------------------
    def sendOrder(self, vtSymbol, orderType, price, volume, strategy):
        """发单"""
        contract = self.mainEngine.getContract(vtSymbol)
        
        req = VtOrderReq()
        req.symbol = contract.symbol
        req.exchange = contract.exchange
        req.vtSymbol = contract.vtSymbol
        req.price = self.roundToPriceTick(contract.priceTick, price)
        req.volume = volume
        
        req.productClass = strategy.productClass
        req.currency = strategy.currency        
        
        # 设计为CTA引擎发出的委托只允许使用限价单
        req.priceType = PRICETYPE_LIMITPRICE    
        
        # CTA委托类型映射
        if orderType == CTAORDER_BUY:
            req.direction = DIRECTION_LONG
            req.offset = OFFSET_OPEN
            
        elif orderType == CTAORDER_SELL:
            req.direction = DIRECTION_SHORT
            req.offset = OFFSET_CLOSE
                
        elif orderType == CTAORDER_SHORT:
            req.direction = DIRECTION_SHORT
            req.offset = OFFSET_OPEN
            
        elif orderType == CTAORDER_COVER:
            req.direction = DIRECTION_LONG
            req.offset = OFFSET_CLOSE
            
        # 委托转换
        reqList = self.mainEngine.convertOrderReq(req)
        vtOrderIDList = []
        
        if not reqList:
            return vtOrderIDList
        
        for convertedReq in reqList:
            vtOrderID = self.mainEngine.sendOrder(convertedReq, contract.gatewayName)    # 发单
            self.orderStrategyDict[vtOrderID] = strategy                                 # 保存vtOrderID和策略的映射关系
            self.strategyOrderDict[req.symbol+strategy.className].add(vtOrderID)                         # 添加到策略委托号集合中
            vtOrderIDList.append(vtOrderID)

            ##写数据库
            traderOrd = TraderOrder()
            traderOrd.orderID = vtOrderID
            traderOrd.orderUuid = datetime.now().strftime("%Y%m%d%H%M%S")+vtOrderID
            traderOrd.symbol = contract.symbol
            traderOrd.strategyName = strategy.className
            traderOrd.direction = req.direction
            traderOrd.offset = req.offset
            traderOrd.orderVolume = convertedReq.volume
            traderOrd.orderPrice = convertedReq.price

            self.mainEngine.mysqlClient.dbInsert(SQL_TABLENAME_TRADER, traderOrd)

            if traderOrd.offset == OFFSET_OPEN:
                self.lastOpenTrade[traderOrd.symbol] = traderOrd

            self.traderDict[vtOrderID] = traderOrd

        self.writeCtaLog(u'策略%s发送委托，%s，%s，%s@%s, %s'
                         %(strategy.name, vtSymbol, req.direction, volume, price,req.offset))
        
        return vtOrderIDList
    
    #----------------------------------------------------------------------
    def cancelOrder(self, vtOrderID):
        """撤单"""
        # 查询报单对象
        order = self.mainEngine.getOrder(vtOrderID)
        
        # 如果查询成功
        if order:
            # 检查是否报单还有效，只有有效时才发出撤单指令
            orderFinished = (order.status==STATUS_ALLTRADED or order.status==STATUS_CANCELLED)
            if not orderFinished:
                req = VtCancelOrderReq()
                req.symbol = order.symbol
                req.exchange = order.exchange
                req.frontID = order.frontID
                req.sessionID = order.sessionID
                req.orderID = order.orderID
                self.mainEngine.cancelOrder(req, order.gatewayName)    


       #----------------------------------------------------------------------
    def recoverStopOrder(self, vtSymbol, orderType, price, volume,direction, offset, strategy, stopDirection):
        """恢复停止单"""
        self.stopOrderCount += 1
        stopOrderID = STOPORDERPREFIX + str(self.stopOrderCount)

        so = StopOrder()
        so.vtSymbol = vtSymbol
        so.orderType = orderType
        so.price = price
        so.volume = volume
        so.strategy = strategy
        so.stopOrderID = stopOrderID
        so.status = STOPORDER_WAITING
        so.stopDirection = stopDirection

        so.direction = direction
        so.offset = offset
        so.strategyName = strategy.className


        # 保存stopOrder对象到字典中
        self.stopOrderDict[stopOrderID] = so
        self.workingStopOrderDict[stopOrderID] = so

        # 保存stopOrderID到策略委托号集合中
        self.strategyOrderDict[so.vtSymbol+strategy.className].add(stopOrderID)

        # 推送停止单状态
        strategy.onStopOrder(so)



    #----------------------------------------------------------------------
    def sendStopOrder(self, vtSymbol, orderType, price, volume, strategy,stopDirection):
        """发停止单（本地实现）"""
        self.stopOrderCount += 1
        stopOrderID = STOPORDERPREFIX + str(self.stopOrderCount)
        
        so = StopOrder()
        so.vtSymbol = vtSymbol
        so.orderType = orderType
        so.price = price
        so.volume = volume
        so.strategy = strategy
        so.stopOrderID = stopOrderID
        so.status = STOPORDER_WAITING
        so.stopDirection = stopDirection
        so.strategyName = strategy.className
        
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
        
        # 保存stopOrderID到策略委托号集合中
        self.strategyOrderDict[so.vtSymbol+strategy.className].add(stopOrderID)
        
        # 推送停止单状态
        strategy.onStopOrder(so)

        ##停止单添加到数据库  目前只处理下单插入， 发出委托后删除
        self.mainEngine.mysqlClient.dbInsert(SQL_TABLENAME_STOP_ORDER, so)
        
        return [stopOrderID]
    
    #----------------------------------------------------------------------
    def cancelStopOrder(self, stopOrderID):
        """撤销停止单"""
        # 检查停止单是否存在
        if stopOrderID in self.workingStopOrderDict:
            so = self.workingStopOrderDict[stopOrderID]
            strategy = so.strategy
            
            # 更改停止单状态为已撤销
            so.status = STOPORDER_CANCELLED
            
            # 从活动停止单字典中移除
            del self.workingStopOrderDict[stopOrderID]
            
            # 从策略委托号集合中移除
            s = self.strategyOrderDict[so.vtSymbol+strategy.className]
            if stopOrderID in s:
                s.remove(stopOrderID)
            
            # 通知策略
            strategy.onStopOrder(so)

            self.mainEngine.mysqlClient.dbDelete(SQL_TABLENAME_STOP_ORDER, so)

    #----------------------------------------------------------------------
    def processStopOrder(self, tick):
        """收到行情后处理本地停止单（检查是否要立即发出）"""
        vtSymbol = tick.vtSymbol
        
        # 首先检查是否有策略交易该合约
        if vtSymbol in self.tickStrategyDict:
            # 遍历等待中的停止单，检查是否会被触发
            for so in self.workingStopOrderDict.values():
                if so.vtSymbol == vtSymbol:

                    if so.offset == OFFSET_CLOSE and so.stopDirection == STOPDIRECTION_SOTP:##止盈
                        longTriggered = so.direction==DIRECTION_LONG and tick.lastPrice<=so.price        # 多头停止单被触发
                        shortTriggered = so.direction==DIRECTION_SHORT and tick.lastPrice>=so.price     # 空头停止单被触发

                    if so.offset == OFFSET_CLOSE and so.stopDirection == STOPDIRECTION_LIMIT: ##止损
                        longTriggered = so.direction==DIRECTION_LONG and   tick.lastPrice >=so.price
                        shortTriggered = so.direction==DIRECTION_SHORT and tick.lastPrice <=so.price

                    if so.offset == OFFSET_OPEN and  so.stopDirection == STOPDIRECTION_SOTP:  ##追涨
                        longTriggered = so.direction==DIRECTION_LONG and tick.lastPrice>=so.price        # 多头停止单被触发
                        shortTriggered = so.direction==DIRECTION_SHORT and tick.lastPrice<=so.price     # 空头停止单被触发


                    if so.offset == OFFSET_OPEN and  so.stopDirection == STOPDIRECTION_LIMIT:  ##等回落
                        longTriggered = so.direction==DIRECTION_LONG and tick.lastPrice<=so.price        # 多头停止单被触发
                        shortTriggered = so.direction==DIRECTION_SHORT and tick.lastPrice>=so.price     # 空头停止单被触发


                    contract = self.mainEngine.getContract(vtSymbol)

                    if longTriggered or shortTriggered:
                        # 买入和卖出分别以涨停跌停价发单（模拟市价单）
                        if so.direction==DIRECTION_LONG:
                            price =  self.roundToPriceTick(contract.priceTick, tick.upperLimit - contract.priceTick )
                        else:
                            price =  self.roundToPriceTick(contract.priceTick,  tick.lowerLimit + contract.priceTick)

                        if so.offset == OFFSET_OPEN:  ##条件单
                            ##条件单用超价下单
                            if so.direction==DIRECTION_LONG:
                                price =  self.roundToPriceTick(contract.priceTick, tick.lastPrice + contract.priceTick )
                            else:
                                price =  self.roundToPriceTick(contract.priceTick, tick.lastPrice -  contract.priceTick )

                        # 发出市价委托
                        vtOrderIDList = self.sendOrder(so.vtSymbol, so.orderType, price, so.volume, so.strategy)
                        
                        # 从活动停止单字典中移除该停止单
                        del self.workingStopOrderDict[so.stopOrderID]
                        
                        # 从策略委托号集合中移除
                        s = self.strategyOrderDict[so.vtSymbol+so.strategy.className]
                        if so.stopOrderID in s:
                            s.remove(so.stopOrderID)
                        
                        # 更新停止单状态，并通知策略
                        so.status = STOPORDER_TRIGGERED
                        so.strategy.onStopOrder(so)

                        for id in vtOrderIDList:
                            self.orderToStopOrder[id] = so.stopOrderID
                        #self.mainEngine.mysqlClient.dbDelete(SQL_TABLENAME_STOP_ORDER, so)

    #----------------------------------------------------------------------
    def processTickEvent(self, event):
        """处理行情推送"""
        tick = event.dict_['data']
        # 收到tick行情后，先处理本地停止单（检查是否要立即发出）
        self.processStopOrder(tick)


        ##判断涨铁停
        if tick.lowerLimit == tick.lastPrice or tick.upperLimit == tick.lastPrice:
            self.isUpperOrLowerLimit[tick.symbol] = True

        # 推送tick到对应的策略实例进行处理
        if tick.vtSymbol in self.tickStrategyDict:
            # tick时间可能出现异常数据，使用try...except实现捕捉和过滤
            try:
                # 添加datetime字段
                if not tick.datetime:
                    tick.datetime = datetime.strptime(' '.join([tick.date, tick.time]), '%Y%m%d %H:%M:%S.%f')
            except ValueError:
                self.writeCtaLog(traceback.format_exc())
                return
                
            # 逐个推送到策略实例中
            l = self.tickStrategyDict[tick.vtSymbol]
            for strategy in l:
                self.callStrategyFunc(strategy, strategy.onTick, tick)
    
    #----------------------------------------------------------------------
    def processOrderEvent(self, event):
        """处理委托推送"""
        order = event.dict_['data']
        
        vtOrderID = order.vtOrderID
        
        if vtOrderID in self.orderStrategyDict:
            strategy = self.orderStrategyDict[vtOrderID]            
            
            # 如果委托已经完成（拒单、撤销、全成），则从活动委托集合中移除
            self.writeCtaLog(u"委托推送:%s %s"%(order.symbol,order.status))
            if order.status in self.STATUS_FINISHED:
                s = self.strategyOrderDict[order.symbol+strategy.className]
                if vtOrderID in s:
                    s.remove(vtOrderID)

                if order.status == STATUS_REJECTED or order.status == STATUS_CANCELLED:
                    ##恢复停止单
                    if self.orderToStopOrder.has_key(vtOrderID):
                        stopOrder = self.stopOrderDict[self.orderToStopOrder[vtOrderID]]
                        stopOrder.status = STOPORDER_WAITING
                        self.workingStopOrderDict[stopOrder.stopOrderID] = stopOrder

                        # 保存stopOrderID到策略委托号集合中
                        self.strategyOrderDict[stopOrder.vtSymbol+strategy.className].add(stopOrder.stopOrderID)

                if order.status == STATUS_ALLTRADED:
                    ##删除数据库停止单
                    if self.orderToStopOrder.has_key(vtOrderID):
                        stopOrder = self.stopOrderDict[self.orderToStopOrder[vtOrderID]]
                        self.mainEngine.mysqlClient.dbDelete(SQL_TABLENAME_STOP_ORDER, stopOrder)

            self.callStrategyFunc(strategy, strategy.onOrder, order)
    
    #----------------------------------------------------------------------
    def processTradeEvent(self, event):
        """处理成交推送"""
        trade = event.dict_['data']
        
        # 过滤已经收到过的成交回报
        if trade.vtTradeID in self.tradeSet:
            return
        self.tradeSet.add(trade.vtTradeID)
        
        # 将成交推送到策略对象中
        if trade.vtOrderID in self.orderStrategyDict:
            strategy = self.orderStrategyDict[trade.vtOrderID]
            
            # 计算策略持仓
            if trade.direction == DIRECTION_LONG:
                strategy.pos += trade.volume
            else:
                strategy.pos -= trade.volume
            
            self.callStrategyFunc(strategy, strategy.onTrade, trade)
            
            # 保存策略持仓到数据库
            self.savePosition(strategy)

        if trade.vtOrderID in self.traderDict:
            trade_h = self.traderDict[trade.vtOrderID]
            trade_h.tradeVolume += trade.volume
            trade_h.tradePrice = trade.price

            self.mainEngine.mysqlClient.dbUpdate(SQL_TABLENAME_TRADER, trade_h)


    def processAccountEvent(self,event):
        self.account = event.dict_['data']

    #----------------------------------------------------------------------
    def registerEvent(self):
        """注册事件监听"""
        self.eventEngine.register(EVENT_TICK, self.processTickEvent)
        self.eventEngine.register(EVENT_ORDER, self.processOrderEvent)
        self.eventEngine.register(EVENT_TRADE, self.processTradeEvent)
        self.eventEngine.register(EVENT_ACCOUNT,self.processAccountEvent)
 
    #----------------------------------------------------------------------
    def insertData(self, dbName, collectionName, data):
        """插入数据到数据库（这里的data可以是VtTickData或者VtBarData）"""
        self.mainEngine.dbInsert(dbName, collectionName, data.__dict__)


    def loadOptData(self,symbol, strategyCycle,days=None):

        db_name = cycle_db[strategyCycle]
        if not db_name:
            self.writeCtaLog(u"db获取失败")

        if not days:
            return self.loadAllBar(db_name,symbol)
        else:
             return self.loadBar(db_name,symbol,days)

    #----------------------------------------------------------------------
    def loadBar(self, dbName, collectionName, days):
        """从数据库中读取Bar数据，startDate是datetime对象"""
        startDate = self.today - timedelta(days)
        
        d = {'datetime':{'$gte':startDate}}
        barData = self.mainEngine.dbQuery(dbName, collectionName, d, 'datetime')
        
        l = []
        for d in barData:
            bar = VtBarData()
            bar.__dict__ = d
            l.append(bar)
        return l

    #----------------------------------------------------------------------
    def loadAllBar(self, dbName, collectionName):
        """从数据库中读取Bar数据，startDate是datetime对象"""
        d = {}
        barData = self.mainEngine.dbQuery(dbName, collectionName,d ,'datetime')

        l = []
        for d in barData:
            bar = VtBarData()
            bar.__dict__ = d
            l.append(bar)
        return l

    #----------------------------------------------------------------------
    def loadTick(self, dbName, collectionName, days):
        """从数据库中读取Tick数据，startDate是datetime对象"""
        startDate = self.today - timedelta(days)
        
        d = {'datetime':{'$gte':startDate}}
        tickData = self.mainEngine.dbQuery(dbName, collectionName, d, 'datetime')
        
        l = []
        for d in tickData:
            tick = VtTickData()
            tick.__dict__ = d
            l.append(tick)
        return l    
    
    #----------------------------------------------------------------------
    def writeCtaLog(self, content):
        """快速发出CTA模块日志事件"""
        log = VtLogData()
        log.logContent = content
        log.gatewayName = 'Daily_STRATEGY'
        event = Event(type_=EVENT_DAILY_LOG)
        event.dict_['data'] = log
        self.eventEngine.put(event)   
    
    #----------------------------------------------------------------------
    def loadStrategy(self, setting):
        """载入策略"""
        try:
            self.capitalUseRat = setting["capitalUseRat"]
            self.riskRate      = setting["riskRate"]

            for (symbol,symbolInfo) in setting["contactInfo"].items():
                self.symbolList.append(symbol)
                self.symbolInfoList[symbol] = symbolInfo

                ##
                listContract = self.getProductContractList(self.today, symbol)
                mainSymbol = self.getMainContact(self.today, listContract)
                self.mainSymbolList.append(mainSymbol)

                if not mainSymbol:
                    self.writeCtaLog(u'主力合约获取失败')
                    return

                self.initStrategyBySymbol(mainSymbol,symbolInfo)



        except Exception, e:
            self.writeCtaLog(u'载入策略出错：%s' %e)
            return



        ##恢复停止单
        so = StopOrder()

        stopArray = self.mainEngine.mysqlClient.dbSelect(SQL_TABLENAME_STOP_ORDER, so,"all")
        for d in stopArray:
            if not self.strategyDict.has_key(d["symbol"] + str(d["strategyName"])) :
                continue
            strategy = self.strategyDict[(d["symbol"] + d["strategyName"])]
            if strategy and d['status'] == STOPORDER_WAITING:
                self.recoverStopOrder(d["symbol"],d["orderType"],d["price"],d["volume"],d["direction"],d["offset"],strategy, d['stopDirection'])
                self.writeCtaLog(u'恢复停止单：%s  %s  %f %s' %(d["symbol"], d["orderType"], d["price"], d["volume"]))




    def initStrategyBySymbol(self,symbol,setting):

        # 创建策略实例
        # 防止策略重名
        if (symbol+setting['className']) in self.strategyDict:
            self.writeCtaLog(u'策略实例重名：%s' %name)
            return

        setting["vtSymbol"] = symbol

        className = setting['className']

        # 获取策略类
        strategyClass = STRATEGY_CLASS.get(className, None)
        if not strategyClass:
            self.writeCtaLog(u'找不到策略类：%s' %className)
            return

        strategy = strategyClass(self, setting)

        self.strategyDict[symbol+className] = strategy
        strategy.setFixSize(self.FIX_SIZE_AUDO)


        # 创建委托号列表
        self.strategyOrderDict[symbol+strategy.className] = set()

        # 保存Tick映射关系
        if strategy.vtSymbol in self.tickStrategyDict:
            l = self.tickStrategyDict[strategy.vtSymbol]
        else:
            l = []
            self.tickStrategyDict[strategy.vtSymbol] = l
        l.append(strategy)



        ##读数据库
        traderOrd = TraderOrder()
        traderOrd.symbol = symbol
        traderOrd.strategyName = strategy.className
        traderOrd.offset = OFFSET_OPEN


        t = self.mainEngine.mysqlClient.dbSelect(SQL_TABLENAME_TRADER,traderOrd,"one")
        if t:
            traderOrd.orderID = t["orderID"]
            traderOrd.orderUuid = t["orderUuid"]
            traderOrd.direction = t["direction"]
            traderOrd.orderVolume = t["orderVolume"]
            traderOrd.orderPrice = t["orderPrice"]
            traderOrd.tradeVolume = t["tradeVolume"]
            traderOrd.tradePrice = t["tradePrice"]

            if traderOrd.offset == OFFSET_OPEN:
                self.lastOpenTrade[traderOrd.symbol] = traderOrd

            self.traderDict[traderOrd.orderID] = traderOrd


        # 订阅合约
        contract = self.mainEngine.getContract(strategy.vtSymbol)
        if contract:

            strategy.setPriceTick(contract.size,contract.priceTick)

            req = VtSubscribeReq()
            req.symbol = contract.symbol
            req.exchange = contract.exchange

            # 对于IB接口订阅行情时所需的货币和产品类型，从策略属性中获取
            req.currency = strategy.currency
            req.productClass = strategy.productClass

            self.mainEngine.subscribe(req, contract.gatewayName)

            self.writeCtaLog("subscribe===%s"%(strategy.vtSymbol))

        else:
            self.writeCtaLog(u'%s的交易合约%s无法找到' %(name, strategy.vtSymbol))

    #----------------------------------------------------------------------
    def initStrategy(self, name):
        """初始化策略"""
        if name in self.strategyDict:
            strategy = self.strategyDict[name]
            
            if not strategy.inited:

                self.callStrategyFunc(strategy, strategy.onInit)
                strategy.inited = True
            else:
                self.writeCtaLog(u'请勿重复初始化策略实例：%s' %name)
        else:
            self.writeCtaLog(u'策略实例不存在：%s' %name)        

    #---------------------------------------------------------------------
    def startStrategy(self, name):
        """启动策略"""
        if name in self.strategyDict:
            strategy = self.strategyDict[name]
            
            if strategy.inited and not strategy.trading:

                self.callStrategyFunc(strategy, strategy.onStart)
                strategy.trading = True
        else:
            self.writeCtaLog(u'策略实例不存在：%s' %name)


    ### 获取合约最大volume
    def getSymbolVolume(self, symbol,price,stopPrice):
        ##判断资金使用率
        if (1- self.getAccountAvailableRate()) > self.capitalUseRat:
            self.writeCtaLog(u'资金已到上限')
            return 0

        maxSymbolVol = self.getSymbolMaxVolume(symbol)

        volumeMultiple = self.mainEngine.getContract(symbol).size
        marginRate = self.mainEngine.getContract(symbol).LongMarginRatio

        maxMarginVol = (self.account.balance*self.capitalUseRat - self.account.margin) / (price*volumeMultiple*marginRate)  ##保证金占用最大手数
        maxMarginVol = int(maxMarginVol)

        maxRiskVol = int(self.account.available *self.riskRate/abs(price - stopPrice)/volumeMultiple)  ##风险敞口

        self.writeCtaLog(u'getSymbolVolume'+str(maxSymbolVol)+" "+str(maxRiskVol)+" "+str(maxMarginVol))

        return min(maxSymbolVol, maxRiskVol,maxMarginVol)


    ### 获取合约最大volume  bu
    def getSymbolVolumeNotMargin(self, symbol,price,stopPrice):
        ##判断资金使用率
        if (1- self.getAccountAvailableRate()) > self.capitalUseRat:
            self.writeCtaLog(u'资金已到上限')
            return 0

        maxSymbolVol = self.getSymbolMaxVolume(symbol)

        volumeMultiple = self.mainEngine.getContract(symbol).size
        marginRate = self.mainEngine.getContract(symbol).LongMarginRatio

        maxMarginVol = (self.account.balance*self.capitalUseRat - self.account.margin) / (price*volumeMultiple*marginRate)  ##保证金占用最大手数
        maxMarginVol = int(maxMarginVol)

        maxRiskVol = int(self.account.available *self.riskRate/abs(price - stopPrice)/volumeMultiple)  ##风险敞口

        self.writeCtaLog(u'getSymbolVolume'+str(maxSymbolVol)+" "+str(maxRiskVol)+" "+str(maxMarginVol))

        return min(maxSymbolVol, maxRiskVol,maxMarginVol)


    ##返回前一次开仓 手数
    def getSymbolPrePosition(self, symbol):
        if self.lastOpenTrade.has_key(symbol):
            trade = self.lastOpenTrade[symbol]
            if trade.tradeVolume != 0:
                return trade.tradeVolume

            return trade.orderVolume

        return 0


    ##先打桩，回头再改
    def getSymbolLastTrade(self, symbol):
        if self.lastOpenTrade.has_key(symbol):
            trade = self.lastOpenTrade[symbol]
            trade.price = trade.tradePrice
            if trade.tradePrice == EMPTY_FLOAT:
                trade.price = trade.orderPrice
            return trade

        return None


    #----------------------------------------------------------------------
    def stopStrategy(self, name):
        """停止策略"""
        if name in self.strategyDict:
            strategy = self.strategyDict[name]
            
            if strategy.trading:
                strategy.trading = False
                self.callStrategyFunc(strategy, strategy.onStop)
                
                # 对该策略发出的所有限价单进行撤单
                for vtOrderID, s in self.orderStrategyDict.items():
                    if s is strategy:
                        self.cancelOrder(vtOrderID)
                
                # 对该策略发出的所有本地停止单撤单
                for stopOrderID, so in self.workingStopOrderDict.items():
                    if so.strategy is strategy:
                        self.cancelStopOrder(stopOrderID)   
        else:
            self.writeCtaLog(u'策略实例不存在：%s' %name)    
            
    #----------------------------------------------------------------------
    def initAll(self):
        """全部初始化"""
        for name in self.strategyDict.keys():
            self.initStrategy(name)    
            
    #----------------------------------------------------------------------
    def startAll(self):
        """全部启动"""
        for name in self.strategyDict.keys():
            self.startStrategy(name)


            
    #----------------------------------------------------------------------
    def stopAll(self):
        """全部停止"""
        for name in self.strategyDict.keys():
            self.stopStrategy(name)    
    
    #----------------------------------------------------------------------
    def saveSetting(self):
        """保存策略配置"""
        with open(self.settingfilePath, 'w') as f:
            l = []
            
            for strategy in self.strategyDict.values():
                setting = {}
                for param in strategy.paramList:
                    setting[param] = strategy.__getattribute__(param)
                l.append(setting)
            
            jsonL = json.dumps(l, indent=4)
            f.write(jsonL)
    
    #----------------------------------------------------------------------
    def loadSetting(self):
        """读取策略配置"""
        with open(self.settingfilePath) as f:
            l = json.load(f)
            
            #for setting in l:
            self.loadStrategy(l)
                
        self.loadPosition()

    def getStopOrders(self):
        varDict = []
        for stopOrderID, so in self.workingStopOrderDict.items():
            so_t = copy.copy(so)
            so_t.strategy = None
            varDict.append(so_t)

        return varDict
    #----------------------------------------------------------------------
    def getStrategyVar(self, name):
        """获取策略当前的变量字典"""
        if name in self.strategyDict:
            strategy = self.strategyDict[name]
            varDict = OrderedDict()
            
            for key in strategy.varList:
                varDict[key] = strategy.__getattribute__(key)
            
            return varDict
        else:
            self.writeCtaLog(u'策略实例不存在：' + name)    
            return None
    
    #----------------------------------------------------------------------
    def getStrategyParam(self, name):
        """获取策略的参数字典"""
        if name in self.strategyDict:
            strategy = self.strategyDict[name]
            paramDict = OrderedDict()
            
            for key in strategy.paramList:  
                paramDict[key] = strategy.__getattribute__(key)
            
            return paramDict
        else:
            self.writeCtaLog(u'策略实例不存在：' + name)    
            return None   
        
    #----------------------------------------------------------------------
    def putStrategyEvent(self, name):
        """触发策略状态变化事件（通常用于通知GUI更新）"""
        event = Event(EVENT_DAILY_STRATEGY+name)
        self.eventEngine.put(event)
        
    #----------------------------------------------------------------------
    def callStrategyFunc(self, strategy, func, params=None):
        """调用策略的函数，若触发异常则捕捉"""
        try:
            if params:
                func(params)
            else:
                func()
        except Exception:
            # 停止策略，修改状态为未初始化
            strategy.trading = False
            strategy.inited = False
            
            # 发出日志
            content = '\n'.join([u'策略%s触发异常已停止' %strategy.name,
                                traceback.format_exc()])
            self.writeCtaLog(content)
            
    #----------------------------------------------------------------------
    def savePosition(self, strategy):
        """保存策略的持仓情况到数据库"""
        #flt = {'name': strategy.name,
        #       'vtSymbol': strategy.vtSymbol}
        
        #d = {'name': strategy.name,
        #     'vtSymbol': strategy.vtSymbol,
        #     'pos': strategy.pos}
        
        #self.mainEngine.dbUpdate(POSITION_DB_NAME, strategy.className,  d, flt, True)

        d = PositionData()
        d.pos = strategy.pos
        d.strategyName = strategy.className
        d.symbol = strategy.vtSymbol

        self.mainEngine.mysqlClient.dbUpdate(SQL_TABLENAME_POSITION,d)
        
        content = '策略%s持仓保存成功，当前持仓%s' %(strategy.name, strategy.pos)
        self.writeCtaLog(content)
    
    #----------------------------------------------------------------------
    def loadPosition(self):
        """从数据库载入策略的持仓情况"""
        for strategy in self.strategyDict.values():
            #flt = {'name': strategy.name,
            #       'vtSymbol': strategy.vtSymbol}
            #posData = self.mainEngine.dbQuery(POSITION_DB_NAME, strategy.className, flt)
            d = PositionData()
            d.strategyName = strategy.className
            d.symbol = strategy.vtSymbol

            posData = self.mainEngine.mysqlClient.dbSelect(SQL_TABLENAME_POSITION,d, "one")
            if posData:
                strategy.pos = posData['pos']


                
    #----------------------------------------------------------------------
    def roundToPriceTick(self, priceTick, price):
        """取整价格到合约最小价格变动"""
        if not priceTick:
            return price
        
        newPrice = round(price/priceTick, 0) * priceTick
        return newPrice    
    
    #----------------------------------------------------------------------
    def stop(self):
        """停止"""
        pass


    #---------------------------------------------------------------------
    def cancelAllStop(self,symbol, strategy_name):
        ##撤销所有的停止单
        s = self.strategyOrderDict[symbol+strategy_name]

        for orderID in list(s):
            if STOPORDERPREFIX in orderID:
                self.cancelStopOrder(orderID)


    #----------------------------------------------------------------------
    def cancelAll(self, symbol, strategy_name):
        """全部撤单"""
        s = self.strategyOrderDict[symbol+strategy_name]
        
        # 遍历列表，全部撤单
        # 这里不能直接遍历集合s，因为撤单时会修改s中的内容，导致出错
        for orderID in list(s):
            if STOPORDERPREFIX in orderID:
                self.cancelStopOrder(orderID)
            else:
                self.cancelOrder(orderID)


    #------------------------------------------------
    # 数据回放相关
    #------------------------------------------------
    def getProductContractList(self, startTime, symbol):
        """  合约前缀+当前日期后12个月  """


        number_0 = symbol.count('0')
        listContract = []
        for i in range(11):
            time_aaa = startTime + pd.tseries.offsets.DateOffset(months=i,days=0)
            if number_0 == 3:
                listContract.append(symbol[0:len(symbol)-number_0] +str(time_aaa.year)[3:4]+str(time_aaa.month).zfill(2))
            if number_0 == 4:
                listContract.append(symbol[0:len(symbol)-number_0] +str(time_aaa.year)[2:4]+str(time_aaa.month).zfill(2))

        return listContract

    ## 判断主力合约
    def getMainContact(self, dateTime , listContract):
        mianSymbol = None
        volume = 0
        for contract in listContract:
            #print contract
             #加载日线file
            kData = self.readDayData(dateTime,contract)
            if not kData:
                continue

            if  kData and kData["volume"] > volume:
                mianSymbol = kData["symbol"]
                volume = kData["volume"]

        return mianSymbol

    ##读取日线文件到那天的数据
    def readDayData(self, dateTime,contract ):

        startDate = self.today - timedelta(20)  ##一般假期不会多于10天吧
        d = {'datetime':{'$gte':startDate}}
        dayData = self.mainEngine.dbQuery(DAY_DB_NAME, contract, d, 'datetime')

        if len(dayData) == 0:
            return None

        return dayData[-1]

    ##获取账户可用资金比率    账户可用资金/ 净值
    def getAccountAvailableRate(self):

        return (self.account.available)/self.account.balance

    ###根据合约号获取产品  比如 rb1805获取 rb0000
    def getProductBySymbol(self, symbol):
        for key, value in self.symbolInfoList.items():
            if len(symbol) == value["length"] and symbol.startswith(value["pre"]):
                return value

        return None

    def getSymbolMaxVolume(self,symbol):
        symbolInfo = self.getProductBySymbol(symbol)
        if symbolInfo:
            return symbolInfo["maxVolume"]

        return 0