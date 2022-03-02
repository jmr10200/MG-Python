FROM python:3.7-slim-stretch
USER root

RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y
RUN apt-get -y install locales && \
    localedef -f UTF-8 -i ja_JP ja_JP.UTF-8
# locale : language_territory.codeset (ex)ko_KR.UTF-8, en_US.UTF-8
ENV LANG ja_JP.UTF-8
ENV LANGUAGE ja_JP:ja
ENV LC_ALL ja_JP.UTF-8
ENV TZ JST-9
ENV TERM xterm

RUN apt-get install -y vim less
RUN pip install --upgrade pip
RUN pip install --upgrade setuptools

COPY requirements.txt /opt/app/
COPY loggerConfig.py /opt/app/
COPY stockCrawling01.py /opt/app/
COPY stockCrawlingException.py /opt/app/
WORKDIR /opt/app
RUN pip install -r requirements.txt
