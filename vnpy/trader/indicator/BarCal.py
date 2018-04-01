# encoding: UTF-8

###有关bar的一些计算  去掉最后一个bar


##是否新高，window窗口
def maxHigh(price,low,high,window):
    isHigh = True
    length_ = len(high)
    for i in range(0,length_)[::-1]:
        if length_ - i > window:
            break;

        if high[i] >= price:
            isHigh = False
            return isHigh

    return isHigh


##是否新低，window窗口
def minLow(price,low,high,window):
    isLow = True
    length_ = len(low)
    for i in range(0,length_)[::-1]:
        if length_ - i > window:
            break;

        if low[i] <= price:
            isLow = False
            return isLow

    return isLow
