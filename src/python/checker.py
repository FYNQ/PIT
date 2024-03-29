import os
import pprint
import logging
from multiprocessing import Pool
import json
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
        if not os.path.exists(path_cur + '/funs_nin_cur'):
            os.makedirs(path_cur + '/funs_nin_cur')

        if not os.path.exists(path_cur + '/struct_diffs'):
            os.makedirs(path_cur + '/struct_diffs')
        if not os.path.exists(path_cur + '/debug_data'):
            os.makedirs(path_cur + '/debug_data')

        self.data_out_funs = []
        self.l_insn_add = 0
        self.l_insn_rm = 0

        self.l_insn_add_t = 0
        self.l_insn_rm_t = 0
        self.l_insn_add_f = 0
        self.l_insn_rm_f = 0
        self.l_fun_add = 0
        self.l_fun_rm = 0
        self.cnt_fun_rm = 0
        self.cnt_fun_add = 0
        self.cnt_fun_ren = 0
        self.result_fun = {}

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
        self.logger.info("Create function diffs!")
        fun_diffs, funs, fun_mv, n_in_cur, n_in_nex = st.gen_funs_diff(path_cur,
                                                       self.fun_src_cur,
                                                       self.fun_src_nex,
                                                       self.fun_decl_cur,
                                                       self.fun_decl_nex)

        self.funs_tot = self.cnt_funs(funs)
        self.logger.info("functions total %d "  % self.cnt_funs(funs))

        self.logger.info("function not in current %d\n" %
                        (self.cnt_funs(n_in_cur)))
        self.logger.info("function not in next %d\n" %
                        (self.cnt_funs(n_in_nex)))

        self.fun_moved = fun_mv
        self.not_in_cur = n_in_cur
        self.fun_diffs = fun_diffs
        self.not_in_nex = n_in_nex
        diff_jobs = []

        self.logger.info("Create diffs for functions")
        self.funs_nin_cur = self.create_diffs(conf.LINUX_SRC, funs,
                                            'fun_diffs', tag_cur, tag_nex)

        self.logger.info("Create diffs functions not in current")
        self.funs_nin_cur = self.create_diffs(conf.LINUX_SRC, n_in_cur,
                                            'funs_nin_cur', tag_cur, tag_nex)

        self.logger.info("Create diffs moved functions")
        self.moved = self.create_diffs(conf.LINUX_SRC, fun_mv,
                                            'funs_moved', tag_cur, tag_nex)

        self.logger.info("Get patch information!")
        self.format_patches = aux.get_patches_fp(path_cur + 'diffs/')
        self.fun_patches = aux.get_patches(path_cur + 'fun_diffs/')
        self.cu_patches = aux.get_patch_lst_by_cu(path_cur + 'diffs/')
        self.fun_patches_nf = aux.get_patches(path_cur + 'funs_nin_cur/')

        self.process()

        # calculate and print out stats
        self.l_insn_add = self.l_insn_add_t + self.l_insn_add_f + self.l_fun_add
        self.l_insn_rm = self.l_insn_rm_t + self.l_insn_rm_f + self.l_fun_rm
        tag_date = aux.get_commit_time_sec(self.tag_cur, conf.LINUX_SRC)
        summary = {'tag': self.tag_cur,
                   'date': tag_date,
                   'patches': len(self.commits_insn_applied),
                   'patches_tot':len(os.listdir(self.diff_path)),
                   'lines_add': self.l_insn_add,
                   'lines_rm': self.l_insn_rm,
                   'funs_tot': self.funs_tot,
                   'funs_rm': self.cnt_fun_rm,
                   'funs_add': self.cnt_fun_add,
                   'funs_ren': self.cnt_fun_ren}
        fname_f = self.path_cur + 'functions_data.json'
        fname_s = self.path_cur + 'summary_data.json'
        fname_sha = self.path_cur + 'sha_lst.json'
        with open(fname_f, 'w') as outfile:
            json.dump(self.data_out_funs, outfile)
        with open(fname_s, 'w') as outfile:
            json.dump(summary, outfile)
        with open(fname_sha, 'w') as outfile:
            json.dump(self.commits_insn_applied, outfile)

        with open(self.path_cur + 'result_fun.json', 'w') as outfile:
            json.dump(self.result_fun , outfile)

        with open(self.path_cur + 'fun_decls_cur.json', 'w') as outfile:
            json.dump(self.fun_decl_cur , outfile)

        with open(self.path_cur + 'fun_decls_nex.json', 'w') as outfile:
            json.dump(self.fun_decl_nex , outfile)



    def get_rm_funs(self, funs_renamed):
        data = {}
        for cu in self.not_in_nex.keys():
            for fun in self.not_in_nex[cu].keys():
                if not fun in funs_renamed:
                    if not cu in data.keys():
                        data.update({cu:{}})
                    data[cu].update({fun : self.not_in_nex[cu][fun]})

        return data


    def process(self):
        l_struct_add = 0
        l_struct_rm = 0
        commits_insn_applied = []

        self.logger.info("Get stats for function diffs ...\n")
        r_fun, d_o, l_a_t, l_r_t, l_a_f, l_r_f, shas_fun = self.get_mod_in_fun(
                                                                self.fun_diffs)
        self.l_insn_add_t += l_a_t
        self.l_insn_add_f += l_a_f
        self.l_insn_rm_t += l_r_t
        self.l_insn_rm_f += l_r_f
        self.data_out_funs.extend(d_o)

        for commit in shas_fun:
            if commit not in commits_insn_applied:
                self.commits_insn_applied.append(commit)

        self.logger.info("Get stats for added functions ...\n")
        ren, added, not_res = self.check_not_in_cur()
        r_ren, d_o, l_a_t, l_r_t, l_a_f, l_r_f, shas_fun = self.get_mod_of_ren(ren)
        self.data_out_funs.extend(d_o)

        self.l_insn_add_t += l_a_t
        self.l_insn_add_f += l_a_f
        self.l_insn_rm_t += l_r_t
        self.l_insn_rm_f += l_r_f

        self.ren = ren
        funs_renamed = self.get_funs(ren)
        funs_removed = self.get_rm_funs(funs_renamed)

        self.l_fun_add, d_o, commits = self.get_lines_mod(added, 'ADD')

        self.data_out_funs.extend(d_o)
        for commit in commits:
            if commit not in commits_insn_applied:
                self.commits_insn_applied.append(commit)

        removed, d_o, commits, self.l_fun_rm = self.check_removed(funs_removed,
                                                         self.cu_patches)
        self.data_out_funs.extend(d_o)
        for commit in commits:
            if commit not in commits_insn_applied:
                self.commits_insn_applied.append(commit)

        if conf.VALIDATION == True:
            validation.print_val_added(added)
            validation.print_val_removed(removed)
            validation.print_val_renamed(ren)

        self.cnt_fun_rm = self.cnt_funs(removed)
        self.cnt_fun_add = self.cnt_funs(added)
        self.cnt_fun_ren = self.cnt_funs(ren)
        self.logger.info("Number of renamed functions: %d" % self.cnt_funs(ren))
        self.logger.info("Number of addded functions: %d" % self.cnt_funs(added))
        self.logger.info("Number of not resolved functions: %d" %
                                                        self.cnt_funs(not_res))



    def create_diffs(self, git_linux, data, path, tag_cur, tag_nex):
        l = {}
        for cu in data.keys():
            for fun in data[cu].keys():
                start = data[cu][fun]['start']
                end = data[cu][fun]['end']
                out_path = self.path_cur + path
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

    def get_lines_mod(self, data, mode):
        l_cnt = 0
        commits = []
        data_out = []
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
                    data_out.append((fun, cnt, 0, cu, [it['commit']], mode))

        return l_cnt, data_out, commits

    def get_mod_of_ren(self, data):
        result = {}
        data_out = []
        l_add_t = 0
        l_rm_t = 0
        l_add_f = 0
        l_rm_f = 0
        shas = []

        for cu in data.keys():
            if not cu in result.keys():
                result.update({cu:{}})
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
                result[cu].update({fun:res})
                fun_i = "%s->%s" % (fun_old ,fun)
                data_out.append(((fun_i),l_add_t + l_add_f, l_rm_t + l_rm_f, cu, shas, 'R'))
                if not fun in self.result_fun.keys():
                    self.result_fun.update({ fun: []})
                self.result_fun[fun].extend((shas, cu))

        return result, data_out, l_add_t, l_rm_t, l_add_f, l_rm_f, shas

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
        shas = []
        data_out = []
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

                data_out.append(((fun),l_add_t + l_add_f, l_rm_t + l_rm_f, \
                        diffs[fun]['cu'], commits, 'MOD'))
                self.result_fun.update({fun:[]})
                self.result_fun[fun].extend((commits, diffs[fun]['cu']))

            if len(res) == 0:
                continue

            result.update(res)

            for i in commits:
                if i not in shas:
                    shas.append(i)

            l_i_add_t += l_add_t
            l_i_rm_t += l_rm_t
            l_i_add_f += l_add_f
            l_i_rm_f += l_rm_f

        return result, data_out, l_i_add_t, l_i_rm_t, l_i_add_f, l_i_rm_f, shas

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
        len_rm_tot = 0
        data_out = []
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
                                        _l = len_rm + len(decl)
                                        result[cu].update({fun: {
                                                         'pname': patch['patch'],
                                                         'cu': cu,
                                                         'htext':hunk_text,
                                                         'len': _l,
                                                        }})
                                        len_rm_tot += len_rm + len(decl)
                                        commits.append(patch['commit'])
                                        data_out.append((fun,0 ,_l,
                                                         cu,
                                                         [patch['commit']], 'RM'))

                                        if not fun in self.result_fun.keys():
                                            self.result_fun.update({fun:[]})
                                        self.result_fun[fun].append((commits,cu))

                                        break

                        if flag == True:
                            break

        return result, data_out, commits, len_rm_tot

    def check_not_in_cur(self):
        not_found = {}
        found = {}
        added = {}

        for cu in self.not_in_cur.keys():
            for fun in self.not_in_cur[cu]:
                flag = False
                if fun in self.fun_patches_nf:
                    patch = self.fun_patches_nf[fun]
                    decl_nex = self.fun_decl_nex[cu][fun]['src']
                    body_start = self.fun_def_len_nex[cu+'.fl'][fun]['start']
                    body_end = self.fun_def_len_nex[cu+'.fl'][fun]['end']
                    if isinstance(patch, bool):
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
                        if body_start == body_end:
                            self.logger.info("Fun: %s could macro or fun with \
                                              body len 0" % fun)
                            continue

                        if not cu in not_found.keys():
                            not_found.update({cu:{}})
                        if not fun in not_found[cu]:
                            data = self.not_in_cur[cu][fun]
                            not_found[cu].update({fun: {'decl_nex': decl_nex,
                                                        'data': data,
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


