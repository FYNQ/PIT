import os
import subprocess
import mmap
import codecs
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
        print("Subprocess failed!")
        print("%s" % cmd)
        print("%s" % res)
        exit()
    return res


def find_in_file(fname, commit):
    if os.stat(fname).st_size == 0:
        False
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

    out, err = process.communicate()
    process.wait()
    t = int(out.decode('utf-8').rstrip('\n'))
    return t/3600


def git_make_fun_diff(linux_path, opath, f_tag, t_tag, line_start, line_end, \
                                                            cu, fun, logger):

    ofile = "%s/%s.diff" % (opath, fun)

    if not os.path.isdir(opath):
        os.makedirs(opath)

    if not os.path.isfile(ofile):
        cmd = ("git log %s..%s -L%d,%d:%s > %s/%s.diff" %
                (f_tag, t_tag, line_start, line_end, cu, opath, fun))

        process = subprocess.Popen(cmd, cwd=linux_path, shell=True,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = process.communicate()
        process.wait()
        return True



def mk_git_diff_funs(linux_repo, path, tag, next_tag, funs, logger):
    out_path = path + 'fun_diffs'
    if not os.path.isdir(out_path):
        os.makedirs(out_path)

    for fun in funs.keys():
        start = funs[fun]['start']
        end = funs[fun]['end']
        cu = funs[fun]['cu']
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

def git_export(src, dst, tag, logger):
    cmd = "git archive --format=tar.gz %s > %s/%s.tar.gz" % (tag, dst, tag)
    do_cmd(cmd, src, logger)

    if not os.path.isdir(dst + '/linux-stable'):
        os.makedirs(dst + '/linux-stable')

    cmd = "tar -xf %s/%s.tar.gz -C %s/linux-stable" % (dst, tag, dst)
    do_cmd(cmd, dst , logger)

    cmd = "rm %s/%s.tar.gz" % (dst,tag)
    do_cmd(cmd, dst, logger)


def create_patch_series(from_tag, to_tag, path, opath, logger):
    """git format-patch implementation

    :param from_tag: starting tag
    :param to_tag: end tag
    :param path: source path location
    :param opath: output path where diffs has to be stored
    :param logger: logger reference in case stdout output needs to be logged

    :returns: No return value
    """
    cmd = "git format-patch %s..%s -o %s > /dev/null" % (from_tag, to_tag, opath)
    do_cmd(cmd, path, logger)
    fix_utf("patch", opath)




def do_fix(fpath, line):
    """ Fix files with non utf8 character found by cmd line tool isutf

    :param fpath: base path
    :param fname: line number with non utf8 compliant character

    :returns: Data or None if file not exists or json cannot be read
    """
    fname = line[0]
    if len(fname) > 0:
        print("fix utf-8: %s" % (fpath + fname[1:-1]))
        fin = codecs.open(fpath + fname[1:-1], 'r',
                        encoding='utf-8', errors='replace')
        inbuf = fin.read()
        fin.close()
        fout = codecs.open(fpath + fname[1:-1], 'w',
                           encoding='utf-8', errors='replace')
        fout.write(inbuf)
        fout.close()


def fix_utf(ftype, fpath):
    """Thanx do some stupid developers using non utf-8 characters we have to \
       check sources for non utf-8 characters

    :param ftype: normaly .c and .h files are scanned
    :param fpath: base path of the linux kernel source

    :returns: No return value
    """
    cmd = "find -iname \"*." + ftype + "\"  -not -path .git | xargs isutf8"
    process = subprocess.Popen(cmd, cwd=fpath, shell=True,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)

    # wait for the process to terminate
    out, err = process.communicate()
    process.wait()
    for line in out.decode('utf-8').split('\n'):
        do_fix(fpath, line.split(' '))
    errcode = process.returncode


def is_patched(path, patch_name):
    """Check if file patched by patch with patch_name

    :param path: base path of source
    :param patch_name: file name of patch

    :returns: 1 not patched, 0 patched
    """
    cmd = "patch -N --dry-run --silent -p1<%s" % patch_name
    process = subprocess.Popen(cmd, cwd=path, shell=True, stdout=subprocess.PIPE)
    out, err = process.communicate()
    process.wait()
    return (process.returncode)


def patch_req(path, req_path, reqs, logger):
    """ Some kernel versions need to be patches before they can be compiled \
        with a news GCC version (gcc-6.3.0)

    :param path: base path
    :param rqu_patch: required patch

    :returns: No return value
    """
    for req in reqs:
        if len(req) > 0:
            patch_file = "%s/%s" % (req_path, req)
            res = is_patched(path, patch_file)
            if res != 1:
                print("not patched!")
                cmd = "patch -p1<%s/%s" % (req_path, req)
                do_cmd(cmd, path, logger)


