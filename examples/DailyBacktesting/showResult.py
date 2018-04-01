# encoding: UTF-8


from vnpy.trader.uiBackMainWindow import *
import qdarkstyle #Qt黑色主题
from  vnpy.trader.widget.BackManage import *

import sys
reload(sys)
sys.setdefaultencoding('utf8')

if __name__ == '__main__': #加载本地trade.csv合约数据
    optKType =["15min"] ## 操作周期k线类型   1min  3min  5min  15min  30min  60min  day
    app = QtWidgets.QApplication(sys.argv)
    styleSheet = qdarkstyle.load_stylesheet(pyside=False)
    app.setStyleSheet(styleSheet)

    main = MainWindow()
    tradePath = getTempPath("trade.csv")
    abc = BackManager(main,tradePath,"G:/tick_bar/rb/",optKType)

    main.showMaximized()
    main.show()
    app.exec_()


