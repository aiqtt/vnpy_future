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
from vnpy.trader.uiKLine import *
from vnpy.trader.uiBackMainWindow import *

import talib
from vnpy.trader.vtFunction import *
import qdarkstyle #Qt黑色主题
from   vnpy.trader.indicator.SAR import *

import sys
reload(sys)
sys.setdefaultencoding('utf8')

########################################################################
class BackManager(object):
    signal = QtCore.Signal(type(Event()))
    #signal=QtCore.pyqtSignal(type(tuple([])))

    def __init__(self, parent=None, man=None):
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
        self.initUi()
    #----------------------------------------------------------------------
    def initUi(self):
        """初始化界面"""
        ##K线跟随

        self.klineOpt = KLineWidget(name="opt")
        self.mainWindow.createDock(self.klineOpt,'opt', u"操作周期线", QtCore.Qt.RightDockWidgetArea,True)

        #self.klineDay = KLineWidget(name="day")
        #self.mainWindow.createDock(self.klineDay,'day', u"周线", QtCore.Qt.RightDockWidgetArea,True)

        ##持仓量
        self.stopOrderMonitor = StopOrderMonitor()
        self.mainWindow.createDock(self.stopOrderMonitor, 'stopOrderMonitor', u"持仓量",QtCore.Qt.LeftDockWidgetArea, False)
        self.stopOrderMonitor.setMaximumWidth(456)
        self.stopOrderMonitor.setMinimumWidth(456)
        self.updateMonitor()  ##更新一下数据

        self.mainWindow.saveWindowSettings('default')
    #################################################################################################################################
    def updateMonitor(self):
        varDict=[]
        ##更新合约
        tradeCount = csvTradeData.shape[0]
        curentIndex = 1
        while curentIndex<tradeCount:
            varSymbol=VtOrderData()
            varSymbol.symbol=csvTradeData.ix[[curentIndex]].values[0][3]  ##合约
            varSymbol.orderTime= csvTradeData.ix[[curentIndex]].values[0][0]  ##时间
            varSymbol.direction=csvTradeData.ix[[curentIndex]].values[0][7]
            varSymbol.offset=csvTradeData.ix[[curentIndex]].values[0][8]
            varSymbol.price=csvTradeData.ix[[curentIndex]].values[0][9]
            varSymbol.volume=csvTradeData.ix[[curentIndex]].values[0][10]
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
        self.loadsar(symbol)
        self.loadSig(symbol)


        # 插入bar数据
        self.klineOpt.KLtitle.setText(symbol + " opt", size='10pt')
        self.klineOpt.loadDataBar(self.hourBarData[symbol])
        self.klineOpt.addIndicatorSar(self.hourSarData[symbol])
        self.klineOpt.updateSig(self.hourListSig[symbol])

        #self.klineDay.KLtitle.setText(symbol + " 5min", size='10pt')
        #self.klineDay.loadDataBar(self.dayBarData[symbol])
        #self.klineDay.addIndicatorSar(self.daySarData[symbol])


    ############################################################################
    # 加载kline数据
    def loadBar(self, symbol):

        #if not self.dayBarData.has_key(symbol):
        #    dbDayList = self.loadAllBarFromDb('5min', symbol)
        #    self.dayBarData[symbol] = dbDayList


        if not self.hourBarData.has_key(symbol):
            #dbHourList = self.loadAllBarFromDb('60min', symbol)
            dbHourList = self.loadAllBarFromDb(optKType, symbol)
            self.hourBarData[symbol] = dbHourList


    def loadsar(self, symbol):
        #if not self.daySarData.has_key(symbol):
        #    sarDayList = self.dayBarData[symbol]
        #    dayHighArray = np.array(sarDayList.high.values)
        #    dayLowArray = np.array(sarDayList.low.values)
        #    sarArr = SAR()
        #    daySar = sarArr.OnCalculate(len(dayHighArray),0, dayHighArray, dayLowArray)

        #    self.daySarData[symbol] = sarArr.ExtSARBuffer

        if not self.hourSarData.has_key(symbol):
            sarHourList = self.hourBarData[symbol]
            hourHighArray = np.array(sarHourList.high.values)
            hourLowArray = np.array(sarHourList.low.values)
            sarArr1 = SAR()
            sarArr1.OnCalculate(len(hourHighArray),0, hourHighArray, hourLowArray)
            #hourSar = talib.SAR(hourHighArray, hourLowArray)
            self.hourSarData[symbol] = sarArr1.ExtSARBuffer

     ##加上开平仓信号########################################
    def loadSig(self, symbol):
        txtData = self.hourBarData[symbol]
        count = self.hourBarData[symbol].shape[0]
        tradeCount = csvTradeData.shape[0]

        listSig = [None for i in range(count)]
        curentIndex = 0
        for dataIndex in range(count):
            listSig[dataIndex] = None
            data_time_tmp = txtData.ix[[dataIndex]].values[0][8]  ##时间
            index_time = datetime.strptime(data_time_tmp, "%Y-%m-%d %H:%M:%S")

            if data_time_tmp == "2015-01-19 14:00:00":
                aabb = 3

            while curentIndex < tradeCount:

                tra_time_str = csvTradeData.ix[[curentIndex]].values[0][0]  ##时间
                if (csvTradeData.ix[[curentIndex]].values[0][3] != self.currrentSymbol):
                    curentIndex += 1
                    continue
                if type(tra_time_str) == float:  ##Nan
                    curentIndex += 1
                    continue

                tra_time = datetime.strptime(tra_time_str, "%Y-%m-%d %H:%M:%S")  ##2014-01-09 09:06:00
                data_time_end=data_time_tmp
                if optKType=="60min":
                    hour_t = tra_time.hour
                    if tra_time.minute != 0 and hour_t != 23:
                        hour_t += 1

                    tra_time = tra_time.replace(hour=(hour_t), minute=0).strftime("%Y-%m-%d %H:%M:%S")
                else:
                    opt_t=1
                    if optKType == "1min":
                        opt_t = 1
                    if optKType == "3min":
                        opt_t =3
                    if optKType == "5min":
                        opt_t = 5
                    if optKType == "10min":
                        opt_t = 10
                    if optKType == "15min":
                        opt_t = 15
                    if optKType == "30min":
                        opt_t = 30
                    minute_t = tra_time.minute
                    tra_time = tra_time.replace(minute=(minute_t)).strftime("%Y-%m-%d %H:%M:%S")
                    tem_time= datetime.strptime(data_time_tmp, "%Y-%m-%d %H:%M:%S")
                    tem_minute=tem_time.minute+opt_t
                    # print "tem_minute1:" + str(tem_minute)
                    if(tem_minute>=60):
                        tem_minute=tem_minute-60
                        tem_hour = tem_time.hour
                        if tem_hour != 23:
                            tem_hour += 1
                            data_time_end = tem_time.replace(hour=(tem_hour),minute=(tem_minute)).strftime("%Y-%m-%d %H:%M:%S")
                    else:
                        data_time_end=tem_time.replace(minute=(tem_minute)).strftime("%Y-%m-%d %H:%M:%S")

                if data_time_tmp>tra_time:
                    aaa = 2
                if data_time_tmp <=tra_time and tra_time<=data_time_end:
                    print  "data_time_tmp:" + str(data_time_tmp) + "tra_time:" + str(tra_time)+ "data_time_end:" + str(data_time_end)

                    sigDataa = {"direction": csvTradeData.ix[[curentIndex]].values[0][7],
                                "offset": csvTradeData.ix[[curentIndex]].values[0][8],
                                "price": csvTradeData.ix[[curentIndex]].values[0][9]}
                    listSig[dataIndex] = sigDataa
                else:
                    break
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
        fullFilePath = filePath + dbName + "/" + collectionName + ".txt"
        barData = pd.DataFrame.from_csv(fullFilePath, header=None, index_col=7)
        barData = barData.rename(
            columns={0: 'symbol', 1: "vtSymbol", 2: "exchange", 3: "open", 4: "high", 5: "low", 6: "close", 7: "date",
                     8: "time", 9: "datetime", 10: "volume", 11: "openInterest"})
        return barData

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




if __name__ == '__main__': #加载本地trade.csv合约数据
    fieldnames = ['dt', 'symbol', 'exchange', 'vtSymbol', 'tradeID', 'vtTradeID', 'orderID', 'vtOrderID',
                  'direction', 'offset', 'price', 'volume', 'tradeTime', "gatewayName", "rawData"]
    tradePath = getTempPath("trade.csv")

    if os.path.exists(tradePath):
        csvTradeData = pd.DataFrame.from_csv(tradePath, encoding="utf_8_sig", index_col=7)

    filePath = "D:/data/"
    # contactSymbol = "rb1605"  ###合约
    # curKType = "5min"  ## 当前加载的k线类型   1min  3min  5min  15min  30min  60min  day
    # fullFilePath = filePath+curKType+"/"+contactSymbol+".txt"
    optKType = "6min"   ## 操作周期k线类型   1min  3min  5min  15min  30min  60min  day

    app = QtWidgets.QApplication(sys.argv)
    styleSheet = qdarkstyle.load_stylesheet(pyside=False)
    app.setStyleSheet(styleSheet)

    main = MainWindow()

    abc = BackManager(main)
    abc.symbolSelect()#初始化symbol数据
    abc.stopOrderMonitor.cellDoubleClicked.connect(abc.symbolSelect)#注册signal
    main.showMaximized()
    main.show()
    app.exec_()



    # filePath = "D:/data/"
    # contactSymbol = "ru0000"  ###合约
    # curKType = "5min"  ## 当前加载的k线类型   1min  3min  5min  15min  30min  60min  day
    # fullFilePath = filePath+curKType+"/"+contactSymbol+".txt"
    # optKType = "1min"   ## 操作周期k线类型   1min  3min  5min  15min  30min  60min  day
    #
    #
    #
    #
    # app = QApplication(sys.argv)
    # # 界面设置
    # cfgfile = QtCore.QFile('css.qss')
    # cfgfile.open(QtCore.QFile.ReadOnly)
    # styleSheet = cfgfile.readAll()
    # styleSheet = unicode(styleSheet, encoding='utf8')
    # app.setStyleSheet(styleSheet)
    #
    #
    #
    # ui = KLineWidget()
    # ui.show()
    # ui.KLtitle.setText(contactSymbol+curKType,size='20pt')
    #
    # txtData = pd.DataFrame.from_csv(fullFilePath ,header=None,index_col=7)
    #
    # txtData = txtData.rename(columns = {0:'symbol', 1:"vtSymbol",2:"exchange",3:"open",4:"high",5:"low",6:"close",7:"date",8:"time",9:"datetime",10:"volume",11:"openInterest"})
    #
    # ui.loadDataBar(txtData)
    #
    # count = txtData.shape[0]
    #
    # ##加入sar指标
    # highArray = np.array(txtData.high.values)
    # lowArray = np.array(txtData.low.values)
    #
    #
    # sar = talib.SAR(highArray, lowArray)
    #
    #
    # ui.addIndicatorSar(sar)
    #
    #
    # import  csv
    #
    # ##加上开平仓信号
    #
    #
    # fieldnames = ['dt','symbol', 'exchange', 'vtSymbol', 'tradeID', 'vtTradeID', 'orderID', 'vtOrderID',
    #                   'direction','offset','price','volume','tradeTime',"gatewayName","rawData"]
    # tradePath = getTempPath("trade.csv")
    # if os.path.exists(tradePath):
    #     csvTradeData = pd.DataFrame.from_csv(tradePath,encoding="utf_8_sig",index_col=7)
    #
    # tradeCount = csvTradeData.shape[0]
    #
    # listSig = [ None for i in range(count)]
    # curentIndex = 0
    # for dataIndex in range(count):
    #     listSig[dataIndex] = None
    #     data_time_tmp = txtData.ix[[dataIndex]].values[0][8]  ##时间
    #     index_time = datetime.strptime(data_time_tmp,"%Y-%m-%d %H:%M:%S")
    #
    #     if data_time_tmp == "2015-01-19 14:00:00":
    #         aabb  =3
    #
    #     while curentIndex < tradeCount:
    #
    #         tra_time_str = csvTradeData.ix[[curentIndex]].values[0][0]    ##时间
    #         #print(csvData.ix[[curentIndex]].values[0][7])
    #         #print(csvData.ix[[curentIndex]].values[0][8])
    #         #print(csvData.ix[[curentIndex]].values[0][3])
    #         if(csvTradeData.ix[[curentIndex]].values[0][3] != contactSymbol):
    #             curentIndex += 1
    #             continue
    #         if type(tra_time_str) == float:  ##Nan
    #             curentIndex += 1
    #             continue
    #
    #         tra_time = datetime.strptime(tra_time_str,"%Y-%m-%d %H:%M:%S")  ##2014-01-09 09:06:00
    #
    #         #if optKType == "1min":
    #         hour_t = tra_time.hour
    #         if tra_time.minute != 0 and hour_t != 23:
    #             hour_t += 1
    #
    #         tra_time = tra_time.replace(hour=(hour_t),minute=0).strftime("%Y-%m-%d %H:%M:%S")
    #
    #         if data_time_tmp > tra_time:
    #             aaa = 2
    #
    #         if data_time_tmp < tra_time:
    #             break
    #
    #         if data_time_tmp == tra_time:
    #             sigDataa = {"direction": csvTradeData.ix[[curentIndex]].values[0][7],"offset":csvTradeData.ix[[curentIndex]].values[0][8],"price":csvTradeData.ix[[curentIndex]].values[0][9]}
    #             listSig[dataIndex] = sigDataa
    #             #if csvData.ix[[curentIndex]].values[0][7] == u'空':
    #                 #listSig[dataIndex] = -1
    #             #else:
    #                # listSig[dataIndex] = 1
    #
    #         curentIndex += 1
    #
    #
    # ui.updateSig(listSig)
    #
    #
    # app.exec_()
