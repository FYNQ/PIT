
# Dockerfile for PIC

# Build with:
# docker-compose build 

# Run with:
# docker-compose up

# user/passwort to login containter: user/nopasswd

# If you have a proxy cache activate and edit the line:
# echo 'Acquire::http { Proxy "http://192.168.2.42:3142"; }; ....
#
###############################################################################
#                                INSTALLATION
###############################################################################


FROM debian:stretch

#RUN  echo 'Acquire::http { Proxy "http://192.168.2.42:3142"; };' >> /etc/apt/     apt.conf.d/01proxy

ARG ARCH
ARG CC
ENV _ARCH=${ARCH}
ENV _CC=${CC}
ENV cmd="make ARCH=${_ARCH} CC=${_CC}"
RUN echo $cmd
RUN set -x \
 && apt-get update -qq

RUN if [ ${_ARCH} = "x86" ] ; then \
set -x && apt-get install --assume-yes  gcc-6-plugin-dev; fi
RUN if [ ${_ARCH} = "powerpc" ] ; then \
set -x && apt-get install --assume-yes gcc-6-plugin-dev-powerpc64-linux-gnu \
    gcc-6-multilib-powerpc64-linux-gnu; fi
RUN  if [ ${_ARCH} = "arm" ] ; then \
set -x && apt-get install --assume-yes gcc-6-plugin-dev-arm-linux-gnueabihf \
    gcc-arm-linux-gnueabihf lzop; fi
RUN if [ ${_ARCH} = "arm64" ] ; then \
set -x && apt-get install --assume-yes gcc-aarch64-linux-gnu \
    gcc-6-plugin-dev-aarch64-linux-gnu lzop; fi
RUN set -x && apt-get install --assume-yes software-properties-common bc\
    libjson-c-dev moreutils vim screen python3-pip passwd locales \
    bash git openssh-server libiberty-dev sudo gcc g++ libelf-dev patch
RUN set -x && apt-get clean
RUN pip3 install dpath python-dateutil patch
ENV TZ=Europe/Vienna
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone
RUN if [ ${_ARCH} = "powerpc" ] ; then \
    ln -s /usr/bin/powerpc64-linux-gnu-gcc-6 /usr/bin/powerpc64-linux-gnu-gcc; fi

RUN locale-gen en_US.UTF-8
RUN localedef -i en_US -f UTF-8 en_US.UTF-8
RUN useradd -p nopasswd user -s /bin/bash
RUN echo "user:nopasswd" | chpasswd && adduser user sudo
RUN mkdir -p /home/user/.ssh

ADD docker/info.txt /home/user/info.txt
ADD docker/sudoers /etc/sudoers
ADD docker/id_dsa  /home/user/.ssh
ADD docker/id_dsa.pub /home/user/.ssh
RUN git clone ../linux-stable

ADD . /home/user/src
RUN chown -R user:user /home/user

USER user
ENV HOME /home/user
ENTRYPOINT sudo service ssh restart && bash && tail -n 100 -f /home/user/info.txt
RUN cd /home/user/src/gcc_plugin && make clean
RUN cd /home/user/src/gcc_plugin && \ 
    export CC=${_CC} && export ARCH=${_ARCH} && make
