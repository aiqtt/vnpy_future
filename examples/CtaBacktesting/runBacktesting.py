# encoding: UTF-8

"""
展示如何执行策略回测。
"""

from __future__ import division
from vnpy.trader.uiBackMainWindow import  *

from vnpy.trader.app.ctaStrategy.ctaBacktesting import BacktestingEngine, MINUTE_DB_NAME
from vnpy.trader.widget.witLine import lineWidget
from vnpy.trader.widget.witBar import BarWidget
from vnpy.trader.widget.witExpTable import Example
from vnpy.trader.widget.witHistogram import HistogramLUTWidget
def formatNumber(n):
    """格式化数字到字符串"""
    rn = round(n, 2)        # 保留两位小数
    return format(rn, ',')  # 加上千分符
if __name__ == '__main__':
    from vnpy.trader.app.ctaStrategy.strategy.strategyKingKeltner import KkStrategy
    
    # 创建回测引擎
    engine = BacktestingEngine()
    
    # 设置引擎的回测模式为K线
    engine.setBacktestingMode(engine.BAR_MODE)

    # 设置回测用的数据起始日期
    engine.setStartDate('20120101')
    
    # 设置产品相关参数
    engine.setSlippage(0.2)     # 股指1跳
    engine.setRate(0.3/10000)   # 万0.3
    engine.setSize(300)         # 股指合约大小 
    engine.setPriceTick(0.2)    # 股指最小价格变动
    
    # 设置使用的历史数据库
    engine.setDatabase(MINUTE_DB_NAME, 'IF0000')
    
    # 在引擎中创建策略对象
    d = {}
    engine.initStrategy(KkStrategy, d)
    
    # 开始跑回测
    engine.runBacktesting()
    # 显示回测结果
    data = engine.showBacktestingResult()
    #engine.showDailyResult()

    import sys

    """
    app = QApplication(sys.argv)
    # 界面设置
    cfgfile = QtCore.QFile('css.qss')
    cfgfile.open(QtCore.QFile.ReadOnly)
    styleSheet = cfgfile.readAll()
    styleSheet = unicode(styleSheet, encoding='utf8')
    app.setStyleSheet(styleSheet)


    ui = initBacktestingResultUi(data)
    ui.show()

    ui.PlotCapital()
    app.exec_()
    """

    app = QtWidgets.QApplication(sys.argv)
    # 界面设置
    cfgfile = QtCore.QFile('css.qss')
    cfgfile.open(QtCore.QFile.ReadOnly)
    styleSheet = cfgfile.readAll()
    styleSheet = unicode(styleSheet, encoding='utf8')
    app.setStyleSheet(styleSheet)
   # main = ui_MainWindow()
    main=MainWindow()
    #Capital
    capitalWidget=lineWidget(data['timeList'],data['capitalList'])
    capitalWidget.PlotCapital()


    # #drawdown
    drawndownWidget=BarWidget(data['timeList'],data['drawdownList'])
    drawndownWidget.refresh()
    ##table
    table={}
    arryList=[]
    keyItem = [u'第一笔交易:', u'最后一笔交易:', u'总交易次数:', u'总盈亏:', u'最大回撤:', u'平均每笔盈利:', u'平均每笔滑点:', u'平均每笔佣金:', u'胜率:',
                       u'盈利交易平均值:', u'亏损交易平均值:', u'盈亏比:']
    valueItem = []
    valueItem.append(data['timeList'][0])
    valueItem.append(data['timeList'][-1])
    valueItem.append(formatNumber(data['capital']))
    valueItem.append(formatNumber(data['totalResult']))
    valueItem.append(formatNumber(min(data['drawdownList'])))
    valueItem.append(formatNumber(data['capital'] / data['totalResult']))
    valueItem.append(formatNumber(data['totalSlippage'] / data['totalResult']))
    valueItem.append(formatNumber(data['totalCommission'] / data['totalResult']))
    valueItem.append(formatNumber(data['winningRate'])+'%')
    valueItem.append(formatNumber(data['averageWinning']))
    valueItem.append(formatNumber(data['averageLosing']))
    valueItem.append(formatNumber(data['profitLossRatio']))
    table['keyItem']=keyItem
    table['valueItem'] = valueItem




    expTableWidget=Example(table)
    expTableWidget.setMaximumWidth(262)
    expTableWidget.setMinimumWidth(262)
    #expTableWidget.setMaximumSize(QSize(300,300))

    #pnl
    histogramWidget=HistogramLUTWidget(data['pnlList'])
    #createDock
    main.createDock(capitalWidget,'capital',u'盈亏',QtCore.Qt.LeftDockWidgetArea,True)
    main.createDock(drawndownWidget, 'drawndown', u'回撤', QtCore.Qt.LeftDockWidgetArea,True)
    main.createDock(histogramWidget, 'histogram', u'pnl', QtCore.Qt.LeftDockWidgetArea,True)
    main.createDock(expTableWidget, 'exptable',u'回测结果', QtCore.Qt.RightDockWidgetArea,False)
    main.saveWindowSettings('default')
    # 保存默认设置




    main.show()
    # #画图

    sys.exit(app.exec_())

