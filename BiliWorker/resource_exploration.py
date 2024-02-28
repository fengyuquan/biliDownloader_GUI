import re
import json
import requests as request

from BiliWorker.base import BiliWorker


def ssADDRCheck(self, inurl):
    """
    更改/SS电影地址, 检查并处理特定的视频地址格式。

    Args:
        inurl (string): 用户输入的网址

    Returns:
        (int, string): 处理后的网址
    """
    # checking1:番剧首页视频地址检查； checking2:番剧单个视频地址检查
    checking1 = re.findall('/play/ss', inurl.split("?")[0], re.S)
    checking2 = re.findall('/play/ep', inurl.split("?")[0], re.S)
    try:
        if checking1 != []:
            res = request.get(
                inurl,
                headers=self.index_headers,
                stream=False,
                timeout=10,
                proxies=self.Proxy,
                auth=self.ProxyAuth
            )
            dec = res.content.decode('utf-8')
            INITIAL_STATE = re.findall(self.re_INITIAL_STATE, dec, re.S)
            temp = json.loads(INITIAL_STATE[0])
            # 更新索引URL
            self.index_url = temp["mediaInfo"]["episodes"][0]["link"]
            return 1, temp["mediaInfo"]["episodes"][0]["link"]
        elif checking2 != []:
            return 1, inurl
        else:
            return 0, inurl
    except Exception as e:
        print("[EXCEPTION]BiliWorker.base.BiliWorker.ssADDRCheck:", e)
        return 0, inurl


def tmp_dffss(self, re_GET):
    """
    解析json格式的playinfo信息, 获取到音视频质量信息及其下载地址

    Args:
        re_GET (_type_): _description_

    Returns:
        _type_: _description_
    """
    temp_v = {}
    for i in range(len(re_GET["data"]["accept_quality"])):
        temp_v[str(re_GET["data"]["accept_quality"][i])] = str(
            re_GET["data"]["accept_description"][i])

    # 列出视频下载质量
    down_dic = {"video": {}, "audio": {}}
    i = 0

    # 获取视频身份信息和初始SegmentBase。
    for dic in re_GET["data"]["dash"]["video"]:
        if str(dic["id"]) in temp_v:
            # qc = temp_v[str(dic["id"])]
            qc = temp_v[str(dic["id"])] + " " + dic["codecs"]
            down_dic["video"][i] = [qc, [dic["baseUrl"]],
                                    'bytes=' + dic["SegmentBase"]["Initialization"]]
            if dic.get('backupUrl') is list:
                for a in range(len(dic["backupUrl"])):
                    down_dic["video"][i][1].append(dic["backupUrl"][a])
            i += 1
        else:
            continue

    # List Audio Stream
    # 获取杜比音轨
    i = 0
    try:
        for dic in re_GET["data"]["dash"]["dolby"]['audio']:
            au_stream = "杜比音轨 " + dic["codecs"] + \
                "  音频带宽：" + str(dic["bandwidth"])
            t = [au_stream, [dic["base_url"]], 'bytes=' +
                 dic["segment_base"]["initialization"]]
            down_dic["audio"][i] = t
            if dic.get('backupUrl') is list:
                for a in range(len(dic["backup_url"])):
                    down_dic["audio"][i][1].append(dic["backupUrl"][a])
            i += 1
    except:
        pass

    # Hi-Res音轨
    try:
        # for dicc in re_GET["data"]["dash"]['flac']['audio']:
        dic = re_GET["data"]["dash"]['flac']['audio']
        au_stream = "Hi-Res " + dic["codecs"] + \
            "  音频带宽：" + str(dic["bandwidth"])
        down_dic["audio"][i] = [au_stream, [dic["base_url"]],
                                'bytes=' + dic["segment_base"]["initialization"]]
        if dic.get('backupUrl') is list:
            for a in range(len(dic["backup_url"])):
                down_dic["audio"][i][1].append(dic["backupUrl"][a])
        i += 1
    except:
        pass

    # 普通音轨
    if type(re_GET["data"]["dash"]["audio"]) is list:
        for dic in re_GET["data"]["dash"]["audio"]:
            au_stream = "普通音轨 " + dic["codecs"] + \
                "  音频带宽：" + str(dic["bandwidth"])
            down_dic["audio"][i] = [au_stream, [dic["baseUrl"]],
                                    'bytes=' + dic["SegmentBase"]["Initialization"]]
            if dic.get('backupUrl') is list:
                for a in range(len(dic["backupUrl"])):
                    down_dic["audio"][i][1].append(dic["backupUrl"][a])
            i += 1
    elif i == 0:
        # 若不存在音轨，则虚拟一个空音轨下载地址
        print(
            "[INFO]BiliWorker.base.BiliWorker.tmp_dffss: This media disable Sounds Track.")
        au_stream = "无音轨"
        down_dic["audio"][0] = [au_stream, [], '']
    else:
        pass

    # Get Video Length
    length = re_GET["data"]["dash"]["duration"]
    return length, down_dic


def search_preinfo(self, index_url):
    """
    资源探查
    通过请求api, 获取到音视频相关的信息和下载链接
    Args:
        index_url (string): _description_

    Returns:
        tuple : 返回视频的信息
    """
    # 获取HTML信息
    index_url = self.ssADDRCheck(index_url)
    url = index_url[1]
    if url.endswith('/'):
        url = url[:-1]
    if "?" in url and "/?" not in url:
        url = url.replace("?", "/?")
    if "spm_id_from" not in url:
        if "/?" in url:
            url += "&spm_id_from=333.999.0.0&oid=1400985499"
        else:
            url += "/?spm_id_from=333.999.0.0&oid=1400985499"
    try:
        res = request.get(
            url,
            headers=self.index_headers,
            stream=False,
            timeout=10,
            proxies=self.Proxy,
            auth=self.ProxyAuth
        )
        dec = res.content.decode('utf-8')
    except Exception as e:
        print("[EXCEPTION]BiliWorker.base.BiliWorker.search_preinfo: Get Initialized Info Error -> ", e)
        return 0, "", "", {}

    # 使用正则表达式查找下载JSON数据
    playinfo = re.findall(self.re_playinfo, dec, re.S)
    INITIAL_STATE = re.findall(self.re_INITIAL_STATE, dec, re.S)
    if playinfo == [] or INITIAL_STATE == []:
        print(
            "[ERROR]BiliWorker.base.BiliWorker.search_preinfo: Get Session Initialized Info Failed!")
        return 0, "", "", {}

    re_init = json.loads(INITIAL_STATE[0])
    re_GET = json.loads(playinfo[0])

    try:
        # 获取视频名称
        vn1 = re.findall(self.vname_expression, dec, re.S)[0].split('>')[1]
        vn2 = ""
        if "videoData" in re_init:
            vn2 = re_init["videoData"]["pages"][re_init["p"] - 1]["part"]
        elif "mediaInfo" in re_init:
            vn2 = re_init["epInfo"]["titleFormat"] + \
                ":" + re_init["epInfo"]["longTitle"]
        video_name = self.name_replace(
            vn1) + "_[" + self.name_replace(vn2) + "]"  # 组合视频名称

        # down_dic包含音视频质量表及其下载地址
        length, down_dic = self.tmp_dffss(re_GET)

        # 返回数据
        return 1, video_name, length, down_dic
    except Exception as e:
        print("[EXCEPTION]BiliWorker.base.BiliWorker.search_preinfo:", e)
        return 0, "", "", {}


def search_videoList(self, index_url):
    """
    搜索视频下载地址列表。

    Args:
        index_url (string): 请求网址

    Returns:
        _type_: _description_
    """
    try:
        res = request.get(
            index_url,
            headers=self.index_headers,
            stream=False,
            timeout=10,
            proxies=self.Proxy,
            auth=self.ProxyAuth
        )
        dec = res.content.decode('utf-8')
    except:
        return 0, {}
    INITIAL_STATE = re.findall(self.re_INITIAL_STATE, dec, re.S)
    if INITIAL_STATE != []:
        try:
            re_init = json.loads(INITIAL_STATE[0])
            init_list = {}
            if "videoData" in re_init:
                init_list["bvid"] = re_init["bvid"]
                init_list["p"] = re_init["p"]
                init_list["pages"] = re_init["videoData"]["pages"]
                # print(init_list)
                return 1, init_list
            elif "mediaInfo" in re_init:
                init_list["bvid"] = re_init["mediaInfo"]["media_id"]
                init_list["p"] = re_init["epInfo"]["i"] + 1
                init_list["pages"] = re_init["mediaInfo"]["episodes"]
                # print(init_list)
                return 2, init_list
            else:
                return 0, {}
        except Exception as e:
            print("[EXCEPTION]BiliWorker.base.BiliWorker.search_videoList:", e)
            return 0, {}
    else:
        return 0, {}


BiliWorker.ssADDRCheck = ssADDRCheck
BiliWorker.tmp_dffss = tmp_dffss
BiliWorker.search_preinfo = search_preinfo
BiliWorker.search_videoList = search_videoList