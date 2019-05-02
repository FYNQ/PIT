import os
import json
import subprocess
import conf
import check_series
import write_data as wd

linux_src = conf.LINUX_SRC

exec_new_tag = True
list_jobs = './jobs.txt'



res_loc = conf.BUILD_DIR + '../results/'
list_done = res_loc + 'done.json'

if not os.path.isdir(res_loc):
    os.makedirs(res_loc)


# do_cmd: subprocess call

def read_tags(fname):
    f = open(fname)
    _tags = f.readlines()
    tags = [t.rstrip() for t in _tags]
    f.close()
    return tags


def do_cmd(cmd, path, logger):
    process = subprocess.Popen(cmd, cwd=path, shell=True,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    out, err = process.communicate()
    process.wait()
    res = out.decode("utf-8")
    if logger != None:
        if path != None:
            logger.info("do cmd: %s in path: %s" % (cmd, path))
        else:
            logger.info("do cmd: %s" % (cmd))
        logger.info(res)
    else:
        print("do cmd: %s in path: %s" % (cmd, path))

    if process.returncode != 0:
        exit()
    return res

def git_pull(path):
    do_cmd('git pull', linux_src, None)

def get_tags(path):
    _tags = do_cmd('git tag --sort=v:refname', linux_src, None).split('\n')
    tags = _tags[_tags.index('v3.0'):-1]
    return tags


def get_todo_tag(job, tags):
    # e.g do tag v4.3
    # we need v4.2, rc tags, v4.3 tag and rest
    todo_tags = []
    start_tag = job.split('.')[0] + '.' + str(int(job.split('.')[1]) - 1)

    todo_tags.append(start_tag)
    # do rc tags
    for tag in tags:
        if tag.startswith(job) and 'rc' in tag:
            todo_tags.append(tag)

#    todo_tags.append(job)
    for tag in tags:
        if tag.startswith(job) and not 'rc' in tag:
            todo_tags.append(tag)

    return todo_tags



def start_job(job, from_tag, to_tag, kconfig):
    cmd = 'python3 check_series.py -k %s -f %s -l %s -a x86_64 &' % \
            (kconfig, from_tag, to_tag[0])
    print("Execute: %s" % cmd)
    cwd = os.getcwd()
    do_cmd(cmd, cwd, None)

# git pull to get new tags
git_pull(linux_src)
tags = get_tags(linux_src)

jobs = open(list_jobs).read().split('\n')
f = open(list_done, 'r')
jobs_done = json.load(f)
f.close()



for _job in jobs:
    if len(_job) == 0 or _job.startswith("#"):
        continue

    job = _job.split(' ')[0]
    kconfig = _job.split(' ')[1]
    arch = _job.split(' ')[2]
    prefix = res_loc + '/' + job.replace('.','_') + '_'

    if not job in jobs_done.keys():
        todo_tags = get_todo_tag(job, tags)
        start_tag = todo_tags[0]
        end_tag = todo_tags[-1:][0]
        done_lst.update({job:todo_tags})

    elif job in jobs_done.keys():
        todos = []
        jdone = jobs_done[job]
        cur_tags = get_todo_tag(job, tags)
        for todo_tag in cur_tags:
            if not todo_tag in jdone:
                todos.append(todo_tag)

        if len(todos) == 0:
            print("jipii nothing to do!")
            continue

        start_tag = jdone[-1:][0]
        end_tag = todos[-1:][0]

        with open(list_done, 'r') as f:
             done_lst = json.load(f)
        done_lst[job].extend(todos)
        with open(list_done, 'w') as f:
             json.dump(done_lst, f)


    print("First: %s  Last: %s" % (start_tag, end_tag))
    done_tags = check_series.do_mp(start_tag, end_tag, kconfig, arch)


    with open(list_done, 'w') as f:
        json.dump(done_lst, f)

    wd.wr_results(job, jobs_done, kconfig, prefix)

