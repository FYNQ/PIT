import os
import sys
import time
import json
import argparse
import logging
import multiprocessing.pool
#import create_report as cr
import conf
import aux
import build_utils
import checker

global logger


class NoDaemonProcess(multiprocessing.Process):
    # make 'daemon' attribute always return False
    def _get_daemon(self):
        return False

    def _set_daemon(self, value):
        pass

    daemon = property(_get_daemon, _set_daemon)


# We sub-class multiprocessing.pool.Pool instead of multiprocessing.Pool
# because the latter is only a wrapper function, not a proper class.
class MyPool(multiprocessing.pool.Pool):
        Process = NoDaemonProcess


parser = argparse.ArgumentParser(description='LK Patch Impact Tester')

parser.add_argument('-k', action='store', dest='kconfig',required=True,
                    help='kernel config')

parser.add_argument('-f', action='store', dest='first', required=True,
                    help='first git tag')

parser.add_argument('-l', action='store', dest='last', required=True,
                    help='last git tag')

parser.add_argument('-a', action='store', dest='arch', required=True,
                    help='arch flag, can be: x86, x86_64, arm, arm64, ppc')


parse = parser.parse_args()

job_lst = []
job_handle = []


def read_reqs(fname):
    req = {}
    f = open(fname)
    _tags = f.readlines()
    for t in _tags:
        l = t.strip().split(';')
        req.update({l[0]: l[1:]})
    return req



def read_tags(fname):
    f = open(fname)
    _tags = f.readlines()
    tags = [t.rstrip() for t in _tags]
    f.close()
    return tags


def compile_kernel(path_proj, linux_path, kconfig, arch, tag):
    logger = logging.getLogger('check_series')
    logger.info("Compile kernel in path: %s" % path_proj)
    build_utils.build_kernel(path_proj, linux_path, kconfig, arch, tag)


def data_job(tag, tag_nex, arch, path, path_nex):
    logger = logging.getLogger('check_series')
    logger.info("Start checker for tag: %s" % tag)

    worker = checker.worker(path, path_nex, tag, tag_nex, arch)

# multiprocessing pool version
def do_mp(first, last, kconfig, arch):
    flag_compile = False
    plg_arch = None
    # First run create build directory
    if not os.path.isdir(conf.BASE + "/build"):
        os.makedirs(conf.BASE + "/build")
    if not os.path.isdir(conf.BASE + "/build/report"):
        os.makedirs(conf.BASE + "/build/report")

    log_name = conf.BASE + "build/check_series_%s_%s.log" % (first, last)
    aux.setup_logger('check_series', log_name)
    logger = logging.getLogger('check_series')
    logger.info("Start check_series!")

    logger.info("check if plugin is compiled for arch: %s" % arch)
    if arch not in conf.ARCHS and arch != None:
        print("Wrong architecture!")
        print("Possible architectres are: %s" % ",".join(conf.ARCHS))
        return
    else:
        if os.path.isdir('../gcc_plugin/compiled4'):
            f = open("../gcc_plugin/compiled4")
            plg_info = f.read()
            plg_arch = plg_info.split(':')[0]
            if arch == None:
                arch = plg_arch
            print('old arch: %s new arch: %s' % (plg_arch, arch))
        else:
            flag_compile = True

        if plg_arch != arch or flag_compile == True:
            cc = conf.CC[arch]
            cmd = "make ARCH=%s CC=%s" % (arch, cc)
            print(cmd, conf.CPLUGIN_DIR)
            aux.do_cmd("make clean", conf.CPLUGIN_DIR, None)
            aux.do_cmd(cmd, conf.CPLUGIN_DIR, None)


    do_tags = []
    tags = read_tags("tags.txt")
    req = read_reqs('req_compiler.txt')
    append = False
    cnt = 0
    # case: v4.3 .. v4.4.1
    if first.split(".")[1] != last.split(".")[1] and ("-") not in first:
        for tag in tags:
            if tag == first:
                cnt += 1
            if cnt == 2:
                do_tags.append(tag)
            if tag == last:
                index = tags.index(tag)
                if index + 1 < len(do_tags):
                    do_tags.append(tags[index+1])
                break
    else:
        for tag in tags:
            if tag == first:
                append = True
            if append == True:
                do_tags.append(tag)
            if tag == last:
                append = False
                break

    # No tag found!
    if append == True:
        print("Please check if tags are valid!")
        return

    logger.info("Do tags: %s" % do_tags)
    do_tags.append(None)
    jobs_kernel = []
    for i in range(0, len(do_tags)-1):
        path_proj = "%sbuild/%s/%s/" % (conf.BASE, do_tags[i], kconfig)

        if not os.path.isdir(path_proj):
            os.makedirs(path_proj)

        path_linux = path_proj + 'linux-stable'

        # check if kernel has been exported
        if not os.path.isfile(path_proj + '/kernel_export'):
            path_linux = path_proj + 'linux-stable'
            aux.git_export(conf.LINUX_SRC, path_proj, do_tags[i], logger)
            aux.do_cmd("touch kernel_export", path_proj, logger)

        # create diff via patch_format
        if not os.path.isdir(path_proj + "/diffs"):
            os.makedirs(path_proj + "diffs")

            path_diffs = path_proj + "diffs"
            if do_tags[i+1] != None:
                aux.create_patch_series(do_tags[i], do_tags[i+1],
                                       conf.LINUX_SRC, path_diffs, logger)



        # check if kernel has been compiled already
        if not os.path.isfile(path_proj + "/kernel_compile"):
            jobs_kernel.append((path_proj, path_linux, kconfig, arch, tag))
        else:
            continue

        # checks requirements
        if do_tags[i] in req:
            logger.info("Tags %s has requirements: %s" %
                                        (do_tags[i], req[do_tags[i]]))

            aux.patch_req(path_proj + 'linux-stable/',
                            conf.BASE + '/src/patches/',
                            req[do_tags[i]], logger)

    pool = multiprocessing.Pool(conf.CPUs)
    res = pool.starmap(compile_kernel, jobs_kernel)
    pool.close()
    pool.join()
    fe_jobs = []

    for i in range(0, len(do_tags)-1):
        if do_tags[i+1] != None:
            logger.info("data: tag: %s next_tag: %s" % (do_tags[i], do_tags[i+1]))
            path_cur = "%sbuild/%s/%s/" % (conf.BASE, do_tags[i], kconfig)
            path_next = "%sbuild/%s/%s/" % (conf.BASE, do_tags[i+1], kconfig)
            fe_jobs.append((do_tags[i], do_tags[i+1], arch, path_cur, path_next))

    pool = MyPool(conf.CPUs)
    res = pool.starmap(data_job, fe_jobs)
    pool.close()
    pool.join()

    sum_summary = []
    sum_sha = []
    sum_fun = []

    for tag in do_tags[:-2]:
        if tag != None:
            rep_path = '%sbuild/%s/%s/' % (conf.BASE, tag, kconfig)
            with open(rep_path + 'summary_data.json') as f:
                    data_sum = json.load(f)
            with open(rep_path + 'sha_lst.json') as f:
                    data_sha = json.load(f)
            with open(rep_path + 'functions_data.json') as f:
                    data_fun = json.load(f)
            ver_date = data_sum['date']
            sum_summary.append((tag, ver_date, data_sum))
            sum_sha.append((tag, ver_date, data_sha))
            sum_fun.append((tag, ver_date, data_fun))

    base = "%sbuild/report/res_series_" % conf.BASE


    fname = base + "result_summary_%s_%s_%s_%s" % (first, last, arch, kconfig)
    with open(fname, 'w') as outfile:
        json.dump(sum_summary, outfile)

    fname = base + "result_sha_%s_%s_%s_%s" % (first, last, arch, kconfig)
    with open(fname, 'w') as outfile:
        json.dump(sum_sha, outfile)

    fname = base + "result_fun_%s_%s_%s_%s" % (first, last, arch, kconfig)
    with open(fname, 'w') as outfile:
        json.dump(sum_fun, outfile)


do_mp(parse.first, parse.last, parse.kconfig, parse.arch)
