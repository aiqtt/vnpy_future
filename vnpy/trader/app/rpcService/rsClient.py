# encoding: UTF-8

import copy

from vnpy.rpc import RpcClient
from pymongo import MongoClient, ASCENDING
from pymongo.errors import ConnectionFailure
from vnpy.trader.vtGlobal import globalSetting
from vnpy.trader.language import text
from vnpy.event import Event
from vnpy.trader.vtObject import  VtLogData
from vnpy.trader.vtEvent import EVENT_LOG

########################################################################
class ObjectProxy(object):
    """对象代理"""

    #----------------------------------------------------------------------
    def __init__(self, nameList, client):
        """Constructor"""
        self.nameList = nameList    # 属性名称关系列表
        self.client = client        # RPC客户端
        
    #----------------------------------------------------------------------
    def __getattr__(self, name):
        """获取某个不存在的属性"""
        # 生成属性层级列表
        newNameList = copy.copy(self.nameList)
        newNameList.append(name)
        
        # 创建代理对象
        proxy = ObjectProxy(newNameList, self.client)
        
        # 缓存代理对象
        self.__dict__[name] = proxy
        
        # 返回
        return proxy
        
    #----------------------------------------------------------------------
    def __call__(self, *args, **kwargs):
        """被当做函数调用时"""
        d = {}
        d['nameList'] = self.nameList
        d['args'] = args
        d['kwargs'] = kwargs
        return self.client.call(d)



    

########################################################################
class RsClient(RpcClient):
    """RPC服务客户端"""

    #----------------------------------------------------------------------
    def __init__(self, reqAddress, subAddress):
        """Constructor"""
        super(RsClient, self).__init__(reqAddress, subAddress)
        
        self.eventEngine = None
        self.mainEngine = None
        
    #----------------------------------------------------------------------
    def callback(self, topic, data):
        """事件推送回调函数"""
        self.eventEngine.put(data)      # 直接放入事件引擎中
    
    #----------------------------------------------------------------------
    def init(self, eventEngine, mainEngine):
        """初始化"""
        self.eventEngine = eventEngine  # 绑定事件引擎对象
        self.mainEngine = mainEngine
        
        self.usePickle()                # 使用cPickle序列化
        self.subscribeTopic('')         # 订阅全部主题推送
        self.start()                    # 启动


########################################################################
class MainEngineProxy(object):
    """主引擎代理"""

    #----------------------------------------------------------------------
    def __init__(self, eventEngine):
        """Constructor"""
        self.eventEngine = eventEngine
        self.eventEngine.start(timer=False)     # 客户端不启动定时器
        
        self.client = None

        # MongoDB数据库相关
        self.dbClient = None    # MongoDB客户端对象   数据库数据还是从数据库读取，从服务器读取会影响服务器


    #----------------------------------------------------------------------
    def dbConnect(self):
        """连接MongoDB数据库"""
        if not self.dbClient:
            # 读取MongoDB的设置
            try:
                # 设置MongoDB操作的超时时间为0.5秒
                if (globalSetting['mongoHost'] == '127.0.0.1' or globalSetting['mongoHost'] == 'localhost'):
                    # 如果是本地连接，不用用户的验证
                    self.dbClient = MongoClient(globalSetting['mongoHost'], globalSetting['mongoPort'], connectTimeoutMS=500)
                else:
                    self.dbClient = MongoClient("mongodb://%s:%s@%s" % (globalSetting['mongoUser'], globalSetting['mongoPassword'], globalSetting['mongoHost']))

                # 调用server_info查询服务器状态，防止服务器异常并未连接成功
                self.dbClient.server_info()

                self.writeLog(text.DATABASE_CONNECTING_COMPLETED)

                # 如果启动日志记录，则注册日志事件监听函数
                if globalSetting['mongoLogging']:
                    self.eventEngine.register(EVENT_LOG, self.dbLogging)

            except ConnectionFailure:
                self.writeLog(text.DATABASE_CONNECTING_FAILED)

    #----------------------------------------------------------------------
    def init(self, reqAddress, subAddress):
        """初始化"""
        self.client = RsClient(reqAddress, subAddress)
        self.client.init(self.eventEngine,self)

    #----------------------------------------------------------------------
    def __getattr__(self, name):
        """获取未知属性"""
        # 生成属性名称层级列表
        nameList = [name]
        
        # 生成属性代理对象
        proxy = ObjectProxy(nameList, self.client)
        
        # 缓存属性代理对象，使得后续调用无需新建
        self.__dict__[name] = proxy
        
        # 返回属性代理
        return proxy
    
    #----------------------------------------------------------------------
    def getApp(self, name):
        """获取应用引擎对象"""
        return self.__getattr__(name)


    def exit(self):
        self.eventEngine.stop()
        self.client.stop()


    ##数据查询从数据库直接查询，走zmq 数据量比较大,对服务器压力大
    #----------------------------------------------------------------------
    def dbQuery(self, dbName, collectionName, d, sortKey='', sortDirection=ASCENDING):
        """从MongoDB中读取数据，d是查询要求，返回的是数据库查询的指针"""
        self.dbConnect()

        if self.dbClient:
            db = self.dbClient[dbName]
            collection = db[collectionName]

            if sortKey:
                cursor = collection.find(d).sort(sortKey, sortDirection)    # 对查询出来的数据进行排序
            else:
                cursor = collection.find(d)

            if cursor:
                return list(cursor)
            else:
                return []
        else:
            self.writeLog(text.DATA_QUERY_FAILED)
            return []

    #----------------------------------------------------------------------
    def writeLog(self, content):
        """快速发出日志事件"""
        log = VtLogData()
        log.logContent = content
        log.gatewayName = 'MAIN_ENGINE'
        event = Event(type_=EVENT_LOG)
        event.dict_['data'] = log
        self.eventEngine.put(event)