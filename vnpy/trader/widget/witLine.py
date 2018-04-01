# -*- coding: utf-8 -*-



# Qt相关和十字光标
from qtpy import QtWidgets, QtGui, QtCore
from qtpy.QtGui import QFont
from qtpy.QtCore import QObject, QUrl, Qt
from qtpy.QtWidgets import QApplication, QWidget
from vnpy.trader import *
import pyqtgraph as pg
from pyqtgraph.Point import Point

import datetime as dt
# 其他
import numpy as np
import pandas as pd
from functools import partial
from collections import deque
from datetime import datetime, timedelta
from collections import OrderedDict
from itertools import product
import multiprocessing
import copy
from vnpy.trader.widget.crosshairTool import  CrosshairTool

import pymongo
# 如果安装了seaborn则设置为白色风格
try:
    import seaborn as sns

    sns.set_style('whitegrid')
except ImportError:
    pass

import sys
# 字符串转换
#---------------------------------------------------------------------------------------
try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    def _fromUtf8(s):
        return s

class KeyWraper(QtWidgets.QWidget):
    """键盘鼠标功能支持的元类"""

    # 初始化
    # ----------------------------------------------------------------------
    def __init__(self, parent=None):
        QtWidgets.QWidget.__init__(self, parent)

        # 重载方法keyPressEvent(self,event),即按键按下事件方法
        # ----------------------------------------------------------------------
        def keyPressEvent(self, event):
            if event.key() == QtCore.Qt.Key_Up:
                self.onUp()
            elif event.key() == QtCore.Qt.Key_Down:
                self.onDown()
            elif event.key() == QtCore.Qt.Key_Left:
                self.onLeft()
            elif event.key() == QtCore.Qt.Key_Right:
                self.onRight()
            elif event.key() == QtCore.Qt.Key_PageUp:
                self.onPre()
            elif event.key() == QtCore.Qt.Key_PageDown:
                self.onNxt()

        # 重载方法mousePressEvent(self,event),即鼠标点击事件方法
        # ----------------------------------------------------------------------
        def mousePressEvent(self, event):
            if event.button() == QtCore.Qt.RightButton:
                self.onRClick(event.pos())
            elif event.button() == QtCore.Qt.LeftButton:
                self.onLClick(event.pos())
                event.accept()

        # 重载方法mouseReleaseEvent(self,event),即鼠标点击事件方法
        # ----------------------------------------------------------------------
        def mouseRelease(self, event):
            if event.button() == QtCore.Qt.RightButton:
                self.onRRelease(event.pos())
            elif event.button() == QtCore.Qt.LeftButton:
                self.onLRelease(event.pos())
                self.releaseMouse()

        # 重载方法wheelEvent(self,event),即滚轮事件方法
        # ----------------------------------------------------------------------
        def wheelEvent(self, event):
            if event.angleDelta().y() / 120.0 > 0:
                self.onUp()
            else:
                self.onDown()

        # 重载方法dragMoveEvent(self,event),即拖动事件方法
        # ----------------------------------------------------------------------
        def paintEvent(self, event):
            self.onPaint()

        # PgDown键
        # ----------------------------------------------------------------------
        def onNxt(self):
            pass

            # PgUp键
            # ----------------------------------------------------------------------
        def onPre(self):
            pass

        # 向上键和滚轮向上
        # ----------------------------------------------------------------------
        def onUp(self):
            pass

        # 向下键和滚轮向下
        # ----------------------------------------------------------------------
        def onDown(self):
            pass

        # 向左键
        # ----------------------------------------------------------------------
        def onLeft(self):
            pass

        # 向右键
        # ----------------------------------------------------------------------
        def onRight(self):
            pass

        # 鼠标左单击
        # ----------------------------------------------------------------------
        def onLClick(self, pos):
            pass

        # 鼠标右单击
        # ----------------------------------------------------------------------
        def onRClick(self, pos):
            pass

        # 鼠标左释放
        # ----------------------------------------------------------------------
        def onLRelease(self, pos):
            pass

        # 鼠标右释放
        # ----------------------------------------------------------------------
        def onRRelease(self, pos):
            pass

        # 画图
        # ----------------------------------------------------------------------
        def onPaint(self):
            pass

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

########################################################################
    # 时间序列，横坐标支持
########################################################################
class MyStringAxis(pg.AxisItem):
        """时间序列横坐标支持"""

         # 初始化
        # ----------------------------------------------------------------------
        def __init__(self, xdict, *args, **kwargs):
            pg.AxisItem.__init__(self, *args, **kwargs)
            self.minVal = 0
            self.maxVal = 0
            self.xdict = xdict
            self.x_values = np.asarray(xdict.keys())
            self.x_strings = xdict.values()
            self.setPen(color=(255, 255, 255, 255), width=0.8)
            self.setStyle(tickFont=QFont("Roman times", 10, QFont.Bold), autoExpandTextSpace=True)

########################################################################
class lineWidget(KeyWraper):
        def __init__(self, xAxis,yAxis, parent=None):
            """Constructor"""
            self.parent = parent
            #self.data = data
            self.xAxis = xAxis
            self.yAxis = yAxis
            super(lineWidget, self).__init__(parent)
            # 初始化完成
            self.initCompleted = False

            # 调用函数
            self.BackinitUi()

            # ----------------------------------------------------------------------
            #  初始化相关
            # ----------------------------------------------------------------------

        def BackinitUi(self):
            # 主图
            self.pw = pg.PlotWidget()
            # 界面布局
            self.lay_KL = pg.GraphicsLayout(border=(100, 100, 100))
            self.lay_KL.setContentsMargins(10, 10, 10, 10)
            self.lay_KL.setSpacing(0)
            self.lay_KL.setBorder(color=(255, 255, 255, 255), width=0.8)
            self.lay_KL.setZValue(0)
            self.pw.setCentralItem(self.lay_KL)
            #self.lay_KL.addLabel("capital")
            # 设置横坐标
            xdict = dict(enumerate(self.xAxis ))
            self.axisTime = MyStringAxis(xdict, orientation='bottom')
            # 初始化子图

            self.initCapital()
            # # 注册十字光标
            xAxis=self.xAxis
            viwe=self.pwOI
            self.crosshair=CrosshairTool(self.pw,xAxis,viwe,self)
            #设置界面
            self.vb = QtWidgets.QVBoxLayout()
            self.vb.addWidget(self.pw)
            self.setLayout(self.vb)

            # 初始化完成
            self.initCompleted = True

        # ----------------------------------------------------------------------

        def output(self, content):
            """输出内容"""
            print str(datetime.now()) + "\t" + content

            # ------------------------------------------------

        def initCapital(self):
            """初始化Capital图"""
            self.pwOI = self.makePI('PlotCapital')
            self.curveOI = self.pwOI.plot()
            self.lay_KL.addItem(self.pwOI)

            # ----------------------------------------------------------------------
            # ----------------------------------------------------------------------

        def makePI(self, name):
            """生成PlotItem对象"""
            vb = CustomViewBox()
            plotItem = pg.PlotItem(viewBox=vb, name=name, axisItems={'bottom': self.axisTime})
            plotItem.setMenuEnabled(False)
            plotItem.setClipToView(True)
            plotItem.showAxis('left')
            plotItem.hideAxis('right')
            plotItem.setDownsampling(mode='peak')
            plotItem.setRange(xRange=(0, 1), yRange=(0, 1))
            plotItem.getAxis('left').setWidth(60)#设置x坐标左边间距
            plotItem.getAxis('left').setStyle(tickFont=QFont("Roman times", 10, QFont.Bold))
            plotItem.getAxis('left').setPen(color=(255, 255, 255, 255), width=0.8)
            plotItem.showGrid(True, True)
            plotItem.hideButtons()
            return plotItem

        def PlotCapital(self, xmin=0, xmax=-1):
            """重画Capital图"""
            if self.initCompleted:
             ##self.cp=pg.plot(self.data['capitalList'][xmin:xmax])
             # self.cp=pg.PlotDataItem(self.data['capitalList'][xmin:xmax])
             # self.pwOI.addItem(self.cp)
             self.curveOI.setData(self.yAxis[xmin:xmax], name="capital")
             self.refresh()

        def refresh(self):
            """
            刷新三个子图的现实范围
            """
            leng_ = len(self.yAxis)
            xMin = min(self.yAxis)
            xMax = max(self.yAxis)
            self.pwOI.setRange(xRange=(0, leng_),yRange=(xMin, xMax))





