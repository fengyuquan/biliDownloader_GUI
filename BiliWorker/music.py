import os
import re
import json
import requests as request

from BiliWorker.base import BiliWorker


def search_AUPreinfo(self, au_url):
    """
    音频进程

    Args:
        au_url (_type_): _description_

    Returns:
        _type_: _description_
    """
    # check1:音乐歌单页面检测；check2:单个音乐页面检测
    check1 = re.findall(r'/audio/am(\d+)', au_url, re.S)
    check2 = re.findall(r'/audio/au(\d+)', au_url, re.S)
    if check1:
        # print(check1[0])
        temps = self.AuList_Maker(check1[0], 2)
        if temps[0]:
            # print(json.dumps(temps[1]))
            return 1, temps[1]
        else:
            return 0, "Audio List Get Error."
    elif check2:
        # print(check2[0])
        temps = self.AuList_Maker(check2[0], 1)
        if temps[0]:
            # print(json.dumps(temps[1]))
            return 2, temps[1]
        else:
            return 0, "Audio Single Get Error."
    else:
        print("[INFO]BiliWorker.base.BiliWorker.search_AUPreinfo: Is NOT Music.")
        return 0, {}


def AuList_Maker(self, sid, modeNUM):
    list_dict = {"audio": [], "total": 0}
    if modeNUM == 1:
        try:
            makeURL = "https://www.bilibili.com/audio/music-service-c/web/song/info?sid=" + sid
            res = request.get(
                makeURL,
                headers=self.index_headers,
                stream=False,
                timeout=10,
                proxies=self.Proxy,
                auth=self.ProxyAuth
            )
            des = res.content.decode('utf-8')
            auinfo = json.loads(des)["data"]
            temp = {
                "title": auinfo["title"] + "_" + auinfo["author"],
                "sid": sid, "cover": auinfo["cover"],
                "duration": auinfo["duration"],
                "lyric": auinfo["lyric"]
            }
            list_dict["audio"].append(temp)
            list_dict["total"] = 1
        except Exception as e:
            print("[EXCEPTION]BiliWorker.base.BiliWorker.search_AUPreinfo:", e)
            return 0, "AuList_Maker_Single:{}".format(e)
        return 1, list_dict
    elif modeNUM == 2:
        try:
            pn = 1
            while True:
                makeURL = "https://www.bilibili.com/audio/music-service-c/web/song/of-menu?sid=" + sid + "&pn=" + str(
                    pn) + "&ps=30"
                res = request.get(
                    makeURL,
                    headers=self.index_headers,
                    stream=False,
                    timeout=10,
                    proxies=self.Proxy,
                    auth=self.ProxyAuth
                )
                des = res.content.decode('utf-8')
                mu_dic = json.loads(des)["data"]
                for sp in mu_dic["data"]:
                    # print(sp)
                    temp = {
                        "title": sp["title"] + "_" + sp["author"],
                        "sid": str(sp["id"]), "cover": sp["cover"],
                        "duration": sp["duration"], "lyric": sp["lyric"]
                    }
                    list_dict["audio"].append(temp)
                    list_dict["total"] += 1
                if pn >= mu_dic["pageCount"]:
                    break
                else:
                    pn += 1
                    continue
        except Exception as e:
            print("[EXCEPTION]BiliWorker.base.BiliWorker.AuList_Maker:", e)
            return 0, "AuList_Maker_List:{}".format(e)
        return 1, list_dict
    else:
        return 0, "ModeNum Error."


@property
def Audio_Show(self):
    """
    显示音频信息

    Returns:
        _type_: _description_
    """
    au_dic = self.search_AUPreinfo(self.index_url)
    if au_dic[0] == 0:
        print("[INFO]BiliWorker.base.BiliWorker.Audio_Show:", au_dic[1])
        return 0
    if au_dic[0] == 1:
        self.business_info.emit('当前歌单包含音乐数量为{}个'.format(au_dic[1]["total"]))
    elif au_dic[0] == 2:
        self.business_info.emit('当前下载歌曲名称为：{}'.format(
            au_dic[1]["audio"][0]["title"]))
        self.business_info.emit('歌曲长度为：{}'.format(
            au_dic[1]["audio"][0]["duration"]))
    else:
        return 0
    i = 0
    for sp in au_dic[1]["audio"]:
        i += 1
        form_make = "{}-->{}".format(i, sp["title"])
        self.media_list.emit([0, form_make])
    self.vq_list.emit("无")
    self.aq_list.emit("最高音质")
    return 1


def Audio_getDownloadList(self, sid):
    """
    获取单个音频下载地址

    Args:
        sid (_type_): _description_

    Returns:
        _type_: _description_
    """
    make_url = "https://www.bilibili.com/audio/music-service-c/web/url?sid=" + sid
    res = request.get(
        make_url,
        headers=self.index_headers,
        stream=False,
        timeout=10,
        proxies=self.Proxy,
        auth=self.ProxyAuth
    )
    des = res.content.decode('utf-8')
    au_list = json.loads(des)["data"]["cdns"]
    return au_list


def simple_downloader(self, url, output_dir, output_file):
    """
    附带资源下载

    Args:
        url (_type_): _description_
        output_dir (_type_): _description_
        output_file (_type_): _description_
    """
    try:
        res = request.get(
            url,
            headers=self.index_headers,
            timeout=10,
            proxies=self.Proxy,
            auth=self.ProxyAuth
        )
        file = res.content
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        with open(output_file, 'wb') as f:
            f.write(file)
    except Exception as e:
        print(
            "[EXCEPTION]BiliWorker.base.BiliWorker.simple_downloader: Simple Download Failed -> ", e)
        self.business_info.emit("附带下载失败：{}".format(url))


def audio_downloader(self):
    """
    音乐下载函数

    Returns:
        _type_: _description_
    """
    self.second_headers["referer"] = "https://www.bilibili.com/"
    self.second_headers["sec-fetch-dest"] = 'audio'
    self.second_headers["sec-fetch-mode"] = 'no-cors'
    temp_dic = self.search_AUPreinfo(self.index_url)
    if temp_dic[0] == 0:
        self.business_info.emit("获取音乐前置信息出错。")
        return 0
    try:
        for index in self.d_list:
            sp = temp_dic[1]["audio"][index - 1]
            output_dir = self.output + "/" + self.name_replace(sp["title"])
            output_name = output_dir + "/" + self.name_replace(sp["title"])
            self.business_info.emit("正在下载音乐：{}".format(sp["title"]))
            if sp["cover"] != "":
                self.simple_downloader(
                    sp["cover"], output_dir, output_name + "_封面.jpg")
            if sp["lyric"] != "":
                self.simple_downloader(
                    sp["lyric"], output_dir, output_name + "_歌词.lrc")
            au_downlist = self.Audio_getDownloadList(sp["sid"])
            self.second_headers["range"] = 'bytes=0-'
            self.d_processor(au_downlist, output_dir,
                             output_name + ".mp3", "下载音乐")
        self.business_info.emit("音乐下载进程结束！")
        return 1
    except Exception as e:
        self.business_info.emit("音频下载出错：{}".format(e))
        print(
            "[EXCEPTION]BiliWorker.base.BiliWorker.audio_downloader: Audio Download Failed -> ", e)
        return 0


BiliWorker.search_AUPreinfo = search_AUPreinfo
BiliWorker.AuList_Maker = AuList_Maker
BiliWorker.Audio_Show = Audio_Show
BiliWorker.Audio_getDownloadList = Audio_getDownloadList
BiliWorker.simple_downloader = simple_downloader
BiliWorker.audio_downloader = audio_downloader
