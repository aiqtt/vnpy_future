# -*- coding: utf-8 -*-
"""
In this example we draw two different kinds of histogram.
"""

from qtpy import QtWidgets, QtGui, QtCore
from qtpy.QtWidgets import QApplication, QWidget
import datetime as dt
from vnpy.trader import *
from vnpy.trader.uiKLine  import *
from vnpy.trader.widget.crosshairTool import  CrosshairTool
import pyqtgraph as pg
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.mlab as mlab
import sys
class HistogramLUTWidget(QWidget):
    def __init__(self, data, parent=None):
        self.parent = parent
        self.data = data
        super(HistogramLUTWidget, self).__init__(parent)  # 继承
    # 界面布局
        self.pw=pg.PlotWidget()

        self.lay_KL = pg.GraphicsLayout(border=(100, 100, 100))
        self.lay_KL.setContentsMargins(10, 10, 10, 10)
        self.lay_KL.setSpacing(0)
        self.lay_KL.setBorder(color=(255, 255, 255, 255), width=0.8)
        self.lay_KL.setZValue(0)
        self.pw.setCentralItem(self.lay_KL)
    #     # 设置横坐标
    #     xdict = dict(enumerate(self.data["timeList"]))
    #     self.axisTime = MyStringAxis(xdict, orientation='bottom')
    #     # 初始化子图
        self.initplotpnl()
        # # 注册十字光标
        x=[]
        viwe = self.plt
        self.crosshair = CrosshairTool(self.pw, x, viwe, self)
        # 设置界面
        self.vb = QtWidgets.QVBoxLayout()
        self.vb.addWidget(self.pw)
        self.setLayout(self.vb)
    # ----------------------------------------------------------------------

    def initplotpnl(self, xmin=0, xmax=-1):
        vals = np.hstack(self.data)
        xMin = min(self.data)
        xMax = max(self.data)
        #histogram
        #y, x = np.histogram(vals, bins=np.linspace(xMin,xMax, 100),normed=False,density=True)
        # #hist
        nx, xbins, ptchs = plt.hist(self.data, bins=50, normed=True, facecolor='black', edgecolor='black',alpha=1,histtype = 'bar')
        histo = plt.hist(self.data, 50)
        vb = CustomViewBox(self.parent)
        # self.plt=pg.PlotItem(viewBox=vb,  axisItems={'bottom': self.axisTime})#设置x轴
        self.plt = pg.PlotItem(viewBox=vb)
        leng_ = len(self.data)
        self.plt.setRange(xRange=(0, leng_), yRange=(xMin, xMax))
        # #histogram
        # self.plt.plot(x, y, stepMode=True, fillLevel=0, brush=(0, 0, 255, 50),size=0.4)#绘制统计所得到的概率密度,直方图
        ##hist  bar
        width = xbins[1] - xbins[0]  # Width of each bin.
        #self.plt.plot(x,y,width=width)# 绘制统计所得到的概率密度,线形图
        self.pi=pg.BarGraphItem(x=histo[1][0:50],height=histo[0],width=width, color='y',)# 绘制统计所得到的概率密度,bar图
        self.plt.addItem(self.pi)
        self.lay_KL.addItem(self.plt)

    def refresh(self):
        """
        刷新三个子图的现实范围
        """
        leng_ = len(self.data)
        xMin = min(self.data)
        xMax = max(self.data)
        self.plt.setRange(xRange=(0, leng_), yRange=(xMin, xMax))

########################################################################
# 选择缩放功能支持
########################################################################
class CustomViewBox(pg.ViewBox):

    # ----------------------------------------------------------------------
    def __init__(self, *args, **kwds):
        pg.ViewBox.__init__(self, *args, **kwds)

        # 拖动放大模式
        # self.setMouseMode(self.RectMode)

    ## 右键自适应
    # ----------------------------------------------------------------------
    def mouseClickEvent(self, ev):
        if ev.button() == QtCore.Qt.RightButton:
            self.autoRange()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = HistogramLUTWidget()
    sys.exit(app.exec_())



