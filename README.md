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
界面介绍https://zhuanlan.zhihu.com/p/36122095

* 界面加载k线，
* 鼠标滚轮缩放，键盘缩放跳转
* 十字光标 显示K线详细信息
* 缩放自适应Y轴坐标
* 回测完以后加载买卖开平仓位置有箭头标记，并且通过键盘可以在标记之间跳转
* 界面切换操作周期
* 界面右键可以切换指标


* 增加回测后基于K线图查看成交,目前已可以研究策略(examples\DailyBacktesting\showResult.py)
* K线显示可以下载我们的数据，运行tool\bar\kLineFile.py
* 复盘和监控界面


![avatar](https://github.com/aiqtt/vnpy_future/blob/master/examples/DailyBacktesting/huice.png)


### 技术交流、商务合作
qq群：538665416


