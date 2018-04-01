# encoding: UTF-8
import numpy as np
import pandas as pd
from vtIndictors import IndicatorParent
import pyqtgraph as pg
import talib

####################移动平均线 指标####################################

class maAlgo(IndicatorParent):
    setting_info = None
    def __init__(self, parent, indicatorsInfo, name):
        IndicatorParent.__init__(self,parent)
        self.parent=parent
        self.curveOI1 = None
        self.curveOI2 = None
        self.curveOI3 = None
        self.curveOI4 = None
        self.curveOI5 = None
        self.curveOI6 = None

        self.line1 = []
        self.line2 = []
        self.line3 = []
        self.line4 = []
        self.line5 = []
        self.line6 = []

        self.indictorname = name
        self.setting_info = indicatorsInfo
        self.figure = self.setting_info["location"]
        self.plotItem = self.plotItems[self.figure]

    def addIndicators(self):
        hourcloseArray = np.array(self.parent.listClose)

        N1 = self.setting_info["param"]["N1"]
        N2 = self.setting_info["param"]["N2"]
        N3 = self.setting_info["param"]["N3"]
        N4 = self.setting_info["param"]["N4"]
        N5 = self.setting_info["param"]["N5"]
        N6 = self.setting_info["param"]["N6"]
        algo = self.setting_info["param"]["algo"]

        self.line1 = self.sma(hourcloseArray, N1,True)
        self.line2 = self.sma(hourcloseArray, N2,True)
        self.line3 = self.sma(hourcloseArray, N3,True)
        self.line4 = self.sma(hourcloseArray, N4,True)
        self.line5 = self.sma(hourcloseArray, N5,True)
        self.line6 = self.sma(hourcloseArray, N6,True)

        self.removeKlineCurve()
        self.curveOI1 = self.addToKline(self.line1)
        self.curveOI2 = self.addToKline(self.line2)
        self.curveOI3 = self.addToKline(self.line3)
        self.curveOI4 = self.addToKline(self.line4)
        self.curveOI5 = self.addToKline(self.line5)
        self.curveOI6 = self.addToKline(self.line6)

        self.setIndicatorsData()

    def removeKlineCurve(self):
        if self.curveOI1:
            self.plotItem.removeItem(self.curveOI1)
        if self.curveOI2:
            self.plotItem.removeItem(self.curveOI2)
        if self.curveOI3:
            self.plotItem.removeItem(self.curveOI3)
        if self.curveOI4:
            self.plotItem.removeItem(self.curveOI4)
        if self.curveOI5:
            self.plotItem.removeItem(self.curveOI5)
        if self.curveOI6:
            self.plotItem.removeItem(self.curveOI6)


    def addToKline(self,line):
        curveOI1 = pg.PlotDataItem()
        curveOI1.setData(y=line)
        self.plotItem.addItem(curveOI1)

        return curveOI1

    # ----------------------------------------------------------------------
    def sma(self, npArray, n, array=False):
        """简单均线"""
        result = talib.SMA(npArray, n)
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

        index = min(index, len(self.line1) - 1)
        self.indicators_html = "MA:N1=" +  str(self.line1[index]) + ",N2=" +str( self.line2[index]) + ",N3=" +str(self.line3[index])
        return self.indicators_html

    def remove(self):
        self.removeKlineCurve()

        self.curveOI1 = None
        self.curveOI2 = None
        self.curveOI3 = None
        self.curveOI4 = None
        self.curveOI5 = None
        self.curveOI6 = None

        self.line1 = []
        self.line2 = []
        self.line3 = []
        self.line4 = []
        self.line5 = []
        self.line6 = []

        self.indicators_html=""
        self.name=""
