import os
import re
import requests as request

from time import sleep
from BiliWorker.base import BiliWorker


def pause(self):
    """
    暂停下载进程
    """
    if self.subpON:  # 如果子进程开启
        self.business_info.emit("视频正在合成，只能终止不能暂停")
        return False
    else:
        self.business_info.emit("下载已暂停")
        self.pauseprocess = True  # 设置暂停进程标志


def resume(self):
    """
    恢复下载进程
    """
    self.business_info.emit("下载已恢复")
    self.pauseprocess = False  # 取消暂停进程标志


def download_single(self, index=""):
    """
    下载单个视频

    Args:
        index (str, optional): _description_. Defaults to "".

    Returns:
        _type_: _description_
    """
    # Get video pre-detial
    if index == "":
        flag, video_name, _, down_dic = self.search_preinfo(self.index_url)
        index = self.index_url
    else:
        flag, video_name, _, down_dic = self.search_preinfo(index)

    # If we can access the video page
    if flag:
        try:
            # Judge file whether exists
            video_dir = self.output + '/' + video_name + '_video.m4s'
            audio_dir = self.output + '/' + video_name + '_audio.m4s'
            sym_video_dir = self.output + '/' + video_name + '.mp4'
            if os.path.exists(video_dir):
                self.business_info.emit("文件：{}\n已存在。".format(video_dir))
                return -1
            if os.path.exists(audio_dir):
                self.business_info.emit("文件：{}\n已存在。".format(audio_dir))
                return -1
            if os.path.exists(sym_video_dir):
                self.business_info.emit("文件：{}\n已存在。".format(sym_video_dir))
                return -1

            # self.business_info.emit("需要下载的视频：{}".format(video_name))
            # Perform video stream length sniffing
            self.second_headers['referer'] = index
            self.second_headers['range'] = down_dic["video"][self.VQuality][2]
            # Switch between main line and backup line(video).
            if self.killprocess:
                return -2
            a = self.d_processor(
                down_dic["video"][self.VQuality][1], self.output, video_dir, "下载视频")

            # Perform audio stream length sniffing
            self.second_headers['range'] = down_dic["audio"][self.AQuality][2]
            # Switch between main line and backup line(audio).
            if self.killprocess:
                return -2
            b = self.d_processor(
                down_dic["audio"][self.AQuality][1], self.output, audio_dir, "下载音频")
            if a or b:
                return -3

            # Merge audio and video (USE FFMPEG)
            if self.killprocess:
                return -2
            if self.synthesis:
                self.business_info.emit('正在启动FFMPEG......')
                # Synthesis processor
                self.ffmpeg_synthesis(video_dir, audio_dir, sym_video_dir)
        except Exception as e:
            print("[EXCEPTION]BiliWorker.base.BiliWorker.download_single:", e)
    else:
        self.business_info.emit("下载失败：尚未找到源地址，请检查网站地址或充值大会员！")


def download_list(self):
    """
    下载视频列表
    """
    r_list = self.d_list
    all_list = self.search_videoList(self.index_url)
    preIndex = self.index_url.split("?")[0]

    if all_list[0] == 1:
        if r_list[0] == 0:
            for p in all_list[1]["pages"]:
                if self.killprocess:
                    break
                self.download_single(preIndex + "?p=" + str(p["page"]))
        else:
            listLEN = len(all_list[1]["pages"])
            for i in r_list:
                if self.killprocess:
                    break
                if i <= listLEN:
                    self.download_single(preIndex + "?p=" + str(i))
                else:
                    continue
        self.business_info.emit("列表视频下载进程结束！")
    elif all_list[0] == 2:
        if r_list[0] == 0:
            for p in all_list[1]["pages"]:
                if self.killprocess:
                    break
                self.download_single(p["link"])
        else:
            listLEN = len(all_list[1]["pages"])
            for i in r_list:
                if self.killprocess:
                    break
                if i <= listLEN:
                    self.download_single(all_list[1]["pages"][i - 1]["link"])
                else:
                    continue
        self.business_info.emit("媒体视频下载进程结束！")
    else:
        self.business_info.emit("未找到视频列表信息。")

# Download  function


def d_processor(self, url_list, output_dir, output_file, dest):
    """
    下载Stream

    Args:
        url_list (_type_): _description_
        output_dir (_type_): _description_
        output_file (_type_): _description_
        dest (_type_): _description_

    Raises:
        Exception: _description_

    Returns:
        _type_: _description_
    """
    for line in url_list:
        self.business_info.emit('使用线路：{}'.format(line.split("?")[0]))
        try:
            # video stream length sniffing
            video_bytes = request.get(
                line,
                headers=self.second_headers,
                stream=False,
                timeout=(5, 10),
                proxies=self.Proxy,
                auth=self.ProxyAuth
            )
            vc_range = video_bytes.headers['Content-Range'].split('/')[1]
            self.business_info.emit("获取{}流范围为：{}".format(dest, vc_range))
            self.business_info.emit('{}  文件大小：{} MB'.format(
                dest, round(float(vc_range) / 1024 / 1024), 4))
            # Get the full video stream
            proc = {"Max": int(vc_range), "Now": 0, "finish": 0}
            err = 0
            while err <= self.set_err:
                try:
                    self.second_headers['range'] = 'bytes=' + \
                        str(proc["Now"]) + '-' + vc_range
                    m4sv_bytes = request.get(
                        line,
                        headers=self.second_headers,
                        stream=True,
                        timeout=10,
                        proxies=self.Proxy,
                        auth=self.ProxyAuth
                    )
                    self.progr_bar.emit(proc)
                    if not os.path.exists(output_dir):
                        os.makedirs(output_dir)
                    with open(output_file, 'ab') as f:
                        for chunks in m4sv_bytes.iter_content(chunk_size=self.chunk_size):
                            while self.pauseprocess:
                                sleep(1.5)
                                if self.killprocess:
                                    return -1
                            if chunks:
                                f.write(chunks)
                                proc["Now"] += self.chunk_size
                                self.progr_bar.emit(proc)
                            if self.killprocess:
                                m4sv_bytes.close()
                                return -1
                    if proc["Now"] >= proc["Max"]:
                        m4sv_bytes.close()
                        break
                    else:
                        print("[INFO]BiliWorker.base.BiliWorker.d_processor: Server Break Connection, "
                              "Re-Connecting...")
                except Exception as e:
                    if not re.findall('10054', str(e), re.S):
                        err += 1
                    print(
                        "[EXCEPTION]BiliWorker.base.BiliWorker.d_processor:", e, err)
            if err > self.set_err:
                raise Exception('线路出错，切换线路。')
            proc["finish"] = 1
            self.progr_bar.emit(proc)
            self.business_info.emit("{}成功！".format(dest))
            return 0
        except Exception as e:
            print("[EXCEPTION]BiliWorker.base.BiliWorker.d_processor:", e)
            self.business_info.emit("{}出错：{}".format(dest, e))
            # print(proc)
            if os.path.exists(output_file):
                os.remove(output_file)
    return 1


BiliWorker.pause = pause
BiliWorker.resume = resume
BiliWorker.download_single = download_single
BiliWorker.download_list = download_list
BiliWorker.d_processor = d_processor
