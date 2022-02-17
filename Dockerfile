# base Image 지정 : ubuntu
FROM ubuntu:18.04
RUN apt-get -y update
# by jmr
MAINTAINER jmr

# python
RUN apt-get -y install python3.7 python3-pip
#RUN pip3 install --upgrade pip

# 컨테이너 실행 전 수행할 쉘 명령어
RUN mkdir -p /opt/mgpython
WORKDIR /opt/mgpythom
COPY . .
RUN pip3 install -r requirements.txt

# 컨테이너가 시작되었을 때 실행할 쉘 명렁어
# 도커파일 내 1회만 실행할 수 있음
EXPOSE 8082
# FIXME 실행
CMD ["python3", "stockCrawling01.py"]
