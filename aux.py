import os
import subprocess
import mmap

import json
import logging
import sort_patches as sortp
import patch
import conf


def setup_logger(logger_name, log_file, level=logging.INFO):
    """Setup logger

    :param path: path for loggfile output
    :param level: logging level
    :name: logfile name
    :returns: logger reference
    """
    l = logging.getLogger(logger_name)
    formatter = logging.Formatter('%(asctime)s : %(message)s')
    fileHandler = logging.FileHandler(log_file, mode='w')
    fileHandler.setFormatter(formatter)
    streamHandler = logging.StreamHandler()
    streamHandler.setFormatter(formatter)

    l.setLevel(level)
    l.addHandler(fileHandler)
    l.addHandler(streamHandler)


def load(fpath, f_suffix):
    """Loads json file and return data

    :param base: base path
    :param fname: file name

    :returns: Data or None if file not exists or json cannot be read
    """

    result = {}
    f_lst = os.listdir(fpath)
    for name in f_lst:
        if name.startswith(f_suffix):
            fname = fpath + '/' + name
            with open(fname, 'r') as infile:
                data = json.load(infile)
            #f = open(fname)
            #data = json.load(data)
            result.update(data)

    return result


def do_cmd(cmd, path, logger):
    """execute a subprocess command

    :param cmd: command to execute
    :param path: Directory where command has to be executed
    :logger: For redirecting output to logger if logger != None
    :returns: No return value
    """
    process = subprocess.Popen(cmd, cwd=path, shell=True,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    process.wait()
    out, err = process.communicate()
    res = out.decode("utf-8")
    if logger != None:
        if path != None:
            logger.info("do cmd: %s in path: %s" % (cmd, path))
        else:
            logger.info("do cmd: %s" % (cmd))
        logger.info(res)
    else:
        print("do cmd: %s in path: %s" % (cmd, path))


    return res


def find_in_file(fname, commit):
    with open(fname, 'rb', 0) as file, \
        mmap.mmap(file.fileno(), 0, access=mmap.ACCESS_READ) as s:
        search_term = str.encode(commit)
        if s.find(search_term) != -1:
            return True
    return False


def find_commit(path, commit):
    files = os.listdir(path + '/')
    for fname in files:
        ret = find_in_file(path + '/' + fname, commit)
        if ret is True:
            return fname

    return False


def get_commit_time_sec(tag, path):
    """Get time in seconds when certain tag was created

    :param tag: linux source tag
    :param path: location path of source

    :returns: time in seconds
    """
    cmd = "git log -1 --pretty=format:\"%ct\" " + tag
    process = subprocess.Popen(cmd, cwd=path, shell=True,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    process.wait()
    out, err = process.communicate()
    t = int(out.decode('utf-8').rstrip('\n'))
    return t/3600


def git_make_fun_diff(linux_path, opath, f_tag, t_tag, line_start, line_end, \
                                                            cu, fun, logger):

    ofile = "%s/%s.diff" % (opath, fun)

    if not os.path.isdir(opath):
        os.makedirs(opath)

    if not os.path.isfile(ofile):

        cmd = ("git log %s..%s -L%d,%d:%s" %
            (f_tag, t_tag, line_start, line_end, cu))
        #print(cmd)
        #r = do_cmd(cmd, linux_path, logger)
        process = subprocess.Popen(cmd, cwd=linux_path, shell=True,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        process.wait()
        out, err = process.communicate()

        if out.decode('utf-8')  == "":
            print("function: %s removed" % fun)
            return True
        else:
            cmd = ("git log %s..%s -L%d,%d:%s > %s/%s.diff" %
                    (f_tag, t_tag, line_start, line_end, cu, opath, fun))
            print(cmd)
            process = subprocess.Popen(cmd, cwd=linux_path, shell=True,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            process.wait()
            out, err = process.communicate()
            return False



def mk_git_diff_funs(linux_repo, path, tag, next_tag, funs, logger):
    out_path = path + 'fun_diffs'
    if not os.path.isdir(out_path):
        os.makedirs(out_path)

    for fun in funs.keys():
        start = funs[fun]['start']
        end = funs[fun]['end']
        cu = funs[fun]['cu']
        #print('create git diff for function: %s' % fun)
        git_make_fun_diff(linux_repo, out_path, tag, next_tag,
                                    start, end, cu, fun, logger)


def get_hash(header):
    """Get commit hash of git patch

    :param header: header of commit

    :returns: commit sha
    """
    for n, _line in enumerate(header):
        line = _line.decode("utf-8").split(" ")
        next_line = header[n + 1].decode('utf-8')
        if next_line.split(" ")[0] == "Merge:":
            continue
        if line[0] == "commit":
            return line[1].rstrip('\n')
        elif line[0] == 'From':
            return line[1]

    return None


def get_patch_lst(path):
    """ Get dict of patches with patch file name as key

        :param path: base path where patches are located

        :returns: Dict of patches with the following fields:
            - items: items of a patch
            - commit: commit hash
            - patch: file name of patch
    """
    flist = listdir(path)
    patch_lst = []
    sortp.sort_nicely(flist)
    for fitem in flist:
        fname = path + fitem
        ppatch = patch.fromfile(fname)
        if isinstance(ppatch, bool):
            a = 0
        else:
            commit = get_hash(ppatch.items[0].header)
            patch_lst.append((commit,fitem))

    return patch_lst


def get_patches(path):
    patch_lst = {}

    flist = os.listdir(path)
    for fitem in flist:
        fname = path + fitem
        data = patch.fromfile(fname)
        patch_lst.update({fitem[:-5] : data })

    return patch_lst


def get_patch_lst_by_cu(path):
    """ Get dict of patches with compile units as key

        :param path: base path where patches are located

        :returns: Dict of compile units with the following fields:
            - items: items of a patch
            - commit: commit hash
            - patch: file name of patch
    """
    flist = os.listdir(path)
    patch_lst = {}
    patches_to_compare = []
    sortp.sort_nicely(flist)
    for fitem in flist:
        fname = path + fitem
        ppatch = patch.fromfile(fname)
        if isinstance(ppatch, bool):
            continue

        for item in ppatch.items:
            commit = get_hash(ppatch.items[0].header)
            cu_name = '/'.join(item.target.decode("utf-8").split('/')[1:])
            if cu_name not in patch_lst:
                patch_lst.update({cu_name: []})
            patch_lst[cu_name].append({"items": ppatch.items,
                                       "commit": commit,
                                       "patch": fitem})

    return patch_lst



def get_patches_fp(path):
    """ Get dict of patches with patch file name as key
        from git format-patch output

        :param path: base path where patches are located

        :returns: Dict of patches with the following fields:
            - items: items of a patch
            - commit: commit hash
            - patch: file name of patch
    """
    flist = os.listdir(path)
    patch_lst = {}
    sortp.sort_nicely(flist)
    for fitem in flist:
        fname = path + fitem
        ppatch = patch.fromfile(fname)
        patch_lst.update({fitem: []})
        if isinstance(ppatch, bool):
            patch_lst[fitem].append({
                                   "items"  : None,
                                   "commit" : None,
                                   "patch"  : fitem,
                                   #"cu"     : cu_name,
                                   })

        else:
            commit = get_hash(ppatch.items[0].header)
            patch_lst[fitem].append({
                                   "items"  : ppatch.items,
                                   "commit" : commit,
                                   "patch"  : fitem,
                                   #"cu"     : cu_name,
                                   })

    return patch_lst




