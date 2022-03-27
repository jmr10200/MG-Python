"""
NAVERの時系列株価データクローリング
株式の銘柄コードと取得開始日を入力すると現在日付までの終値と出来高を取得してcsvファイルを出力

parameter : 銘柄コード, 取得開始日
"""
import traceback
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime

from stockCrawlingException import StockCrawlingException
import loggerConfig
import sys
import re
import os
import plotly
from elasticsearch import Elasticsearch, helpers


# elasticsearch(7.17.1)
def save_data(df, code, stock_name, str_start_date):
    try:
        es = Elasticsearch("http://localhost:9200")
        indexName = 'stockdata'  # index : RDBMSのdatabase
        mapping = {
            "mappings": {
                "properties": {
                    "date": {"type": "date",  # date
                             "store": True,
                             "index": True},
                    "price": {"type": "integer",
                              "store": True,
                              "index": True},
                    "volume": {"type": "integer",
                               "store": True,
                               "index": True}
                }
            }
        }
        # indexを存在チェックして作成
        if es.indices.exists(index=indexName):
            pass
        else:
            es.indices.create(index=indexName, body=mapping)

        # column名を英語に変換
        df = df.rename(columns={
            '날짜': 'date',
            '종가': 'price',
            '거래량': 'volume'
        })
        helpers.bulk(es, es_doc_generator(code, df))
        return es
    except Exception:
        msg_type = '[save data failed] '
        msg = 'failed insert data into Elasticsearch'  # Elasticsearchにインサートを失敗しました。
        raise StockCrawlingException(msg_type, msg)


# data生成
def es_doc_generator(code, df):
    try:
        records = [d[1] for d in df.iterrows()]
        docs_es = [{key: doc[key] for key in doc.keys()} for doc in records]
        for doc in docs_es:
            yield {
                "_index": code,  # code
                "_id": doc['date'],  # PK
                "_type": "_doc",
                "_source": doc,
            }
    except Exception:
        msg_type = '[es data generator failed] '
        msg = 'failed data generation'  # Elasticsearchにインサートを失敗しました。
        raise StockCrawlingException(msg_type, msg)


# data検索
def search_data(es, code):
    query = {
        "query": {
            "range": {
                "date": {
                    "gte": "2021-12-01"  # 2021-12-01以後のデータ検索
                }
            }
        }
    }
    # ドキュメントを検索
    result = es.search(index=code, body=query, size=30)
    # 検索結果からドキュメントの内容のみ表示
    for document in result["hits"]["hits"]:
        print(document["_source"])


# ページごとにデータを取得
def page_data(code, header, page):
    try:
        url = 'http://finance.naver.com/item/sise_day.naver?code={code}&page={page}'.format(code=code, page=page)
        res = requests.get(url, headers=header)
        soap_data = BeautifulSoup(res.text, 'lxml')
        df = pd.read_html(str(soap_data.find("table")), header=0)[0]
        df = df.dropna()
        return df
    except Exception:
        msg_type = '[crawling page data failed] '
        msg = '페이지 데이터 취득에 실패하였습니다.'  # ページデータの取得を失敗しました。
        raise StockCrawlingException(msg_type, msg)
    return None


# クローリング
def crawling_stock_data(df, code, header, start_date, last_page):
    try:
        pg = 1
        while pg <= last_page:
            logger.info(str(pg) + '페이지 데이터를 추출합니다.')  # ○ページのデータを取得します。
            page_df = page_data(code, header, pg)
            page_df_filtered = page_df[page_df['날짜'] > start_date]
            if df is None:
                df = page_df_filtered
            else:
                df = pd.concat([df, page_df_filtered])
            if len(page_df) > len(page_df_filtered):
                break
            pg += 1

        # float -> int 변환
        df = df.astype({'전일비': 'int', '종가': 'int', '시가': 'int', '고가': 'int', '저가': 'int', '거래량': 'int'})
        return df
    except Exception:
        msg_type = '[crawling stock data failed] '
        msg = '데이터 추출에 실패하였습니다.'  # データ取得を失敗しました。
        raise StockCrawlingException(msg_type, msg)
    # return None


# チャート出力
def print_graph(df, code, stock_name, str_start_date):
    try:
        # MEMO　課題のデータのコード：010140
        # headerの取得
        df_header = df.columns.tolist()
        # DataFrameをlistに変換、取引中止の状態のデータを編集加工
        list_df = df.values.tolist()
        for i in list_df:
            # 前日比 == 0 and 出来高 == 0 の場合、
            if i[2] == 0 and i[6] == 0:
                close_price = i[1]
                # 始値、高値、安値を終値に設定
                i[3:6] = [close_price, close_price, close_price]
        # 取得してたheaderでDataFrameを生成
        graph_df = pd.DataFrame(list_df, columns=df_header)
        # 日付でソート
        graph_df = graph_df.sort_values(by='날짜')

        # candleチャート生成
        candle = plotly.graph_objs.Candlestick(
            x=graph_df['날짜'],
            open=graph_df['시가'],
            high=graph_df['고가'],
            low=graph_df['저가'],
            close=graph_df['종가'],
            increasing_line_color='red',
            decreasing_line_color='blue'
        )
        # 出来高チャートの生成
        volume_h = plotly.graph_objs.Bar(x=graph_df['날짜'], y=graph_df['거래량'])
        # figure生成
        figure = plotly.subplots.make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.02)
        # キャンドルチャート
        figure.add_trace(candle, row=1, col=1)
        # 出来高チャート
        figure.add_trace(volume_h, row=2, col=1)
        # チャートのレイアウト編集
        figure.update_layout(
            title='<b>' + stock_name + ' (' + code + ') Chart</b>',
            title_x=0.5,
            title_xanchor='center',
            title_font_size=25,
            showlegend=False,
            yaxis1=dict(
                title='<b>주가</b>',
                tickformat=','
            ),
            xaxis2=dict(
                title='<b>날짜</b>',
                rangeslider_visible=True
            ),
            yaxis2=dict(
                title='<b>거래량</b>',
                tickformat=',',
            ),
            xaxis1_rangeslider_visible=False,
            xaxis2_rangeslider_visible=False
        )
        # figure.show()
        directory = '../tmp/chart/'
        os.makedirs(directory, exist_ok=True)
        filename = code + "_chart_" + str_start_date + '~' + datetime.now().strftime('%Y-%m-%d')
        # htmlファイル出力
        plotly.io.write_html(figure, file=directory + "{filename}.html".format(filename=filename))
        # pngファイル出力
        plotly.io.write_image(figure, file=directory + "{filename}.png".format(filename=filename))
        logger.info('{filename}.png'.format(filename=filename))
    except Exception:
        msg_type = '[print stock chart failed] '
        msg = '차트 출력에 실패하였습니다.'  # チャート出力を失敗しました。
        traceback.print_exc()
        raise StockCrawlingException(msg_type, msg)


# csvファイル出力
def print_csv(df, code, stock_name, str_start_date):
    try:
        # 不要な列削除 (axisが0の場合は行, 1の場合は列)
        df.drop(['전일비', '시가', '고가', '저가'], axis=1, inplace=True)

        # ファイル名: 株式名_コード_yyyy-mm-dd~yyyy-mm-dd.csv
        directory = '../tmp/mg-csv'
        os.makedirs(directory, exist_ok=True)
        filename = stock_name + '_' + code + '_' + str_start_date + '~' + datetime.now().strftime('%Y-%m-%d')
        # CSVファイル出力
        df.to_csv(directory + '/{filename}.csv'.format(filename=filename), index=False)
        logger.info('{filename}.csv'.format(filename=filename))
    except Exception:
        msg_type = '[csv file print failed] '
        msg = 'csv 파일 출력에 실패하였습니다.'  # csvファイル出力を失敗しました。
        raise StockCrawlingException(msg_type, msg)


# 株式名取得
def stock_name_by_code(code, header):
    try:
        # FIXME BeautifulSoup練習
        url = 'https://finance.naver.com/item/sise.naver?code={code}'.format(code=code)
        res = requests.get(url, headers=header)
        soup = BeautifulSoup(res.text, 'lxml')
        stock_name = soup.select_one('div.wrap_company>h2>a').text
        return stock_name
    except Exception:
        msg_type = '[stock name failed]'
        msg = '주식 종목명 취득에 문제가 발생했습니다.'  # 株式名の取得に問題が発生しました。
        raise StockCrawlingException(msg_type, msg)


def validation_check(code, str_start_date):
    logger.info(f'[start] validation check start (code={code}, start_date={str_start_date})'
                .format(code=code, str_start_date=str_start_date))

    code_reg = re.compile(r'\d{6}$')
    start_date_reg = re.compile(r'([12]\d{3})-(0\d|1[0-2])-([0-2]\d|3[01])$')
    msg_type = '[validation check error] '

    if not code_reg.match(code):
        msg = '종목코드를 확인해 주세요. 입력예: 005930'  # 銘柄コードを確認してください。入力例: 005930
        raise StockCrawlingException(msg_type, msg)  # java : throw

    if not start_date_reg.match(str_start_date):
        msg = '취득개시일을 확인해 주세요. 입력예: 2020-01-01'  # 取得開始日を確認してください。入力例 2020-01-01
        raise StockCrawlingException(msg_type, msg)

    # 취득개시일 현재날짜보다 미래면 크롤링 불가능
    start_date = datetime.strptime(str_start_date, '%Y-%m-%d')
    today_date = datetime.today().date()
    if start_date.date() > today_date:
        msg = '취득개시일을 확인해 주세요. 취득개시일이 현재 날짜보다 미래입니다.'  # 取得開始日を確認してください。取得開始日が現在の日付より未来です。
        raise StockCrawlingException(msg_type, msg)

    logger.info('[end] validation check finished')
    return start_date


def execute():
    # 실행
    logger.info('[start] stock crawling execute')
    try:
        code = input("code? ")
        str_start_date = input("start date? ")
        # 銘柄コード、取得開始日
        # code = sys.argv[1]
        # str_start_date = sys.argv[2]

        # validation check
        start_date = validation_check(code, str_start_date)

        # 入力された日付のフォーマット変換 yyyy-mm-dd -> yyyy.mm.dd
        converted_start_date = start_date.strftime('%Y.%m.%d')

        # Header情報が要求される
        header = {'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                                'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.82 Safari/537.36'}
        url = 'https://finance.naver.com/item/sise_day.naver?code={code}'.format(code=code)
        res = requests.get(url, headers=header)

        # res.status_code
        html = res.text
        soup = BeautifulSoup(html, 'lxml')

        # データの存在チェック
        if not soup.select_one('table>tr>td>span.tah.p10.gray03').text:  # テーブルの最初データ
            msg_type = '[invalid stock code] '
            msg = '입력한 종목코드에 해당하는 데이터가 없습니다.'  # 入力したコードに該当するデータが存在しないです。
            raise StockCrawlingException(msg_type, msg)
        else:
            # 存在する場合、株式名を取得
            stock_name = stock_name_by_code(code, header)

        # 全体ページ数を取得
        if not isinstance(soup.select_one('td.pgRR'), type(None)):
            last_page = int(soup.select_one('td.pgRR').a['href'].split('=')[-1])
        else:
            # 'pgRR'(最後ページ)がない場合、1ページのみ存在する
            last_page = 1

        logger.info('[start] 크롤링을 시작합니다. (종목명: ' + stock_name + ', 종목코드: ' + code + ')')  # クローリングを開始します。
        df = None
        df = crawling_stock_data(df, code, header, converted_start_date, last_page)
        logger.info('[end] 크롤링이 완료되었습니다. (종목명: ' + stock_name + ', 종목코드: ' + code + ')')  # クローリングを完了しました。

        # チャート出力
        logger.info('[start] 차트 출력을 시작합니다.')  # チャート出力を開始します。
        # print_graph(df, code, stock_name, str_start_date)
        logger.info('[end] 차트 출력이 완료되었습니다.')  # チャート出力を完了しました

        # CSVファイル出力
        logger.info('[start] csv 파일 출력을 시작합니다.')  # csvファイル出力を開始します。
        print_csv(df, code, stock_name, str_start_date)
        logger.info('[end] csv 파일 출력이 완료되었습니다.')  # csvファイル出力を完了しました。

        # FIXME docker環境ではまだ確認出来てないのでコメントアウト
        logger.info('[start] insert data into Elasticsearch')  # ElasticSearchに保存を開始します。
        es = save_data(df, code, stock_name, str_start_date)
        logger.info('[end] successfully inserted into Elasticsearch')  # ElasticSearchに保存されました。
        # TODO dataを検索するメソッド
        search_data(es, code)
        logger.info('[end] stock crawling finished')
    except StockCrawlingException as se:
        logger.error(se)
    except Exception as e:
        # 予想外のエラーはtrace出力
        traceback.print_exc()
        logger.error(e)


if __name__ == '__main__':
    # ログ
    logger = loggerConfig.logger
    execute()
