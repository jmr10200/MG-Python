## Python 을 이용한 네이버 일별 주가데이터 크롤링



### 구현 내용
```
종목코드와 취득개시일을 입력하면, 취득개시일부터 실행일 현재까지의 종가와 거래량을 취득하여 csv파일을 출력합니다.
```

### 실행 방법
```
* 커맨드 창에서 stockCrawling01.py 종목코드 취득개시일(yyyy-mm-dd)
* 입력예 : 삼성전자, 2020년 1월 1일부터 현재시간까지 일별 주가 데이터 취득
  * stockCrawling01.py 005930 2020-01-01
```

### 출력결과 확인
```
* 이하의 형식으로 출력됩니다.
  * ../tmp/mg-csv/종목명(종목코드)_yyyy-mm-dd~yyyy-mm-dd.csv
```

```
(참고)
* 로그 출력
  * ../tmp/mg-log/stock_yyyy-mm-dd.log
```
