# encoding: UTF-8
'''
本文件包含了期权引擎中的策略开发用模板，开发策略时需要继承类。
'''

from vnpy.trader.vtConstant import *

class StTemplate(object):
    className = 'StTemplate'
    author = EMPTY_UNICODE

    # 策略的基本参数
    name = EMPTY_UNICODE           # 策略实例名称

    # 策略的基本变量，由引擎管理
    inited = False                 # 是否进行了初始化
    trading = False                # 是否启动交易，由引擎管理
    pos = 0                        # 持仓情况

    volumeMultiple = 1       #跳价的点位
    priceTick = 1.0           # 价格最小变动

    #----------------------------------------------------------------------
    def __init__(self, optionEngine, setting):
        """Constructor"""
        self.optionEngine = optionEngine

        # 设置策略的参数
        if setting:
            d = self.__dict__
            for key in self.paramList:
                if key in setting:
                    d[key] = setting[key]


    def updatePortfolioTick(self,tick):
        pass


        ##组合开仓
    def protforlioOpen(self,direction):
        self.optionEngine.protforlioOpen(self, direction)


    #组合平仓
    def protforlioClose(self):

        self.optionEngine.protforlioClose(self)


    #----------------------------------------------------------------------
    def writeCtaLog(self, content):
        """记录CTA日志"""
        content = self.className + ':' + content
        self.optionEngine.writeOptionLog(content)
    #----------------------------------------------------------------------
    def putEvent(self):
        """发出策略状态变化事件"""
        self.optionEngine.putStrategyEvent(self.name)
