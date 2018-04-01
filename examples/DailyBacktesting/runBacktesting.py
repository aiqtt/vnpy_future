# encoding: UTF-8

"""
展示如何执行策略回测。
"""

from __future__ import division
import json

from vnpy.trader.app.dailyStrategy.dailyBacktesting  import BacktestingEngine, MINUTE_DB_NAME
from vnpy.trader.vtFunction import getJsonPath
from vnpy.trader.uiBackMainWindow import  *
from vnpy.trader.widget.witLine import lineWidget
from vnpy.trader.widget.witBar import BarWidget
from vnpy.trader.widget.witExpTable import Example
from vnpy.trader.widget.witHistogram import HistogramLUTWidget
import sys
import qdarkstyle


settingFileName = 'Daily_setting.json'
settingfilePath = getJsonPath(settingFileName, __file__)
def loadSetting():
    """读取策略配置"""
    with open(settingfilePath) as f:
        l = json.load(f)
        return l
def formatNumber(n):
    """格式化数字到字符串"""
    rn = round(n, 2)        # 保留两位小数
    return format(rn, ',')  # 加上千分符

def reverse_time(x, y):
    a = x.dt>y.dt
    if a == True:
        return 1
    if a == False:
        return -1

def reverse_resu(x, y):
    a = x.exitDt>y.exitDt
    if a == True:
        return 1
    if a == False:
        return -1

if __name__ == '__main__':

    from vnpy.trader.app.dailyStrategy.strategy.strategyDualThrust import DualThrustStrategy
    from vnpy.trader.app.dailyStrategy.strategy.strategyMI import MIStrategy

    setting = loadSetting()


    allResult_trade = []
    allResult_result = []
    capitalSymbolList = {}
    for (symbol,symbolInfo) in setting["contactInfo"].items():
        print "key:"+symbol+",value:"+str(symbolInfo)
        capitalSymbolList[symbol] = []

        # 创建回测引擎
        engine = BacktestingEngine()

        # 设置引擎的回测模式为Tick  日内 一般是 5分钟 ，bar线回测没有意义
        engine.setBacktestingMode(engine.TICK_MODE)

        # 设置回测用的数据起始日期
        engine.setStartDate('20151101')
        engine.setEndDate(  '20160101')
     #20160501
        # 设置产品相关参数
        engine.setSlippage(1)     # 股指1跳
        engine.setRate(1/10000)   # 万0.3
        engine.setSize(symbolInfo["volumeMultiple"])         # 股指合约大小
        engine.setPriceTick(symbolInfo["priceTick"])    # 股指最小价格变动
        engine.setCapital(setting["capital"])

        # 设置使用的历史数据库
        engine.setSymbol(symbol)
        engine.setDataPath(setting["filePath"])

        # 在引擎中创建策略对象
        contactInfo = {symbol:symbolInfo}
        engine.initStrategy(DualThrustStrategy, contactInfo,setting)

        # 开始跑回测
        engine.runBacktesting()

        # 显示回测结果
        resultList = engine.getBacktestingResult_trade()
        resultList1 = engine.getBacktestingResult_result()

        allResult_trade.extend(resultList)
        allResult_result.extend(resultList1)



    capitalSymbolList = {}
    for (symbol,symbolInfo) in setting["contactInfo"].items():
        capitalSymbolList[symbol] = []

    allResult_trade.sort(cmp=reverse_time)
    allResult_result.sort(cmp=reverse_resu)

    MultiResult=engine.showMultiResult_Margin(allResult_trade,1000000, capitalSymbolList)
    data=engine.showBacktestingResult(allResult_result)
    app = QtWidgets.QApplication(sys.argv)

    # 界面设置
    cfgfile = QtCore.QFile('css.qss')
    cfgfile.open(QtCore.QFile.ReadOnly)
    styleSheet = cfgfile.readAll()

    styleSheet = unicode(styleSheet, encoding='utf8')
    styleSheet = qdarkstyle.load_stylesheet(pyside=False)
    app.setStyleSheet(styleSheet)
    # main = ui_MainWindow()
    main = MainWindow()
    # Capital
    capitalWidget = lineWidget(data['timeList'], data['capitalList'])
    capitalWidget.PlotCapital()

    # #drawdown
    drawndownWidget = BarWidget(data['timeList'], data['drawdownList'])
    drawndownWidget.refresh()
    ##table
    table = {}
    keyItem = [u'第一笔交易:', u'最后一笔交易:', u'总交易次数:', u'总盈亏:', u'最大回撤:', u'最大回撤率;', u'平均每笔盈利:', u'平均每笔滑点:', u'平均每笔佣金:',
               u'胜率:',
               u'盈利交易平均值:', u'亏损交易平均值:', u'盈亏比:']
    valueItem = []
    valueItem.append(data['timeList'][0])
    valueItem.append(data['timeList'][-1])
    valueItem.append(formatNumber(data['totalResult']))
    valueItem.append(formatNumber(data['capital']))
    valueItem.append(formatNumber(min(data['drawdownList'])))
    valueItem.append(formatNumber(data['maxDrawDownRat']))

    valueItem.append(formatNumber(data['capital'] / data['totalResult']))
    valueItem.append(formatNumber(data['totalSlippage'] / data['totalResult']))
    valueItem.append(formatNumber(data['totalCommission'] / data['totalResult']))
    valueItem.append(formatNumber(data['winningRate']) + '%')
    valueItem.append(formatNumber(data['averageWinning']))
    valueItem.append(formatNumber(data['averageLosing']))
    valueItem.append(formatNumber(data['profitLossRatio']))
    table['keyItem'] = keyItem
    table['valueItem'] = valueItem

    expTableWidget = Example(table)
    expTableWidget.setMaximumWidth(262)
    expTableWidget.setMinimumWidth(262)
    # expTableWidget.setMaximumSize(QSize(300,300))
    ##multiResult
    table.clear()
    keyItem = []
    valueItem = []
    keyItem = [u'第一笔交易:', u'最后一笔交易:', u'总交易次数:', u'总盈亏:', u'最大回撤:', u'最大回撤率;', u'最大资金占用']
    valueItem.append(MultiResult['timeList'][0])
    valueItem.append(MultiResult['timeList'][-1])
    valueItem.append(formatNumber(MultiResult['totalResult']))
    valueItem.append(formatNumber(MultiResult['capital']))
    valueItem.append(formatNumber(min(MultiResult['drawdownList'])))
    valueItem.append(formatNumber(MultiResult['maxDrawDownRat']))
    valueItem.append(formatNumber(MultiResult['maxMargin']))
    table['keyItem'] = keyItem
    table['valueItem'] = valueItem

    multiResultWidget = Example(table)
    multiResultWidget.setMaximumWidth(262)
    multiResultWidget.setMinimumWidth(262)

    # pnl
    histogramWidget = HistogramLUTWidget(data['pnlList'])
    # createDock
    main.createDock(capitalWidget, 'capital', u'盈亏', QtCore.Qt.LeftDockWidgetArea, True)
    main.createDock(drawndownWidget, 'drawndown', u'回撤', QtCore.Qt.LeftDockWidgetArea, True)
    main.createDock(histogramWidget, 'histogram', u'pnl', QtCore.Qt.LeftDockWidgetArea, True)
    main.createDock(expTableWidget, 'exptable', u'回测结果', QtCore.Qt.RightDockWidgetArea, True)
    main.createDock(multiResultWidget, 'multiResult', u'仓位管理统计回测结果', QtCore.Qt.RightDockWidgetArea, True)
    # 保存默认设置
    main.saveWindowSettings('default')
    main.show()
    sys.exit(app.exec_())
