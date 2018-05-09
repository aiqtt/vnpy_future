# -*- coding: utf-8 -*-


# Qt相关和十字光标

from qtpy import QtWidgets, QtGui, QtCore
from qtpy.QtGui import QFont
from qtpy.QtCore import QObject, QUrl, Qt, pyqtSlot, pyqtSignal
from qtpy.QtWidgets import QApplication, QWidget,QFileDialog,QGridLayout,QLabel,QLineEdit,QPushButton,QDialogButtonBox

import pyqtgraph as pg
# 其他
import numpy as np
import pandas as pd
from functools import partial
from datetime import datetime, timedelta
from collections import deque
import qdarkstyle #Qt黑色主题
from vnpy.trader.uiKLine import *
import sys
reload(sys)
sys.setdefaultencoding('utf8')
# 字符串转换
# ---------------------------------------------------------------------------------------
try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    def _fromUtf8(s):
        return s


########################################################################
# 功能测试
########################################################################
import sys

def getTxtData(path):
    txtData = pd.DataFrame.from_csv(path, header=None, index_col=7)

    txtData = txtData.rename(
        columns={0: 'symbol', 1: "vtSymbol", 2: "exchange", 3: "open", 4: "high", 5: "low", 6: "close", 7: "date",
                 8: "time", 9: "datetime", 10: "volume", 11: "openInterest"})
    return txtData


if __name__ == '__main__':
    app = QApplication(sys.argv)
    # 界面设置
    cfgfile = QtCore.QFile('css.qss')
    cfgfile.open(QtCore.QFile.ReadOnly)
    styleSheet = cfgfile.readAll()
    styleSheet = unicode(styleSheet, encoding='utf8')
    app.setStyleSheet(styleSheet)

    #path = 'D:/data/10min/hc1705.txt'
    #path = 'D:/data/portfolio/rb1605hc1605.txt'
    path = 'D:/data/50etf/portfolio/1803-2.90.txt'
    # K线界面
    ui = KLineWidget(name="23")
    ui.show()
    ui.KLtitle.setText('day+ rb1101', size='10pt')




    ui.loadDataBar(getTxtData(path))




    app.exec_()
