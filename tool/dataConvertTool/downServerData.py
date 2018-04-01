# encoding: UTF-8
"""
1.从服务器上同步数据到本地
2.每天同步一次，运行时间为每天晚上，同步当日的，从前一晚上21点到本日下午15点
"""

import json
from datetime import datetime, time, timedelta
from pymongo import MongoClient, ASCENDING
from pymongo.errors import ConnectionFailure
import traceback

from vnpy.trader.app.dataRecorder.drBase import *
from vnpy.trader.vtFunction import todayDate, getJsonPath


#每天的开始和结束时间
NIGHT_START = time(20, 59)
DAY_END = time(15, 1)

class DownServerData(object):

    def __init__(self):
        self.serverClient = None
        self.localClient = None
        self.setting = {}
        self.loadFileSettinig()
        self.dbConnect()

    # --------------------------------------------------------------
    def loadFileSettinig(self):
        settingFileName = "DCT_setting.json"
        settingFilePath = getJsonPath(settingFileName, __file__)
        """读取文件路径配置"""
        try:
            with open(settingFilePath) as f:
                self.setting = json.load(f)
        except:
            traceback.print_exc()

    # ----------------------------------------------------------------------
    def dbConnect(self):
        """连接MongoDB数据库"""
        if not self.serverClient:
            # 读取MongoDB的设置
            try:
                # 设置MongoDB操作的超时时间为0.5秒
                self.serverClient = MongoClient("mongodb://%s:%s@%s" % (self.setting['server_mongodb_user'],
                                                                        self.setting['server_mongodb_password'],
                                                                        self.setting['server_mongodb_ip']))
                # 调用server_info查询服务器状态，防止服务器异常并未连接成功
                self.serverClient.server_info()
            except ConnectionFailure:
                print "server mongo connect error~"
        if not self.localClient:
            # 读取MongoDB的设置
            try:
                # 设置MongoDB操作的超时时间为0.5秒
                self.localClient = MongoClient(self.setting['local_mongodb_ip'], self.setting['local_mongodb_port'],
                                            connectTimeoutMS=500)
                # 调用server_info查询服务器状态，防止服务器异常并未连接成功
                self.localClient.server_info()
            except ConnectionFailure:
                print "local mongo connect error~"

    def downloadTickDataOneDay(self, day):
        #从服务器同步一周的tick
        if self.serverClient:
            server_db = self.serverClient[TICK_DB_NAME]
            print server_db
            local_db = self.localClient[TICK_DB_NAME]
            collections = server_db.collection_names()
            print len(collections)
            for i in range(0, len(collections)):
                print 'symbol:%s' % collections[i]
                server_col = server_db[collections[i]]
                local_col = local_db[collections[i]]
                self.processOneSymbol(day, server_col, local_col)

    def downloadOneSymbol(self, symbol, day):
        if self.serverClient:
            server_db = self.serverClient[TICK_DB_NAME]
            server_col = server_db[symbol]
            local_db = self.localClient[TICK_DB_NAME]
            local_col = local_db[symbol]
            self.processOneSymbol(day, server_col, local_col)

    def processOneSymbol(self, day, server_col, local_col):
        #处理一个symbol的下载

        timeStart = day.replace(hour=20, minute=59)
        #结束时间是第二天
        timeEnd = (day + timedelta(days=1)).replace(hour=15, minute=1)
        #print "timeStart:%s" % timeStart
        #print "timeEnd:%s" % timeEnd
        timeRun = True
        while timeRun:
            # 每次循环读取30分钟的数据，写入本地db
            timeItem = timeStart + timedelta(seconds=1800)
            #print "timeItem:%s" % timeItem
            if timeItem > timeEnd:
                timeRun = False
            ticks_count = server_col.find({"datetime": {"$gte": timeStart, "$lte": timeItem}}).count()
            #print "symbol:%s,count:%s" % (server_col, ticks_count)
            ticks = server_col.find({"datetime": {"$gte": timeStart, "$lte": timeItem}})
            for tick in ticks:
                # print tick['time']
                del tick['_id']
                local_col.insert_one(tick)
            timeStart = timeItem