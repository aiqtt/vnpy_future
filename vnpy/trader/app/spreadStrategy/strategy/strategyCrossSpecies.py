# encoding: UTF-8

"""
采用sar实现的跨品种价差

"""


from ..stBase import *
from vnpy.trader.vtObject import VtBarData
from vnpy.trader.vtConstant import *
from datetime import datetime, time,timedelta
from vnpy.trader.app.spreadStrategy.stTemplate import  (StTemplate,
                                                     )
from vnpy.trader.app.barManager import BarManager


########################################################################

class CrossSpeciesStrategy(StTemplate):
    """比率价差交易策略"""
    className = 'CrossSpeciesStrategy'
    author = u'用Python的交易员'

    # 策略参数
    vtSymbol = ''            #策略处理的当前合约
    strategyCycle = ''       #策略处理的周期  半小时还是1小时
    sarAcceleration = 0.02  #sar加速因子
    sarMaxNum = 0.2         #sa最大值

    trailingPercent = 0.8   # 百分比移动止损
    initDays = 10           # 初始化数据所用的天数
    fixedSize = 1           # 每次交易的数量


    # 策略变量

    intraTradeHigh = 0                  # 移动止损用的持仓期内最高价
    intraTradeLow = 0                   # 移动止损用的持仓期内最低价

    TICK_MODE = 'tick'
    BAR_MODE = 'bar'

    # 参数列表，保存了参数的名称
    paramList = ['name',
                 'className',
                 'author',
                 'vtSymbol',
                 'strategyCycle',
                 'sarAcceleration',
                 'sarMaxNum',
                 'trailingPercent']

    # 变量列表，保存了变量的名称
    varList = ['inited',
               'trading',
               'pos']

    #----------------------------------------------------------------------
    def __init__(self, spreadEngine, protforlio, setting):
        """Constructor"""
        super(CrossSpeciesStrategy, self).__init__(spreadEngine, setting)

        # 创建K线合成器对象
        if setting['strategyCycle'] == '3min':
            self.bm = BarManager(self.onBar, 3, self.onXminBar)

        if setting['strategyCycle'] == '15min':
            self.bm = BarManager(self.onBar, 15, self.onXminBar)

        if setting['strategyCycle'] == '10min':
            self.bm = BarManager(self.onBar, 10, self.onXminBar)

        if setting['strategyCycle'] == '5min':
            self.bm = BarManager(self.onBar, 5, self.onXminBar)

        self.optSarManager = None


        self.strategyCycle =  setting['strategyCycle']
        self.protforlio = protforlio

        self.mode = self.TICK_MODE    # 回测模式，默认为K线

        self.protforlioPosList = {}  ##组合仓位list

        self.commission = 4

        self.frencyUpper  = 0  ##频率上限
        self.frencyLower  = 0  ## 下


        # 注意策略类中的可变对象属性（通常是list和dict等），在策略初始化时需要重新创建，
        # 否则会出现多个策略实例之间数据共享的情况，有可能导致潜在的策略逻辑错误风险，
        # 策略类中的这些可变对象属性可以选择不写，全都放在__init__下面，写主要是为了阅读
        # 策略时方便（更多是个编程习惯的选择）

    #----------------------------------------------------------------------
    def onInit(self):
        """初始化策略（必须由用户继承实现）"""
        self.writeCtaLog(u'%s策略初始化' %self.className)


        initData = self.optionEngine.loadPortfolioPriceData(self.protforlio.symbol, self.strategyCycle)
        print("init_" + str(len(initData)))
        self.setOptBar(initData)

        self.putEvent()

    #----------------------------------------------------------------------
    def onStart(self):
        """启动策略（必须由用户继承实现）"""
        self.writeCtaLog(u'%s策略启动' %self.className)
        self.putEvent()

    #----------------------------------------------------------------------
    def onStop(self):
        """停止策略（必须由用户继承实现）"""
        self.writeCtaLog(u'%s策略停止' %self.className)
        self.putEvent()

    #----------------------------------------------------------------------
    def updatePortfolioTick(self, tick):
        """收到行情TICK推送（必须由用户继承实现）"""

        if self.inited != True:
            return

        if tick.datetime.hour == 15: ##3点的先丢掉
            return





        self.bm.updateTick(tick)

 #----------------------------------------------------------------------
    def onBar(self, bar):
        """收到1min Bar推送（必须由用户继承实现）处理策略"""
        #self.writeCtaLog('onBar sar'+ str(bar.datetime))

        self.bm.updateBar(bar)
        # 发出状态更新事件
        self.putEvent()


    def setMode(self, mode):
        self.mode = mode

    ##每次成交手数
    def setFixSize(self,size):
        self.fixedSize = size



    ##处理策略，触发信号
    def  handleStrategy(self):


        self.protforlioClose()


        proPrice = self.protforlio.calculateLastPrice()

        print "handleStrategy" + str(proPrice)



        self.protforlioOpen(DIRECTION_SHORT)



    ###更新hour sarmanager
    def onXminBar(self, bar):
        self.handleStrategy()


    def setOptBar(self,initData):
        #self.optSarManager.initBar(initData)
        pass




    #----------------------------------------------------------------------
    def onOrder(self, order):
        """收到委托变化推送（必须由用户继承实现）"""
        pass



    #----------------------------------------------------------------------
    def onTrade(self, trade):
        # 发出状态更新事件

        self.writeCtaLog("onTrade order price:" + str(trade.price) + str(trade.tradeTime))

        self.putEvent()

    #----------------------------------------------------------------------
    def onStopOrder(self, so):
        """停止单推送"""
        pass