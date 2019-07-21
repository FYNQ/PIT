import os
import sys
import time
import json
import argparse
import logging
from multiprocessing import Pool
import math
import conf
import aux
import build_utils
import checker
from shutil import rmtree

global logger


parser = argparse.ArgumentParser(description='LK Patch Impact Tester')

parser.add_argument('-k', action='store', dest='kconfig',required=True,
                    help='kernel config')

parser.add_argument('-f', action='store', dest='first', required=True,
                    help='first git tag')

parser.add_argument('-l', action='store', dest='last', required=True,
                    help='last git tag')

parser.add_argument('-a', action='store', dest='arch', required=True,
                    help='arch flag, can be: x86, x86_64, arm, arm64, ppc')



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

def get_tags(path):
    _tags = aux.do_cmd('git tag --sort=v:refname', conf.LINUX_SRC, None).split('\n')
    tags = _tags[_tags.index('v3.0'):-1]
    return tags

def read_tags(fname):
    f = open(fname)
    _tags = f.readlines()
    tags = [t.rstrip() for t in _tags]
    f.close()
    return tags

#def find_tag_item(versions, base):
#    for vers in versions:
#        if base in list(vers.keys())[0]:
#            return vers[base]

def prep_tags(tags):
    idx = tags.index('v3.2')
    tags = tags[idx:]
    main_vers = {}
    for tag in tags:
        if not 'rc' in tag:
            if len(tag.split('.'))== 2:
                main_vers.update({tag:[]})
                start_tag = tag.split('.')[0]+'.' + str(int(tag.split('.')[1])-1)
                main_vers[tag].append(start_tag)

    for i, tag in enumerate(tags):
        f = False
        if 'rc' in tag:
            base = tag.split('-')[0]
            #New RC kernels are not considered
            if base in main_vers.keys():
                main_vers[base].append(tag)
        if i + 1 < len(tags):
            if 'rc' in tag and not 'rc' in tags[i+1]:
                main_vers[base].append(base)



    for tag in tags:
        if not 'rc' in tag and len(tag.split('.')) == 3:
            n = tag.split('.')
            base = '.'.join(n[0:2])
            main_vers[base].append(tag)

    return main_vers

def get_todo_tags(first, last, tags):
    # e.g do tag v4.3
    # we need v4.2, rc tags, v4.3 tag and rest
    todo_tags = []
    if len(first.split('.')) == 2 and not 'rc' in first:
        first_is_base = True
    else:
        first_is_base = False

    if first.split('.')[:2] == last.split('.')[:2]:
        same_base = True
    else:
        same_base = False

    #if first_is_base and last_is_base:
    if not 'rc' in first:
        if same_base == True:
            n = first.split('.')
            base = '.'.join(n[0:2])
        else:
            if 'rc' in last:
                base = last.split('-')[0]
            else:
                n = last.split('.')
                base = '.'.join(n[0:2])

    else:
        base = first.split('-')[0]

    if first_is_base and same_base:
        t = tags[base]
        idx = tags[base].index(first)
        for tag in tags[base][idx:]:
            todo_tags.append(tag)
            if tag == last:
                break
    elif first_is_base:
        for tag in tags[base]:
            todo_tags.append(tag)
            if tag == last:
                break


    if first_is_base == False and same_base:
        idx = tags[base].index(first)
        for tag in tags[base][idx:]:
            todo_tags.append(tag)
            if tag == last:
                break

    #print("Tags todo: %s" % todo_tags)
    return todo_tags



def compile_kernel(path_proj, linux_path, kconfig, arch, tag, is_last):
    logger = logging.getLogger('check_series')
    logger.info("Compile kernel in path: %s" % path_proj)
    build_utils.build_kernel(path_proj, linux_path, kconfig, arch, tag)
    #if is_last == False:
    #    rmtree(linux_path)


def data_job(tag, tag_nex, arch, path, path_nex, comp_bef):
    logger = logging.getLogger('check_series')
    logger.info("Start checker for tag: %s %s %s" % (tag, tag_nex, comp_bef))
    worker = checker.worker(path, path_nex, tag, tag_nex, arch)



# multiprocessing pool version
def do_mp(first, last, kconfig, arch):
    print('do_mp: %s %s %s %s' % (first,last,kconfig,arch))
    num_cpus = conf.CPUs
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
    tags = get_tags(conf.LINUX_SRC)
    tags_a = prep_tags(tags)
    do_tags = get_todo_tags(first, last, tags_a)
    req = read_reqs('/home/user/src/python/req_compiler.txt')
    rnds = math.ceil(len(do_tags)/num_cpus)
    print('this takes %d rounds' % rnds)

    print(do_tags)
    for i in range(0, rnds):
        idx_start = num_cpus *i
        idx_end = num_cpus*i + num_cpus
        if idx_end > len(do_tags):
            idx_end = len(do_tags)
        jobs_compile = []
        jobs_compare = []
        print('-----------------')
        for j in range(idx_start, idx_end):
            print('compile do tag: %s' % do_tags[j])
            path_proj = "%sbuild/%s/%s/" % (conf.BASE, do_tags[j], kconfig)
            if os.path.isfile(path_proj + 'kernel_export'):
                print('already done!')
                continue

            if not os.path.isdir(path_proj):
                os.makedirs(path_proj)

            # export kernel
            path_linux = path_proj + 'linux-stable'
            aux.git_export(conf.LINUX_SRC, path_proj, do_tags[j], logger)
            aux.do_cmd("touch kernel_export", path_proj, logger)


            if j == idx_end-2:
                is_last = True
            else:
                is_last = False

            # checks requirements
            if do_tags[j] in req:
                logger.info("Tags %s has requirements: %s" %
                                            (do_tags[j], req[do_tags[j]]))

                aux.patch_req(path_proj + 'linux-stable/',
                                conf.BASE + '/src/patches/',
                                req[do_tags[j]], logger)


            job = (path_proj, path_linux, kconfig, arch, do_tags[j],  is_last)
            jobs_compile.append(job)

            if j + 1 == len(do_tags):
                continue

            # Leftover
            if j != 0 and idx_start == j:
                path_cur = "%sbuild/%s/%s/" % (conf.BASE, do_tags[j - 1], kconfig)
                path_next = "%sbuild/%s/%s/" % (conf.BASE, do_tags[j], kconfig)

                jobs_compare.append((do_tags[j-1], do_tags[j], arch, path_cur,\
                                path_next, False))


        pool = Pool(processes=num_cpus)
        res = pool.starmap(compile_kernel, jobs_compile)
        pool.close()
        pool.join()

        print('-----------------')
        for j in range(idx_start, idx_end):
            if j == len(do_tags) - 1:
                break
            print('analyze do tag: %i %s -> %s' % (j, do_tags[j], do_tags[j+1]))
            path_cur = "%sbuild/%s/%s/" % (conf.BASE, do_tags[j], kconfig)
            path_next = "%sbuild/%s/%s/" % (conf.BASE, do_tags[j+1], kconfig)

            path_diffs = path_cur + "diffs"
            if not os.path.isdir(path_diffs):
                os.makedirs(path_diffs)

                print('create diff for %s %s ' % (do_tags[j], do_tags[j+1]))
                aux.create_patch_series(do_tags[j], do_tags[j+1],
                                        conf.LINUX_SRC, path_diffs, logger)

            if j == idx_end - 1:
                continue

            jobs_compare.append((do_tags[j], do_tags[j+1], arch, path_cur,\
                                path_next, False))


        pool = Pool(processes=num_cpus)
        res = pool.starmap(data_job, jobs_compare)
        pool.close()
        pool.join()


    return do_tags


if __name__== "__main__":
    parse = parser.parse_args()
    done_tags = do_mp(parse.first, parse.last, parse.kconfig, parse.arch)

