# encoding: UTF-8


import copy
from datetime import  time
from vnpy.trader.vtObject import VtTickData, VtBarData


########################################################################
class BarManager(object):
    """
    K线合成器，支持：
    1. 基于Tick合成1分钟K线
    2. 基于1分钟K线合成X分钟K线（X可以是2、3、5、10、15、30、60）
    """

    #----------------------------------------------------------------------
    def __init__(self, onBar, xmin=0, onXminBar=None):
        """Constructor"""
        self.bar = None             # 1分钟K线对象
        self.onBar = onBar          # 1分钟K线回调函数

        self.xminBar = None         # X分钟K线对象
        self.xmin = xmin            # X的值
        self.onXminBar = onXminBar  # X分钟K线的回调函数

        self.lastTick = None        # 上一TICK缓存对象

    #----------------------------------------------------------------------
    def updateTick(self, tick):
        """TICK更新"""
        newMinute = False   # 默认不是新的一分钟

        # 小时线生成----判断59min-bar的数据缺失，强制生成整点的bar(13是休市，要去掉)(包括了23:30结束的夜盘)
        # 说明：bar的hour和tick的hour不同，表示进入了下一小时，这时bar的min不是59，证明59min-bar缺失了
        hour_not_end = (self.bar != None) and (tick.datetime.hour != 13) and (tick.datetime.hour != 9) and (self.bar.datetime.hour != tick.datetime.hour) and (self.bar.datetime.minute != 59)

        if hour_not_end:
            # 生成上一分钟K线的时间戳
            self.bar.datetime = self.bar.datetime.replace(second=0, microsecond=0)  # 将秒和微秒设为0
            self.bar.date = self.bar.datetime.strftime('%Y%m%d')
            self.bar.time = self.bar.datetime.strftime('%H:%M:%S.%f')

            # 推送已经结束的上一分钟K线
            self.onBar(self.bar)

            not_end_bar = copy.deepcopy(self.bar)
            not_end_bar.gatewayName = None
            not_end_bar.rawData = None
            #复制上一个bar来生成59min-bar
            not_end_bar.datetime = not_end_bar.datetime.replace(minute=59)
            not_end_bar.time = not_end_bar.datetime.strftime('%H:%M:%S.%f')
            #推送整点的bar
            self.onBar(not_end_bar)

            #恢复正常流程
            self.bar = None

        # 尚未创建对象
        if not self.bar:
            self.bar = VtBarData()
            newMinute = True
        # 新的一分钟
        elif (self.bar.datetime.minute != tick.datetime.minute):
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
            #self.bar.TradingDay = tick.TradingDay

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
        #TradingDay写在这里，把夜盘收盘的tick算在9点里面，避免9点的分钟bar被算到前一天
        self.bar.TradingDay = tick.TradingDay
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
        """1分钟K线更新"""
        # 尚未创建对象
        if not self.xminBar:
            self.xminBar = VtBarData()

            self.xminBar.vtSymbol = bar.vtSymbol
            self.xminBar.symbol = bar.symbol
            self.xminBar.exchange = bar.exchange

            self.xminBar.open = bar.open
            self.xminBar.high = bar.high
            self.xminBar.low = bar.low

            self.xminBar.datetime = bar.datetime
        # 累加老K线
        else:
            self.xminBar.high = max(self.xminBar.high, bar.high)
            self.xminBar.low = min(self.xminBar.low, bar.low)

        # 通用部分
        self.xminBar.close = bar.close

        self.xminBar.openInterest = bar.openInterest
        self.xminBar.volume += int(bar.volume)


        inday_mins = (6, 7, 8, 9)
        if self.xmin in inday_mins:   ##非整除
            #日内异形bar另外判断
            inday_mins = bar.datetime.hour*60+bar.datetime.minute
            if not (inday_mins +1) % self.xmin :

                self.xminBar.datetime = self.xminBar.datetime.replace(second=0, microsecond=0)  # 将秒和微秒设为0

                self.xminBar.date = self.xminBar.datetime.strftime('%Y%m%d')
                self.xminBar.time = self.xminBar.datetime.strftime('%H:%M:%S.%f')

                # 推送
                self.onXminBar(self.xminBar)

                # 清空老K线缓存对象
                self.xminBar = None
        else:

            #上午10点15休盘15分钟要生成30min的bar
            ten_rest_30min = (self.xmin == 30) and (bar.datetime.hour == 10 and bar.datetime.minute == 14)

            # X分钟已经走完
            if not (bar.datetime.minute +1) % self.xmin  or ten_rest_30min:   # 可以用X整除
                # 生成上一X分钟K线的时间戳
                min_tmp = self.xminBar.datetime.minute
                min_tmp = (int(min_tmp/self.xmin))*self.xmin

                self.xminBar.datetime = self.xminBar.datetime.replace(minute=min_tmp , second=0, microsecond=0)  # 将秒和微秒设为0
                #self.xminBar.datetime = self.xminBar.datetime.replace( second=0, microsecond=0)  # 将秒和微秒设为0
                self.xminBar.date = self.xminBar.datetime.strftime('%Y%m%d')
                self.xminBar.time = self.xminBar.datetime.strftime('%H:%M:%S.%f')

                # 推送
                self.onXminBar(self.xminBar)

                # 清空老K线缓存对象
                self.xminBar = None



    #------------------------------------------------
    #累计自然时间的分钟数,传入参数是bar的datetime的time
    #用于计算6,7,8,9分钟的bar
    def grandMinutes(self,bar_datetime):
        bar_time = time(bar_datetime.hour, bar_datetime.minute)
        bar_hour = bar_time.hour
        grand_mins = 0
        if bar_hour == 9:
            #从9点开始计算
            grand_mins = bar_time.minute
        elif bar_hour == 10 and bar_time <= time(10, 15):
            grand_mins = 60 + bar_time.minute
        elif bar_hour == 10 and bar_time >= time(10, 30):
            #因10:15到10:30休市要减掉15分钟
            grand_mins = 45 + bar_time.minute
        elif bar_hour == 11 or bar_hour == 13:
            #中午不间断
            grand_mins = 105 + bar_time.minute
        elif bar_hour == 14:
            grand_mins = 165 + bar_time.minute
        elif bar_hour == 21:
            #夜盘开盘重新开始累计
            grand_mins = bar_time.minute
        elif bar_hour == 22:
            grand_mins = 60 + bar_time.minute
        elif bar_hour == 23:
            grand_mins = 120 + bar_time.minute
        elif 0 <= bar_hour <= 2:
            #0-2点的夜盘继续累计
            grand_mins = 180 + bar_hour * 60 + bar_time.minute

        return grand_mins
