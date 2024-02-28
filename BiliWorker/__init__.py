
import socket
import urllib3.util.connection as urllib3_conn

# 强制使用IPv4
urllib3_conn.allowed_gai_family = lambda: socket.AF_INET

import BiliWorker.download
import BiliWorker.interact
import BiliWorker.music
import BiliWorker.postprocessing
import BiliWorker.resource_exploration
import BiliWorker.show