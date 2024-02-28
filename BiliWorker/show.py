from BiliWorker.base import BiliWorker


def show_preDetail(self):
    """
    在界面控制台中显示预下载信息

    Returns:
        int: 执行状态
    """
    # flag,video_name,length,down_dic = self.search_preinfo()
    temp = self.search_preinfo(self.index_url)
    preList = self.search_videoList(self.index_url)
    self.business_info.emit('--------------------我是分割线--------------------')

    try:
        if temp[0] and preList[0] != 0:
            if preList[0] == 1:
                # Show video pages
                self.business_info.emit(
                    '当前需要下载的BV号为: {}'.format(preList[1]["bvid"]))
                self.business_info.emit(
                    '当前BV包含视频数量为{}个'.format(len(preList[1]["pages"])))
                for sp in preList[1]["pages"]:
                    form_str = "{}-->{}".format(sp["page"], sp["part"])
                    if sp["page"] == preList[1]["p"]:
                        self.media_list.emit([1, form_str])
                    else:
                        self.media_list.emit([0, form_str])
            elif preList[0] == 2:
                # Show media pages
                self.business_info.emit(
                    '当前需要下载的媒体号为：{}'.format(preList[1]["bvid"]))
                self.business_info.emit(
                    '当前媒体包含视频数量为{}个'.format(len(preList[1]["pages"])))
                self.business_info.emit('-----------具体分P视频名称与下载号-----------')
                i = 0
                for sp in preList[1]["pages"]:
                    i += 1
                    form_str = "{}-->{}".format(i, sp["share_copy"])
                    if i == preList[1]["p"]:
                        self.media_list.emit([1, form_str])
                    else:
                        self.media_list.emit([0, form_str])
            self.business_info.emit(
                '--------------------我是分割线--------------------')

            # Show Video Download Detail
            self.business_info.emit('当前下载视频名称：{}'.format(temp[1]))
            self.business_info.emit('当前下载视频长度：{} 秒'.format(temp[2]))

            for i in range(len(temp[3]["video"])):
                # print("{}-->视频画质：{}".format(i, temp[3]["video"][i][0]))
                self.vq_list.emit("{}.{}".format(
                    i + 1, temp[3]["video"][i][0]))
            for i in range(len(temp[3]["audio"])):
                # print("{}-->音频编码：{}".format(i, temp[3]["audio"][i][0]))
                self.aq_list.emit("{}.{}".format(
                    i + 1, temp[3]["audio"][i][0]))
            return 1
        else:
            return 0
    except Exception as e:
        print("[EXCEPTION]BiliWorker.base.BiliWorker.show_preDetail:", e)
        return 0


BiliWorker.show_preDetail = show_preDetail
