# -*- coding: utf-8 -*-



# Qt相关和十字光标
import pyqtgraph as pg
from qtpy import QtWidgets, QtGui, QtCore
from pyqtgraph.Point import Point
import datetime as dt

from vnpy.trader import *

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
from vnpy.trader.uiKLine  import *
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
            try:
                if event.angleDelta().y() / 120.0 > 0:
                    self.onUp()
                else:
                    self.onDown()
            except:
                if event.delta() > 0:
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

########################################################################
    class BarWidget(KeyWraper):
        #signal = QtCore.pyqtSignal(type(tuple([])))
        def __init__(self, xAxis,yAxis, parent=None):
            """Constructor"""
            self.parent = parent
            #self.data = data
            self.xAxis=xAxis
            self.yAxis = yAxis

            super(BarWidget, self).__init__(parent)#继承
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
            # 设置横坐标
            xdict = dict(enumerate(self.xAxis))
            self.axisTime = MyStringAxis(xdict, orientation='bottom')
            # 初始化子图
            self.initplotVol()
            # # 注册十字光标
            x =  self.xAxis
            viwe = self.pwVol
            self.crosshair = CrosshairTool(self.pw, x, viwe, self)
            # 设置界面
            self.vb = QtWidgets.QVBoxLayout()
            self.vb.addWidget(self.pw)
            self.setLayout(self.vb)

            # 初始化完成
            self.initCompleted = True
        # ----------------------------------------------------------------------
        def output(self, content):
            """输出内容"""
            print str(datetime.now()) + "\t" + content

            # ----------------------------------------------------------------------
        def formatNumber(n):
             """格式化数字到字符串"""
             rn = round(n, 2)  # 保留两位小数
             return format(rn, ',')  # 加上千分符
            # ------------------------------------------------

        def initplotVol(self):
            """初始化成交量子图"""
            self.pwVol = self.makePI('PlotVol')#必要
            self.volume = RectItem(self.yAxis)
            self.pwVol.addItem(self.volume)
            self.lay_KL.nextRow()
            self.lay_KL.addItem(self.pwVol)
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

            # ----------------------------------------------------------------------
            #  画图相关
            # ----------------------------------------------------------------------

        def plotVol(self, redraw=False):
            """重画drawdown图"""
            if self.initCompleted:

               # self.vol = pg.BarGraphItem(x=range(len(self.data['timeList'])), height=self.data['drawdownList'], width=0.5)# 画图
               # self.pwVol.addItem(self.vol)
              self.volume.generatePicture(self.yAxis, redraw)
              #self.refresh()

        def refresh(self):
            """
            刷新三个子图的现实范围
            """
            leng_ = len(self.yAxis)
            xMin = min(self.yAxis)
            xMax = max(self.yAxis)



            self.pwVol.setRange(xRange=(0, leng_),yRange=(xMin, xMax))
########################################################################





########################################################################
# K线图形对象

class CandlestickItem(pg.GraphicsObject):
    """K线图形对象"""

    # 初始化
    #----------------------------------------------------------------------
    def __init__(self, data):
        """初始化"""
        pg.GraphicsObject.__init__(self)
        # 数据格式: [ (time, open, close, low, high),...]
        self.data = data
        # 只重画部分图形，大大提高界面更新速度
        self.setFlag(self.ItemUsesExtendedStyleOption)
        # 画笔和画刷
        w = 0.4
        self.offset   = 0
        self.low      = 0
        self.high     = 1
        self.picture  = QtGui.QPicture()
        self.pictures = []
        self.bPen     = pg.mkPen(color=(0, 240, 240, 255), width=w*2)
        self.bBrush   = pg.mkBrush((0, 240, 240, 255))
        self.rPen     = pg.mkPen(color=(255, 60, 60, 255), width=w*2)
        self.rBrush   = pg.mkBrush((255, 60, 60, 255))
        self.rBrush.setStyle(Qt.NoBrush)
        # 刷新K线

        self.generatePicture(self.data)


    # 画K线
    #----------------------------------------------------------------------
    def generatePicture(self,data=None,redraw=False):
        """重新生成图形对象"""
        # 重画或者只更新最后一个K线
        if redraw:
            self.pictures = []
        elif self.pictures:
            self.pictures.pop()
        w = 0.4
        bPen   = self.bPen
        bBrush = self.bBrush
        rPen   = self.rPen
        rBrush = self.rBrush
        low,high = (data[0],data[0]) if len(data)>0 else (0,1)
        for (t, open0, close0, low0, high0) in data:
            if t >= len(self.pictures):

                tShift = t

                low,high = (min(low,low0),max(high,high0))
                picture = QtGui.QPicture()
                p = QtGui.QPainter(picture)
                # 下跌蓝色（实心）, 上涨红色（空心）
                pen,brush,pmin,pmax = (bPen,bBrush,close0,open0)\
                    if open0 > close0 else (rPen,rBrush,open0,close0)
                p.setPen(pen)
                p.setBrush(brush)
                # 画K线方块和上下影线
                if open0 == close0:
                    p.drawLine(QtCore.QPointF(tShift-w,open0), QtCore.QPointF(tShift+w, close0))
                else:
                    p.drawRect(QtCore.QRectF(tShift-w, open0, w*2, close0-open0))
                if pmin  > low0:
                    p.drawLine(QtCore.QPointF(tShift,low0), QtCore.QPointF(tShift, pmin))
                if high0 > pmax:
                    p.drawLine(QtCore.QPointF(tShift,pmax), QtCore.QPointF(tShift, high0))
                p.end()
                self.pictures.append(picture)
        self.low,self.high = low,high

    # 手动重画
    #----------------------------------------------------------------------
    def update(self):
        if not self.scene() is None:
            self.scene().update()

    # 自动重画
    #----------------------------------------------------------------------
    def paint(self, p, o, w):
        rect = o.exposedRect
        xmin,xmax = (max(0,int(rect.left())),min(len(self.pictures),int(rect.right())))
        [p.drawPicture(0, 0, pic) for pic in self.pictures[xmin:xmax]]

    # 定义边界
    #----------------------------------------------------------------------
    def boundingRect(self):
        return QtCore.QRectF(0,self.low,len(self.pictures),(self.high-self.low))



# 柱图形对象
########################################################################
class RectItem(pg.GraphicsObject):
    """K线图形对象"""

    # 初始化
    #----------------------------------------------------------------------
    def __init__(self, data):
        """初始化"""
        pg.GraphicsObject.__init__(self)
        # 数据格式:
        self.data = data
        # 只重画部分图形，大大提高界面更新速度
        self.setFlag(self.ItemUsesExtendedStyleOption)
        # 画笔和画刷
        w = 0.4

        self.picture  = QtGui.QPicture()
        self.pictures = []
        self.bPen     = pg.mkPen(color=(0, 240, 240, 255), width=w*2)
        self.bBrush   = pg.mkBrush((0, 240, 240, 255))
        self.rPen     = pg.mkPen(color=(255, 60, 60, 255), width=w*2)
        self.rBrush   = pg.mkBrush((255, 60, 60, 255))
        self.rBrush.setStyle(Qt.NoBrush)
        # 刷新K线

        self.generatePicture(self.data)


    # 画K线
    #----------------------------------------------------------------------
    def generatePicture(self,data=None,redraw=False):
        """重新生成图形对象"""
        # 重画或者只更新最后一个K线
        if redraw:
            self.pictures = []
        elif self.pictures:
            self.pictures.pop()
        w = 0.2
        t = 0
        for d in data:
            if t >= len(self.pictures):
                tShift = t
                picture = QtGui.QPicture()
                p = QtGui.QPainter(picture)
                # 下跌蓝色（实心）, 上涨红色（空心）

                p.setPen(self.bPen)
                p.setBrush(self.bBrush)
                # 画K线方块和上下影线

                p.drawRect(QtCore.QRectF(tShift - w, 0, w * 2, d))

                p.end()
                self.pictures.append(picture)
                t += 1



    # 手动重画
    #----------------------------------------------------------------------
    def update(self):
        if not self.scene() is None:
            self.scene().update()

    # 自动重画
    #----------------------------------------------------------------------
    def paint(self, p, o, w):
        rect = o.exposedRect
        xmin,xmax = (max(0,int(rect.left())),min(len(self.pictures),int(rect.right())))
        [p.drawPicture(0, 0, pic) for pic in self.pictures[xmin:xmax]]

    # 定义边界
    #----------------------------------------------------------------------
    def boundingRect(self):
        low = min(self.data[0:-1])
        high = max(self.data[0:-1])
        return QtCore.QRectF(0,low,len(self.pictures),(high-low))




