## vnpy_future

### 简介
此项目在vnpy 1.7.1基础上结合工作中实际情况做了修改。所以项目结构、环境安装等参考vnpy。


### 修改项
回测(examples\DailyBacktesting)：
* 使用成交量比较自动切换合约
* 增加模拟仓位管理
* 基于文件回测，tick回测1个月大概4分钟不到
* 增加价差回测
* 初步回测数据可以加群索要

实盘(vnpy\trader\app\dailyStrategy)：
* 修改支持多策略多品种
* 使用mysql记录实盘中仓位、成交记录等

界面：
* 增加回测后基于K线图查看成交,目前已可以研究策略(examples\DailyBacktesting\showResult.py)
* 复盘和监控界面

![avatar](https://github.com/aiqtt/vnpy_future/blob/master/examples/DailyBacktesting/huice.png)


### 技术交流、商务合作
qq群：538665416


