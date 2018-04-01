# encoding: UTF-8

'''
风控模块相关的GUI控制组件
'''


from vnpy.event import Event
from vnpy.trader.vtEvent import *
from vnpy.trader.uiBasicWidget import QtGui, QtCore, QtWidgets, BasicCell
from vnpy.trader.widget.uiKLine import *
from vnpy.trader.uiBasicWidget import *
from collections import OrderedDict
# from vnpy.trader.app.dailyStrategy.dailyEngine import  EVENT_DAILY_LOG ,EVENT_DAILY_STRATEGY
from vnpy.trader.app.dailyStrategy.dailyBase import *   #  DAY_DB_NAME,MINUTE_30_DB_NAME,MINUTE_60_DB_NAME,MINUTE_5_DB_NAME,MINUTE_DB_NAME,WEEK_DB_NAME
from vnpy.trader.indicator.SAR import  *
from vnpy.trader.vtEngine import *
import timer
import time
import threading as thd
from  vnpy.trader.vtFunction import *
from vnpy.trader.gateway.ctpGateway import *
from vnpy.trader.vtEngine import *
from vnpy.trader.uiBasicWidget import *



########################################################################
class MmEngineManager(QtWidgets.QMainWindow):#QWidget
    """监控引擎的管理组件"""

    signal = QtCore.Signal(type(Event()))
    signal_tick = QtCore.Signal(type(Event()))
    settingFileName = 'Daily_setting.json'
    settingfilePath = getJsonPath(settingFileName, __file__)

    def __init__(self, MmEngine, eventEngine, parent=None):
        """Constructor"""
        super(MmEngineManager, self).__init__(parent)

        self.MmEngine = MmEngine
        self.eventEngine = eventEngine
        self.isReplay = False  ##监控

        # 监控的事件类型
        self.eventType = EVENT_TICK
        if isinstance(self.MmEngine.mainEngine, MainEngine) == True:
            print("replay")
            self.isReplay = True  ##复盘

        self.name = "zzsd"

        self.stopOrderMonitor = None
        self.traderOrderMonitor=None
        self.klineDay = None
        self.klineOpt = None

        self.symbolText=None
        self.dayBarData = {}
        self.hourBarData = {}
        self.hourSarData = {}
        self.currrentSymbol = None
        self.currrentXmin = None
        self.initUi()


    # ----------------------------------------------------------------------
    def initUi(self):
        """初始化界面"""
        self.setWindowTitle(u"监控界面")
        self. initMenu()

        ##log
        self.logMonitor = LogMonitor(self.MmEngine, self.eventEngine)
        widgetLogM, dockLogM = self.createDock(self.logMonitor, u"log", QtCore.Qt.LeftDockWidgetArea)
        ##行情
        self.marketMonitor = MarketMonitor(self.MmEngine, self.eventEngine)
        widgetMarketM, dockMarketM = self.createDock(self.marketMonitor, vtText.MARKET_DATA,
                                                     QtCore.Qt.LeftDockWidgetArea)
        ##合约
        self.symbolMonitor=ContractManager(self.MmEngine,self.eventEngine,self)
        widgetSymbolM, dockLogM = self.createDock(self.symbolMonitor, u"订阅合约", QtCore.Qt.LeftDockWidgetArea)

        ##成交单
        self.traderOrderMonitor = TraderOrderMonitor(None, self.eventEngine)
        widgetStopOrderM, dockStopOrderM = self.createDock(self.traderOrderMonitor, u"成交单", QtCore.Qt.LeftDockWidgetArea)
        self.updateTraderMonitor()  ##更新一下数据
        self.traderOrderMonitor.cellDoubleClicked.connect(self.symbolSelect)
        self.logMonitor.setMaximumWidth(575)
        self.traderOrderMonitor.setMaximumWidth(575)
        ##K线跟随
        self.klineOpt = KLineWidget(name="opt")
        widgetklineOptM, dockklineOptM = self.createDock(self.klineOpt, u"操作周期线", QtCore.Qt.RightDockWidgetArea)
        # self.klineDay = KLineWidget(name="day")
        # widgetklineDayM, dockklineDayM = self.createDock(self.klineDay, u"周线", QtCore.Qt.RightDockWidgetArea)


        if self.isReplay == True:
            self.fun_timer()#每隔5秒执行一次加载交易数据的函数和日志函数updateTraderMonitor()，updateLogMonitor()

            self.refreshTimer = thd.Timer(60, self.fun_timer)
            self.refreshTimer.start()

    def fun_timer(self):
        ##加载交易数据
        self.updateTraderMonitor()
        ##加载log数据
        self.updateLogMonitor()


    def closeEvent(self, event):
        if self.refreshTimer:
            self.refreshTimer.cancel()

    def initMenu(self):
        """初始化菜单"""
        # 创建菜单
        menubar = self.menuBar()
        self.cycle = ["1min", "3min", "5min", "15min", "30min", "1H", "day"]
        n = 0
        for item in self.cycle:
            action = QtWidgets.QAction(item, self)
            menubar.addAction(action)
            try:
                action.triggered[()].connect(
                    lambda item=item: self.cycleAction(item))#一个空元组用于指定触发的信号。如果没有这样做，触发信号将在默认情况下发送一个布尔值，这将阻塞lambda的项目参数。
            finally:
                pass

    def cycleAction(self,cycle):
        self.loadXKlineData(self.currrentSymbol,cycle)




    def logSelect(self, row=None, column=None):

        content = self.logMonitor.item(row, 1).text()
        print(content)
        if content and content.startswith("subscribe===") == True:
            symbol = content[len("subscribe==="):len(content)]
            self.loadKlineData(symbol)

    ##显示合约k线
    def symbolSelect(self, row=None, column=None):
        symbol = self.traderOrderMonitor.item(row, 1).text()
        print(symbol)
        if symbol:
            self.loadKlineData(symbol)

    ##显示合约k线
    def symbolSelectMarket(self, row=None, column=None):
        symbol = self.marketMonitor.item(row, 0).text()
        if symbol:
            self.loadKlineData(symbol)
    def loadKlineData(self, symbol):

        if self.currrentSymbol == symbol:
            return;
        self.subscribeEvent(symbol)  # 订阅合约
        self.currrentSymbol = symbol
        print symbol

        self.loadBar(symbol)

        # self.klineDay.clearData()
        self.klineOpt.clearData()

        self.klineOpt.KLtitle.setText(symbol + " opt", size='20pt')
        self.klineOpt.loadDataBarArray(self.hourBarData[symbol].barData)
    def  subscribeEvent(self,symbol):
        # # 重新注册事件监听
        # self.eventEngine.unregister(EVENT_TICK + self.currrentSymbol, self.signal_tick.emit)
        self.signal_tick.connect(self.updateEvent)
        self.eventEngine.register(EVENT_TICK + symbol, self.signal_tick.emit)
        self.signal_tick.connect(self.processTickEvent)
        self.eventEngine.register(EVENT_TICK + symbol, self.signal_tick.emit)
        # 订阅行情

        req = VtSubscribeReq()
        req.symbol = symbol
        # req.exchange ="SHFE"
        self.MmEngine.mainEngine.subscribe(req, "CTP")
    # ----------------------------------------------------------------------
    def updateEvent(self, event):
        """收到事件更新"""
        data = event.dict_['data']
        self.marketMonitor.updateData(data)

    def loadXKlineData(self, symbol,xmin):

        if self.currrentSymbol == symbol and  self.currrentXmin==xmin:
            return;
        # 订阅合约
        self.subscribeEvent(symbol)
        self.currrentSymbol = symbol
        self.currrentXmin=xmin
        print symbol

        self.loadXBar(symbol,xmin)

        self.klineOpt.clearData()
        self.klineOpt.KLtitle.setText(symbol + " opt="+xmin, size='20pt')
        if xmin=="day":
            self.klineOpt.loadDataBarArray(self.dayBarData[symbol].barData)
        else:
            self.klineOpt.loadDataBarArray(self.hourBarData[symbol].barData)
        # 初始化sar指标
        self.klineOpt.initIndicator("SAR")

    def refreshKline(self, symbol):
        if self.hourBarData.has_key(symbol):
            hourBar = VtBarData()
            hourBar.__dict__ = self.hourBarData[symbol].barData[-1]

            self.klineOpt.onBar(hourBar)


    def loadBar(self, symbol):
            """读取策略配置"""
            with open(self.settingfilePath) as f:
                l = json.load(f)

            db = MINUTE_5_DB_NAME
            xmin = 5
            self.currrentXmin=5
            if  xmin=="day":
                if not self.dayBarData.has_key(symbol):
                    dbDayList = self.loadAllBarFromDb(DAY_DB_NAME, symbol)
                    self.dayBarData[symbol] = BarManager(dbDayList, symbol, isDay=True)
            else:
                # if not self.hourBarData.has_key(symbol):
                dbHourList = self.loadAllBarFromDb(db, symbol)
                self.hourBarData[symbol] = BarManager(dbHourList, symbol, xmin)

    def loadXBar(self, symbol,cycle):

        db = MINUTE_5_DB_NAME
        xmin = 5
        if cycle == 'week':
            db = WEEK_DB_NAME
        elif cycle == 'day':
            db = DAILY_DB_NAME
            xmin="day"
        elif  cycle=='1H':
            xmin = 60
            db = MINUTE_60_DB_NAME
        else:
            xmin=cycle_number[cycle]
            db=cycle_db[cycle]

        self.currrentXmin = xmin
        if xmin=="day":
            if not self.dayBarData.has_key(symbol):
                dbDayList = self.loadAllBarFromDb(DAY_DB_NAME,symbol)

                self.dayBarData[symbol] = BarManager(dbDayList,symbol,isDay=True)
        else:
            # if  not self.hourBarData.has_key(symbol):
            dbHourList = self.loadAllBarFromDb(db, symbol)
            self.hourBarData[symbol] = BarManager(dbHourList, symbol, xmin)

    # ----------------------------------------------------------------------
    def loadAllBarFromDb(self, dbName, collectionName):
        """从数据库中读取Bar数据，startDate是datetime对象"""
        d = {}
        if hasattr(self.MmEngine, "client"):  ##rpc模式
            barData = self.MmEngine.client.mainEngine.dbQuery(dbName, collectionName, d, 'datetime')
        else:
            barData = self.MmEngine.mainEngine.dbQuery(dbName, collectionName, d, 'datetime')

        return barData
    def updateLogMonitor(self):
        logList = self.MmEngine.mainEngine.mysqlClient.dbSelect(SQL_TABLENAME_LOG, None, "all")
        for log in logList:
            logEntity = VtLogData()
            logEntity.gatewayName = log["gatewayName"]
            logEntity.logContent = log["logContent"]
            logEntity.logLevel = log["logLevel"]
            logEntity.logTime = log["logTime"]
            self.logMonitor.updateData(logEntity)

        ##日志table加入click事件  subscribe===
        self.logMonitor.cellDoubleClicked.connect(self.logSelect)
    def updateTraderMonitor(self):
        ##更新交易单
        varOrders = self.MmEngine.getTraderOrders()
        self.traderOrderMonitor.updateAllData(varOrders)
        # ----------------------------------------------------------------------

    def processTickEvent(self, event):
        """收到事件更新"""
        tick = event.dict_['data']

        if self.dayBarData.has_key(tick.symbol):
           self.dayBarData[tick.symbol].updateTick(tick)

        if self.hourBarData.has_key(tick.symbol):
            self.hourBarData[tick.symbol].updateTick(tick)

        if self.currrentSymbol == tick.symbol:
            self.refreshKline(tick.symbol)

    # ----------------------------------------------------------------------
    def createDock(self, widget, widgetName, widgetArea):
        """创建停靠组件"""
        dock = QtWidgets.QDockWidget(widgetName)
        dock.setWidget(widget)
        dock.setObjectName(widgetName)
        dock.setFeatures(dock.DockWidgetFloatable | dock.DockWidgetMovable)
        self.addDockWidget(widgetArea, dock)
        return widget, dock

 ########################################################################
class TraderOrderMonitor(BasicMonitor):
    """日志监控"""
    def __init__(self, mainEngine, eventEngine, parent=None):
        """Constructor"""
        super(TraderOrderMonitor, self).__init__(mainEngine, eventEngine, parent)

        d = OrderedDict()
        d['orderID'] = {'chinese': u"订单ID", 'cellType': BasicCell}
        d['symbol'] = {'chinese': u"合约", 'cellType': BasicCell}
        d['orderUuid'] = {'chinese': u"订单编号", 'cellType': BasicCell}
        d['direction'] = {'chinese': u"方向", 'cellType': BasicCell}
        # d['offset'] = {'chinese': u"offset", 'cellType': BasicCell}
        d['tradePrice'] = {'chinese': u"交易价格", 'cellType': BasicCell}
        d['tradeVolume'] = {'chinese': u"tradeVolume", 'cellType': BasicCell}

        self.setHeaderDict(d)

        self.setFont(BASIC_FONT)
        self.initTable()
########################################################################
########################################################################
class ContractManager(QtWidgets.QWidget):
    """合约管理组件"""
    signal = QtCore.Signal(type(Event()))
    # ----------------------------------------------------------------------
    def __init__(self,mainEngine, eventEngine, parent):
        """Constructor"""
        super(ContractManager, self).__init__(parent=parent)

        self.eventEngine = eventEngine
        self.mainEngine=mainEngine
        self.parent=parent
        self.initUi()

    # ----------------------------------------------------------------------
    def initUi(self):
        """初始化界面"""
        self.lineSymbol = QtWidgets.QLineEdit(u'rb1805')
        self.pushButton = QtWidgets.QPushButton(u'订阅合约')

        self.pushButton.clicked.connect(self.symbolTextSelect)
        hbox = QtWidgets.QHBoxLayout()
        hbox.addWidget(self.lineSymbol)
        hbox.addWidget(self.pushButton)
        hbox.addStretch()

        vbox = QtWidgets.QVBoxLayout()
        vbox.addLayout(hbox)

        self.setLayout(vbox)

    def symbolTextSelect(self):
        self.symbolText = self.lineSymbol.text()
        print(self.symbolText)
        if self.symbolText:
            self.parent.loadKlineData(str(self.symbolText))

########################################################################
class StopOrderMonitor(BasicMonitor):
    """日志监控"""

    # ----------------------------------------------------------------------
    def __init__(self, mainEngine, eventEngine, parent=None):
        """Constructor"""
        super(StopOrderMonitor, self).__init__(mainEngine, eventEngine, parent)


        d = OrderedDict()
        d['vtSymbol'] = {'chinese': u"合约", 'cellType': BasicCell}
        d['orderType'] = {'chinese': u"类型", 'cellType': BasicCell}
        d['direction'] = {'chinese': u"方向", 'cellType': BasicCell}
        d['offset'] = {'chinese': u"offset", 'cellType': BasicCell}
        d['price'] = {'chinese': u"价格", 'cellType': BasicCell}
        d['volume'] = {'chinese': u"volume", 'cellType': BasicCell}
        d['status'] = {'chinese': u"status", 'cellType': BasicCell}

        self.setHeaderDict(d)

        self.setFont(BASIC_FONT)
        self.initTable()


########################################################################
class LogMonitor(BasicMonitor):
    """日志监控"""

    # ----------------------------------------------------------------------
    def __init__(self, mainEngine, eventEngine, parent=None):
        """Constructor"""
        super(LogMonitor, self).__init__(mainEngine, eventEngine, parent)

        d = OrderedDict()
        d['logTime'] = {'chinese': u"time", 'cellType': BasicCell}
        d['logContent'] = {'chinese': u"content", 'cellType': BasicCell}
        d['gatewayName'] = {'chinese': u"gateway", 'cellType': BasicCell}
        self.setHeaderDict(d)

        # self.setEventType(EVENT_DAILY_LOG)
        self.setFont(BASIC_FONT)
        self.initTable()
        self.registerEvent()


########################################################################
class MarketMonitor(BasicMonitor):
    """市场监控组件"""

    # ----------------------------------------------------------------------
    def __init__(self, mainEngine, eventEngine, parent=None):
        """Constructor"""
        super(MarketMonitor, self).__init__(mainEngine, eventEngine, parent)

        # 设置表头有序字典
        d = OrderedDict()
        d['symbol'] = {'chinese': u"合约", 'cellType': BasicCell}
        d['lastPrice'] = {'chinese': u"最新价", 'cellType': BasicCell}
        d['volume'] = {'chinese': u"仓位", 'cellType': BasicCell}

        self.setHeaderDict(d)

        # 设置数据键
        self.setDataKey('symbol')

        # 设置监控事件类型
        self.setEventType(EVENT_TICK)

        # 设置字体
        self.setFont(BASIC_FONT)

        # 设置允许排序
        self.setSorting(True)

        # 初始化表格
        self.initTable()

        # 注册事件监听
        self.registerEvent()


########################################################################
class BarManager(object):
    """
    K线合成器，支持：

    """

    # ----------------------------------------------------------------------
    def __init__(self, initBarList, symbol, xmin=None, isDay=False):
        """Constructor"""

        self.symbol = symbol
        self.barData = initBarList  # bar数组

        self.isDay = isDay
        self.dayHasAppend = False

        self.xmin = xmin  # X的值

        self.lastTick = None  # 上一TICK缓存对象

    ##========-----------------------------
    def updateTickDay(self, tick):
        if self.dayHasAppend == False:
            tick.datetime = datetime.strptime(' '.join([tick.date, tick.time]), '%Y%m%d %H:%M:%S.%f')
            bar_day = {}
            bar_day["vtSymbol"] = tick.vtSymbol
            bar_day["symbol"] = tick.symbol
            bar_day["exchange"] = tick.exchange

            bar_day["open"] = tick.lastPrice
            bar_day["high"] = tick.lastPrice
            bar_day["low"] = tick.lastPrice
            bar_day["datetime"] = tick.datetime

            self.barData.append(bar_day)
            self.dayHasAppend = True

        bar_day = self.barData[-1]

        bar_day["high"] = max(bar_day["high"], tick.lastPrice)
        bar_day["low"] = min(bar_day["low"], tick.lastPrice)

        # 通用更新部分
        bar_day["close"] = tick.lastPrice
        bar_day["openInterest"] = tick.openInterest
        bar_day["volume"] = 10  ##没有用

    def updateTick(self, tick):
        if self.symbol == tick.symbol:
            if self.isDay == True:
                self.updateTickDay(tick)
            else:
                self.updateTickOpt(tick)

    # ----------------------------------------------------------------------
    def updateTickOpt(self, tick):
        """TICK更新"""
        if  tick:
            tick.datetime=datetime.strptime(' '.join([tick.date, tick.time]), '%Y%m%d %H:%M:%S.%f')
            optBar = self.barData[-1]
            if tick.datetime.minute % self.xmin == 0 or optBar["datetime"].day != tick.datetime.day:

                if optBar["datetime"].minute != tick.datetime.minute:
                    optBar = {}
                    optBar["vtSymbol"] = tick.vtSymbol
                    optBar["symbol"] = tick.symbol
                    optBar["exchange"] = tick.exchange

                    optBar["open"] = tick.lastPrice
                    optBar["high"] = tick.lastPrice
                    optBar["low"] = tick.lastPrice
                    optBar["datetime"] = tick.datetime

                    self.barData.append(optBar)

            optBar["high"] = max(optBar["high"], tick.lastPrice)
            optBar["low"] = min(optBar["low"], tick.lastPrice)

            # 通用更新部分
            optBar["close"] = tick.lastPrice
            optBar["openInterest"] = tick.openInterest
            optBar["volume"] = 10  ##没有用
