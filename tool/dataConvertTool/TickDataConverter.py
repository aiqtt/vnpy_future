# encoding: UTF-8
"""
tick历史数据的转换
1.增加时间的过滤 add by JingHui 20171124
        if ((NIGHT_START <= dt < NIGHT_END) or
            (DAY_OPEN <= dt < DAY_END)):
            return True
"""

import json
import os
from vnpy.trader.vtFunction import todayDate, getJsonPath
from vnpy.trader.vtObject import VtTickData
import csv
from datetime import datetime, time

NIGHT_START = time(21, 0)
NIGHT_END = time(2, 30)
DAY_OPEN = time(9, 0)
DAY_END = time(15, 0, 1)

class TickDataConverter(object):

    settingFileName = 'DCT_setting.json'
    settingFilePath = getJsonPath(settingFileName, __file__)

    def __init__(self):
        self.historyFilePath = None
        self.tickFilePath = None

        self.loadFileSettinig()

# --------------------------------------------------------------
    def loadFileSettinig(self):
        """读取文件路径配置"""
        with open(self.settingFilePath) as f:
            setting = json.load(f)
            self.historyFilePath = setting['history_file_path']
            self.tickFilePath = setting['tick_file_path']

#--------------------------------------------------------------
    def processLine(self, line):
        historyData = line.split(',')
        #historyDataLen = len(historyData)
        symbol = historyData[2]
        #print 'processLine, symbol:' + symbol

        #从list转化为tick对象
        historytick = VtTickData()
        historytick._id = historyData[0]
        historytick.gatewayName = 'CTP'
        historytick.symbol = symbol
        historytick.TradingDay = historyData[1]
        historytick.exchange = historyData[3]
        historytick.vtSymbol = historytick.symbol  # '.'.join([tick.symbol, tick.exchange])

        historytick.lastPrice = self.convertFloatZero(historyData[5])
        #lastVolume
        historytick.volume = historyData[12]
        historytick.openInterest = historyData[14]

        UpdateMillisec = int(historyData[20])
        historytick.time = '.'.join([historyData[19], str(UpdateMillisec/ 100)])
        historytick.date = historyData[42]
        historytick.datetime = datetime.strptime(' '.join([historytick.date, historytick.time]), '%Y%m%d %H:%M:%S.%f')

        historytick.openPrice = self.convertFloatZero(historyData[9])
        historytick.highPrice = self.convertFloatZero(historyData[10])
        historytick.lowPrice = self.convertFloatZero(historyData[11])
        historytick.preClosePrice = self.convertFloatZero(historyData[12])

        historytick.ClosePrice = self.convertFloatZero(historyData[15])
        historytick.SettlementPrice = self.convertFloatZero(historyData[16])
        historytick.upperLimit = self.convertFloatZero(historyData[17])
        historytick.lowerLimit = self.convertFloatZero(historyData[18])

        # CTP只有一档行情
        historytick.bidPrice1 = self.convertFloatZero(historyData[21])
        historytick.bidVolume1 = historyData[22]
        historytick.askPrice1 = self.convertFloatZero(historyData[23])
        historytick.askVolume1 = historyData[24]

        historytick.AveragePrice = self.convertFloatZero(historyData[41])

        return historytick

# --------------------------------------------------------------
    def runConvert(self):
        """
        同时打开两个文件，进行读写
        """
        fieldnames = ['_id', 'gatewayName', 'symbol', 'exchange', 'vtSymbol', 'lastPrice', 'lastVolume', 'volume',
                     'openInterest', 'time', 'date', 'datetime', 'openPrice', 'highPrice', 'lowPrice', 'preClosePrice',
                     'upperLimit', 'lowerLimit', 'bidPrice1', 'bidPrice2', 'bidPrice3', 'bidPrice4', 'bidPrice5',
                     'askPrice1', 'askPrice2', 'askPrice3', 'askPrice4', 'askPrice5',
                     'bidVolume1', 'bidVolume2', 'bidVolume3', 'bidVolume4', 'bidVolume5',
                     'askVolume1', 'askVolume2', 'askVolume3', 'askVolume4', 'askVolume5',
                     'TradingDay', 'PreSettlementPrice', 'PreOpenInterest', 'ClosePrice', 'SettlementPrice',
                     'AveragePrice']

        if os.path.exists(self.tickFilePath) and os.path.exists(self.historyFilePath):
            listDir = os.listdir(self.historyFilePath)#history文件夹下可能会有多个文件
            for f in listDir:
                file1 = self.historyFilePath + f
                if os.path.isfile(file1):
                    symbol = os.path.basename(file1)#文件名就是合约名字
                    historypath = self.historyFilePath + symbol
                    print historypath
                    tickpath = self.tickFilePath + symbol

                    with open(historypath, 'rb') as historyFile:
                        with open(tickpath, 'ab+') as tickFile:
                            dict_writer = csv.DictWriter(tickFile, fieldnames=fieldnames)
                            for line in historyFile:
                                tick = self.processLine(line)
                                if self.isDirtyData(tick):
                                    tick_dict = tick.__dict__
                                    del tick_dict['rawData']
                                    dict_writer.writerow(tick_dict)
                            print 'end for open...'
            print 'end fro listDir...'

# --------------------------------------------------------------
    def isDirtyData(self, tick):
        #根据时间过滤脏数据
        dt = datetime.strptime(tick.time, "%H:%M:%S.%f").time()
        if ((NIGHT_END < dt < DAY_OPEN) or (DAY_END < dt < NIGHT_START)):
            return False
        else:
            return True
# --------------------------------------------------------------
    def convertFloatZero(self, floatStr):
        """
        1.把老数据中的.00000换成0.0
        2.把多余的小数位去掉，只留一位
        """
        flaotArr = floatStr.split('.')
        if len(flaotArr) > 1:
            #有整数部分
            if len(flaotArr[1]) > 1:
                floatStr1 = flaotArr[1]
                return float('.'.join((flaotArr[0], floatStr1[0])))
            else:
                return float(floatStr)
        else:
            #无整数部分
            #if floatStr == '.00000':
                return 0.0


if __name__ == '__main__':
    test = TickDataConverter()
    #print test.convertZero('.00000')
    print test.convertFloatZero('123.6')