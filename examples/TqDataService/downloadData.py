# encoding: UTF-8

"""
立即下载数据到数据库中，用于手动执行更新操作。
"""

from dataService import *


if __name__ == '__main__':
    #downloadAllMinuteBar(1000)
    downloadAllBar(1000, MINUTE_60_DB_NAME)  ##DAY_DB_NAME  MINUTE_60_DB_NAME


