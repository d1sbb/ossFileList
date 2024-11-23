# -*- coding: utf-8 -*-
# @Author  : disbb.com
# @Time    : 2024/11/18 00:27

import csv
import time
import warnings
import re
import argparse
import xml.etree.ElementTree as ET
import requests
import urllib3
import pandas as pd  # 新增
from pathlib import Path  # 用于检查文件路径


# 忽略InsecureRequestWarning警告
warnings.filterwarnings("ignore", category=urllib3.exceptions.InsecureRequestWarning)

# 用来统计所有key的列表
totoal_keys = []

# 获取存储桶页面默认显示条数max-keys,默认最大不超过1000
def get_info(url):
    response = requests.get(url, verify=False)
    # 解析XML内容
    xml_content = response.content
    # 解析XML
    root = ET.fromstring(xml_content)
    maxkey = root.findtext(f".//MaxKeys")
    nextmarker = root.find(f".//NextMarker")
    xpath_expr = ".//Contents"
    # 检查是否存在命名空间，存在命名空间的索引写法需要改变
    has_namespace = root.tag.startswith("{")
    if has_namespace:
        # 获取命名空间
        namespace = root.tag.split('}')[0].strip('{')
        xpath_expr = f".//{{{namespace}}}Contents"
        maxkey = root.findtext(f".//{{{namespace}}}MaxKeys")
        nextmarker = root.find(f".//{{{namespace}}}NextMarker")
    # 获取所有子标签的名称
    child_tags = set()
    for contents_element in root.findall(xpath_expr):
        for child_element in contents_element:
            if has_namespace:
                child_tags.add(child_element.tag.replace(f"{{{namespace}}}", ""))
            else:
                child_tags.add(child_element.tag)
    # 创建csv文件写入表头也就是各列名称
    filename = write_csv_header(child_tags, url)
    # 返回PageSize、下一页索引、创建的CSV文件名称、以及列名集合
    return maxkey, nextmarker, filename, child_tags


def getdata(baseurl, max_keys, csv_filename, child_tags, marker='', page=0):
    if int(max_keys) < 1000:
        max_keys = 1000
    baseurl = baseurl
    url = baseurl + f'?max-keys={max_keys}&marker={marker}'
    #print(f"[+] {url}")
    response = requests.get(url, verify=False)
    xml_content = response.content.decode("utf-8")
    # 使用正则表达式，去除不在 GBK 范围内的字符 㤲
    cleaned_xml = re.sub(r'[^\x00-\x7F\u4e00-\u9fa5]+', '', re.sub(r'&#\d+;', '', xml_content))
    root = ET.fromstring(cleaned_xml)
    # 检查是否存在命名空间
    namespace = ''
    xpath_expr = ".//Contents"
    nextmarker = root.findtext(f".//NextMarker")
    has_namespace = root.tag.startswith("{")
    if has_namespace:
        # 获取命名空间
        namespace = root.tag.split('}')[0].strip('{')
        xpath_expr = f".//{{{namespace}}}Contents"
        nextmarker = root.findtext(f".//{{{namespace}}}NextMarker")
    datas = root.findall(xpath_expr)
    # 写入数据
    nums, is_repeate, repeate_nums, total_nums = write_csv_content(csv_filename, datas, has_namespace, namespace,
                                                                   child_tags, baseurl)
    page += 1
    print(f"[+] 第{page}页写入{nums}条数据,共计发现{total_nums}个文件")
    # 是否存在nextmarker存在则说明还有下一页需要迭代进行遍历，不存在则说明以及遍历完成退出
    if nextmarker is None or is_repeate == 1:
        print(f"[+] 数据结果已写入文件：{csv_filename}")
        output_filename = split_csv_to_excel(csv_filename)  # 新增：处理生成的 CSV 文件
        print(f"[+] 数据分类已写入文件：{output_filename}")
        return
    getdata(baseurl, max_keys, csv_filename, child_tags, nextmarker, page)


def write_csv_header(child_tags, url):
    # 获取当前时间戳
    timestamp = int(time.time())
    # 将时间戳转换为字符串
    timestamp_str = str(timestamp)
    # 创建CSV文件并写入数据
    url = re.sub(r'^http://', '', url)
    url = re.sub(r":", "_", url )
    csv_filename = f'{url}_{timestamp_str}.csv'
    with open(csv_filename, 'w', newline='') as csv_file:
        # 写入表头，另外增加完整的url和文件类型列
        writer = csv.writer(csv_file)
        list_tags = list(child_tags)
        list_tags.append("url")
        list_tags.append("filetype")
        writer.writerow(list_tags)
        return csv_filename


def write_csv_content(csv_filename, datas, has_namespace, namespace, child_tags, baseUrl):
    # 提取数据并写入CSV文件
    with open(csv_filename, 'a', newline='') as csv_file:
        nums = 0
        repeate_nums = 0
        is_repeate = 0
        # 写入数据
        for contents_element in datas:
            if has_namespace:
                row = [contents_element.findtext(f"{{{namespace}}}{tag}") for tag in child_tags]
                key = contents_element.findtext(f"{{{namespace}}}Key")
            else:
                row = [contents_element.findtext(tag) for tag in child_tags]
                key = contents_element.findtext(f"Key")
            if str(key) not in totoal_keys:
                nums += 1
                totoal_keys.append(key)
                url = str(baseUrl) + str(key)
                head, dot, file_extension = str(key).rpartition(".")
                if dot and re.match(r"^[a-zA-Z0-9]+$", file_extension):
                    pass
                else:
                    # 否则，文件后缀名不存在
                    file_extension = "unknown"
                row.append(url)
                row.append(file_extension)
                writer = csv.writer(csv_file)
                writer.writerow(row)
            else:
                repeate_nums += 1
        if repeate_nums > 2:
            is_repeate = 1

        return nums, is_repeate, repeate_nums, len(totoal_keys)


def split_csv_to_excel(csv_filename):
    """将CSV数据按filetype分组并保存为Excel工作表"""
    try:
        # 检查文件是否存在
        if not Path(csv_filename).is_file():
            print(f"[-] 文件 {csv_filename} 不存在")
            return

        # 读取CSV文件
        df = pd.read_csv(csv_filename, encoding='gbk')  # 尝试 GBK 编码

        # 检查是否存在filetype列
        if "filetype" not in df.columns:
            print(f"[-] 文件 {csv_filename} 中不存在 filetype 列")
            return

        # 创建一个新的Excel文件
        output_filename = csv_filename.replace(".csv", "_Type.xlsx")
        with pd.ExcelWriter(output_filename, engine='openpyxl') as writer:
            for filetype, group in df.groupby("filetype"):
                # 将每种filetype的内容写入单独的工作表
                # 替换非法字符
                sheet_name = re.sub(r'[\/\\\?\*\[\]\:]', '_', filetype) if filetype else "unknown" # 如果filetype为空，用unknown命名
                sheet_name = sheet_name[:31]  # Excel工作表名最多31字符
                group.to_excel(writer, index=False, sheet_name=sheet_name)
        return output_filename
    except Exception as e:
        print(f"[-] 处理CSV文件时发生错误：{e}")


def url_xml(url, baseUrl):
    if baseUrl == '':
        baseUrl = url
    if not baseUrl.endswith('/'):
        baseUrl += '/'
    try:
        maxkey, nextmarker, csv_filename, child_tags = get_info(url)
        if len(child_tags) != 0:
            print("[+] 解析 XML 数据成功")
            if maxkey == None:
                maxkey = 1000
            print(f"[o] 该存储桶默认每页显示 {maxkey} 条数据")
            if nextmarker == None:
                print("[-] 该存储桶不支持 Web 翻页遍历")
            else:
                print("[+] 该存储桶支持遍历, 正在获取文件及数量")
            getdata(baseUrl, max_keys=maxkey, child_tags=child_tags, csv_filename=csv_filename)
        else:
            print("[-] 该存储桶不支持遍历, 或检查 URL 是否有误")
    except Exception as e:
        print(f"[-] 处理 URL 时发生错误：{e}")


if __name__ == '__main__':
    # 发送HTTP请求获取响应
    #url = input("[*] 请输入存储桶遍历url：").strip()
    try:
        parser = argparse.ArgumentParser()
        parser.add_argument('-u', dest='oss', help='python3 ossFileList.py -u [Bucketurl]')
        parser.add_argument('-f', dest='file', help='python3 ossFileList.py -f [filename]')
        args = parser.parse_args()
        baseUrl = input("[*] 请输入存储桶根路径(不输入则和上述 URL 保持一致)：").strip()
        if args.oss:
            url = args.oss
            url_xml(url, baseUrl)
        elif args.file:
            file_path = args.file
            try:
                # 检查文件是否存在
                if not Path(file_path).is_file():
                    print(f"[-] 文件 {file_path} 不存在，请检查路径")
                else:
                    print(f"[+] 正在从文件 {file_path} 中读取 URL 列表")
                    with open(file_path, 'r', encoding='utf-8') as f:
                        for line in f:
                            url = line.strip()
                            if url:
                                print(f"[+] ----------------------------------------------------------------------\n[*] 开始解析 URL：{url}")
                                url_xml(url, baseUrl)
                                totoal_keys = [] # 统计清零
            except Exception as e:
                print(f"[-] 无法读取文件：{e}")
    except KeyboardInterrupt:
        print("Bye~ disbb.com")