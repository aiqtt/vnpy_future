# encoding: UTF-8

'''
本文件中实现了风控引擎，用于提供一系列常用的风控功能：
1. 委托流控（单位时间内最大允许发出的委托数量）
2. 总成交限制（每日总成交数量限制）
3. 单笔委托的委托数量控制
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
from vnpy.trader.vtGateway import VtLogData
from vnpy.trader.vtFunction import *
from vnpy.trader.data.mysqlEngine import SQL_TABLENAME_POSITION, SQL_TABLENAME_STOP_ORDER,SQL_TABLENAME_TRADER
from vnpy.trader.app.dailyStrategy.dailyEngine import  EVENT_DAILY_LOG ,EVENT_DAILY_STRATEGY,ENGINETYPE_TRADING
from vnpy.trader.app.gEntityObject import *
from vnpy.trader.app.ctaStrategy.strategy import STRATEGY_CLASS
from vnpy.trader.app.ctaStrategy.ctaBase import *


########################################################################
class MmEngine(object):
    #读取策略配置

    STATUS_FINISHED = set([STATUS_REJECTED, STATUS_CANCELLED, STATUS_ALLTRADED])
    FIX_SIZE_AUDO = -1
    name = u'监控界面模块'

    #----------------------------------------------------------------------
    def __init__(self, mainEngine, eventEngine):
        """Constructor"""
        settingFileName = 'Daily_setting.json'
        self.settingfilePath = getJsonPath(settingFileName, __file__)
        self.mainEngine = mainEngine
        self.eventEngine = eventEngine
        mainEngine.MmEngine = self
        self.lastOpenTrade = {}  ##最后一次开仓记录  key  symbol
        self.traderDict = {}  ##交易记录   key为vtOrderID
        # # 引擎类型为实盘
        # self.engineType = ENGINETYPE_TRADING
        self.engineType=EVENT_TICK

        # 注册日式事件类型
        self.mainEngine.registerLogEvent(EVENT_CTA_LOG)
        # 注册事件监听
        self.registerEvent()
    #----------------------------------------------------------------------
    def loadSetting(self):
        """读取配置"""
        with open(self.settingfilePath) as f:
            d = json.load(f)
            name = d['name']
            className = d['className']

            # 获取策略类
            strategyClass = STRATEGY_CLASS.get(className, None)
            if not strategyClass:
                self.writeCtaLog(u'找不到策略类：%s' % className)
                return
            strategy = strategyClass(self, d)

            # 设置风控参数
            self.active = d['active']

            self.orderFlowLimit = d['orderFlowLimit']
            self.orderFlowClear = d['orderFlowClear']

            self.orderSizeLimit = d['orderSizeLimit']

            self.tradeLimit = d['tradeLimit']

            self.workingOrderLimit = d['workingOrderLimit']

            self.orderCancelLimit = d['orderCancelLimit']
            
            self.marginRatioLimit = d['marginRatioLimit']
    def getTraderOrders(self):
        ##读数据库
        traderOrd = TraderOrder()
        # traderOrd.strategyName = className
        traderOrd.offset = OFFSET_OPEN
        t = self.mainEngine.mysqlClient.dbSelect(SQL_TABLENAME_TRADER, traderOrd, "all")

        if t:
            varTraderDict = []
            for i in t:
                order=TraderOrder()
                # order.strategyName = className
                order.offset = OFFSET_OPEN
                order.orderID = i["orderID"]
                order.orderUuid = i["orderUuid"]
                order.direction = i["direction"]
                order.orderVolume = i["orderVolume"]
                order.orderPrice = i["orderPrice"]
                order.tradeVolume = i["tradeVolume"]
                order.tradePrice = i["tradePrice"]
                order.symbol=i["symbol"]
                varTraderDict.append(order)
            return varTraderDict
    def getStopOrders(self):

        varDict = []
        for stopOrderID, so in self.workingStopOrderDict.items():
            so_t = copy.copy(so)
            so_t.strategy = None
            varDict.append(so_t)

            return varDict
    #----------------------------------------------------------------------
    def saveSetting(self):
        """保存风控参数"""
        with open(self.settingfilePath, 'w') as f:
            # 保存风控参数
            d = {}

            d['active'] = self.active

            d['orderFlowLimit'] = self.orderFlowLimit
            d['orderFlowClear'] = self.orderFlowClear

            d['orderSizeLimit'] = self.orderSizeLimit

            d['tradeLimit'] = self.tradeLimit

            d['workingOrderLimit'] = self.workingOrderLimit

            d['orderCancelLimit'] = self.orderCancelLimit
            
            d['marginRatioLimit'] = self.marginRatioLimit

            # 写入json
            jsonD = json.dumps(d, indent=4)
            f.write(jsonD)

    #----------------------------------------------------------------------
    def registerEvent(self):
        """注册事件监听"""
        self.eventEngine.register(EVENT_ACCOUNT, self.updateAccount)

# # ----------------------------------------------------------------------

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
    def updateTimer(self, event):
        """更新定时器"""
        self.orderFlowTimer += 1

        # 如果计时超过了流控清空的时间间隔，则执行清空
        if self.orderFlowTimer >= self.orderFlowClear:
            self.orderFlowCount = 0
            self.orderFlowTimer = 0

    #----------------------------------------------------------------------
    def updateAccount(self, event):
        """账户资金更新"""
        account = event.dict_['data']
        
        # 计算保证金占比
        ratio = 0
        if account.balance:
            ratio = account.margin / account.balance
        
        # 更新到字典中
        self.marginRatioDict[account.gatewayName] = ratio

    #----------------------------------------------------------------------
    def writeRiskLog(self, content):
        """快速发出日志事件"""
        # 发出报警提示音

        if platform.uname() == 'Windows':
            import winsound
            winsound.PlaySound("SystemHand", winsound.SND_ASYNC)

        # 发出日志事件
        log = VtLogData()
        log.logContent = content
        log.gatewayName = self.name
        event = Event(type_=EVENT_LOG)
        event.dict_['data'] = log
        self.eventEngine.put(event)


    #----------------------------------------------------------------------
    def stop(self):
        """停止"""
        #self.saveSetting()
        pass
        
