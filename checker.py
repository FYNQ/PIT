import os
import logging
from multiprocessing import Pool
import aux
import conf
import src_tools as st

ppath = '/home/markus/work_ot/PIT/build/v4.3/ppc_men_defconfig/'

#format_patches = aux.get_patches_fp(ppath + 'diffs/')
#fun_patches = aux.get_patches(ppath + 'fun_diffs/')
#cu_patches = aux.get_patch_lst_by_cu(ppath + 'diffs/')



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

result = []
def analyse_fun_diffs(fun_patches, cu_patches):
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




class worker:
    def __init__(self, path_cur, path_nex, tag_cur, tag_nex, arch):
        self.commits_insn_applied = []

        if not os.path.exists(path_cur + '/fun_diffs'):
            os.makedirs(path_cur + '/fun_diffs')
        if not os.path.exists(path_cur + '/struct_diffs'):
            os.makedirs(path_cur + '/struct_diffs')
        if not os.path.exists(path_cur + '/debug_data'):
            os.makedirs(path_cur + '/debug_data')

        logger_name = "checker_%s" % tag_cur
        aux.setup_logger(logger_name, path_cur + "/check_series.log")
        self.logger = logging.getLogger(logger_name)
        self.logger.info("Start check_series!\n")

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
        self.funs_cur_dict = {}
        self.funs_nex_dict = {}
        fun_diffs, funs, fun_moved, not_in_cur, not_in_nex = st.gen_fun_diffs(path_cur,
                                                       self.fun_src_cur,
                                                       self.fun_src_nex,
                                                       self.fun_decl_cur,
                                                       self.fun_decl_nex,
                                                       self.funs_cur_dict,
                                                       self.funs_nex_dict)

        self.logger.info("function not in current %d\n" %
                        (self.cnt_funs(not_in_cur)))
        self.logger.info("function not in next %d\n" %
                        (self.cnt_funs(not_in_nex)))



        self.fun_moved = fun_moved
        self.not_in_cur = not_in_cur
        self.fun_diffs = fun_diffs

        self.logger.info("Create function diffs!\n")
        diff_jobs = []
        i = 0
        print("functions total %d "  % len(funs))

        aux.mk_git_diff_funs(conf.LINUX_SRC, path_cur, tag_cur, tag_nex, funs,
                                                        self.logger)

        print("functions not in current")
        self.not_found = self.create_diffs(conf.LINUX_SRC, not_in_cur,
                                            'funs_not_found', tag_cur, tag_nex)
        print("functions moved")
        self.moved = self.create_diffs(conf.LINUX_SRC, fun_moved,
                                            'funs_moved', tag_cur, tag_nex)

        self.logger.info("Get patch information!")
        self.format_patches = aux.get_patches_fp(path_cur + 'diffs/')
        self.fun_patches = aux.get_patches(path_cur + 'fun_diffs/')
        self.cu_patches = aux.get_patch_lst_by_cu(path_cur + 'diffs/')
        self.fun_patches_nf = aux.get_patches(path_cur + 'funs_not_found/')
        self.fun_patches_mv = aux.get_patches(path_cur + 'funs_moved/')


    def get_mod_diff(self):
        l_insn_add = 0
        l_insn_rm = 0
        l_struct_add = 0
        l_struct_rm = 0
        commits_insn_applied = 0
        tag_date = aux.get_commit_time_sec(self.tag_cur, conf.LINUX_SRC)


        self.logger.info("Get function diffs ...")
        res_fun, l_a, l_r, commits_fun = self.get_mod_in_fun(self.fun_diffs)
        l_insn_add += l_a
        l_insn_rm += l_r
        for commit in commits_fun:
            if commit not in commits_insn_applied:
                self.commits_insn_applied.append(commit)



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
        l_insn_add = 0
        l_insn_rm = 0
        h_insn_tot = 0
        h_insn_app = 0
        commits_app = []

        for fun in diffs.keys():
            if fun not in self.fun_patches.keys():
                print("Missing patch for fun: %s" % fun)
                continue
            if self.fun_patches[fun] == False:
                print("Missing fun diff: %s" % fun)
                continue
            else:
                res, l_add, l_rm, commits = st.get_mod_fun(fun,
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

            l_insn_add += l_add
            l_insn_rm += l_rm

        return result, l_insn_add, l_insn_rm, commits_app


    def check_not_in_cur(self, data, patch_data):
        not_found = {}
        not_found_by_cu = {}
        found = {}
        for cu in data.keys():
            for fun in data[cu]:
                if fun in patch_data:
                    patch = patch_data[fun]
                    decl = self.fun_decl_nex[cu][fun]['src']
                    for item in patch.items:
                        for hunk in item.hunks:
                            ht = st.hunk_decode(hunk)
                            if fun == 'blkdev_roset':
                                print("x: %s" % ht[3].rstrip('\n'))
                                print("__: %s" % decl[0] == ht[3].rstrip('\n'))
                                print("D: |%s|" % decl[0])
                                for i in ht:
                                    print(i)

                            for line in ht:
                                if decl[0] == line[1:].rstrip('\n') :
                                    hunkfind = [x[1:].rstrip(b"\r\n")
                                            for x in hunk.text if x[0] in b" -"]
                                    hunkreplace = [x[1:].rstrip(b"\r\n")
                                            for x in hunk.text if x[0] in b" + "]
                                    print("function %s in hunk add" % fun)
                                    if not cu in found.keys():
                                        found.update({cu:{}})
                                    if fun not in found[cu].keys():
                                        found[cu].update({fun:{
                                                          'decl': decl,
                                                          'htext': ht,
                                                          'hfind': hunkfind,
                                                          'hreplace':hunkreplace}})


                                elif decl[0] in hunk.text:
                                    print("------------------XXXX")

                if not cu in not_found.keys():
                    not_found.update({cu:{}})
                if not fun in not_found[cu]:
                    not_found[cu].update({fun: {'decl': decl, 'patch': patch}})

        return found, not_found


    def cnt_funs(self, data):
        l = 0
        for cu in data.keys():
            l += len(data[cu])
        return l


path_cur = '/home/markus/work_ot/PIT/build/v4.3/ppc_men_defconfig/'
path_nex = '/home/markus/work_ot/PIT/build/v4.4-rc1/ppc_men_defconfig/'

a = worker(path_cur, path_nex, 'v4.3', 'v4.4-rc1', 'ppc')
res, n_res = a.check_not_in_cur(a.not_in_cur, a.fun_patches_nf)

#resolved = a.res_unresolved(a.not_resolved, a.cu_patches)
#not_resolved = a.collect_unresolved(a.not_resolved)
#still_missing = list(set(not_resolved)-set(resolved))

