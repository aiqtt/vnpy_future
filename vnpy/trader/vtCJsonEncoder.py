# encoding: UTF-8

"""
继承json的JSONEncoder来处理对象转换到json时的时间转换
使用：json.dumps(datalist, cls=CJsonEncoder)
"""

import json
from datetime import datetime, date

class CJsonEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.strftime('%Y-%m-%d %H:%M:%S')
        elif isinstance(obj, date):
            return obj.strftime('%Y-%m-%d')
        else:
            return json.JSONEncoder.default(self, obj)