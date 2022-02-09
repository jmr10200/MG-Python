"""
네이버 일별 주가(종가) 및 거래량 크롤링
회사코드(명), 취득 개시일을 입력받아 현재 날짜까지의 주가 및 거래량을 취득하여 csv 파일을 출력

parameter : 회사코드, 취득개시일
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
        msg = '페이지 데이터 취득에 실패하였습니다.'
        raise StockCrawlingException(msg_type, msg)
    return None


def crawling_stock_data(df, code, header, start_date, last_page):
    try:
        pg = 1
        while pg <= last_page:
            logger.info(str(pg) + '페이지 데이터를 추출합니다.')
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
        df = df.astype({'종가': 'int', '시가': 'int', '고가': 'int', '저가': 'int', '거래량': 'int'})
        return df
    except Exception:
        msg_type = '[crawling stock data failed] '
        msg = '데이터 추출에 실패하였습니다.'
        raise StockCrawlingException(msg_type, msg)
    # return None


def print_graph(df, code, stock_name):
    # 날짜 오름차순 정렬
    graph_df = df.sort_values(by='날짜').astype({'날짜':'datetime64[D]'})
    # 캔들 차트 객체 생성
    candle = plotly.graph_objs.Candlestick(
        x=graph_df['날짜'],
        open=graph_df['시가'],
        high=graph_df['고가'],
        low=graph_df['저가'],
        close=graph_df['종가'],
        increasing_line_color='red',  # 상승봉
        decreasing_line_color='blue'  # 하락봉
    )
    # 히스토그램 (거래량) 객체 생성
    volume_h = plotly.graph_objs.Bar(x=graph_df['날짜'], y=graph_df['거래량'])
    # figure 생성
    figure = plotly.subplots.make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.02)
    # 첫번째 캔들 차트
    figure.add_trace(candle, row=1, col=1)
    # 두번째 거래량 차트
    figure.add_trace(volume_h, row=2, col=1)
    # TODO 차트 레이아웃 수정
    figure.update_layout(
        title=stock_name + ' (' + code + ') 차트',
        title_x=0.5,
        title_xanchor='center',
        title_font_size=15,
        yaxis1=dict(
            title='주가',
            tickformat=','
        ),
        xaxis2=dict(
            title='날짜',
            rangeslider_visible=True,
            tickformat='%Y-%m-%d'
        ),
        yaxis2=dict(
            title='거래량',
            tickformat=',',
        ),
        xaxis1_rangeslider_visible=False
    )
    figure.show()


def print_csv(df, code, stock_name, str_start_date):

    try:
        # 필요없는 열 삭제 (axis 값이 0이면 행, 1이면 열)
        df.drop(['전일비', '시가', '고가', '저가'], axis=1, inplace=True)

        # 파일명: 종목명(종목코드)_yyyy-mm-dd~yyyy-mm-dd.csv
        directory = '../tmp/mg-csv'
        os.makedirs(directory, exist_ok=True)
        filename = stock_name + '(' + code + ')_' + str_start_date + '~' + datetime.now().strftime('%Y-%m-%d')
        # CSV 파일 출력.
        df.to_csv(directory + '/{filename}.csv'.format(filename=filename), index=False)
        logger.info('{filename}.csv'.format(filename=filename))
    except Exception:
        msg_type = '[csv file print failed] '
        msg = 'csv 파일 출력에 실패하였습니다.'
        raise StockCrawlingException(msg_type, msg)


def stock_name_by_code(code, header):
    try:
        # FIXME 키움 API 등 증권사 API 가 존재하지만, BeautifulSoup 연습을 위해
        url = 'https://finance.naver.com/item/sise.naver?code={code}'.format(code=code)
        res = requests.get(url, headers=header)
        soup = BeautifulSoup(res.text, 'lxml')
        stock_name = soup.select_one('div.wrap_company>h2>a').text
        return stock_name
    except Exception:
        msg_type = '[stock name failed]'
        msg = '주식 종목명 취득에 문제가 발생했습니다.'
        raise StockCrawlingException(msg_type, msg)


def validation_check(code, str_start_date):
    logger.info(f'[start] validation check start (code={code}, start_date={str_start_date})'
                .format(code=code, str_start_date=str_start_date))

    code_reg = re.compile(r'\d{6}$')
    start_date_reg = re.compile(r'([12]\d{3})-(0\d|1[0-2])-([0-2]\d|3[01])$')
    msg_type = '[validation check error] '

    if not code_reg.match(code):
        msg = '종목코드를 확인해 주세요. 입력예: 005930'
        raise StockCrawlingException(msg_type, msg)  # java : throw

    if not start_date_reg.match(str_start_date):
        msg = '취득개시일을 확인해 주세요. 입력예: 2020-01-01'
        raise StockCrawlingException(msg_type, msg)

    # 취득개시일 현재날짜보다 미래면 크롤링 불가능
    start_date = datetime.strptime(str_start_date, '%Y-%m-%d')
    today_date = datetime.today().date()
    if start_date.date() > today_date:
        msg = '취득개시일을 확인해 주세요. 취득개시일이 현재 날짜보다 미래입니다.'
        raise StockCrawlingException(msg_type, msg)

    logger.info('[end] validation check finished')
    return start_date


def execute():
    # 실행
    logger.info('[start] stock crawling execute')
    try:
        # 종목코드, 취득개시일 입력받기
        code = sys.argv[1]
        str_start_date = sys.argv[2]

        # validation check
        start_date = validation_check(code, str_start_date)

        # 입력받은 날짜 포맷 변환 yyyy-mm-dd -> yyyy.mm.dd
        converted_start_date = start_date.strftime('%Y.%m.%d')

        # 일별 시세 페이지는 헤더 정보 요구
        header = {'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                                'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.82 Safari/537.36'}
        url = 'https://finance.naver.com/item/sise_day.naver?code={code}'.format(code=code)
        res = requests.get(url, headers=header)

        # res.status_code
        html = res.text
        soup = BeautifulSoup(html, 'lxml')

        # 종목코드 데이터 존재 체크
        if not soup.select_one('table>tr>td>span.tah.p10.gray03').text:  # 테이블의 첫번째 데이터
            msg_type = '[invalid stock code] '
            msg = '입력한 종목코드에 해당하는 데이터가 없습니다.'
            raise StockCrawlingException(msg_type, msg)
        else:
            # 존재시 종목명 취득, 키움 API 가 있지만, 크롤링 연습차..
            stock_name = stock_name_by_code(code, header)

        # 전체 페이지 수 계산
        if not isinstance(soup.select_one('td.pgRR'), type(None)):
            last_page = int(soup.select_one('td.pgRR').a['href'].split('=')[-1])
        else:
            # 'pgRR'(맨뒤)가 없으면 1페이지만 존재
            last_page = 1

        logger.info('[start] 크롤링을 시작합니다. (종목명: ' + stock_name + ', 종목코드: ' + code + ')')
        df = None
        df = crawling_stock_data(df, code, header, converted_start_date, last_page)
        logger.info('[end] 크롤링이 완료되었습니다. (종목명: ' + stock_name + ', 종목코드: ' + code + ')')

        # 그래프 출력
        print_graph(df, code, stock_name)

        # CSV 파일 출력
        logger.info('[start] csv 파일 출력을 시작합니다.')
        print_csv(df, code, stock_name, str_start_date)
        logger.info('[end] csv 파일 출력이 완료되었습니다.')

        logger.info('[end] stock crawling finished')
    except StockCrawlingException as se:
        logger.error(se)
    except Exception as e:
        # 예상하지 못한 에러는 trace 출력
        traceback.print_exc()
        logger.error(e)


if __name__ == '__main__':
    # 로그
    logger = loggerConfig.logger
    execute()
