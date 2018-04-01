# encoding: UTF-8
import psutil
from qtpy import QtCore, QtGui, QtWidgets
from qtpy.QtWidgets import *

from qtpy.QtCore import *
from qtpy.QtGui import *
import traceback

from vnpy.trader.vtFunction import loadIconPath
from vnpy.trader.vtGlobal import globalSetting
from vnpy.trader.uiBasicWidget import *

# 字符串转换
#---------------------------------------------------------------------------------------
try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    def _fromUtf8(s):
        return s

class MainWindow( QtWidgets .QMainWindow):
    signalStatusBar = QtCore.Signal(type(Event()))
    def __init__(self):
        QtWidgets.QMainWindow.__init__(self)
        super(MainWindow, self).__init__()
        self.initUi()
    # ----------------------------------------------------------------------
    def initUi(self):
        """初始化界面"""
        self.setWindowTitle(u'爱宽客')
        #self.initCentral()
        self.initMenu()
       # self.initStatusBar()
        # ----------------------------------------------------------------------

    def initCentral(self):
        """初始化中心区域"""


        self. saveWindowSettings('default')

    def createDock(self, widget,dockName,dockTitle,widgetArea,isMova):
        # 停靠窗口2
        dock = QtWidgets.QDockWidget(dockTitle)
        dock.setWidget(widget)
        dock.setObjectName(dockName)
        if isMova:
            dock.setFeatures(dock.DockWidgetFloatable | dock.DockWidgetMovable|QDockWidget.AllDockWidgetFeatures)
        else:
            dock.setFeatures(dock.DockWidgetFloatable)
        self.addDockWidget(widgetArea, dock)
        #return  dock
        #self.addDockWidget(Qt.RightDockWidgetArea, dockName)
    # ----------------------------------------------------------------------

    def initMenu(self):
        """初始化菜单"""
        # 创建菜单
        menubar = self.menuBar()
        # 帮助
        helpMenu = menubar.addMenu(vtText.HELP)
        # helpMenu.addAction(self.createAction(vtText.CONTRACT_SEARCH, self.openContract, loadIconPath('contract.ico')))
        # helpMenu.addAction(self.createAction(vtText.EDIT_SETTING, self.openSettingEditor, loadIconPath('editor.ico')))
        helpMenu.addSeparator()
        helpMenu.addAction(self.createAction(vtText.RESTORE, self.restoreWindow, loadIconPath('restore.ico')))
        helpMenu.addAction(self.createAction(vtText.ABOUT, self.openAbout, loadIconPath('about.ico')))
        #helpMenu.addSeparator()
        #helpMenu.addAction(self.createAction(vtText.TEST, self.test, loadIconPath('test.ico')))
     # ----------------------------------------------------------------------

    def createAction(self, actionName, function, iconPath=''):
        """创建操作功能"""
        action = QtWidgets.QAction(actionName, self)
        action.triggered.connect(function)

        if iconPath:
            icon = QtGui.QIcon(iconPath)
            action.setIcon(icon)

        return action

    # ----------------------------------------------------------------------
    def saveWindowSettings(self, settingName):
            """保存窗口设置"""
            settings = QtCore.QSettings('vn.trader', settingName)
            settings.setValue('state', self.saveState())
            settings.setValue('geometry', self.saveGeometry())

    # ----------------------------------------------------------------------
    def loadWindowSettings(self, settingName):
            """载入窗口设置"""
            settings = QtCore.QSettings('vn.trader', settingName)
            state = settings.value('state')
            geometry = settings.value('geometry')

            # 尚未初始化
            if state is None:
                return
            # 老版PyQt
            elif isinstance(state, QtCore.QVariant):
                self.restoreState(state.toByteArray())
                self.restoreGeometry(geometry.toByteArray())
            # 新版PyQt
            elif isinstance(state, QtCore.QByteArray):
                self.restoreState(state)
                self.restoreGeometry(geometry)
            # 异常
            else:
                content = u'载入窗口配置异常，请检查'
                self.mainEngine.writeLog(content)

                # ----------------------------------------------------------------------

    # ----------------------------------------------------------------------
    def openAbout(self):
        """打开关于"""
        try:
            self.widgetDict['aboutW'].show()
        except KeyError:
            self.widgetDict['aboutW'] = AboutWidget(self)
            self.widgetDict['aboutW'].show()

    #----------------------------------------------------------------------
    def restoreWindow(self):
        """还原默认窗口设置（还原停靠组件位置）"""
        self.loadWindowSettings('default')
        self.showMaximized()


class AboutWidget(QtWidgets.QDialog):
    """显示关于信息"""

    # ----------------------------------------------------------------------
    def __init__(self, parent=None):
        """Constructor"""
        super(AboutWidget, self).__init__(parent)

        self.initUi()

    # ----------------------------------------------------------------------
    def initUi(self):
        """"""
        self.setWindowTitle(vtText.ABOUT + u'爱宽客量化交易平台')

        text = u"""

            Website：www.aiqtt.com

            """

        label = QtWidgets.QLabel()
        label.setText(text)
        label.setMinimumWidth(500)

        vbox = QtWidgets.QVBoxLayout()
        vbox.addWidget(label)

        self.setLayout(vbox)
