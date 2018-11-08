
import argparse
import os
import argparse
import subprocess
import sys
import codecs
import logging
import json
from time import gmtime, strftime

import checker
import conf
import aux

parser = argparse.ArgumentParser(description='Linux kernel patch checker')

parser.add_argument('-k', action='store', dest='kconfig',
                            help='kernel config')

parser.add_argument('-p', action='store_false', dest='patch', required=False,
                            help='patch to verify')

parser.add_argument('-f', action='store', dest='first',
                            help='start git tag for series')

parser.add_argument('-l', action='store', dest='last', required=False,
                            help='end git tag for series')

parser.add_argument('-c', action='store', dest='commit', required=False,
                            help='check patch against commit, works only with -p option')

parser.add_argument('-a', action='store', dest='arch', required=False,
                            help='arch flag, can be: x86, x86_66, arm, arm64')

CFLAGS_PPC = ' -Wno-array-bounds -Wno-unused-const-variable '


def version_check(tag, linux_path):
    if aux.is_tag_bef(tags, tag, "v4.0") == True:
        fname = "%s/src/Makefile.diff" % conf.BASE
        if aux.is_patched(linux_path, fname) == 0:
            print("Patch Makefile")
            cmd = "patch -p1<%s" % fname
            aux.do_cmd(cmd, linux_path, None)
    #compiler header

def build_kernel(proj_path, linux_path, kconfig, arch, tag):
    """ Used to build a build kernel in a certain path with a certain
        kernel configuration and architecture

    :param proj_path: root project path folder (something like:
                      build/kernel_version/kernel_config)
    :param linux_path: proj_path + linux-stable
    :param kconfig: linux kernel configuration file name
    :param arch: kernel architecture

    :returns: No return value
    """

    logger_name = "kernel_compile_%s" % tag
    aux.setup_logger(logger_name, proj_path + "/check_series.log")
    logger = logging.getLogger(logger_name)

    _cmd = 'make clean'
    aux.do_cmd(_cmd, linux_path, logger)

    logger.info("make %s" % kconfig)

    if arch == 'x86' or arch == 'x86_64':
        cmd = "cp %s/src/kconfigs/%s  %s/arch/x86/configs/" % \
                    (conf.BASE, kconfig, linux_path)
        aux.do_cmd(cmd, linux_path, logger)
        cmd = "make %s" % (kconfig)

    elif arch == 'arm':
        cmd = "cp %s/src/kconfigs/%s  %s/arch/arm/configs/" % \
                    (conf.BASE, kconfig, linux_path)
        aux.do_cmd(cmd, linux_path, logger)
        cmd = "make ARCH=arm %s" % (kconfig)

    elif arch == 'arm64':
        cmd = "cp %s/src/kconfigs/%s  %s/arch/arm64/configs/" % \
                    (conf.BASE, kconfig, linux_path)
        aux.do_cmd(cmd, linux_path, logger)
        cmd = "make ARCH=arm64 %s" % (kconfig)

    elif arch == 'powerpc' or arch == 'powerpc64':
        cmd = "cp %s/src/kconfigs/%s  %s/arch/powerpc/configs/" % \
                    (conf.BASE, kconfig, linux_path)
        aux.do_cmd(cmd, linux_path, logger)
        cmd = "make ARCH=%s %s" % (arch, kconfig)

    aux.do_cmd(cmd, linux_path, logger)
    aux.fix_utf("c",  linux_path)
    aux.fix_utf("h",  linux_path)
    aux.do_cmd('make clean', linux_path, logger)

    if os.path.isdir(proj_path + 'gcc_output'):
        aux.do_cmd("rm -rf %s" % proj_path + 'gcc_output/*', proj_path, logger)

    if arch == 'x86' or arch == 'x86_64':
        aux.do_cmd('make ' + kconfig, linux_path, logger)
        cmd = 'make -j1 CC=\'gcc -fplugin=' + conf.CPLUGIN
        cmd = cmd + ' -fplugin-arg-pit_plugin-log=' + proj_path + 'gcc_output '
        cmd = cmd + ' -fplugin-arg-pit_plugin-base=' + linux_path + "\'"
        print(cmd)
        aux.do_cmd(cmd, linux_path, logger)
        aux.do_cmd("touch kernel_compile", proj_path, logger)
    else:
        # make config
        _cmd = 'make -j1 ARCH=%s ' % arch
        aux.do_cmd(_cmd + kconfig, linux_path, logger)
        # assemble compile make statement
        # Todo powerpc: create link in d cker so we can remove this section
        if arch == 'powerpc' or arch == 'powerpc64':
            compiler = ' CROSS_COMPILE=' + "-".join(conf.CC[arch].split('-')[:-2])
            cmd = _cmd + compiler
        else:
            compiler = ' CROSS_COMPILE=' + "-".join(conf.CC[arch].split('-')[:-1])
            cmd = _cmd + compiler


        cmd += '- CFLAGS_KERNEL=\'' + CFLAGS_PPC + '-fplugin=' + conf.CPLUGIN

        cmd = cmd + ' -fplugin-arg-pit_plugin-log=' + proj_path + 'gcc_output '
        cmd = cmd + ' -fplugin-arg-pit_plugin-base=' + linux_path + "\'"
        aux.do_cmd(cmd, linux_path, logger)
        aux.do_cmd("touch kernel_compile", proj_path, logger)

    aux.do_cmd('make clean', linux_path, logger)


