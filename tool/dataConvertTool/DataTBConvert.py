# encoding: UTF-8
"""
1.TB上下载数据，转换为本地bar数据格式
"""
from datetime import datetime, time, timedelta
from vnpy.trader.vtObject import *

#----------------------------------------------------------------------
def loadTBCsv(tbfileName, fileName, symbol):
    """将Multicharts导出的csv格式的历史数据插入到Mongo数据库中"""
    import csv

    start = time.time()
    print u'开始读取CSV文件%s中的数据插入到%s的%s中' %(tbfileName, fileName, symbol)

    fieldnames = ["time","open","high","low","close","volume","openInterest"]
    varFieldNames = ['vtSymbol' , 'symbol', 'exchange', 'open', 'high', 'low' , 'close' , 'date', 'time', 'datetime', 'volume', 'openInterest']

    # 读取数据和插入到数据库
    reader = csv.DictReader(file(tbfileName, 'r'),fieldnames)
    writer = csv.DictWriter(file(fileName,'ab+'),varFieldNames)
    for d in reader:
        bar = VtBarData()
        bar.vtSymbol = symbol
        bar.symbol = symbol
        bar.exchange="SHFE"
        bar.open = float(d['open'])
        bar.high = float(d['high'])
        bar.low = float(d['low'])
        bar.close = float(d['close'])
        bar.date = datetime.strptime(d['time'], '%Y/%m/%d').strftime('%Y%m%d')
        bar.time = "00:00:00"
        bar.datetime = datetime.strptime(bar.date + ' ' + bar.time, '%Y%m%d %H:%M:%S')
        bar.volume = d['volume']
        bar.openInterest=d["openInterest"]

        dicta = bar.__dict__
        del dicta["rawData"]
        del dicta["gatewayName"]
        writer.writerow(dicta)

        print bar.date, bar.time

    print u'插入完毕，耗时：%s' % (time.time()-start)

if __name__ == '__main__':
    tbfileName = "D:/data/week_tb/"
    fileName = "D:/data/week/"
    symbol = "rb0000"
    loadTBCsv(tbfileName+symbol+".txt", fileName+symbol+".txt", symbol)