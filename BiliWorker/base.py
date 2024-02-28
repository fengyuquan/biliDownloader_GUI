from PySide2.QtCore import QThread, Signal


class BiliWorker(QThread):
    """
    biliDownloader下载主工作线程
    """
    # 信息槽发射
    business_info = Signal(str)     # 用于发送业务信息，如下载状态、错误信息等。
    vq_list = Signal(str)           # 发送视频的质量选项列表。
    aq_list = Signal(str)           # 发送音频的质量选项列表。
    media_list = Signal(list)       # 发送媒体列表，如视频分P列表或音频列表。
    progr_bar = Signal(dict)        # 发送下载进度信息。
    is_finished = Signal(int)       # 发送下载任务完成的信号。
    interact_info = Signal(dict)    # 发送交互视频的相关信息。

    def __init__(self, args, model=0):
        super(BiliWorker, self).__init__()
        self.run_model = model                  # 运行模式
        self.haveINFO = False                   # 是否有信息
        self.pauseprocess = False               # 是否暂停进程
        self.subpON = False                     # 子进程是否开启
        self.killprocess = False                # 是否终止进程

        self.index_url = args["Address"]        # 索引URL
        self.d_list = args["DownList"]          # 下载列表
        self.VQuality = args["VideoQuality"]    # 视频质量
        self.AQuality = args["AudioQuality"]    # 音频质量
        self.output = args["Output"]            # 输出目录
        self.synthesis = args["sym"]            # 是否合成
        self.systemd = args["sys"]              # 系统守护进程
        self.chunk_size = args["chunk_size"]    # 块大小
        self.set_err = args["dl_err"]           # 设置错误

        # 正则表达式，用于匹配播放信息
        self.re_playinfo = 'window.__playinfo__=([\s\S]*?)</script>'
        # 正则表达式，用于匹配初始状态
        self.re_INITIAL_STATE = 'window.__INITIAL_STATE__=([\s\S]*?);\(function'
        # 正则表达式，用于匹配视频名称
        self.vname_expression = '<title(.*?)</title>'

        # URL请求头
        self.index_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/72.0.3626.121 Safari/537.36"
        }
        self.second_headers = {
            "accept": "*/*",
            "Connection": "keep-alive",
            "accept-encoding": "identity",
            "accept-language": "zh-CN,zh;q=0.9",
            "origin": "https://www.bilibili.com",
            "sec-fetch-site": "cross-site",
            "sec-fetch-mode": "cors",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/72.0.3626.121 Safari/537.36"
        }
        # 如果使用Cookie，则URL请求头加上cookie选项
        if args["useCookie"]:
            self.index_headers["cookie"] = args["cookie"]
            self.second_headers["cookie"] = args["cookie"]
        else:
            self.index_headers["cookie"] = ""
            self.second_headers["cookie"] = ""

        # 代理
        self.Proxy = None
        if args["useProxy"]:
            self.Proxy = args["Proxy"]
        # 代理验证
        self.ProxyAuth = None
        if args["ProxyAuth"]["inuse"]:  # 如果代理需要验证
            from requests.auth import HTTPProxyAuth
            self.ProxyAuth = HTTPProxyAuth(
                args['ProxyAuth']['usr'], args['ProxyAuth']['pwd'])

    def model_set(self, innum):
        """
        运行模式设置函数

        Args:
            innum (int): 运行模式
        """
        self.run_model = innum  # 设置运行模式

    def close_process(self):
        """
        结束进程函数
        """
        self.killprocess = True  # 设置终止进程标志
        self.pauseprocess = False  # 取消暂停进程标志
        self.business_info.emit("正在结束下载进程......")

    def run(self):
        # print("Current Attributes of self:")
        # for attr in dir(self):
        #     if not attr.startswith("__") and not callable(getattr(self, attr)):
        #         print(f"{attr}: {getattr(self, attr)}")

        if self.run_model == 0:
            # 探查资源类型
            self.interact_info.emit({"state": 0})
            d = self.interact_preinfo()
            r = self.show_preDetail()
            if r == 1:
                if d[0] == 0:
                    self.interact_info.emit({"state": 1, "data": d[1]})
                self.is_finished.emit(1)
            elif self.Audio_Show:
                self.is_finished.emit(4)
            else:
                self.is_finished.emit(0)
        elif self.run_model == 1:
            # 下载非交互视频
            if self.d_list:
                # print(1)
                self.download_list()
                if self.killprocess:
                    self.business_info.emit("下载已终止")
                self.progr_bar.emit({"finish": 1})
                self.is_finished.emit(2)
            else:
                self.is_finished.emit(2)
        # elif self.run_model == 2:
        #     # 交互视频信息读取
        #     d = self.interact_nodeList()
        #     if d == {}:
        #         self.interact_info.emit({"state":-2,"data":{}})
        #         self.is_finished.emit(3)
        #     else:
        #         self.interact_info.emit({"state":2,"nowin":self.now_interact,"ivf":d})
        elif self.run_model == 3:
            # 交互视频下载
            self.requests_start(self.now_interact, self.iv_structure)
            self.is_finished.emit(3)
        elif self.run_model == 4:
            # 音频列表下载
            if self.d_list:
                self.audio_downloader()
                if self.killprocess:
                    self.business_info.emit("下载已终止")
                self.progr_bar.emit({"finish": 1})
                self.is_finished.emit(2)
            else:
                self.is_finished.emit(2)
