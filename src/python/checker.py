import os
import pprint
import logging
from multiprocessing import Pool
import aux
import conf
import src_tools as st

pp = pprint.PrettyPrinter(indent=4)


ppath = '/home/markus/work_ot/PIT/build/v4.3/ppc_men_defconfig/'

import validation


# get hunks applied
# fun diffs allways have one item and on hunk
def cmp_patch(commit, fun, cu, text, patches):
    res = {}
    for patch in patches:
        if patch['commit'] == commit:
            for item in patch['items']:
                hunks = []
                for i, hunk in enumerate(item.hunks):
                    for _line in hunk.text:
                        line = _line.decode('utf-8')
                        if line.startswith('+') or line.startswith('-'):
                            for l in text:
                                if _line == l:
                                    hunks.append(i)
                if len(hunks) > 0:
                    res.update({ commit : {'fun': fun,
                                           'hunks': list(set(hunks)),
                                           'patch': patch['patch'],
                                           'cu': cu}})
    return res

def analyse_fun_diffs(fun_patches, cu_patches):
    result = []
    for fun in fun_patches.keys():
        if isinstance(fun_patches[fun], bool):
            continue
        res = {fun : []}

        for item in fun_patches[fun]:
            fun_cu = item.source.decode('utf-8')[2:]
            fun_text = item.hunks[0].text
            commit = aux.get_hash(item.header)
            r = cmp_patch(commit, fun, fun_cu, fun_text, cu_patches[fun_cu])
            print("%s" % (r))
            res[fun].append(r)

        result.append(res)
    return result



class worker:
    def __init__(self, path_cur, path_nex, tag_cur, tag_nex, arch):
        self.commits_insn_applied = []

        if not os.path.exists(path_cur + '/fun_diffs'):
            os.makedirs(path_cur + '/fun_diffs')
        if not os.path.exists(path_cur + '/struct_diffs'):
            os.makedirs(path_cur + '/struct_diffs')
        if not os.path.exists(path_cur + '/debug_data'):
            os.makedirs(path_cur + '/debug_data')


        self.l_insn_add_t = 0
        self.l_insn_rm_t = 0
        self.l_insn_add_f = 0
        self.l_insn_rm_f = 0

        logger_name = "checker_%s" % tag_cur
        aux.setup_logger(logger_name, path_cur + "/check_series.log")
        self.logger = logging.getLogger(logger_name)
        self.logger.info("Start check_series!\n")
        self.diff_path = path_cur + "diffs/"
        self.linux_cur = path_cur + "linux-stable/"
        self.linux_nex = path_nex + "linux-stable/"
        self.path_cur = path_cur
        self.path_nex = path_nex
        self.tag_cur = tag_cur
        self.tag_nex = tag_nex

        gcc_out_cur = path_cur + '/gcc_output'
        gcc_out_nex = path_nex + '/gcc_output'

        self.fun_def_len_cur = aux.load(gcc_out_cur, 'data_flen')
        self.fun_def_len_nex = aux.load(gcc_out_nex, 'data_flen')

        self.fun_decl_len_cur = aux.load(gcc_out_cur, 'data_dlen')
        self.fun_decl_len_nex = aux.load(gcc_out_nex, 'data_dlen')

        self.insns_cur = aux.load(gcc_out_cur, 'data_stmt')
        self.insns_nex = aux.load(gcc_out_nex, 'data_stmt')

        self.parsed_cur = aux.load(gcc_out_cur, 'data_pre')
        self.parsed_nex = aux.load(gcc_out_nex, 'data_pre')

        self.fun_src_cur = st.get_src(self.linux_cur,
                                      self.fun_def_len_cur, len('.fl'))

        self.fun_src_nex = st.get_src(self.linux_nex,
                                      self.fun_def_len_nex, len('.fl'))

        self.fun_decl_cur = st.get_src(self.linux_cur,
                                       self.fun_decl_len_cur, len('.dl'))

        self.fun_decl_nex = st.get_src(self.linux_nex,
                                       self.fun_decl_len_nex, len('.dl'))

        self.logger.info("function in tag %s: %d\n" %
                        (tag_cur, self.cnt_funs(self.fun_src_cur)))
        self.logger.info("function in tag %s: %d\n" %
                        (tag_nex, self.cnt_funs(self.fun_src_nex)))
        fun_diffs, funs, fun_mv, n_in_cur, n_in_nex = st.gen_funs_diff(path_cur,
                                                       self.fun_src_cur,
                                                       self.fun_src_nex,
                                                       self.fun_decl_cur,
                                                       self.fun_decl_nex)


        self.logger.info("function not in current %d\n" %
                        (self.cnt_funs(n_in_cur)))
        self.logger.info("function not in next %d\n" %
                        (self.cnt_funs(n_in_nex)))



        self.fun_moved = fun_mv
        self.not_in_cur = n_in_cur
        self.fun_diffs = fun_diffs
        self.not_in_nex = n_in_nex
        self.logger.info("Create function diffs!")
        diff_jobs = []
        self.logger.info("functions total %d "  % len(funs))

        self.logger.info("functions not in current")
        self.funs_nin_cur = self.create_diffs(conf.LINUX_SRC, n_in_cur,
                                            'funs_nin_cur', tag_cur, tag_nex)

        self.logger.info("functions moved")
        self.moved = self.create_diffs(conf.LINUX_SRC, fun_mv,
                                            'funs_moved', tag_cur, tag_nex)

        self.logger.info("Get patch information!")
        self.format_patches = aux.get_patches_fp(path_cur + 'diffs/')
        self.fun_patches = aux.get_patches(path_cur + 'fun_diffs/')
        cu_patches = aux.get_patch_lst_by_cu(path_cur + 'diffs/')
        self.fun_patches_nf = aux.get_patches(path_cur + 'funs_nin_cur/')

        ren, added, not_res = self.check_not_in_cur(n_in_cur, self.fun_patches_nf)
        self.get_stats(fun_diffs, ren, added)
        self.added = added
        self.ren = ren
        self.logger.info("Number of renamed functions: %d" % self.cnt_funs(ren))
        self.logger.info("Number of addded functions: %d" % self.cnt_funs(added))
        self.logger.info("Number of not resolved functions: %d" %
                                                        self.cnt_funs(not_res))

        funs_renamed = self.get_funs(ren)
        funs_removed = self.get_rm_funs(n_in_nex, funs_renamed)

        l_added, res_commits = self.get_lines_mod(added)
        removed ,b = self.check_removed(funs_removed, cu_patches)
        if conf.VALIDATION == True:
            validation.print_val_added(added)
            validation.print_val_removed(removed)
            validation.print_val_renamed(ren)

    def get_rm_funs(self, n_in_nex, funs_renamed):
        data = {}
        for cu in n_in_nex.keys():
            for fun in n_in_nex[cu].keys():
                if not fun in funs_renamed:
                    if not cu in data.keys():
                        data.update({cu:{}})
                    data[cu].update({fun : n_in_nex[cu][fun]})

        return data


    def get_stats(self, data, renamed, added):
        l_struct_add = 0
        l_struct_rm = 0
        commits_insn_applied = []
        tag_date = aux.get_commit_time_sec(self.tag_cur, conf.LINUX_SRC)

        self.logger.info("Get stats for function diffs ...\n")
        r_fun, l_a_t, l_r_t, l_a_f, l_r_f, shas_fun = self.get_mod_in_fun(data)
        self.l_insn_add_t += l_a_t
        self.l_insn_rm_t += l_r_t
        self.l_insn_add_f += l_a_f
        self.l_insn_rm_f += l_r_f

        for commit in shas_fun:
            if commit not in commits_insn_applied:
                self.commits_insn_applied.append(commit)

        self.logger.info("Get stats for added functions ...\n")
        r_ren, l_a_t, l_r_t, l_a_f, l_r_f, shas_fun =self.get_mod_of_ren(renamed)
        self.l_insn_add_t += l_a_t
        self.l_insn_rm_t += l_r_t
        self.l_insn_add_f += l_a_f
        self.l_insn_rm_f += l_r_f


    def create_diffs(self, git_linux, data, path, tag_cur, tag_nex):
        l = {}
        for cu in data.keys():
            for fun in data[cu].keys():
                start = data[cu][fun]['start']
                end = data[cu][fun]['end']
                out_path = path_cur + path
                aux.git_make_fun_diff(git_linux, out_path, tag_cur, tag_nex,
                                            start, end, cu, fun, self.logger)

                if not cu in l.keys():
                    l.update({cu:{}})
                l[cu].update({fun: {'start': start, 'end': end}})

        return l

    def get_pre_data(self, data, start, end):
        s = -1
        e = -1
        for n,i in enumerate(data):
            if i >= start and s == -1:
                s = n
            if i > end and e == -1:
                e = n - 1
        if s != -1 and e != -1:
            return data[s:e]
        else:
            return None

    def get_lines_mod(self, data):
        l_cnt = 0
        commits = []
        for cu in data:
            for fun in data[cu]:
                it = data[cu][fun]
                start = self.fun_def_len_nex[cu + '.fl'][fun]['start']
                end = self.fun_def_len_nex[cu + '.fl'][fun]['end']
                parsed = sorted(self.parsed_nex[cu + '.pre'])
                pre_data = self.get_pre_data(parsed, start, end)
                if pre_data != None:
                    cnt = len(pre_data)
                    l_cnt += cnt
                    if it['commit'] not in commits:
                        commits.append(it['commit'])


        return l_cnt, commits

    def get_mod_of_ren(self, data):
        for cu in data.keys():
            for fun in data[cu]:
                it = data[cu][fun]
                fun_old = it['fun_old']
                cur_src = self.fun_src_cur[cu][fun_old]['src']
                nex_src = self.fun_src_nex[cu][fun]['src']

                add, rm = st.get_diff(cur_src, nex_src)
                p_it = {'data' : {'+': add, '-': rm},
                        'cu' : cu,
                        'info_cur': self.fun_src_cur[cu][fun_old]['info'],
                        'info_next': self.fun_src_nex[cu][fun]['info']}

                res, l_add_t, l_rm_t, l_add_f, l_rm_f, shas = st.get_mod_fun(
                                fun, self.insns_cur, self.insns_nex,
                                self.parsed_cur, self.parsed_nex, p_it,
                                self.fun_patches_nf[fun])
        return res, l_add_t, l_rm_t, l_add_f, l_rm_f, shas

    def get_mod_in_fun(self, diffs):
        """ Get modification between two versions of a function.

        :param diffs: A dict with compile unit names as keys. Each key has
                      a list of dict entries (one for each function).
                      The entry has the information:
                      - info_cur : start/end info of current function
                      - info_next : start/end info of next function
                      - name : function name
                      - data : diff data with two keys:
                        + : lines added
                        - : lines removed

        :returns:
            - res: dict [cu][[commit], [patch_name], [fun], [add], [rm]]
            - h_insn_app: hunks applied on instructions
            - h_insn_tot: hunks total on instructions
            - l_insn_add: lines added total
            - l_insn_rm: lines removed total
            - patches: patches applied

        """
        result = {}
        l_i_add_t = 0
        l_i_rm_t = 0
        l_i_add_f = 0
        l_i_rm_f = 0

        h_insn_tot = 0
        h_insn_app = 0
        commits_app = []

        for fun in diffs.keys():
            if fun not in self.fun_patches.keys():
                self.logger.info("Missing patch for fun: %s" % fun)
                continue
            if self.fun_patches[fun] == False:
                self.logger.info("Missing fun diff: %s" % fun)
                continue
            else:
                res, l_add_t, l_rm_t, l_add_f, l_rm_f,commits = st.get_mod_fun(fun,
                                                        self.insns_cur,
                                                        self.insns_nex,
                                                        self.parsed_cur,
                                                        self.parsed_nex,
                                                        diffs[fun],
                                                        self.fun_patches[fun])


            if len(res) == 0:
                continue

            result.update(res)

            for i in commits:
                if i not in commits_app:
                    commits_app.append(i)

            l_i_add_t += l_add_t
            l_i_rm_t += l_rm_t
            l_i_add_f += l_add_f
            l_i_rm_f += l_rm_f

        return result, l_i_add_t, l_i_rm_t, l_i_add_f, l_i_rm_f, commits_app

    def decl_in_patch(self, data, cu, hunk_text):
        for fun in data[cu].keys():
            decl = data[cu][fun]['src']
            for line in hunk_text:
                if decl[0] in line.rstrip('\n'):
                    return decl, fun
        return None, None


    def check_removed(self, data, patch_data):
        result = {}
        commits = []
        for cu in data.keys():
            for fun in data[cu].keys():
                if cu + '.fl' in self.fun_def_len_cur.keys():
                    if not fun in self.fun_def_len_cur[cu + '.fl'].keys():
                        self.logger.info("Fun %s  cannot be found in current tree"
                                                                            % fun)
                        continue
                flag = False
                info = self.fun_def_len_cur[cu+'.fl'][fun]
                len_rm = info['end'] - info['start']
                if len_rm == 0:
                    continue
                if not cu in patch_data.keys():
                    continue
                for patch in patch_data[cu]:
                    for item in patch['items']:
                        for hunk in item.hunks:
                            ht = st.get_hunk_rm_text(hunk)
                            _decl = data[cu][fun]['decl']['src']
                            decl = []
                            for t in _decl:
                                decl.append(t.replace('\t','').lstrip(' '))
                            for k, i in enumerate(ht):
                                if decl[0] in i:
                                    if decl == ht[k:k+len(decl)]:
                                        hunk_text = ht[k:k+len_rm+len(decl)]
                                        flag = True
                                        if not cu in result.keys():
                                            result.update({cu:{}})
                                        result[cu].update({fun: {
                                                         'pname': patch['patch'],
                                                         'cu': cu,
                                                         'htext':hunk_text,
                                                         'len': len_rm + len(decl),
                                                        }})
                                        commits.append(patch['commit'])
                                        break

                        if flag == True:
                            break

        return result, commits

    def check_not_in_cur(self, data, patch_data):
        not_found = {}
        found = {}
        added = {}

        for cu in data.keys():
            for fun in data[cu]:
                flag = False
                if fun in patch_data:
                    patch = patch_data[fun]
                    decl_nex = self.fun_decl_nex[cu][fun]['src']
                    body_start = self.fun_def_len_nex[cu+'.fl'][fun]['start']
                    body_end = self.fun_def_len_nex[cu+'.fl'][fun]['end']
                    if body_start == body_end:
                        self.logger.info("##Fun: %s could be define macro" % fun)
                        continue

                    commit = aux.get_hash(patch.items[0].header)
                    for item in patch.items:
                        for hunk in item.hunks:
                            ht = st.hunk_decode(hunk)
                            hunkfind = [x[1:].rstrip(b"\r\n").decode('utf-8')
                                            for x in hunk.text if x[0] in b" -"]
                            hunkreplace = [x[1:].rstrip(b"\r\n").decode('utf-8')
                                            for x in hunk.text if x[0] in b" + "]
                            for line in hunkreplace:
                                if decl_nex[0] == line.rstrip('\n') :
                                    r,fun_o = self.decl_in_patch(
                                                   self.fun_decl_cur, cu, hunkfind)

                                    flag = True
                                    if r != None:
                                        if not cu in found.keys():
                                            found.update({cu:{}})

                                        patch_name = aux.find_commit(
                                                        self.diff_path, commit)

                                        found[cu].update({fun:{
                                                          'decl_nex': decl_nex,
                                                          'decl_old': r,
                                                          'fun_old': fun_o,
                                                          'fun_new': fun,
                                                          'patch': patch,
                                                          'commit':commit,
                                                          'cu': cu,
                                                          'pname':patch_name,
                                                          'htext': ht,
                                                          'hfind': hunkfind,
                                                          'hreplace':hunkreplace}})
                                    else:
                                        if not cu in added.keys():
                                            added.update({cu:{}})
                                        patch_name = aux.find_commit(
                                                        self.diff_path, commit)
                                        add_len = body_end = body_start
                                        add_len += len(decl_nex)
                                        added[cu].update({fun: {
                                                          'decl_nex': decl_nex,
                                                          'patch': patch,
                                                          'pname':patch_name,
                                                          'commit':commit,
                                                          'htext': ht,
                                                          'hfind': hunkfind,
                                                          'hreplace':hunkreplace}})


                    if flag == False:
                        # if there is only declration but no body seems
                        # like define/macro
                        if not cu in not_found.keys():
                            not_found.update({cu:{}})
                        if not fun in not_found[cu]:
                            not_found[cu].update({fun: {'decl_nex': decl_nex,
                                                        'data': data[cu][fun],
                                                        'commit': commit,}})
                else:
                    self.logger.info("---> No patch for fun: %s available" % fun)

        return found, added, not_found


    def cnt_funs(self, data):
        l = 0
        for cu in data.keys():
            l += len(data[cu])
        return l

    def get_funs(self, data):
        l = []
        for cu in data.keys():
            for fun in data[cu].keys():
                l.append(data[cu][fun]['fun_old'])
                l.append(fun)
        return l



path_cur = '/home/markus/work_ot/PIT/build/v4.3/ppc_men_defconfig/'
path_nex = '/home/markus/work_ot/PIT/build/v4.4-rc1/ppc_men_defconfig/'

a = worker(path_cur, path_nex, 'v4.3', 'v4.4-rc1', 'ppc')

#format_patches = aux.get_patches_fp(ppath + 'diffs/')

#fun_patches = aux.get_patches(ppath + 'fun_diffs/')
#cu_patches = aux.get_patch_lst_by_cu(ppath + 'diffs/')

#analyse_fun_diffs(fun_patches, cu_patches)

