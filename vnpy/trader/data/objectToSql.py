# encoding: UTF-8
import sys
reload(sys)
sys.setdefaultencoding('utf8')




from datetime import datetime

SQL_TABLENAME_STOP_ORDER = "t_stop_order"    ##停止单
SQL_TABLENAME_LOG  = "t_log"                  ##log
SQL_TABLENAME_POSITION = "t_position"        ##position
SQL_TABLENAME_TRADER = "t_trader_order"
SQL_TABLENAME_ACCOUNT = "t_account_detail"


def getInsertSql(tableName,obj,accountId):
    timenow = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    if tableName == SQL_TABLENAME_STOP_ORDER:
        ##stop order
        sql = 'insert into t_stop_order(accountId,direction,price,symbol,status, volume,offset,strategyName,stopDirection,orderType,createTime,updateTime) ' \
              "values('%s','%s',%f,'%s','%s','%s','%s','%s','%s','%s','%s','%s')"\
              %(accountId,obj.direction,obj.price,obj.vtSymbol,obj.status,obj.volume,obj.offset,obj.strategyName,obj.stopDirection,obj.orderType,timenow,timenow)

        return sql

    if tableName == SQL_TABLENAME_LOG:

        sql = 'insert into t_log(accountId,logLevel,logContent,logTime,createTime) ' \
              "values('%s','%s','%s','%s','%s')"\
              %(accountId,obj.logLevel,obj.logContent,obj.logTime,timenow)

        return sql
    if tableName == SQL_TABLENAME_POSITION:

        sql = 'insert into t_position(accountId,symbol,strategyName,pos,createTime,updateTime) ' \
              "values('%s','%s','%s','%s','%s','%s')"\
              %(accountId,obj.symbol,obj.strategyName,obj.pos,timenow,timenow)

        return sql

    if tableName == SQL_TABLENAME_ACCOUNT:

        sql = 'insert into t_account_detail(accountId,preBalance,balance,available,commission,margin,createTime) ' \
              "values('%s','%s','%s','%s','%s','%s','%s')"\
              %(accountId,obj.preBalance,obj.balance,obj.available,obj.commission,obj.margin,timenow)

        return sql


    if tableName == SQL_TABLENAME_TRADER:
        sql = 'insert into t_trader_order(accountId,symbol,strategyName,orderID,orderUuid ,direction,offset,orderVolume, orderPrice, tradeVolume,tradePrice,   createTime,updateTime) ' \
              "values('%s','%s','%s','%s','%s','%s','%s','%s','%s','%s','%s','%s','%s')"\
              %(accountId,obj.symbol,obj.strategyName,obj.orderID,obj.orderUuid, obj.direction, obj.offset,obj.orderVolume,obj.orderPrice,obj.tradeVolume,obj.tradePrice,timenow,timenow)

        return sql


def getDeleteSql(tableName,obj,accountId):
    if tableName == SQL_TABLENAME_STOP_ORDER:
        ##stop order
        sql = "delete from t_stop_order where accountId ='%s' and symbol='%s' and direction='%s' "\
              %(accountId,obj.vtSymbol, obj.direction)

        if obj.strategyName != "":
            sql = "delete from t_stop_order where accountId ='%s' and symbol='%s' and direction='%s' and strategyName='%s' "\
              %(accountId,obj.vtSymbol, obj.direction,obj.strategyName)

        return sql

def getSelectSql(tableName,obj,accountId, ret_type):
    if tableName == SQL_TABLENAME_STOP_ORDER:
        if ret_type == "all":
            sql = "select * from t_stop_order where accountId ='%s'  "\
                %(accountId)

            return  sql
    if tableName == SQL_TABLENAME_LOG:
         if ret_type == "all":
            sql = "select * from t_log where accountId ='%s'  "\
                %(accountId)

            return  sql
    if tableName == SQL_TABLENAME_POSITION:
        if ret_type == "all":
            sql = "select * from t_position where accountId ='%s'  "\
                %(accountId)

            return  sql
        if ret_type == "one":
            sql = "select * from t_position where accountId ='%s' and symbol='%s' and strategyName='%s'  "\
                %(accountId,obj.symbol, obj.strategyName)

            return  sql

    if tableName == SQL_TABLENAME_TRADER:
        if ret_type == "all":
            sql = "select * from t_trader_order where accountId ='%s'  "\
                %(accountId)

            return  sql
        if ret_type == "one":
            sql = "select * from t_trader_order where accountId ='%s' and symbol='%s' and strategyName='%s' and offset='%s' ORDER BY createTime  desc limit 0,1 "\
                %(accountId,obj.symbol, obj.strategyName,obj.offset)

            return  sql


def getUpdateSql(tableName,obj,accountId):
    if tableName == SQL_TABLENAME_POSITION:
        sql = "UPDATE t_position set pos='%s'  where accountId ='%s' and symbol='%s' and strategyName='%s' "\
              %(obj.pos, accountId, obj.symbol, obj.strategyName)

        return sql

    if tableName == SQL_TABLENAME_TRADER:
        sql = "UPDATE t_trader_order set tradeVolume='%s',tradePrice='%s'  where accountId ='%s' and symbol='%s' and strategyName='%s' and orderUuid='%s' "\
              %(obj.tradeVolume,obj.tradePrice, accountId, obj.symbol, obj.strategyName,obj.orderUuid)

        return sql


if __name__ == '__main__':
    getInsertSql(SQL_TABLENAME_STOP_ORDER,None,"")
