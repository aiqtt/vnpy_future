# encoding: UTF-8
import sys,os

import pyqtgraph as pg
import datetime as dt
import numpy as np
import traceback

from pyqtgraph.Qt import QtGui, QtCore
from pyqtgraph.Point import Point
########################################################################
# 十字光标支持
########################################################################
class CrosshairTool(QtCore.QObject):
    """
    此类给pg.PlotWidget()添加crossHair功能,PlotWidget实例需要初始化时传入
    """
    signal = QtCore.pyqtSignal(type(tuple([])))
    #----------------------------------------------------------------------
    def __init__( self,pw,xAxis,viwe,parent=None):
        self.__view = viwe
        self.pw=pw
        self.xData=xAxis
        super(CrosshairTool, self).__init__()
        self.xAxis = 0
        self.yAxis = 0

        # 在y轴动态mid跟随最新价显示最新价和最新时间
        self.rects = [self.__view.vb.sceneBoundingRect()]
        self.__textDate = pg.TextItem()
        self.__textSig=pg.TextItem()
        self.__textDate.setZValue(2)
        self.__textSig.setZValue(2)
        # 注册十字光标
        self.vLine = pg.InfiniteLine(angle=90, movable=False)
        self.hLine = pg.InfiniteLine(angle=0, movable=False)
        self.vLine.setPos(0)
        self.hLine.setPos(0)
        self.__view.vb.addItem(self.vLine, ignoreBounds=True)
        self.__view.vb.addItem(self.hLine, ignoreBounds=True)
        self.__view.vb.addItem(self.__textDate, ignoreBounds=True)
        self.__view.vb.addItem(self.__textSig, ignoreBounds=True)
        self.proxy = pg.SignalProxy(self.pw.scene().sigMouseMoved, rateLimit=60, slot=self.mouseMoved)
        # 跨线程刷新界面支持
        self.signal.connect(self.update)

    # ----------------------------------------------------------------------
    def update(self, pos):
        """刷新界面显示"""
        xAxis, yAxis = pos
        xAxis, yAxis = (self.xAxis, self.yAxis) if xAxis is None else (xAxis, yAxis)
        self.moveTo(xAxis, yAxis)

    # ----------------------------------------------------------------------
    def mouseMoved(self, evt):

            pos = evt[0]  ## using signal proxy turns original arguments into a tuple
            self.rects = [self.__view.vb.sceneBoundingRect()]
            # if self.pw.sceneBoundingRect().contains(pos):
            mousePoint = self.__view.vb.mapSceneToView(pos)
            xAxis = mousePoint.x()
            yAxis = mousePoint.y()
            self.moveTo(xAxis, yAxis)

     # ----------------------------------------------------------------------

    def moveTo(self, xAxis, yAxis):
        xAxis, yAxis = (self.xAxis, self.yAxis) if xAxis is None else (xAxis, yAxis)
        self.rects = [self.__view.sceneBoundingRect() ]
        if not xAxis or not yAxis:
            return
        self.xAxis = xAxis
        self.yAxis = yAxis
        self.vhLinesSetXY(xAxis, yAxis)
        self.plotVolue(xAxis,yAxis)
    # ----------------------------------------------------------------------

    def vhLinesSetXY(self, xAxis, yAxis):
        """水平和竖线位置设置"""
        self.vLine.setPos(xAxis)
        self.hLine.setPos(yAxis)
    # ----------------------------------------------------------------------
    def plotVolue(self,xAxis,yAxis):
        if self.xData:
            if int(round(xAxis)) <=len(self.xData)-1:
                 xValue =self.xData[int(round(xAxis))]
            elif int(xAxis)>len(self.xData)-1:
                xValue=self.xData[len(self.xData)-1]
            else:
                xValue = self.xData[int(xAxis)]
            if (isinstance(xValue, dt.datetime)):
                xValueText = dt.datetime.strftime(xValue, '%Y-%m-%d %H:%M:%S')
            elif (isinstance(xValue, (str))):
                xValueText = xValue
            elif (isinstance(xValue, (int))):
                xValueText = xValue
            else:
                xValueText = ""
        else:
             xValueText=xAxis
        self.__textDate.setHtml(
            '<div style="text-align: center">\
                <span style="color: yellow; font-size: 20px;">x=%s</span>\
            </div>' \
            % (xValueText))
        self.__textSig.setHtml(
            '<div style="text-align: right">\
                <span style="color: yellow; font-size: 20px;">y=%0.2f</span>\
            </div>' \
            % (yAxis))
        # y，右上角显示
        rightAxis = self.__view.getAxis('right')
        rightAxisWidth = rightAxis.width()
        rectTextsig = self.__textDate.boundingRect()
        rectTextsigwidth = rectTextsig.width()
        topRight = self.__view.vb.mapSceneToView(
            QtCore.QPointF(self.rects[0].width() - (rightAxisWidth+rectTextsigwidth), self.rects[0].top()))
        if yAxis<self.rects[0].top():
            self.__textSig.anchor=Point((1,1));
        else:
            self.__textSig.anchor = Point((1, 0));


        self.__textSig.setPos(topRight.x(), yAxis)
        # X坐标时间显示
        rectTextDate = self.__textDate.boundingRect()
        rectTextDateHeight = rectTextDate.height()
        bottomAxis = self.__view.getAxis('bottom')
        bottomAxisHeight = bottomAxis.height()
        bottomRight = self.__view.vb.mapSceneToView(QtCore.QPointF(self.rects[0].width(), \
                                                                   self.rects[0].bottom() - (
                                                                       bottomAxisHeight + rectTextDateHeight)))
        # # 修改对称方式防止遮挡
        if xAxis >self.rects[0].width():
            self.__textDate.anchor = Point((1, 0))
        else:
            self.__textDate.anchor = Point((0, 0))


        self.__textDate.setPos(xAxis, bottomRight.y())

