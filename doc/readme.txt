#PIT DOCUMENTATION


# Native install

apt-get install --assume-yes software-properties-common bc\
    libjson-c-dev moreutils vim screen python3-pip passwd locales \
    bash git openssh-server libiberty-dev sudo gcc g++ libelf-dev patch


pip3 install dpath python-dateutil patch

## x86 and x86_64

apt-get install --assume-yes  gcc-6-plugin-dev

## ARM

set -x && apt-get install --assume-yes gcc-6-plugin-dev-arm-linux-gnueabihf \
    gcc-arm-linux-gnueabihf lzop;

## ARM64

set -x && apt-get install --assume-yes gcc-aarch64-linux-gnu \
    gcc-6-plugin-dev-aarch64-linux-gnu lzop;

## powerpc and powerpc64

apt-get install --assume-yes gcc-6-plugin-dev-powerpc64-linux-gnu \
    gcc-6-multilib-powerpc64-linux-gnu

ln -s /usr/bin/powerpc64-linux-gnu-gcc-6 /usr/bin/powerpc64-linux-gnu-gcc; fi


# Container install

$ export LINUX_SRC=PATH_TO_LINUX_STABLE_SRC

For ssh login use: user/nopasswd

## x86 and x86_64

docker-compose build  --no-cache pit_arm64 -e LINUX_SRC=/PATH_TO_LINUX_SRC

Port to use: 1233

## ARM64

docker-compose build  --no-cache pit_arm64

Port to use: 1231

## ARM

docker-compose build  --no-cache pit_arm

Port to use: 1231

## powerpc and powerpc64

docker-compose build  --no-cache pit_powerpc

Port to use: 1230

# Adaptions and preparations

Enter to /home/user/src and git clone /home/use/linux-src

and set LINUX_SRC path in conf.py.



# Kernel config

Use this schema: NAME_defconfig


# Use check_series.py

$ python3 check_series.py -f v4.13 -l v4.14.67 -k ppc_men_defconfig -a powerpc

-f ... start kernel tag version
-l ... last kernel tag version
-k ... kernel kconfig
-a ... architecture definition

# tags.txt file

On each git pull in the linux source directory the tags.txt file needs to
be updated.


# Results

Go to /home/user/build/results

