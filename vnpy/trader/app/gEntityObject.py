# encoding: UTF-8

##策略用到的entity
from vnpy.trader.vtConstant import EMPTY_UNICODE, EMPTY_STRING, EMPTY_FLOAT, EMPTY_INT

class PositionData():
    ##策略仓位
    def __init__(self):
        self.strategyName = EMPTY_STRING #策略名
        self.pos = EMPTY_INT             #pos
        self.symbol = EMPTY_STRING       #合约


class TraderOrder(object):
    """交易订单"""

    #----------------------------------------------------------------------
    def __init__(self):
        self.orderID = EMPTY_STRING
        self.orderUuid = EMPTY_STRING  ##由时间和orderId组成

        self.symbol = EMPTY_STRING
        self.strategyName = EMPTY_STRING #策略名

        self.direction = EMPTY_UNICODE
        self.offset = EMPTY_UNICODE

        self.orderVolume = EMPTY_INT   ##下单volume
        self.orderPrice = EMPTY_FLOAT  ##下单price

        self.tradeVolume = EMPTY_INT   ##成交volume
        self.tradePrice = EMPTY_FLOAT  ##成交price