import os

VALIDATION = False

CWD = os.getcwd()
BASE = os.path.realpath(CWD + "/../../") + '/'
CPLUGIN = BASE + "src/gcc_plugin/pit_plugin.so"
CPLUGIN_DIR = BASE + "/src/gcc_plugin/"
LINUX_SRC = "/home/markus/work_ot/linux-stable/"
BUILD_DIR = BASE + "build/"


# compile param

CPUs = 4


# compiler

ARCHS = ['arm', 'arm64', 'x86', 'x86_64', 'powerpc', 'powerpc64']

CC = {
    'arm': '/usr/bin/arm-linux-gnueabihf-gcc',
    'arm64': '/usr/bin/aarch64-linux-gnu-gcc',
    'x86': '/usr/bin/gcc',
    'x86_64': '/usr/bin/gcc',
    'powerpc':'/usr/bin/powerpc64-linux-gnu-gcc-6',
    'powerpc64': '/usr/bin/powerpc64-linux-gnu-gcc-6'
}


