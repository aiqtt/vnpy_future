# encoding: UTF-8
from vnpy.trader.uiQt import QtGui, QtWidgets, QtCore, BASIC_FONT
from qtpy.QtCore import Qt,QRect
from qtpy.QtWidgets import QApplication, QWidget,QPushButton,QMenu
from qtpy.QtGui  import  QPainter, QPainterPath, QPen, QColor, QPixmap, QIcon, QBrush, QCursor
from vnpy.trader import vtText
from vnpy.event import Event
import qdarkstyle #Qt黑色主题
from vnpy.trader.IndicatorsFun.indicatorsManage import IndicatorsFunManage


import sys
class CustomMenu( QtWidgets.QPushButton):
    """合约管理组件"""
    signal = QtCore.Signal(type(Event()))
    # ----------------------------------------------------------------------
    def __init__(self,parent):
        """Constructor"""
        super(CustomMenu, self).__init__()
        self.parent=parent

        # self.initUi()
        self.initMenu()
    #-----------------------------------------------------------------------
    def initMenu(self):
        self.setStyleSheet("QMenu{background:purple;}"
                           "QMenu{border:1px solid lightgray;}"
                           "QMenu{border-color:green;}"
                           "QMenu::item{padding:0px 20px 0px 15px;}"
                           "QMenu::item{height:30px;}"
                           "QMenu::item{color:blue;}"
                           "QMenu::item{background:white;}"
                           "QMenu::item{margin:1px 0px 0px 0px;}"

                           "QMenu::item:selected:enabled{background:lightgray;}"
                           "QMenu::item:selected:enabled{color:white;}"
                           "QMenu::item:selected:!enabled{background:transparent;}"

                           "QMenu::separator{height:50px;}"
                           "QMenu::separator{width:1px;}"
                           "QMenu::separator{background:white;}"
                           "QMenu::separator{margin:1px 1px 1px 1px;}"

                           "QMenu#menu{background:white;}"
                           "QMenu#menu{border:1px solid lightgray;}"
                           "QMenu#menu::item{padding:0px 20px 0px 15px;}"
                           "QMenu#menu::item{height:15px;}"
                           "QMenu#menu::item:selected:enabled{background:lightgray;}"
                           "QMenu#menu::item:selected:enabled{color:white;}"
                           "QMenu#menu::item:selected:!enabled{background:transparent;}"
                           "QMenu#menu::separator{height:1px;}"
                           "QMenu#menu::separator{background:lightgray;}"
                           "QMenu#menu::separator{margin:2px 0px 2px 0px;}"
                           "QMenu#menu::indicator {padding:5px;}"
                           )
        self.color = QColor(Qt.gray)
        self.opacity = 1.0
        ''''''' 创建右键菜单 '''
        # 必须将ContextMenuPolicy设置为Qt.CustomContextMenu
        # 否则无法使用customContextMenuRequested信号
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.showContextMenu)

        # 创建QMenu
        self.contextMenu = QMenu(self)
        self.trendMenu=self.contextMenu.addMenu(u"趋势分析指标")
        self.swingMenu = self.contextMenu.addMenu(u"摆动分析")
        self.amountMenu = self.contextMenu.addMenu(u"量仓分析")
        # 添加二级菜单

        #趋势分析指标
        self.actionSAR= self.trendMenu.addAction(u'SAR')
        self.actionSAR.triggered.connect(lambda: self.parent.initIndicator(u"SAR"))

        self.actionBOLL = self.trendMenu.addAction(u'BOLL')
        self.actionBOLL.triggered.connect(lambda: self.parent.initIndicator(u"BOLL"))

        self.actionMA = self.trendMenu.addAction(u'MA')
        self.actionMA.triggered.connect(lambda: self.parent.initIndicator(u"MA"))

        #摆动分析
        self.actionCCI = self.swingMenu.addAction(u'CCI')
        self.actionCCI.triggered.connect(lambda: self.parent.initIndicator(u"CCI"))

        ##量仓分析
        self.actionOPI = self.amountMenu.addAction(u'OPI')
        self.actionOPI.triggered.connect(lambda: self.parent.initIndicator(u"OPI"))


        self.contextMenu.exec_(QCursor.pos())  # 在鼠标位置显示
        #添加二级菜单



    def showContextMenu(self, pos):
        '''''
        右键点击时调用的函数
        '''
        # 菜单显示前，将它移动到鼠标点击的位置
        # self.contextMenu.move(self.pos() + pos)
        self.contextMenu.show()
        self.contextMenu.exec_(QCursor.pos())
        # ----------------------------------------------------------------------
    # def initUi(self):
    #
    #     """初始化界面"""
    #     self.setWindowTitle(u"技术指标")
    #     self.resize(200,300)
    #     self.setLineWidth(1)
    #     self.buttonSar = QtWidgets.QPushButton(u"SAR")
    #     self.buttonSar.clicked.connect(lambda :self.parent.initIndicator(u"SAR"))
    #     self.buttonBoll = QtWidgets.QPushButton(u"BOLL")
    #     self.buttonBoll.clicked.connect(lambda :self.parent.initIndicator(u"BOLL"))
    #
    #
    #     self.grid=QtWidgets.QGridLayout()
    #     self.grid.addWidget(self.buttonSar , 0, 0)
    #     self.grid.addWidget(self.buttonBoll , 0, 1)
    #     hbox = QtWidgets.QHBoxLayout()
    #     hbox.addLayout(self.grid)
    #
    #
    #     vbox = QtWidgets.QVBoxLayout()
    #     vbox.addLayout(hbox)
    #     vbox.addStretch()
    #     self.setLayout( vbox)

# if __name__ == '__main__':
#         app = QApplication(sys.argv)
#         ex = QtWidgets.PushButton()
#         ex.show()
#         sys.exit(app.exec_())

