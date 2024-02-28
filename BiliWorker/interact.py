import os
import re
import json
import requests as request

from BiliWorker.base import BiliWorker


def interact_preinfo(self):
    """
    交互进程初始数据获取函数

    Returns:
        _type_: _description_
    """
    self.now_interact = {"cid": "", "bvid": "", "session": "",
                         "graph_version": "", "node_id": "", "vname": ""}
    t1 = self.Get_Init_Info(self.index_url)
    self.index_headers['referer'] = self.index_url
    self.second_headers = self.index_headers
    t2 = self.isInteract()
    if t1[0] or t2[0]:
        return 1, {}, {}
    return 0, self.now_interact


def requests_start(self, now_interact, iv_structure):
    """
    Interactive video download

    Args:
        now_interact (_type_): _description_
        iv_structure (_type_): _description_
    """
    self.now_interact = now_interact
    self.recursion_for_Download(iv_structure, self.output)
    self.business_info.emit("下载交互视频完成。")


def Set_Structure(self, now_interact, iv_structure):
    """
    设置预下载信息

    Args:
        now_interact (_type_): _description_
        iv_structure (_type_): _description_
    """
    self.now_interact = now_interact
    self.iv_structure = iv_structure


def Get_Init_Info(self, url):
    """
    Interactive video initial information

    Args:
        url (_type_): _description_

    Raises:
        Exception: _description_

    Returns:
        _type_: _description_
    """
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
        playinfo = re.findall(self.re_playinfo, dec, re.S)
        INITIAL_STATE = re.findall(self.re_INITIAL_STATE, dec, re.S)
        if playinfo == [] or INITIAL_STATE == []:
            raise Exception("无法找到初始化信息。")
        playinfo = json.loads(playinfo[0])
        INITIAL_STATE = json.loads(INITIAL_STATE[0])
        self.now_interact["session"] = playinfo["session"]
        self.now_interact["bvid"] = INITIAL_STATE["bvid"]
        self.now_interact["cid"] = str(
            INITIAL_STATE["cidMap"][INITIAL_STATE["bvid"]]["cids"]["1"])
        self.now_interact["vname"] = self.name_replace(
            INITIAL_STATE["videoData"]["title"])
        return 0, ""
    except Exception as e:
        return 1, str(e)


def isInteract(self):
    """
    Judge the interactive video.

    Raises:
        Exception: _description_

    Returns:
        _type_: _description_
    """
    make_API = "https://api.bilibili.com/x/player/v2"
    param = {
        'cid': self.now_interact["cid"],
        'bvid': self.now_interact["bvid"],
    }
    try:
        res = request.get(
            make_API,
            headers=self.index_headers,
            params=param,
            timeout=10,
            proxies=self.Proxy,
            auth=self.ProxyAuth
        )
        des = json.loads(res.content.decode('utf-8'))
        if "interaction" not in des["data"]:
            raise Exception("非交互视频")
        self.now_interact["graph_version"] = str(
            des["data"]["interaction"]["graph_version"])
        return 0, ""
    except Exception as e:
        return 1, str(e)


def down_list_make(self, cid_num):
    """
    Get interactive video download URL and Dict

    Args:
        cid_num (_type_): _description_

    Returns:
        _type_: _description_
    """
    make_API = "https://api.bilibili.com/x/player/playurl"
    param = {
        'cid': cid_num,
        'bvid': self.now_interact["bvid"],
        'qn': '116',
        'type': '',
        'otype': 'json',
        'fourk': '1',
        'fnver': '0',
        'fnval': '976',
        'session': self.now_interact["session"]
    }
    try:
        des = request.get(
            make_API,
            headers=self.index_headers,
            params=param,
            timeout=10,
            proxies=self.Proxy,
            auth=self.ProxyAuth
        )
        playinfo = json.loads(des.content.decode('utf-8'))
    except Exception as e:
        return False, str(e)
    if playinfo != {}:
        re_GET = playinfo
        # List Video Quality Table
        length, down_dic = self.parse_video_audio_info(re_GET)
        # Return Data
        return True, length, down_dic
    else:
        return False, "Get Download List Error."


def recursion_for_Download(self, json_list, output_dir):
    """
    Interactive video download processor (Use recursion algorithm)

    Args:
        json_list (_type_): _description_
        output_dir (_type_): _description_

    Returns:
        _type_: _description_
    """
    for ch in json_list:
        chn = self.name_replace(ch)
        output = output_dir + "/" + chn
        video_dir = output + "/" + chn + '_video.m4s'
        audio_dir = output + "/" + chn + '_audio.m4s'
        # 新字典判断
        if json_list[ch]['isChoose']:
            # if "cid" in json_list[ch]:
            dic_return = self.down_list_make(json_list[ch]["cid"])
            # print(dic_return)
            if not dic_return[0]:
                self.business_info.emit("节点（{}）获取下载地址出错".format(ch))
                print(
                    "[ERROR]BiliWorker.base.BiliWorker.recursion_for_Download:", dic_return[1])
                return -1
            _, _, down_dic = dic_return
            self.second_headers["range"] = down_dic["video"][self.VQuality][2]
            self.d_processor(
                down_dic["video"][self.VQuality][1], output, video_dir, "下载视频：" + chn)
            # 增加是否有音轨判定，若无音轨则直接转换视频文件为MP4
            has_au = True
            if down_dic["audio"][self.AQuality][1]:
                self.second_headers['range'] = down_dic["audio"][self.AQuality][2]
                self.d_processor(
                    down_dic["audio"][self.AQuality][1], output, audio_dir, "下载音频：" + chn)
            else:
                has_au = False
            if self.synthesis and has_au:
                self.business_info.emit('正在启动ffmpeg......')
                self.ffmpeg_synthesis(
                    video_dir, audio_dir, output + '/' + chn + '.mp4')
            else:
                os.rename(video_dir, output + '/' + chn + '.mp4')
        if "choices" in json_list[ch]:
            self.recursion_for_Download(json_list[ch]["choices"], output)
    return 0


BiliWorker.interact_preinfo = interact_preinfo
BiliWorker.requests_start = requests_start
BiliWorker.Set_Structure = Set_Structure
BiliWorker.Get_Init_Info = Get_Init_Info
BiliWorker.isInteract = isInteract
BiliWorker.down_list_make = down_list_make
BiliWorker.recursion_for_Download = recursion_for_Download
