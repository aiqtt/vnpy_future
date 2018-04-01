# encoding: UTF-8
from vnpy.trader.vtConstant import (EMPTY_STRING, EMPTY_UNICODE,
                                    EMPTY_FLOAT, EMPTY_INT)
from vnpy.trader.vtFunction import getJsonPath,getTempPath
import numpy as np
import pandas as pd
import json
import talib

import pyqtgraph as pg

import os
import importlib
import traceback

from .algo import INDICATORS_CLASS,sarAlgo,bollAlgo

###################切换指标##########################
class IndicatorsFunManage(object):
    settingFileName = 'Indicators_setting.json'
    settingfilePath = getJsonPath(settingFileName, __file__)
    def __init__(self, parent):
        self.indicators_seeting=None   # 指标配置文件
        self.parent = parent
        self.indicatorsFunc = {}  # 添加指标
        # 读取本地指标配置文件
        with open(self.settingfilePath) as f:
            self.indicators_seeting = json.load(f)

    def  RemoveIndicators(self,name):
        if self.indicatorsFunc.has_key(name):
            removeFunc = self.indicatorsFunc[name]
            removeFunc.remove()

    def getYRange(self,xMin,xMax,location):
         if self.indicatorsFunc:
            for indicators in self.indicatorsFunc.values():
                if indicators.base.figure == location:
                    return  indicators.getYRange(xMin, xMax)

         return 0,1

    def addIndicators(self,name):
        if self.indicatorsFunc.has_key(name):
            return

        if not (self.indicatorsFunc.has_key(name)):
            indicatorsInfo = self.indicators_seeting[name]
            figure =indicatorsInfo["location"]
            if self.indicatorsFunc:
                for indicators in self.indicatorsFunc.values():
                    if indicators.base.figure == figure:
                        indicators.remove()
                        del self.indicatorsFunc[indicators.base.name]
                        break
            indicator = self.startFun(indicatorsInfo, name)
            if indicator:
                self.indicatorsFunc[name] = indicator
                indicator.addIndicators()


    def updateIndicators(self):
        if self.indicatorsFunc:
             for indicators in self.indicatorsFunc.values():
                indicators.updateIndicators()


    def getIndicatorsHtml(self,figure,index):
        if self.indicatorsFunc:
            for indicators in self.indicatorsFunc.values():
                if indicators.base.figure == figure:
                    html = indicators.getIndicatorsHtml(index)
                    return html


    def startFun(self,indicatorsInfo,name):
        """载入算法"""
        try:
            className = indicatorsInfo["className"]
        except Exception, e:
            print (u'载入指标算法出错：%s' % e)

        # 获取算法类
        alogClass = INDICATORS_CLASS.get(className, None)
        return self.callIndicatorsFunc(alogClass, self.parent, indicatorsInfo, name)
        if not alogClass:
            print(u'找不到指标算法类：%s' % className)

        return None

     # ----------------------------------------------------------------------

    def callIndicatorsFunc(self, func, parent, indicatorsInfo, name):
        """调用策略的函数，若触发异常则捕捉"""
        try:
            if parent:
                return func(parent, indicatorsInfo, name)
                #self.indicatorsFunc[name] = self.func

        except Exception:
            # 停止类，修改状态为未初始化

            print(u'算法%s触发异常已停止', traceback.format_exc())

