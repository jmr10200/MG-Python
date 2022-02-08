import logging
from datetime import datetime
import os

# 로그 생성
logger = logging.getLogger()
# 로그 출력 레벨 설정 : (default=WARN)이므로 INFO 레벨부터 출력하기위해 설정
logger.setLevel(logging.INFO)
# 로그 출력 포맷 : [INFO][yyyy/MM/dd HH:mm:ss] message
formatter = logging.Formatter('[%(levelname)s][%(asctime)s][%(process)s] %(message)s')
# log 스트림 출력 설정 : StreamHandler
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)
# log 파일 출력 설정 : FileHandler
date = datetime.now().strftime('%Y-%m-%d')
directory = '../tmp/mg-log'
os.makedirs(directory, exist_ok=True)
file_handler = logging.FileHandler(directory + '/stock_{date}.log'.format(date=date))
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)
