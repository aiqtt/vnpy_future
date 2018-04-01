# encoding: UTF-8

"""
通过VT_setting.json加载全局配置
"""

import os
import traceback
import json
from vtFunction import getJsonPath


settingFileName = "VT_setting.json"
settingFilePath = getJsonPath(settingFileName, __file__)

globalSetting = {}      # 全局配置字典

try:
    f = file(settingFilePath)
    globalSetting = json.load(f)
except:
    traceback.print_exc()


SymbolFileName = "Symbol_setting.json"
SymbolFilePath = getJsonPath(SymbolFileName, __file__)

globalSymbolSetting = {}      # 全局配置字典

try:
    f1 = file(SymbolFilePath)
    globalSymbolSetting = json.load(f1)
except:
    traceback.print_exc()

##2018假期 的前一天
globalHolidaySetting = ["20180214",  ##春节
                        "20180404",  ##清明
                        "20180427",  ##五一
                        "20180615", ##端午
                        "20180921",  #中秋
                        "20180928"   ]   ##国庆
