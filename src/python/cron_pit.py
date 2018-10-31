import os
import json
import subprocess
import conf


linux_src = conf.LINUX_SRC

exec_new_tag = True
list_jobs = './jobs.txt'
list_done = './done.json'


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
#git_pull(linux_src)
tags = get_tags(linux_src)

jobs = open(list_jobs).read().split('\n')
print(jobs)
f = open(list_done, 'r')
jobs_done = json.load(f)
f.close()

#jobs_done = open(list_done).read().split('\n')


for _job in jobs:
    if len(_job) == 0:
        continue

    job = _job.split(' ')[0]
    kconfig = _job.split(' ')[1]
    if not job in jobs_done.keys():
        todo_tags = get_todo_tag(job, tags)
        print("L: %s" % todo_tags)
        start_job(job, todo_tags[0], todo_tags[-1:], kconfig)
        jobs_done.update({job:todo_tags})
        print("x1: %s" % jobs_done)
        with open(list_done, 'w') as f:
            json.dump(jobs_done, f)

    if job in jobs_done.keys():
        todos = []
        jdone = jobs_done[job]
        last_job = jdone[-1:]
        todo_tags = get_todo_tag(job, tags)
        for todo_tag in todo_tags:
            if not todo_tag in jdone:
                todos.append(todo_tag)
        if len(todos) == 0:
            continue
        print("todos: %s" % todos)
        start_job(job, todos[0], todos[-1:][0], kconfig)
        done_lst = []
        with open(list_done, 'r') as f:
             done_lst = json.load(f)
        done_lst[job].extend(todos)
        with open(list_done, 'w') as f:
            json.dump(done_lst, f)


