"""
クローリングの実行中に発生するエラーを管理するクラス
"""


class StockCrawlingException(Exception):
    def __init__(self, msg_type, msg):
        self.msg_type = msg_type
        self.msg = msg

    def __str__(self):
        return self.msg_type + self.msg  # エラーメッセージの加工
