# encoding: UTF-8

from __future__ import print_function
__author__ = 'CHENXY'

# C++和python类型的映射字典
type_dict = {
    'int': 'int',
    'char': 'char',
    'double': 'float',
    'short': 'int',
    'string': 'string'
}


def process_line(line):
    """处理每行"""
    if '///' in line:           # 注释
        py_line = process_comment(line)
    elif 'typedef' in line:     # 类型申明
        py_line = process_typedef(line)
    elif '#define' in line:     # 定义常量
        py_line = process_define(line)
    elif line == '\n':          # 空行
        py_line = line
    else:
        py_line = ''

    return py_line


def process_comment(line):
    """处理注释"""
    # if line[3] == '/':
    #     py_line = ''
    # else:
    #     py_line = '#' + line[3:]
    py_line = '#' + line[3:]
    return py_line


def process_typedef(line):
    """处理类型申明"""
    content = line.split(' ')
    type_ = type_dict[content[1]]

    if type_ == 'char' and '[' in line:
        type_ = 'string'

    keyword = content[2]
    if '[' in keyword:
        i = keyword.index('[')
        keyword = keyword[:i]
    else:
        keyword = keyword.replace(';\n', '')  # 删除行末分号

    py_line = 'typedefDict["%s"] = "%s"\n' % (keyword, type_)

    return py_line


def process_define(line):
    """处理定义常量"""
    content = line.split(' ')
    constant = content[1]

    if len(content)>2:
        value = content[-1]
        py_line = 'defineDict["%s"] = %s' % (constant, value)
    else:
        py_line = ''

    return py_line


def main():
    """主函数"""
    try:
        fcpp = open('ThostFtdcUserApiDataType.h','r')
        fpy = open('ctp_data_type.py', 'w')

        fpy.write('# encoding: UTF-8\n')
        fpy.write('\n')
        fpy.write('defineDict = {}\n')
        fpy.write('typedefDict = {}\n')
        fpy.write('\n')

        for line in fcpp:
            py_line = process_line(line)
            if py_line:
                fpy.write(py_line.decode('gbk').encode('utf-8'))

        fcpp.close()
        fpy.close()

        print(u'data_type.py生成过程完成')
    except:
        print(u'data_type.py生成过程出错')


if __name__ == '__main__':
    main()

