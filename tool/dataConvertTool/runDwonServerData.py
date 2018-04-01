# encoding: UTF-8

from downServerData import DownServerData
from datetime import timedelta
from vnpy.trader.vtFunction import todayDate

def runDataDown():
    runDown = DownServerData()
    day = todayDate() - timedelta(days=1)
    runDown.downloadTickDataOneDay(day)

def runOneSymbolDown():
    runDown = DownServerData()
    day = todayDate() - timedelta(days=1)
    #day = todayDate()
    runDown.downloadOneSymbol('rb1805', day)


if __name__ == '__main__':
    #runDataDown()
    runOneSymbolDown()