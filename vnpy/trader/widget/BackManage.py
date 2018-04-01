# encoding: UTF-8
from vnpy.trader.uiCrosshair import Crosshair
import pyqtgraph as pg
# 其他
import numpy as np
import pandas as pd
from functools import partial
from datetime import datetime,timedelta
from collections import deque
from vnpy.trader.uiBasicWidget import *
from vnpy.trader.widget.uiKLine import *
from vnpy.trader.uiBackMainWindow import *

import talib
from vnpy.trader.vtFunction import *
import qdarkstyle #Qt黑色主题

########################################################################

class BackManager(QtWidgets.QMainWindow):
    signal = QtCore.Signal(type(Event()))

    def __init__(self, main,tradePath,filePath,optKType):
        super(BackManager, self).__init__()
        self.mainWindow = main
        self.stopOrderMonitor = None
        self.klineDay = None
        self.klineOpt = None

        self.dayBarData = {}
        self.hourBarData = {}
        self.daySarData={}
        self.hourSarData = {}
        self.hourListSig={}
        self.currrentSymbol = ""
        self.csvTradeData=self.loadcsvTradeData(tradePath)
        self.optKType=optKType
        self.filePath = filePath
        self.initUi()
        self.symbolSelect()
    #----------------------------------------------------------------------
    def initUi(self):
        """初始化界面"""
        ##K线跟随

        for  opt in  self.optKType:
            if opt=="day":
                self.klineDay = KLineWidget(name="day")
                self.mainWindow.createDock(self.klineDay,'day', u"周线", QtCore.Qt.RightDockWidgetArea,True)
            else:
                self.klineOpt = KLineWidget(name="opt="+opt)
                self.mainWindow.createDock(self.klineOpt,'opt'+opt, u"操作周期线", QtCore.Qt.RightDockWidgetArea,True)



        ##持仓量
        self.stopOrderMonitor = StopOrderMonitor()
        self.mainWindow.createDock(self.stopOrderMonitor, 'stopOrderMonitor', u"持仓量",QtCore.Qt.LeftDockWidgetArea, False)
        self.stopOrderMonitor.cellDoubleClicked.connect(self.symbolSelect)  # 注册signal
        self.stopOrderMonitor.setMaximumWidth(456)
        self.stopOrderMonitor.setMinimumWidth(456)
        self.updateMonitor()  ##更新一下数据

        self.mainWindow.saveWindowSettings('default')

    def setPath(self,path):
        self.filePath = path
    #################################################################################################################################
    def updateMonitor(self):
        varDict=[]
        ##更新合约
        tradeCount = self.csvTradeData.shape[0]
        curentIndex = 1
        while curentIndex<tradeCount:
            varSymbol=VtOrderData()
            varSymbol.symbol=self.csvTradeData.ix[[curentIndex]].values[0][3]  ##合约
            varSymbol.orderTime= self.csvTradeData.ix[[curentIndex]].values[0][0]  ##时间
            varSymbol.direction=self.csvTradeData.ix[[curentIndex]].values[0][7]
            varSymbol.offset=self.csvTradeData.ix[[curentIndex]].values[0][8]
            varSymbol.price=self.csvTradeData.ix[[curentIndex]].values[0][9]
            varSymbol.volume=self.csvTradeData.ix[[curentIndex]].values[0][10]
            if type(varSymbol.symbol) == float:#排除空数据
                curentIndex += 1
                continue

            varDict.append(varSymbol)
            curentIndex += 1

        self.stopOrderMonitor.updateAllData(varDict)
    #---------------------------------------------------------------------------
        ##显示合约k线

    def symbolSelect(self, row=None, column=None):
        if  row==None:
            row=0

        symbol = self.stopOrderMonitor.item(row, 0).text()
        print (symbol)
        if symbol:
            self.loadKlineData(symbol)

    def loadKlineData(self, symbol):
        if self.currrentSymbol == symbol:
            return;
        self.currrentSymbol = symbol
        self.loadBar(symbol)
        self.loadSig(symbol)

        # 插入bar数据
        for opt in self.optKType:
            if opt=="day":
                self.klineDay.KLtitle.setText(symbol + "opt=day", size='10pt')
                self.klineDay.loadDataBar(self.dayBarData[symbol])
            else:
                self.klineOpt.KLtitle.setText(symbol + " opt="+opt, size='10pt')
                self.klineOpt.loadDataBar(self.hourBarData[symbol])
        self.klineOpt.updateSig(self.hourListSig[symbol])





    ############################################################################
    # 加载kline数据
    def loadBar(self, symbol):
        for opt in self.optKType:
            if opt=="day":
                if not self.dayBarData.has_key(symbol):
                   dbDayList = self.loadAllBarFromDb('day', symbol)
                   self.dayBarData[symbol] = dbDayList
            else:
                if not self.hourBarData.has_key(symbol):
                    dbHourList = self.loadAllBarFromDb(opt, symbol)
                    self.hourBarData[symbol] = dbHourList


    def loadSig(self, symbol):
        txtData = self.hourBarData[symbol]
        count = self.hourBarData[symbol].shape[0]
        tradeCount = self.csvTradeData.shape[0]

        listSig = [None for i in range(count)]
        curentIndex = 0
        for dataIndex in range(count):
            if dataIndex == count - 1:  ##去掉最后一个
                break;

            listSig[dataIndex] = None
            data_time_tmp = txtData.ix[[dataIndex]].values[0][8]  ##时间
            index_time = datetime.strptime(data_time_tmp, "%Y-%m-%d %H:%M:%S")

            data_time_tmp_next = txtData.ix[[dataIndex + 1]].values[0][8]  ##时间
            index_time_next = datetime.strptime(data_time_tmp_next, "%Y-%m-%d %H:%M:%S")

            while curentIndex < tradeCount:

                tra_time_str = self.csvTradeData.ix[[curentIndex]].values[0][0]  ##时间
                if (self.csvTradeData.ix[[curentIndex]].values[0][3] != self.currrentSymbol):
                    curentIndex += 1
                    continue
                if type(tra_time_str) == float:  ##Nan
                    curentIndex += 1
                    continue

                tra_time = datetime.strptime(tra_time_str, "%Y-%m-%d %H:%M:%S")  ##2014-01-09 09:06:00

                index_time_end = index_time + timedelta(hours=1)

                if index_time_next < tra_time:
                    break

                if index_time <= tra_time and index_time_next > tra_time:
                    sigDataa = {"direction": self.csvTradeData.ix[[curentIndex]].values[0][7],
                                "offset": self.csvTradeData.ix[[curentIndex]].values[0][8],
                                "price": self.csvTradeData.ix[[curentIndex]].values[0][9]}
                    listSig[dataIndex] = sigDataa

                curentIndex += 1
        self.hourListSig[symbol] = listSig


        # ----------------------------------------------------------------------

    def loadAllBarFromDb(self, dbName, collectionName):
        # """从数据库中读取Bar数据，startDate是datetime对象"""
        # d = {}
        # if self.zzsdEngine.client:  ##rpc模式
        #     barData = self.zzsdEngine.client.mainEngine.dbQuery(dbName, collectionName, d)
        # else:
        #     barData = self.zzsdEngine.mainEngine.dbQuery(dbName, collectionName, d)
        d = {}
        # 本地读取Bar数据
        fullFilePath = self.filePath + dbName + "/" + collectionName + ".txt"
        barData = pd.DataFrame.from_csv(fullFilePath, header=None, index_col=7)
        barData = barData.rename(
            columns={0: 'symbol', 1: "vtSymbol", 2: "exchange", 3: "open", 4: "high", 5: "low", 6: "close", 7: "date",
                     8: "time", 9: "datetime", 10: "volume", 11: "openInterest"})
        return barData
    def loadcsvTradeData(self,tradePath):
       if  tradePath:
            fieldnames = ['dt', 'symbol', 'exchange', 'vtSymbol', 'tradeID', 'vtTradeID', 'orderID', 'vtOrderID',
                          'direction', 'offset', 'price', 'volume', 'tradeTime', "gatewayName", "rawData"]
            if os.path.exists(tradePath):
                return pd.DataFrame.from_csv(tradePath, encoding="utf_8_sig", index_col=7)
       return None
    #----------------------------------------------------------------------
    def createDock(self, widget, widgetName, widgetArea):
        """创建停靠组件"""
        dock = QtWidgets.QDockWidget(widgetName)
        dock.setWidget(widget)
        dock.setObjectName(widgetName)
        dock.setFeatures(dock.DockWidgetFloatable|dock.DockWidgetMovable)
        self.addDockWidget(widgetArea, dock)
        return widget, dock
#############################################################################

class StopOrderMonitor(BasicMonitor):
    """日志监控"""
    #----------------------------------------------------------------------
    def __init__(self, parent=None):
        """Constructor"""
        super(StopOrderMonitor, self).__init__( parent)


        d = OrderedDict()
        d['symbol'] = {'chinese': u"合约", 'cellType':BasicCell}
        d['orderTime'] = {'chinese': u"时间", 'cellType':BasicCell}
        d['direction'] = {'chinese':u"direction", 'cellType':BasicCell}
        d['offset'] = {'chinese':u"offset", 'cellType':BasicCell}
        d['price'] = {'chinese':u"price", 'cellType':BasicCell}
        d['volume'] = {'chinese':u"volume", 'cellType':BasicCell}

        self.setHeaderDict(d)
        self.setFont(BASIC_FONT)
        self.initTable()

