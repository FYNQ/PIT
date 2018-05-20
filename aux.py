import os
import sort_patches as sortp
from os import listdir
import patch



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




