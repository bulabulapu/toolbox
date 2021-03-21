# encoding:utf-8
import json
import shutil
import os
import platform
from pathlib import Path

git_enable = False  # todo 实现gitignore文件过滤
log_enable = False
delete_fail_list = []
copy_fail_list = []


def read_config():
    """
    读取配置文件
    :return: json数组
    """
    with open('sync_config.json', 'r') as config_file:
        content = config_file.read()
        try:
            config = json.loads(content)
        except json.decoder.JSONDecodeError:
            print('配置文件json格式错误')
            return []
        return config


def delete(path):
    """
    删除文件或者文件夹
    :param path: 被删除的文件或者文件夹
    :return:
    """
    try:
        if log_enable:
            print('删除 {}'.format(path))
        if path.is_file():
            path.unlink()
        else:
            shutil.rmtree(path)
    except PermissionError as e:
        if platform.system().lower() == 'windows':  # win下权限错误
            os.system('del "{}" /F'.format(str(path)))
        else:
            print('错误 {}'.format(e))
            print()
            delete_fail_list.append(str(path))


def copy(source, target):
    """
    复制文件或文件夹
    :param source: 源文件夹
    :param target: 目标文件夹
    :return:
    """
    try:
        if log_enable:
            print('复制 {}'.format(source))
        if source.is_file():
            shutil.copy2(source, target)
        else:
            target = str(target) + '/' + source.name
            shutil.copytree(source, target)
    except PermissionError as e:  # win下权限错误
        print('错误 {}'.format(e))
        print()
        copy_fail_list.append(str(source))


def sync(source, target):
    """
    进行文件夹同步
    :param source: 源文件夹
    :param target: 目标文件夹
    :return:
    """
    source_list = get_child_name_list(source)
    target_list = get_child_name_list(target)
    copy_list = get_difference_set(source_list, target_list)
    delete_list = get_difference_set(target_list, source_list)
    intersection_list = get_intersection(source_list, target_list)
    for i in intersection_list:  # 筛选需要更新的文件或文件夹
        source_temp = Path(str(source) + '/' + i)
        target_temp = Path(str(target) + '/' + i)
        if source_temp.is_file() and target_temp.is_file() and \
                source_temp.stat().st_mtime_ns > target_temp.stat().st_mtime_ns:  # 以更改时间进行判断需要更新的文件,同名文件夹不更改
            delete_list.append(i)
            copy_list.append(i)
        if (source_temp.is_file() and target_temp.is_dir()) or (
                source_temp.is_dir() and target_temp.is_file()):  # 检测文件文件夹是否存在相同的名称
            if i not in delete_list:  # 且未被添加
                delete_list.append(i)
                copy_list.append(i)
    for i in delete_list:
        delete(Path(str(target) + '/' + i))
    for i in copy_list:
        copy(Path(str(source) + '/' + i), target)
    same_list = get_difference_set(intersection_list, copy_list)  # 未变化的文件或文件夹
    for i in same_list:
        source_temp = Path(str(source) + '/' + i)
        target_temp = Path(str(target) + '/' + i)
        if source_temp.is_dir():
            sync(source_temp, target_temp)


def get_child_name_list(folder):
    """
    获取文件夹下的子文件和文件夹名称
    :param folder: 文件夹
    :return: 名称List
    """
    result = []
    for i in folder.iterdir():
        result.append(i.name)
    return result


def get_intersection(set_a, set_b):
    """
    获取交集
    :param set_a: a集合List
    :param set_b: b集合List
    :return: 集合List
    """
    result = []
    for a in set_a:
        if a in set_b:
            result.append(a)
    return result


def get_difference_set(set_a, set_b):
    """
    获取集合ab的差集
    :param set_a: a集合List
    :param set_b: b集合List
    :return: 集合List
    """
    result = []
    for a in set_a:
        if a not in set_b:
            result.append(a)
    return result


def check_conf(conf_json):
    """
    检测配置是否正确,同时写入全局变量git_enable,show_log
    :param conf_json: 配置文件json
    :return:
    """
    try:
        name = conf_json['name'].strip()
        if len(name) == 0:
            print_conf_error(conf_json, 'name为空')
            return False
    except KeyError:
        print_conf_error(conf_json, '变量name不存在')
        return False
    try:
        source = conf_json['source']
        if not Path(source).exists():
            print_conf_error(conf_json, '路径不存在: {}'.format(source))
            return False
    except KeyError:
        print_conf_error(conf_json, '变量source不存在')
        return False
    try:
        target = conf_json['target']
        if not Path(target).exists():
            print_conf_error(conf_json, '路径不存在: {}'.format(target))
            return False
    except KeyError:
        print_conf_error(conf_json, '变量target不存在')
        return False
    try:
        global git_enable
        git_enable = conf_json['gitEnable']
    except KeyError:
        git_enable = False
    try:
        global log_enable
        log_enable = conf_json['logEnable']
    except KeyError:
        log_enable = False
    return True


def print_conf_error(conf_json, info):
    """
    打印配置错误信息
    :param conf_json: 配置文件json
    :param info: 错误信息
    :return:
    """
    print('配置错误: {}'.format(info))
    print('配置错误: {}'.format(conf_json))


if __name__ == '__main__':
    try:
        conf = read_config()
        for item in conf:
            if check_conf(item):
                print('执行任务 {}'.format(item['name']))
                sync(Path(item['source']), Path(item['target']))
                print()
    except Exception as err:
        print(err)
    if len(delete_fail_list) != 0:
        for f in delete_fail_list:
            print('删除失败 {}'.format(f))
        print()
    if len(copy_fail_list) != 0:
        for f in copy_fail_list:
            print('同步失败 {}'.format(f))
        print()
    print('结束,按任意键关闭')
    input()
