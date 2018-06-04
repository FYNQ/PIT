import codecs
import difflib
import pprint
import aux
import validation
pp = pprint.PrettyPrinter(indent=4)

VALIDATE = True
DEBUG = True

# Get function declaration sources to detect refactoring of functions
def get_src(src_path, len_def, suffix_len):
    """ Get source code from starting to ending bracket

    :param src_path: base location path
    :param len_def: dict with function names and function start/end information
                     in dict with file name information

    :param suffix_len: length of file information suffix

    :returns: dict of dict [compile_unit][function] with the corresponding
              source code (src key) and the location (start/end) information
              (info key)
    """
    data = {}
    for cu in len_def.keys():
        fname = src_path + cu[:-suffix_len]

        f = codecs.open(fname, "r", encoding='utf-8', errors='replace')

        lines = f.readlines()

        for fun in len_def[cu]:
            start = len_def[cu][fun]['start']
            end = len_def[cu][fun]['end']

            if cu[:-suffix_len] not in data:
                data.update({cu[:-suffix_len]: {}})

            src = [x.rstrip() for x in lines[start-1:end]]
            data[cu[:-suffix_len]].update({fun: {"src": src,
                                                 "info": len_def[cu][fun]}})
        f.close()

    return data


def get_file_for_fun(fun, data):

    for cu in data.keys():
        if fun in data[cu].keys():
            return cu

    return None


def fun_exists(data, fun):
    for cu in data.keys():
        if fun in data[cu]:
            return cu

    return None




def get_diff(a, b):
    """Get diff of two lists

    :param a: list of source lines a
    :param b: list of source lines b

    :returns:
        - lines_add: lines added
        - lines_rm: lines removed

    """
    add = list(difflib.ndiff(a, b))
    rm = list(difflib.ndiff(b, a))
    add_nr = 0
    rm_nr = 0
    line_add = []
    line_rm = []
    for line in add:
        code = line[:2]
        if code in ("  ", "+ "):
            add_nr += 1

        if code == "+ ":
            line_add.append((add_nr, line[2:].strip().replace('\t', '')))

    for line in rm:
        code = line[:2]
        if code in ("  ", "+ "):
            rm_nr += 1

        if code == "+ ":
            line_rm.append((rm_nr, line[2:].strip().replace('\t', '')))

    return line_add, line_rm


def get_removed_line(hunk):
    """ Return lines added and removed in two list separated list

    :param hunk: hunk of patch

    :returns:
        - res_add: lines added in hunk
        - res_rm: lines removed in hunk

    """
    res_rm = []
    for i in hunk.text:
        l = i.decode("utf-8").rstrip('\n')
        #if l.startswith('+'):
        #    res_add.append(l[1:])
        if l.startswith('-'):
            res_rm.append(l[1:])

    return res_rm


def hunk_decode(hunk):
    text = []
    for i in hunk.text:
        l = i.decode("utf-8").replace('\t', '').rstrip('\n').lstrip(' ')
        text.append(l)

    return text

def get_hunk_text(hunk):
    """ Return lines added and removed in two list separated list

    :param hunk: hunk of patch

    :returns:
        - res_add: lines added in hunk
        - res_rm: lines removed in hunk

    """
    res_add = []
    res_rm = []
    n = 0
    for i in hunk.text:
        l = i.decode("utf-8").replace('\t', '').rstrip('\n').lstrip(' ')
        if l.startswith('+'):
            res_add.append(l[1:])
        if l.startswith('-'):
            res_rm.append(l[1:])
        n += 1

    return res_add, res_rm, n


def get_mod_fun(fun, insn_cur, insn_next, insn_pre_cur, insn_pre_next,
                                            diffs, patches):

    """Get which patch modified a function

    :param cu: compile unit we are handling
    :param insn_cur:
    :param insn_next:
    :param diff: diff information of changed functions in the
               corresponding compilation unit
    :param patch_lst: dict of all patches, with patch name as key
    :param patch_lst_cu: dict of all patches, with compile unit as key

    :returns:
        - res: dict [cu][[commit], [patch_name], [fun], [add], [rm]]
        - lines_add: lines added total for compilation unit
        - lines_rm: lines removed total for compilatino unit
        - patches_app: patches applied
        - hunks_tot: hunks total
        - hunks_app: hunks applied

    """

    l_cnt_add_t = 0
    l_cnt_rm_t= 0
    l_cnt_add_f = 0
    l_cnt_rm_f = 0

    result = {}
    commits = []
    pp = pprint.PrettyPrinter(indent=4)

    if patches == False:
        print("FUN: %s" % fun)
        return

    for patch_it in patches:
        tname = patch_it.target.decode("utf-8")
        cu_name = '/'.join(tname. split('/')[1:])
        commit = aux.get_hash(patch_it.header)
        res = check_patch(fun, insn_cur, insn_next, insn_pre_cur, insn_pre_next,
                                        patch_it.hunks[0], diffs, commit)

        if res == None:
            continue
        #print("RES: %s" % str(res))
        l_cnt_add_t += res['add_cnt_t']
        l_cnt_rm_t += res['rm_cnt_t']

        l_cnt_add_f += res['add_cnt_f']
        l_cnt_rm_f += res['rm_cnt_f']

        commits.append(commit)

        if not fun in result.keys():
            result.update({fun:[]})

        result[fun].append(res)

    return result, l_cnt_add_t, l_cnt_rm_t, l_cnt_add_f, l_cnt_rm_f, commits


def line_skip(l):
    line = l[1]
    if line == '' or line.startswith('*') or line.startswith('/*') or \
        line.startswith('}'):
        return True
    else:
        return False


def compare_lines(start, end, d_data, p_data, insns, insns_pre, op, ldbg):
    line_cnt_false = 0
    line_cnt_true = 0
    line_data = []
    found = False
    idx = 0

    for i, line in enumerate(d_data):
        loc = start + i
        # and now iterate over patch info
        for j, s_line in enumerate(p_data[idx:]):
            if ldbg == True:
                print(s_line)
            pos = start + line[0] - 1
            if line[1] in s_line:
                if pos in insns or pos in insns_pre:
                    print("%s:T:%d:%s|" % (op, pos,line[1]))
                    idx = j
                    line_data.append((pos, True))
                    line_cnt_true += 1
                    break
                else:
                    skip = line_skip(line)
                    if skip == True:
                        continue
                    if not any(pos in ld for ld in line_data):
                        print("%s:F:%d:%s|" % (op, pos,line[1]))
                        idx = j
                        line_data.append((pos, False))
                        line_cnt_false += 1

    return line_data, line_cnt_true, line_cnt_false



def check_patch(fun, insn_cur, insn_next, insn_pre_cur, insn_pre_next,
                                hunk, diff, commit):
    commits = []
    it = None
    ldbg = False
    start_cur = diff["info_cur"]["start"]
    start_next = diff["info_next"]["start"]
    end_cur = diff["info_cur"]["end"]
    end_next = diff["info_next"]["end"]
    cu = diff["cu"]
    print("******************************************")
    if fun in validation.funs:
        print("\n\n**-------------------------------------------")
        print("cur  start: %d end: %d" % (start_cur, end_cur))
        print("next start: %d end: %d" % (start_next, end_next))
        print("cu: %s" % cu)

    l_add = []
    l_rm = []
    lines_add = []
    lines_rm = []
    l_cnt_add_t = 0
    l_cnt_rm_t = 0
    l_cnt_add_f = 0
    l_cnt_rm_f = 0


    add, rm, hunk_len = get_hunk_text(hunk)

    if fun in validation.funs:
        print("function: %s" % fun)

    if len(add) > 0:
        print("-------------------------------------------")
        data = diff['data']['+']
        lines_add, l_cnt_add_t, l_cnt_add_f  = compare_lines(start_next, end_next,
                                             data, add,
                                             insn_next[cu + '.stmt'],
                                             insn_pre_next[cu + '.pre'], '+', ldbg)

    if len(rm) > 0:
        print("-------------------------------------------")
        data = diff['data']['-']
        lines_rm, l_cnt_rm_t, l_cnt_rm_f = compare_lines(start_cur, end_cur,
                                           data, rm,
                                           insn_cur[cu + '.stmt'],
                                           insn_pre_cur[cu + '.pre'], '-', ldbg)

    if l_cnt_rm_t > 0 or l_cnt_add_t > 0 or \
        l_cnt_rm_f > 0 or l_cnt_add_f > 0:
        print('-------------------------------------------------')
        print("cu: %s" % cu)
        print("fun: %s" % fun)
        print("commit: %s\n\n******" % commit)

        if commit not in commits:
            commits.append(commit)


        it = {'fun': fun,
              'cu': cu,
              'commit': commit,
              'add_cnt_t': l_cnt_add_t,
              'add_cnt_f': l_cnt_add_f,
              'rm_cnt_t': l_cnt_rm_t,
              'rm_cnt_f': l_cnt_rm_f,
              'lines_add': lines_add,
              'lines_rm': lines_rm}


        if 'ren_name' in diff.keys():
            it[found].update({'ren_name': diff['ren_name']})

        if VALIDATE == True:
            if fun in validation.funs:
                print("\ncu: %s fun: %s\n" % (cu, fun))
                pp.pprint(it)
                print("\n")
    # else:
    # Todo: check else path

    return it


def gen_fun_diffs(path, src_cur, src_next, decl_cur, decl_next,
                                    funs_in_cur_d, funs_in_nex_d):
    """Generate diff for used functions

    :param path: base path, used for debug output into current work directory
    :param fun_src_cur: dict of dict with current source information
    :param fun_src_next: dict of dict with next to be compared source

    :returns:
        - diffs: The root dict contains the compilations units. The dict in the\
                dict contains keys with:

                - info_cur : start/end info of current function
                - info_next : start/end info of next function
                - name : function name
                - data : diff data with two keys:
                     + : lines added
                     - : lines removed

    """

    cu_not_in_next = []
    out_path = path + '/debug_data/'
    not_in_next = {}
    diffs = {}
    funs_in_cur = {}
    funs_in_nex = {}
    fun_tot = 0
    fun_moved = {}

    funs_next = {}
    # build dict of cu with list of funs_in_cur
    for cu in src_next.keys():
        if not cu in funs_in_nex.keys():
            funs_in_nex_d.update({cu:[]})
        for fun in src_next[cu]:
            funs_in_nex_d[cu].append(fun)

    for cu in src_cur.keys():
        if not cu in funs_in_cur.keys():
            funs_in_cur_d.update({cu:[]})
        for fun in src_cur[cu]:
            funs_in_cur_d[cu].append(fun)


    # check cu and function is available in next
    for cu in src_cur.keys():
        for fun in src_cur[cu]:
            #print("create diff function:%s" % fun)
            state = None
            info = src_cur[cu][fun]["info"]
            if cu in src_next.keys():
                cur_src = src_cur[cu][fun]["src"]

                if fun in src_next[cu].keys():
                    next_src = src_next[cu][fun]["src"]
                    add, rm = get_diff(cur_src, next_src)
                    state = 'mod'
                else:
                    # check if function has been moved to other cu
                    fun_mov = fun_exists(funs_next, fun)
                    # seems function removed or renamed
                    if fun_mov == None:
                        next_src = []
                        state = 'ref_or_del'

                        if cu not in not_in_next.keys():
                            not_in_next.update({cu:{}})

                        fun_info_cur = src_cur[cu][fun]["info"]
                        not_in_next[cu].update({fun:{
                                                  'src' : cur_src,
                                                  'start': fun_info_cur['start'],
                                                  'end': fun_info_cur['end']}})

                        print("fun %s in file: %s removed or refactored" %
                                                                (fun, cu))
                        continue
                    else:
                        fun_info_moved = src_next[fun_mov][fun]['info']

                        if not fun_mov in fun_moved.keys():
                            fun_moved.update({fun_mov:{}})

                        fun_moved[fun_mov].update({fun:{
                                            'start':fun_info_moved['start'],
                                            'end':fun_info_moved['end'],
                                            'cu': fun_mov}})

                        next_src = src_next[fun_mov][fun]["src"]
                        add, rm = get_diff(cur_src, next_src)
                        print("fun %s moved to: %s" % (fun, fun_mov))
                        state = 'mov'

                if len(add) > 0 or len(rm) > 0:
                    #dump_diff(out_path + fun + '_diff', cu, add, rm)
                    fun_info_cur = src_cur[cu][fun]["info"]


                    if state == 'mod':
                        fun_info_nex = src_next[cu][fun]["info"]
                        start = decl_next[cu][fun]["info"]["start"]
                        end = src_next[cu][fun]["info"]["end"]
                        funs_in_cur.update({fun:{'start': start,
                                          'end': end,
                                          'cu': cu}})

                    elif state == 'mov':
                        fun_info_nex = src_next[fun_mov][fun]["info"]
                        start = fun_info_nex["start"]
                        end = fun_info_nex["end"]

                        funs_in_cur.update({fun:{'start': start,
                                          'end': end,
                                          'old_cu': cu,
                                          'cu': fun_mov}})

                    diffs.update({fun: {"info_next": fun_info_nex,
                                        "info_cur": fun_info_cur,
                                        "cu": cu,
                                        "modified": state,
                                        "data": {"+": add, "-": rm}}})

    not_in_cur = {}
    not_in_nex = {}

    for cu in src_next.keys():
        if cu in src_cur.keys():
            for fun in src_next[cu]:
                if not fun in src_cur[cu].keys():
                    if not cu in not_in_cur.keys():
                        not_in_cur.update({cu:{}})
                    fun_info_nex = src_next[cu][fun]['info']
                    not_in_cur[cu].update({fun:{ 'start': fun_info_nex['start'],
                                                 'end': fun_info_nex['end']}})


    for cu in src_cur.keys():
        if cu in src_next.keys():
            for fun in src_cur[cu]:
                if not fun in src_next[cu].keys():
                    if not cu in not_in_nex.keys():
                        not_in_nex.update({cu:{}})
                    fun_info_cur = src_cur[cu][fun]['info']
                    not_in_nex[cu].update({fun:{ 'start': fun_info_cur['start'],
                                                 'end': fun_info_cur['end']}})



    return diffs, funs_in_cur, fun_moved, not_in_cur, not_in_nex

