# encoding: UTF-8
import numpy as np
import pandas as pd
from vtIndictors import IndicatorParent
import pyqtgraph as pg
import talib

####################cci 指标####################################

class cciAlgo(IndicatorParent):
    setting_info = None
    def __init__(self, parent, indicatorsInfo, name):
        IndicatorParent.__init__(self,parent)
        self.parent=parent
        self.curveOI1 = None

        self.cciValue = []

        self.indictorname = name
        self.setting_info = indicatorsInfo
        self.figure = self.setting_info["location"]
        self.plotItem = self.plotItems[self.figure]

    def addIndicators(self):
        highArray = np.array(self.parent.listHigh)
        lowArray = np.array(self.parent.listLow)
        closeArray = np.array(self.parent.listClose)

        N = self.setting_info["param"]["N"]

        self.cciValue = self.cci(highArray, lowArray,closeArray,N, True)


        self.addCci()

        self.setIndicatorsData()

    def addCci(self):
        if self.curveOI1:
            self.plotItem.removeItem(self.curveOI1)

        self.curveOI1 = pg.PlotDataItem()
        self.curveOI1.setData(y=self.cciValue)
        self.plotItem.addItem(self.curveOI1)


    def getYRange(self,xMin,xMax):
        y_min = min(self.cciValue[xMin:xMax])
        y_max = max(self.cciValue[xMin:xMax])
        return y_min,y_max


    # ----------------------------------------------------------------------
    def cci(self, highArray,lowArray,closeArray, n, array=False):
        """简单均线"""
        result = talib.CCI(highArray,lowArray,closeArray, timeperiod = n)
        if array:
            return result
        return result[-1]


    def updateIndicators(self):
        pass

    def setIndicatorsData(self):
        #保存当前指标
        self.base.name=  self.indictorname
        self.base.className=self.setting_info["className"]
        self.base.plotItem=self.plotItem
        self.base.figure=self.figure


    def getIndicatorsHtml(self,index):

        index = min(index, len(self.up) - 1)
        self.indicators_html = "CCI:" +  str(self.cciValue[index])
        return self.indicators_html

    def remove(self):
        if self.curveOI1:
            self.plotItem.removeItem(self.curveOI1)

        self.curveOI1 = None

        self.indicators_html=""
        self.name=""