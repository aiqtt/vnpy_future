# encoding: UTF-8
import sys
reload(sys)
sys.setdefaultencoding('utf8')

import MySQLdb
import time, re
from Queue import Queue, Empty
from threading import Thread
from time import sleep
from .objectToSql import *


SQL_TABLENAME_STOP_ORDER = "t_stop_order"    ##停止单
SQL_TABLENAME_LOG  = "t_log"                  ##log
SQL_TABLENAME_POSITION = "t_position"        ##position
SQL_TABLENAME_TRADER = "t_trader_order"
SQL_TABLENAME_ACCOUNT = "t_account_detail"


class mysqlManager:

    TYPE_INSERT = "insert"
    TYPE_DELETE = "delete"
    TYPE_UPDATE = "update"


    def __init__(self,dbconfig):
        self.accountId = dbconfig["accountId"]
        self.db = baseMysql(dbconfig)
        self.__queue = Queue()
        self.__thread = Thread(target = self.__run)    ##io操作另起线程跑
        self.__active = True
        self.__thread.start()


    #----------------------------------------------------------------------
    def stop(self):
        """停止引擎"""
        # 将引擎设为停止
        self.__active = False

        # 等待事件处理线程退出
        self.__thread.join()

    #----------------------------------------------------------------------
    def __run(self):
        """引擎运行"""
        while self.__active == True:
            try:
                event = self.__queue.get(block = True, timeout = 1)  # 获取事件的阻塞时间设为1秒
                self.__process(event)
            except Empty:
                pass

        #----------------------------------------------------------------------
    def __process(self, reqData):
        tableName = reqData.table
        type = reqData.type
        if type == self.TYPE_INSERT:
            self.dbInsert_(tableName,reqData.dict_["data"])

        if type == self.TYPE_DELETE:
            self.dbDelete_(tableName,reqData.dict_["data"])

        if type == self.TYPE_UPDATE:
            self.dbUpdate_(tableName,reqData.dict_["data"])



    def putReq(self,req):
         self.__queue._put(req)

    #----------------------------------------------------------------------
    def dbInsert(self, tableName, d):
        """向MongoDB中插入数据，d是具体数据"""
        req = DatabaseReq(tableName,self.TYPE_INSERT)
        req.dict_['data'] = d

        self.putReq(req)

    def dbInsert_(self, tableName, d):
        sql = getInsertSql(tableName,d,self.accountId)
        self.db.dml(sql)

    def dbDelete(self, tableName,d):
        req = DatabaseReq(tableName,self.TYPE_DELETE)
        req.dict_['data'] = d

        self.putReq(req)

    def dbDelete_(self,tableName,d):
        sql = getDeleteSql(tableName,d,self.accountId)
        self.db.dml(sql)

    def dbUpdate(self,tableName,d):
        req = DatabaseReq(tableName,self.TYPE_UPDATE)
        req.dict_['data'] = d

        self.putReq(req)

    def dbUpdate_(self,tableName,d):
        if tableName == SQL_TABLENAME_POSITION:
            ##先查询有没有，没有则插入
            ret_one = self.dbSelect(tableName,d,"one")
            if not ret_one:
                self.dbInsert(tableName,d)
            else:
                sql = getUpdateSql(tableName,d,self.accountId)
                self.db.dml(sql)
        else:
            sql = getUpdateSql(tableName,d,self.accountId)
            self.db.dml(sql)

    ##select不做异步，因为一般都是启动加载
    def dbSelect(self,tableName,d,ret_type):

        sql =getSelectSql(tableName,d,self.accountId,ret_type)
        return self.db.query(sql,ret_type)









class baseMysql:
    """Lightweight python class connects to MySQL. """

    _dbconfig = None
    _cursor = None
    _connect = None
    _error_code = '' # error_code from MySQLdb

    TIMEOUT_DEADLINE = 30 # quit connect if beyond 30S
    TIMEOUT_THREAD = 10 # threadhold of one connect
    TIMEOUT_TOTAL = 0 # total time the connects have waste

    def __init__(self, dbconfig):

        try:
            self._dbconfig = dbconfig
            self.dbconfig_test(dbconfig)
            self._connect = MySQLdb.connect(
                host=self._dbconfig['host'],
                port=self._dbconfig['port'],
                user=self._dbconfig['user'],
                passwd=self._dbconfig['passwd'],
                db=self._dbconfig['db'],
                charset=self._dbconfig['charset'],
                connect_timeout=self.TIMEOUT_THREAD)
        except MySQLdb.Error, e:
            self._error_code = e.args[0]
            error_msg = "%s --- %s" % (time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time())), type(e).__name__), e.args[0], e.args[1]
            print error_msg

            # reconnect if not reach TIMEOUT_DEADLINE.
            if self.TIMEOUT_TOTAL < self.TIMEOUT_DEADLINE:
                interval = 0
                self.TIMEOUT_TOTAL += (interval + self.TIMEOUT_THREAD)
                time.sleep(interval)
                return self.__init__(dbconfig)
            raise Exception(error_msg)

        self._cursor = self._connect.cursor(MySQLdb.cursors.DictCursor)

    def dbconfig_test(self, dbconfig):
        flag = True
        if type(dbconfig) is not dict:
            print 'dbconfig is not dict'
            flag = False
        else:
            for key in ['host','port','user','passwd','db']:
                if not dbconfig.has_key(key):
                    print "dbconfig error: do not have %s" % key
                    flag = False
            if not dbconfig.has_key('charset'):
                self._dbconfig['charset'] = 'utf8'

        if not flag:
            raise Exception('Dbconfig Error')
        return flag

    def query(self, sql, ret_type='all'):
        try:
            self._cursor.execute("SET NAMES utf8")
            self._cursor.execute(sql)
            if ret_type == 'all':
                return self.rows2array(self._cursor.fetchall())
            elif ret_type == 'one':
                return self._cursor.fetchone()
            elif ret_type == 'count':
                return self._cursor.rowcount
        except MySQLdb.Error, e:
            self._error_code = e.args[0]
            print "Mysql execute error:",e.args[0],e.args[1]
            return False

    def dml(self, sql):
        '''update or delete or insert'''
        try:
            self._cursor.execute("SET NAMES utf8")
            self._cursor.execute(sql)
            self._connect.commit()
            type = self.dml_type(sql)
            # if primary key is auto increase, return inserted ID.
            if type == 'insert':
                return self._connect.insert_id()
            else:
                return True
        except MySQLdb.Error, e:
            self._error_code = e.args[0]
            print "Mysql execute error:",e.args[0],e.args[1]
            return False

    def dml_type(self, sql):
        re_dml = re.compile('^(?P<dml>\w+)\s+', re.I)
        m = re_dml.match(sql)
        if m:
            if m.group("dml").lower() == 'delete':
                return 'delete'
            elif m.group("dml").lower() == 'update':
                return 'update'
            elif m.group("dml").lower() == 'insert':
                return 'insert'
        print "%s --- Warning: '%s' is not dml." % (time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time())), sql)
        return False


    def rows2array(self, data):
        '''transfer tuple to array.'''
        result = []
        for da in data:
            if type(da) is not dict:
                raise Exception('Format Error: data is not a dict.')
            result.append(da)
        return result

    def __del__(self):
        '''free source.'''
        try:
            self._cursor.close()
            self._connect.close()
        except:
            pass

    def close(self):
        self.__del__()


class DatabaseReq:
    """事件对象"""

    #----------------------------------------------------------------------
    def __init__(self, table_=None,type_=None):
        """Constructor"""
        self.type = type_
        self.table = table_      # 事件类型
        self.dict_ = {}         # 字典用于保存具体的事件数据