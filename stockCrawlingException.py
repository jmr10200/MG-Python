"""
크롤링 실행 과정에서 발생하는 에러를 관리하는 클래스
"""


class StockCrawlingException(Exception):
    def __init__(self, msg_type, msg):
        self.msg_type = msg_type
        self.msg = msg

    def __str__(self):
        return self.msg_type + self.msg  # 에러 메시지 가공
