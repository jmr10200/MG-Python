import logging
from datetime import datetime
import os

# ログ生成
logger = logging.getLogger()
# ログ出力のレベル設定 : (default=WARN)なのでINFOレベルから出力されるように設定
logger.setLevel(logging.INFO)
# ログ出力のフォーマット設定 : [INFO][yyyy/MM/dd HH:mm:ss] message
formatter = logging.Formatter('[%(levelname)s][%(asctime)s][%(process)s] %(message)s')
# log streamの出力設定 : StreamHandler
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)
# log fileの出力設定 : FileHandler
date = datetime.now().strftime('%Y-%m-%d')
directory = '../tmp/mg-log'
os.makedirs(directory, exist_ok=True)
file_handler = logging.FileHandler(directory + '/stock_{date}.log'.format(date=date))
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)
