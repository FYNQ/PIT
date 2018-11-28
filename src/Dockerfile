
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



ARG SEL_ARCH
ARG SEL_CC
ARG SEL_CXX
ENV ARCH=${SEL_ARCH}
ENV CC=${SEL_CC}
ENV CXX=${SEL_CXX}
ENV cmd="make ARCH=${ARCH} CC=${SEL_CC}"
RUN echo $cmd

RUN set -x \
 && apt-get update -qq

RUN if [ ${ARCH} = "x86" ] ; then \
set -x && apt-get install --assume-yes  gcc-6-plugin-dev; fi
RUN if [ ${ARCH} = "powerpc" ] ; then \
set -x && apt-get install --assume-yes gcc-6-plugin-dev-powerpc64-linux-gnu \
    gcc-6-multilib-powerpc64-linux-gnu; fi
RUN  if [ ${ARCH} = "arm" ] ; then \
set -x && apt-get install --assume-yes gcc-6-plugin-dev-arm-linux-gnueabihf \
    gcc-arm-linux-gnueabihf g++-arm-linux-gnueabihf lzop; fi
RUN if [ ${ARCH} = "arm64" ] ; then \
set -x && apt-get install --assume-yes gcc-aarch64-linux-gnu \
    gcc-6-plugin-dev-aarch64-linux-gnu lzop; fi
RUN set -x && apt-get install --assume-yes software-properties-common bc\
    libjson-c-dev moreutils vim screen python3-pip passwd locales \
    bash git openssh-server libiberty-dev sudo gcc g++ libelf-dev patch bison \
    libssl-dev flex
RUN set -x && apt-get clean
RUN pip3 install dpath python-dateutil patch
ENV TZ=Europe/Vienna
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone
RUN if [ ${ARCH} = "powerpc" ] ; then \
    ln -s /usr/bin/powerpc64-linux-gnu-gcc-6 /usr/bin/powerpc64-linux-gnu-gcc; fi

RUN locale-gen en_US.UTF-8
RUN localedef -i en_US -f UTF-8 en_US.UTF-8
RUN useradd -p nopasswd user -s /bin/bash
RUN echo "user:nopasswd" | chpasswd && adduser user sudo
RUN mkdir -p /home/user/.ssh

ADD docker/info.txt /home/user/info.txt
ADD docker/sudoers /etc/sudoers

ADD . /home/user/src
RUN chown -R user:user /home/user

USER user
ENV HOME /home/user
RUN cd /home/user/src/gcc_plugin && make clean
RUN cd /home/user/src/gcc_plugin && make
ENTRYPOINT /home/user/src/entrypoint.sh
