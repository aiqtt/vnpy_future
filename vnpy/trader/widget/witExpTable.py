# -*- coding: utf-8 -*-
import sys
from qtpy import QtWidgets, QtGui, QtCore
from qtpy.QtCore import QTextCodec
import pyqtgraph as pg
from qtpy.QtWidgets import QWidget, QLabel, QLineEdit, QTextEdit, QGridLayout, QApplication
from vnpy.trader.uiBasicWidget import  *
from datetime import datetime, timedelta
# 如果安装了seaborn则设置为白色风格
try:
    import seaborn as sns

    sns.set_style('whitegrid')
except ImportError:
    pass

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    def _fromUtf8(s):
        return s



########################################################################
class Example(BasicMonitor):

    def __init__(self,data, parent=None):
        super(Example, self).__init__(parent)
        self.data = data
        self.columnCount =len(data)

        self.initTable()

    def formatNumber(self,n):
        """格式化数字到字符串"""
        rn = round(n, 2)  # 保留两位小数
        return format(rn, ',')  # 加上千分符
     # ----------------------------------------------------------------------

    def initTable(self):
        conLayout = QtWidgets.QVBoxLayout()
        tableWidget = QtWidgets.QTableWidget()
        keyItem=self.data['keyItem']
        tableWidget.setRowCount(len(keyItem)-1)

        tableWidget.setColumnCount( self.columnCount)
        tableWidget.setColumnWidth(1, 140)
        # tableWidget.setVerticalHeaderLabels(self.data['titleItem'])
        # 隐藏行表头
        tableWidget.horizontalHeader().setVisible(False);
        tableWidget.verticalHeader().setVisible(False);
        # 设为不可编辑
        tableWidget.setEditTriggers(self.NoEditTriggers)
        tableWidget.setFont(QtGui.QFont("Helvetica"));#设置字体
        tableWidget.setAutoScroll(False);#去掉自动滚动
        conLayout.addWidget(tableWidget)



        i=0
        for j in self.data['valueItem']:
            if i<len(self.data['keyItem']):
                tableItem1 = QtWidgets.QTableWidgetItem()
                tableItem1.setText(_fromUtf8(self.data['keyItem'][i]))
                tableItem=QtWidgets.QTableWidgetItem()
                tableItem.setText(str(j))

                tableWidget.setItem(i , 0,tableItem1 )
                tableWidget.setItem(i,1,tableItem)
                i+=1

        self.setLayout(conLayout)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = Example()
    sys.exit(app.exec_())


