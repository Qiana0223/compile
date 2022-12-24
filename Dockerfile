FROM ubuntu:focal

ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
  && apt-get install -y \
     libsqlite3-0 \
     libsqlite3-dev  \
     apt-utils \
     git \
     nano \
  && apt-get install -y \    
     build-essential \
     libssl-dev \
     python3-dev \
     python-pip-whl \
     python3-pip \
     libleveldb-dev \
     python3-setuptools \
     software-properties-common \
  && add-apt-repository -y ppa:ethereum/ethereum \
  && apt-get update \
  && apt-get install -y \
     solc 
RUN pip3 install solc-select
RUN solc-select install all
RUN  export PATH=/usr/local/bin:$PATH

COPY .  /opt/iccfwnc
RUN cd /opt/iccfwnc \
  && python3 setup.py install

WORKDIR /home/iccfwnc




