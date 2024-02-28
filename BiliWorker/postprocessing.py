import os
import re
import subprocess
import sys
from BiliWorker.base import BiliWorker


def name_replace(self, name):
    """
    文件名冲突替换
    """
    vn = name.replace(' ', '_').replace(
        '\\', '').replace('/', '')  # 替换文件名中的特殊字符
    vn = vn.replace('*', '').replace(':', '').replace('?', '').replace('<', '')
    vn = vn.replace('>', '').replace(
        '\"', '').replace('|', '').replace('\x08', '')
    return vn  # 返回处理后的文件名


def subp_GUIFollow(self, ffcommand):
    """
    Subprocess Progress of FFMPEG, RUN and Following Function

    Args:
        ffcommand (_type_): _description_

    Returns:
        _type_: _description_
    """
    proc = {"Max": 100, "Now": 0, "finish": 2}
    subp = subprocess.Popen(ffcommand, shell=True, stderr=subprocess.PIPE, stdin=subprocess.PIPE,
                            encoding=sys.getfilesystemencoding())
    self.business_info.emit('FFMPEG正在执行合成指令')
    while True:
        status = subp.poll()
        if status is not None:
            if status != 0:
                self.business_info.emit("FFMPEG运行出错, 代码: {}".format(status))
                proc["finish"] = 1
                self.progr_bar.emit(proc)
                return status
            else:
                proc["finish"] = 1
                self.progr_bar.emit(proc)
                return 0
        if self.killprocess:
            subp.stdin.write('q')
        line = os.read(subp.stderr.fileno(), 1024)
        if line:
            # print(line)
            sf = re.findall('Duration: ([\s\S]*?),', str(line), re.S)
            cf = re.findall('time=([\s\S]*?) bitrate=', str(line), re.S)
            if sf:
                temp = sf[0]
                temp = temp.split(".")[0].split(":")
                num = int(temp[0]) * 3600 + int(temp[1]) * 60 + int(temp[2])
                # print("视频总长：", num)
                proc["Max"] = num
            if cf:
                temp = cf[0].split(".")[0].split(":")
                cnum = int(temp[0]) * 3600 + int(temp[1]) * 60 + int(temp[2])
                # print("当前进度", cnum)
                proc["Now"] = cnum
            self.progr_bar.emit(proc)


def ffmpeg_synthesis(self, input_v, input_a, output_add):
    """
    ffmpeg合并音视频

    Args:
        input_v (_type_): _description_
        input_a (_type_): _description_
        output_add (_type_): _description_

    Raises:
        Exception: _description_

    Returns:
        _type_: _description_
    """
    if os.path.exists(output_add):
        self.business_info.emit("文件：{}\n已存在。".format(output_add))
        return -1
    ffcommand = ""
    if self.systemd == "win32":
        ffpath = os.path.dirname(os.path.realpath(sys.argv[0]))
        ffcommand = '"' + ffpath + '\\ffmpeg.exe" -i "' + \
                    input_v + '" -i "' + \
                    input_a + '" -strict unofficial -strict -2 -brand mp42 -c copy -y "' + output_add + '"'
    elif self.systemd == "linux":
        ffcommand = 'ffmpeg -i "' + input_v + '" -i "' + input_a + \
            '" -strict unofficial -strict -2 -brand mp42 -c copy -y "' + output_add + '"'
    elif self.systemd == "darwin":
        ffpath = os.path.dirname(os.path.realpath(sys.argv[0]))
        ffcommand = '"' + ffpath + '/ffmpeg" -i "' + \
                    input_v + '" -i "' + \
                    input_a + '" -strict unofficial -strict -2 -brand mp42 -c copy -y "' + output_add + '"'
    else:
        self.business_info.emit("未知操作系统: 无法确定FFMpeg命令。")
        return -2
    # 内测版专属
    self.business_info.emit('--------------------内测分割线--------------------')
    self.business_info.emit(
        "操作系统：{}\nFFMPEG命令: {}".format(self.systemd, ffcommand))
    self.business_info.emit('--------------------内测分割线--------------------')
    try:
        self.subpON = True
        temp = self.subp_GUIFollow(ffcommand)
        if temp:
            raise Exception(temp)
        self.subpON = False
        self.business_info.emit("视频合并完成！")
        os.remove(input_v)
        os.remove(input_a)
    except Exception as e:
        self.business_info.emit("视频合成失败：{}".format(e))
        self.subpON = False


BiliWorker.name_replace = name_replace
BiliWorker.subp_GUIFollow = subp_GUIFollow
BiliWorker.ffmpeg_synthesis = ffmpeg_synthesis
