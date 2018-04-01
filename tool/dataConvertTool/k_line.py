# encoding: UTF-8
"""
生成K线数据
"""
import json
import os
from vnpy.trader.vtFunction import todayDate, getJsonPath
from vnpy.trader.vtObject import VtTickData, VtBarData
import csv
from datetime import datetime, timedelta , time

class k_line(object):

    settingFileName = 'DCT_setting.json'
    settingFilePath = getJsonPath(settingFileName, __file__)

    def __init__(self):

        #self.FilePath = 'D:/data/'

        self.FilePath = None
        self.loadSetting()



    #----------------------------------------------------------------------
    def loadSetting(self):
        """加载配置"""
        with open(self.settingFilePath) as f:
            drSetting = json.load(f)

            self.FilePath = drSetting['data_path']
            #if not os.path.exists(self.FilePath):
            #    os.mkdir(self.FilePath)


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

        varFieldNames = ['vtSymbol' , 'symbol', 'exchange', 'open', 'high', 'low' , 'close' , 'date', 'time', 'datetime', 'volume', 'openInterest']

        if os.path.exists(self.FilePath+'tick/'):
            listDir = os.listdir(self.FilePath+'tick/')#文件夹下可能会有多个文件
            for f in listDir:
                file1 = self.FilePath+'tick/' + f
                if os.path.isfile(file1):
                    symbol = os.path.basename(file1)  #文件名就是合约名字
                    #if os.path.isfile(self.FilePath+'1min/'+symbol) :  #如果文件存在，不处理
                    #    continue
                    with open(self.FilePath+'tick/'+symbol, 'rb') as tickFile:
                        # 处理合成K线
                        file_1min = open(self.FilePath+'1min/'+symbol, 'ab+')
                        file_3min = open(self.FilePath+'3min/'+symbol, 'ab+')
                        file_5min = open(self.FilePath+'5min/'+symbol, 'ab+')
                        file_15min = open(self.FilePath+'15min/'+symbol, 'ab+')
                        file_30min = open(self.FilePath+'30min/'+symbol, 'ab+')
                        file_60min = open(self.FilePath+'60min/'+symbol, 'ab+')
                        file_day = open(self.FilePath+'day/'+symbol, 'ab+')

                        barmanger = RecorderBarManager(csv.DictWriter(file_1min, varFieldNames),
                                                       csv.DictWriter(file_3min, varFieldNames),
                                                       csv.DictWriter(file_5min, varFieldNames),
                                                       csv.DictWriter(file_15min, varFieldNames),
                                                       csv.DictWriter(file_30min, varFieldNames),
                                                       csv.DictWriter(file_60min, varFieldNames),
                                                       csv.DictWriter(file_day, varFieldNames))

                        dict_reader = csv.DictReader(tickFile, fieldnames=fieldnames)
                        for reader in dict_reader:
                            #print( reader['_id'])
                            barmanger.updateTick(reader)
                        #读文件结束后再调一次，防止最后一个bar不生成
                        barmanger.updateTick(None)
                        file_1min.close()
                        file_3min.close()
                        file_5min.close()
                        file_15min.close()
                        file_30min.close()
                        file_60min.close()
                        file_day.close()
            print 'end fro listDir...'


class RecorderBarManager(object):
    """
    K线合成器，支持：
    1. 基于Tick合成1分钟K线
    2. 基于1分钟K线合成X分钟K线（X可以是2、3、5、10、15、30、60）
    """

    #----------------------------------------------------------------------
    def __init__(self, file_1min, file_3min, file_5min, file_15min,file_30min,file_60min, file_day):
        """Constructor"""
        self.bar = None             # 1分钟K线对象
        self.dayBar = None

        self.xminBar = None         # X分钟K线对象
        self.file_1min = file_1min
        self.file_3min = file_3min
        self.file_5min = file_5min
        self.file_15min = file_15min
        self.file_30min = file_30min
        self.file_60min = file_60min
        self.file_day   = file_day

        self.lastTick = None        # 上一TICK缓存对象

        self.myXminBar = {}
        self.myXminBar[3] = None
        self.myXminBar[5] = None
        self.myXminBar[15] = None
        self.myXminBar[30] = None
        self.myXminBar[60] = None

        self.DAY_END = time(15, 00)
        self.NIGHT_START = time(20, 57)      # 夜盘启动和停止时间



    #----------------------------------------------------------------------
    def onBar(self, bar):
        """分钟线更新"""
        dicta = bar.__dict__
        del dicta['gatewayName']
        del dicta['rawData']
        self.file_1min.writerow(dicta)

        self.updateBar(bar)

    #----------------------------------------------------------------------

    def onXBar(self, xmin, bar):
        """X分钟线更新"""
        vtSymbol = bar.vtSymbol
        dicta = bar.__dict__
        del dicta['gatewayName']
        del dicta['rawData']

        if xmin == 3:
            self.file_3min.writerow(dicta)

        if xmin == 5:
            self.file_5min.writerow(dicta)

        if xmin == 15:
            self.file_15min.writerow(dicta)

        if xmin == 30:
            self.file_30min.writerow(dicta)

        if xmin == 60:
            self.file_60min.writerow(dicta)
            self.updateDay(bar)

    def onDayBar(self, bar):
        vtSymbol = bar.vtSymbol
        dicta = bar.__dict__
        del dicta['gatewayName']
        del dicta['rawData']
        self.file_day.writerow(dicta)

    def loadTickData(self, tick):

        tickData = VtTickData()
        tickData.lastPrice = float(tick['lastPrice'])
        tickData.date = tick['date']
        tickData.time = tick['time']
        tickData.datetime = datetime.strptime(' '.join([tick['date'], tick['time']]), '%Y%m%d %H:%M:%S.%f')
        tickData.volume = int(tick['volume'])
        tickData.vtSymbol = tick['vtSymbol']
        tickData.symbol = tick['symbol']
        tickData.exchange = tick['exchange']
        tickData.openInterest = int(tick['openInterest'])

        return tickData

    #----------------------------------------------------------------------
    def updateTick(self, tickData):
        """TICK更新"""
        newMinute = False   # 默认不是新的一分钟

        if not tickData:
            #传入的数据是None，表示文件末尾，强制结束当前bar，不然会丢掉最后一天
            if self.bar and self.lastTick:
                self.bar.datetime = self.bar.datetime.replace(second=0, microsecond=0)  # 将秒和微秒设为0
                self.bar.date = self.bar.datetime.strftime('%Y%m%d')
                self.bar.time = self.bar.datetime.strftime('%H:%M:%S.%f')

                # 推送已经结束的上一分钟K线
                self.onBar(self.bar)
            return

        tick = self.loadTickData(tickData)
        #tick.time = tick.datetime.strftime('%H:%M:%S.%f')

        if tick.lastPrice == 0.0:  ##过滤当前价为0的。
            return

        # 生成datetime对象
        #if not tick['datetime']:
        #tick['datetime'] = datetime.strptime(' '.join([tick['date'], tick['time']]), '%Y%m%d %H:%M:%S.%f')

        #判断整点的数据缺失，强制生成整点的bar(13是休市，要去掉)
        hour_not_end = (self.bar != None) and (tick.datetime.minute != 0 and tick.datetime.second != 0) and (tick.datetime.hour != 13) and (tick.datetime.hour != self.bar.datetime.hour)
        #15点需要单独判断
        day_not_end = (self.bar != None) and (tick.datetime.hour == 21 or tick.datetime.hour == 9) and self.bar.datetime.hour == 14
        #整点(23点和1点)结束的夜盘也需要判断有无缺失
        night_not_end1 = (self.bar != None) and (tick.datetime.hour == 9) and self.bar.datetime.hour == 23
        night_not_end2 = (self.bar != None) and (tick.datetime.hour == 9) and self.bar.datetime.hour == 0
        not_end_falg = (day_not_end or night_not_end1 or night_not_end2)
        if (hour_not_end or not_end_falg):
            #新tick不是整点，证明整点的tick丢失
            # 生成上一分钟K线的时间戳
            self.bar.datetime = self.bar.datetime.replace(second=0, microsecond=0)  # 将秒和微秒设为0
            self.bar.date = self.bar.datetime.strftime('%Y%m%d')
            self.bar.time = self.bar.datetime.strftime('%H:%M:%S.%f')

            # 推送已经结束的上一分钟K线
            self.onBar(self.bar)

            # 有丢失，就用前一小时的最后一个tick复制生成整点的bar
            self.bar = VtBarData()
            self.bar.vtSymbol = self.lastTick.vtSymbol
            self.bar.symbol = self.lastTick.symbol
            self.bar.exchange = self.lastTick.exchange

            self.bar.open = self.lastTick.lastPrice
            self.bar.high = self.lastTick.lastPrice
            self.bar.low = self.lastTick.lastPrice

            self.bar.close = self.lastTick.lastPrice
            self.bar.openInterest = self.lastTick.openInterest
            self.bar.volume = int(self.lastTick.volume)

            if day_not_end:
                hour_str = "15:00:00.000"
            elif night_not_end1:
                hour_str = "23:00:00.000"
            elif night_not_end2:
                hour_str = "01:00:00.000"
            else:
                hour_str = tick.datetime.strftime("%H") + ":00:00.000"
            self.bar.datetime = datetime.strptime(' '.join([tick.date, hour_str]), '%Y%m%d %H:%M:%S.%f')
            self.bar.date = self.bar.datetime.strftime('%Y%m%d')
            self.bar.time = self.bar.datetime.strftime('%H:%M:%S.%f')
            #推送整点的bar
            self.onBar(self.bar)
            #恢复正常流程
            self.bar = None

        #因为是读文件，需要用21点(或没夜盘用9点)的tick来判断15点的bar
        day_close = False
        night_close = False
        if self.bar:
            day_close = ((tick.datetime.hour == 21 or tick.datetime.hour == 9) and self.bar.datetime.hour == 15)
            night_close = ((tick.datetime.hour == 9) and (self.bar.datetime.hour == 23 or self.bar.datetime.hour == 1))
        close_flag = (day_close or night_close)

        # 尚未创建对象
        if not self.bar:
            self.bar = VtBarData()
            newMinute = True
        # 新的一分钟
        elif ((self.bar.datetime.minute != tick.datetime.minute) or close_flag):
            # 生成上一分钟K线的时间戳
            self.bar.datetime = self.bar.datetime.replace(second=0, microsecond=0)  # 将秒和微秒设为0
            self.bar.date = self.bar.datetime.strftime('%Y%m%d')
            self.bar.time = self.bar.datetime.strftime('%H:%M:%S.%f')

            # 推送已经结束的上一分钟K线
            self.onBar(self.bar)

            # 创建新的K线对象
            self.bar = VtBarData()
            newMinute = True

        # 初始化新一分钟的K线数据
        if newMinute:
            self.bar.vtSymbol = tick.vtSymbol
            self.bar.symbol = tick.symbol
            self.bar.exchange = tick.exchange

            self.bar.open = tick.lastPrice
            self.bar.high = tick.lastPrice
            self.bar.low = tick.lastPrice
        # 累加更新老一分钟的K线数据
        else:
            self.bar.high = max(self.bar.high, tick.lastPrice)
            self.bar.low = min(self.bar.low, tick.lastPrice)

        # 通用更新部分
        self.bar.close = tick.lastPrice
        self.bar.datetime = tick.datetime
        self.bar.openInterest = tick.openInterest

        if self.lastTick:
            currntVolume = int(tick.volume)
            if currntVolume == 0:  # 晚上9点或早上，即开市的第一个tick的volume
                self.bar.volume = 0
            elif int(tick.volume) < int(self.lastTick.volume):
                # 开市的情况下，lastTick是上一日的，因此判断是负数的话不用lastTick
                self.bar.volume = int(tick.volume)
            else :
                self.bar.volume += (int(tick.volume) - int(self.lastTick.volume)) # 当前K线内的成交量

        # 缓存Tick
        self.lastTick = tick

    #----------------------------------------------------------------------
    def updateBar(self, bar):
        for min in self.myXminBar:
            self.updateMyBar(min, bar)
#----------------------------------------------------------------------

    def updateMyBar(self, minute, bar):
        """1分钟K线更新"""
        # 尚未创建对象
        if not self.myXminBar[minute]:
            self.myXminBar[minute] = VtBarData()

            self.myXminBar[minute].vtSymbol = bar.vtSymbol
            self.myXminBar[minute].symbol = bar.symbol
            self.myXminBar[minute].exchange = bar.exchange

            self.myXminBar[minute].open = bar.open
            self.myXminBar[minute].high = bar.high
            self.myXminBar[minute].low = bar.low
        # 累加老K线
        else:
            self.myXminBar[minute].high = max(self.myXminBar[minute].high, bar.high)
            self.myXminBar[minute].low = min(self.myXminBar[minute].low, bar.low)

        # 通用部分
        self.myXminBar[minute].close = bar.close
        self.myXminBar[minute].datetime = bar.datetime
        self.myXminBar[minute].openInterest = bar.openInterest
        self.myXminBar[minute].volume += int(bar.volume)

        # X分钟已经走完
        if (not bar.datetime.minute % minute) :   # 可以用X整除
            # 生成上一X分钟K线的时间戳
            self.myXminBar[minute].datetime = self.myXminBar[minute].datetime.replace(second=0, microsecond=0)  # 将秒和微秒设为0
            self.myXminBar[minute].date = self.myXminBar[minute].datetime.strftime('%Y%m%d')
            self.myXminBar[minute].time = self.myXminBar[minute].datetime.strftime('%H:%M:%S.%f')

            # 推送
            self.onXBar(minute, self.myXminBar[minute])

            # 清空老K线缓存对象
            self.myXminBar[minute] = None


#----------------------------------------------------------------------

    def updateDay(self,  bar):
        """天更新"""
        # 尚未创建对象
        if not self.dayBar:
            self.dayBar = VtBarData()

            self.dayBar.vtSymbol = bar.vtSymbol
            self.dayBar.symbol = bar.symbol
            self.dayBar.exchange = bar.exchange

            self.dayBar.open = bar.open
            self.dayBar.high = bar.high
            self.dayBar.low = bar.low
        # 累加老K线
        else:
            self.dayBar.high = max(self.dayBar.high, bar.high)
            self.dayBar.low = min(self.dayBar.low, bar.low)

        # 通用部分
        self.dayBar.close = bar.close
        self.dayBar.datetime = bar.datetime
        self.dayBar.openInterest = bar.openInterest
        self.dayBar.volume += int(bar.volume)

        # 判断天数
        if  bar.datetime.time()  == self.DAY_END :   #
            print "updateDay:%s" % bar.date
            # 生成上一X分钟K线的时间戳
            self.dayBar.datetime = self.dayBar.datetime.replace(hour=0,minute=0,second=0, microsecond=0)  # 将秒和微秒设为0
            self.dayBar.date = self.dayBar.datetime.strftime('%Y%m%d')
            self.dayBar.time = self.dayBar.datetime.strftime('%H:%M:%S.%f')

            # 推送
            self.onDayBar(self.dayBar)

            # 清空老K线缓存对象
            self.dayBar = None


if __name__ == '__main__':
    print('---start convert ---')
    kLine = k_line()
    kLine.runConvert()
    print('----end----')