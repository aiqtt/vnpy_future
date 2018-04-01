# encoding: UTF-8
from vtIndictors import IndicatorParent
import pyqtgraph as pg

####################布林通道计算####################################
class sarAlgo(IndicatorParent):
    setting_info=None
    def __init__(self, parent, indicatorsInfo, name):
        IndicatorParent.__init__(self,parent)
        self.parent = parent
        self.sars = []  # sar指标元素
        self.setting_info = indicatorsInfo
        self.indictorname = name
        self.figure= self.setting_info["location"]
        self.plotItem = self.plotItems[self.figure]

    def addIndicators(self):


        self.sarDatas=self.hourSarData.ExtSARBuffer
        """增加sar指标"""
        if len(  self.sarDatas) == 0:
            return
        for sar in self.sars:
            self.plotItem.removeItem(sar)
        # 画信号
        for i in range(len( self.sarDatas)):
            arrow = pg.ArrowItem(pos=(i, self.sarDatas[i]), angle=90, tipAngle=5, headLen=2, tailWidth=4, pen={'width': 1},
                                 brush=(0, 0, 255))

            defaultOpts = {
                'pxMode': True,
                'angle': -150,  ## If the angle is 0, the arrow points left
                'pos': (0, 0),
                'headLen': 10,
                'tipAngle': 10,
                'baseAngle': 0,
                'tailLen': None,
                'tailWidth': 3,
                'pen': (200, 200, 200),
                'brush': (255, 0, 0),
            }
            self.plotItem.addItem(arrow)
            self.sars.append(arrow)
        self.setIndicatorsData()
    def updateIndicators(self):
        #sar 只计算最后3个值

        preSARLen = len( self.hourSarData.ExtSARBuffer)
        self.hourSarData.OnCalculate(len(self.parent.listHigh), len(self.parent.listHigh)-3, self.parent.listHigh, self.parent.listLow)
        startIndex=preSARLen - 1
        self.sarDatas=self.hourSarData.ExtSARBuffer

        for i in range(startIndex, preSARLen):
            arrow = pg.ArrowItem(pos=(i,  self.sarDatas[i]), angle=90, tipAngle=5, headLen=2, tailWidth=4, pen={'width': 1},
                                 brush=(0, 0, 255))

            defaultOpts = {
                'pxMode': True,
                'angle': -150,  ## If the angle is 0, the arrow points left
                'pos': (0, 0),
                'headLen': 10,
                'tipAngle': 10,
                'baseAngle': 0,
                'tailLen': None,
                'tailWidth': 3,
                'pen': (200, 200, 200),
                'brush': (255, 0, 0),
            }
            print self.base.plotItem
            self.base.plotItem.addItem(arrow)
            self.base.indicatorsElements.append(arrow)

    def setIndicatorsData(self):
        # 保存当前指标
        self.base.name = self.indictorname
        self.base.className =  self.setting_info["className"]
        self.base.figure = self.figure
        self.base.plotItem=self.plotItem
        self.base.indicatorsElements = self.sars
        self.base.indictatorsDatas=self.sarDatas


    def getIndicatorsHtml(self,index):
       if len(self.base.indictatorsDatas)>0:
          index = min(index, len(self.base.indictatorsDatas) - 1)
          self.indicators_html = "SAR:sarLine=" +str(self.base.indictatorsDatas[index])
       return self.indicators_html

    def remove(self):
        self.sarIndicators=self.base.indicatorsElements
        for sar in  self.sarIndicators:
            self.base.plotItem.removeItem(sar)
        self.sars=[]
        self.sarDatas=[]
        self.indicators_html = ""
        self.name=""

