# encoding: UTF-8
import numpy as np
import pandas as pd
from vtIndictors import IndicatorParent
import pyqtgraph as pg
import talib

####################持仓量 指标####################################

class opiAlgo(IndicatorParent):
    setting_info = None
    def __init__(self, parent, indicatorsInfo, name):
        IndicatorParent.__init__(self,parent)
        self.parent=parent
        self.curveOI1 = None


        self.indictorname = name
        self.setting_info = indicatorsInfo
        self.figure = self.setting_info["location"]
        self.plotItem = self.plotItems[self.figure]

    def addIndicators(self):

        self.addOpenInterest()

        self.setIndicatorsData()

    def addOpenInterest(self):
        if self.curveOI1:
            self.plotItem.removeItem(self.curveOI1)

        self.curveOI1 = pg.PlotDataItem()
        self.curveOI1.setData(y=self.parent.listOpenInterest)
        self.plotItem.addItem(self.curveOI1)


    def getYRange(self,xMin,xMax):
        y_min = min(self.parent.listOpenInterest[xMin:xMax])
        y_max = max(self.parent.listOpenInterest[xMin:xMax])
        return y_min,y_max

    def updateIndicators(self):
        pass

    def setIndicatorsData(self):
        #保存当前指标
        self.base.name=  self.indictorname
        self.base.className=self.setting_info["className"]
        self.base.plotItem=self.plotItem
        self.base.figure=self.figure


    def getIndicatorsHtml(self,index):

        index = min(index, len(self.parent.listOpenInterest) - 1)
        self.indicators_html = "OPI:" +  str(self.parent.listOpenInterest[index])
        return self.indicators_html

    def remove(self):
        if self.curveOI1:
            self.plotItem.removeItem(self.curveOI1)

        self.curveOI1 = None

        self.indicators_html=""
        self.name=""