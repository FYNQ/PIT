import os
import json
import subprocess
import conf
import check_series
import write_data as wd

linux_src = conf.LINUX_SRC
list_jobs = './jobs.txt'
res_loc = conf.BUILD_DIR + '../results/'
list_done = res_loc + 'done.json'

if not os.path.isdir(res_loc):
    os.makedirs(res_loc)

def read_tags(fname):
    f = open(fname)
    _tags = f.readlines()
    tags = [t.rstrip() for t in _tags]
    f.close()
    return tags

def do_cmd(cmd, path):
    process = subprocess.Popen(cmd, cwd=path, shell=True,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    out, err = process.communicate()
    process.wait()
    res = out.decode("utf-8")
    print res

def get_tags(path):
    _tags = do_cmd('git tag --sort=v:refname', linux_src).split('\n')
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

    for tag in tags:
        if tag.startswith(job) and not 'rc' in tag:
            todo_tags.append(tag)

    return todo_tags

tags = get_tags(linux_src)
jobs = open(list_jobs).read().split('\n')
f = open(list_done, 'r')
jobs_done = json.load(f)
f.close()

for _job in jobs:
    if len(_job) == 0 or _job.startswith("#"):
        continue
    print(_job)
    job = _job.split(' ')[0]
    kconfig = _job.split(' ')[1]
    arch = _job.split(' ')[2]
    prefix = res_loc + '/' + job + '_'
    wd.wr_results(job, jobs_done, kconfig, prefix)


