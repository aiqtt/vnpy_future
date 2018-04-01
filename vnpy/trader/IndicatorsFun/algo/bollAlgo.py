# encoding: UTF-8
import numpy as np
import pandas as pd
from vtIndictors import IndicatorParent
import pyqtgraph as pg
import talib


####################布林通道计算####################################
class bollAlgo(IndicatorParent):
    setting_info = None
    def __init__(self, parent, indicatorsInfo, name):
        IndicatorParent.__init__(self,parent)
        self.parent=parent
        self.curveOI1 = None
        self.curveOI2 = None
        self.curveOI3 = None
        self.upperline = []
        self.midline = []
        self.downline = []
        self.indictorname = name
        self.setting_info = indicatorsInfo
        self.figure = self.setting_info["location"]
        self.plotItem = self.plotItems[self.figure]

    def addIndicators(self):
        hourcloseArray = np.array(self.parent.listClose)

        N = self.setting_info["param"]["N"]
        M= self.setting_info["param"]["M"]
        P = self.setting_info["param"]["P"]

        self.hourBollData_up, self.hourBollData_mid, self.hourBollData_low = self.boll(
            hourcloseArray, N,M, P, True)

        self.addUpper(self.hourBollData_up)
        self.addMid(self.hourBollData_mid)
        self.addDown(self.hourBollData_low)
        self.setIndicatorsData()

    def addUpper(self, up):
        if self.curveOI1:
            self.plotItem.removeItem(self.curveOI1)
        self.upperline = up
        self.curveOI1 = pg.PlotDataItem()
        self.curveOI1.setData(y=self.upperline)
        self.plotItem.addItem(self.curveOI1)

    def addMid(self, mid):
        if self.curveOI2:
            self.plotItem.removeItem(self.curveOI2)
        self.midline = mid
        self.curveOI2 = pg.PlotDataItem()
        self.curveOI2.setData(y=self.midline)
        self.plotItem.addItem(self.curveOI2)


    def addDown(self, down):
        if self.curveOI3:
            self.plotItem.removeItem(self.curveOI3)

        self.downline = down
        self.curveOI3 = pg.PlotDataItem()
        self.curveOI3.setData(y=self.downline)
        self.plotItem.addItem(self.curveOI3)

    # ----------------------------------------------------------------------
    def sma(self, npArray, n, array=False):
        """简单均线"""
        result = talib.SMA(npArray, n)
        if array:
            return result
        return result[-1]

        # ----------------------------------------------------------------------

    def std(self, npArray, n, array=False):
        """标准差"""
        result = talib.STDDEV(npArray, n)
        if array:
            return result
        return result[-1]

        # ----------------------------------------------------------------------

    def boll(self, npArray, n,m, dev, array=False):
        """布林通道"""
        mid = self.sma(npArray, n, array)
        std = self.std(npArray, m, array)

        up = mid + std * dev
        down = mid - std * dev
        return up, mid, down
    def updateIndicators(self):
        pass

    def setIndicatorsData(self):
        #保存当前指标
        self.base.name=  self.indictorname
        self.base.className=self.setting_info["className"]
        self.base.plotItem=self.plotItem
        self.base.figure=self.figure
        self.base.indicatorsElements.append(self.curveOI1)
        self.base.indicatorsElements.append(self.curveOI2)
        self.base.indicatorsElements.append(self.curveOI3)
        self.base.indictatorsDatas.append(self.upperline)
        self.base.indictatorsDatas.append(self.midline)
        self.base.indictatorsDatas.append(self.downline)

    def getIndicatorsHtml(self,index):
        if len(self.base.indictatorsDatas)>0:
            if len(self.base.indictatorsDatas[0])>0:

                self.up=self.base.indictatorsDatas[0]
                self.mid=self.base.indictatorsDatas[1]
                self.down = self.base.indictatorsDatas[2]
                index = min(index, len(self.up) - 1)
                self.indicators_html = "BOLL:up=" +  str(self.up[index]) + ",mid=" +str( self.mid[index]) + ",low=" +str(self.down[index])
        return self.indicators_html

    def remove(self):
        for i in self.base.indicatorsElements:
            self.base.plotItem.removeItem(i)

        self.curveOI1 = None
        self.curveOI2 = None
        self.curveOI3 = None
        self.upperline = []
        self.midline = []
        self.downline = []
        self.indicators_html=""
        self.name=""

