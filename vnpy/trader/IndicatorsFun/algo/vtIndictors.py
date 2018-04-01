# encoding: UTF-8
from vnpy.trader.vtConstant import (EMPTY_STRING, EMPTY_UNICODE,
                                    EMPTY_FLOAT, EMPTY_INT)
########################################################################
class IndicatorParent(object):
    def __init__(self,parent):
        self.indicators_html = EMPTY_STRING
        self.parent=parent
        self.plotItems={"mainfigure":self.parent.pwKL,"vicefigure1":self.parent.pwVol,"vicefigure2":self.parent.pwOI}
        # mainfigure=self.parent.pwKL#主图pwKL
        # vicefigure1=self.parent.pwVol#副图pwVol
        # vicefigure2 =self.parent.pwOI#副图pwOI
        self.base=VtIndicatorsData()
    ###############################
    def setIndicatorsData(self):
        #保存指标对象
        pass
    def setIndicatorsHtml(self):
        pass
    ###############################
    def getIndicatorsHtml(self):
        #获取指标值HTML，显示在界面
       return str(self.indicators_html)
    def addIndicators(self):
        pass
    def updateIndicators(self):
        pass

    ###############################
    def remove(self):
        #移除指标元素
        pass

    ##返回指标界面y 坐标 只有副图需要
    def getYRange(self,xMin,xMax):
        return 0, 1

########################################################################
class VtIndicatorsData(object):
    """指标类"""

    # ----------------------------------------------------------------------
    def __init__(self):
        """Constructor"""
        self.name = EMPTY_STRING  # 指标
        self.className = EMPTY_STRING  # class
        self.plotItem=None
        self.figure = EMPTY_STRING  #
        self.indicatorsElements = []
        self.indictatorsDatas=[]
