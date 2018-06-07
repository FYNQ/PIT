import os
import logging
from multiprocessing import Pool
import aux
import conf
import src_tools as st

ppath = '/home/markus/work_ot/PIT/build/v4.3/ppc_men_defconfig/'



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
        self.funs_cur_dict = {}
        self.funs_nex_dict = {}
        fun_diffs, funs, fun_mv, n_in_cur, n_in_nex = st.gen_fun_diffs(path_cur,
                                                       self.fun_src_cur,
                                                       self.fun_src_nex,
                                                       self.fun_decl_cur,
                                                       self.fun_decl_nex,
                                                       self.funs_cur_dict,
                                                       self.funs_nex_dict)

        self.logger.info("function not in current %d\n" %
                        (self.cnt_funs(n_in_cur)))
        self.logger.info("function not in next %d\n" %
                        (self.cnt_funs(n_in_nex)))



        self.fun_moved = fun_mv
        self.not_in_cur = n_in_cur
        self.fun_diffs = fun_diffs

        self.logger.info("Create function diffs!\n")
        diff_jobs = []
        i = 0
        print("functions total %d "  % len(funs))

        #aux.mk_git_diff_funs(conf.LINUX_SRC, path_cur, tag_cur, tag_nex, funs,
        #                                                self.logger)

        print("functions not in current")
        self.funs_nin_cur = self.create_diffs(conf.LINUX_SRC, n_in_cur,
                                            'funs_nin_cur', tag_cur, tag_nex)
        #self.funs_nin_nex = self.create_diffs(conf.LINUX_SRC, n_in_nex,
        #                                    'funs_nin_nex', tag_cur, tag_nex)


        print("functions moved")
        self.moved = self.create_diffs(conf.LINUX_SRC, fun_mv,
                                            'funs_moved', tag_cur, tag_nex)

        self.logger.info("Get patch information!")
        self.format_patches = aux.get_patches_fp(path_cur + 'diffs/')
        self.fun_patches = aux.get_patches(path_cur + 'fun_diffs/')
        self.cu_patches = aux.get_patch_lst_by_cu(path_cur + 'diffs/')
        self.fun_patches_nf = aux.get_patches(path_cur + 'funs_nin_cur/')
#        self.fun_patches_mv = aux.get_patches(path_cur + 'funs_moved/')
        self.get_mod_diff(fun_diffs)


    def get_mod_diff(self, data):
        l_struct_add = 0
        l_struct_rm = 0
        commits_insn_applied = []
        tag_date = aux.get_commit_time_sec(self.tag_cur, conf.LINUX_SRC)

        self.logger.info("Get function diffs ...\n")
        r_fun, l_a_t, l_r_t, l_a_f, l_r_f, shas_fun = self.get_mod_in_fun(data)
        self.l_insn_add_t += l_a_t
        self.l_insn_rm_t += l_r_t
        self.l_insn_add_f += l_a_f
        self.l_insn_rm_f += l_r_f

        for commit in shas_fun:
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
        l_i_add_t = 0
        l_i_rm_t = 0
        l_i_add_f = 0
        l_i_rm_f = 0

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
                if decl[0] in line[1:].rstrip('\n'):
                    print("Found decl %s of fun: %s" % (decl, fun))
                    return decl, fun
        return None, None

    def check_not_in_cur(self, data, patch_data):
        not_found = {}
        not_found_by_cu = {}
        found = {}
        added = {}
        #
        for cu in data.keys():
            for fun in data[cu]:
                flag = False
                if fun in patch_data:
                    patch = patch_data[fun]
                    decl_nex = self.fun_decl_nex[cu][fun]['src']
                    commit = aux.get_hash(patch.items[0].header)
                    for item in patch.items:
                        for hunk in item.hunks:
                            ht = st.hunk_decode(hunk)
                            if fun == '__spi_register_driver':
                                print("x: %s" % ht[3].rstrip('\n'))
                                print("__: %s" % decl_nex[0] == ht[3].rstrip('\n'))
                                print("D: |%s|" % decl_nex[0])
                                for i in ht:
                                    print(i)

                            for line in ht:
                                if decl_nex[0] == line[1:].rstrip('\n') :
                                    hunkfind = [x[1:].rstrip(b"\r\n")
                                            for x in hunk.text if x[0] in b" -"]
                                    hunkreplace = [x[1:].rstrip(b"\r\n")
                                            for x in hunk.text if x[0] in b" + "]
                                    print("function %s in hunk add" % fun)
                                    r,fun_o = self.decl_in_patch(self.fun_decl_cur,
                                                                        cu, ht)
                                    flag = True
                                    if r != None:
                                        if not cu in found.keys():
                                            found.update({cu:{}})
                                        if fun not in found[cu].keys():
                                            found[cu].update({fun:[]})

                                        patch_name = aux.find_commit(
                                                        self.diff_path, commit)

                                        found[cu][fun].append({
                                                          'decl_nex': decl_nex,
                                                          'decl_old': r,
                                                          'fun_old': fun_o,
                                                          'patch': patch,
                                                          'cu': cu,
                                                          'pname':patch_name,
                                                          'htext': ht,
                                                          'hfind': hunkfind,
                                                          'hreplace':hunkreplace})
                                    else:
                                        if not cu in added.keys():
                                            added.update({cu:{}})
                                        patch_name = aux.find_commit(
                                                        self.diff_path, commit)
                                        added[cu].update({fun: {
                                                          'decl_nex': decl_nex,
                                                          'patch': patch,
                                                          'pname':patch_name,
                                                          'htext': ht,
                                                          'hfind': hunkfind,
                                                          'hreplace':hunkreplace}})


                    if flag == False:
                        # if there is only declration but no body seems
                        # like define/macro
                        body_start = self.fun_def_len_nex[cu+'.fl'][fun]['start']
                        body_end = self.fun_def_len_nex[cu+'.fl'][fun]['end']
                        if body_start == body_end:
                            print("+++> Fun: %s seems to be define macro" % fun)
                            continue
                        if not cu in not_found.keys():
                            not_found.update({cu:{}})
                        if not fun in not_found[cu]:
                            not_found[cu].update({fun: {'decl_nex': decl_nex,
                                                        'data': data[cu][fun],
                                                        'commit': commit,}})
                else:
                    print("---> No patch for fun: %s available" % fun)

        return found, added, not_found


    def cnt_funs(self, data):
        l = 0
        for cu in data.keys():
            l += len(data[cu])
        return l


def print_added(data):
    for cu in data:
        for fun in data[cu]:
            it = data[cu][fun]
            print("-----------------------------------")
            print("Function: %s" % fun)
            print("Patch   : %s" % it['pname'])
            print("File    : %s" % cu)
            for i in it['htext']:
                print(i)



def print_renamed(data):
    for cu in data:
        for fun in data[cu]:
            items = data[cu][fun]
            for it in items:
                print("-------------------------------")
                print("Fun ren : %s->%s " % (it['fun_old'], fun))
                print("File    : %s" % it['cu'])
                print("Patch   : %s" % it['pname'])
                for i in it['htext']:
                    print(i)

def find_fun(data, fun):
    for cu in data.keys():
        if fun in data[cu]:
            print("cu: %s" % cu)


path_cur = '/home/markus/work_ot/PIT/build/v4.3/ppc_men_defconfig/'
path_nex = '/home/markus/work_ot/PIT/build/v4.4-rc1/ppc_men_defconfig/'

a = worker(path_cur, path_nex, 'v4.3', 'v4.4-rc1', 'ppc')
renamed, added, n_res = a.check_not_in_cur(a.not_in_cur, a.fun_patches_nf)

print("Renamed  : %d" % a.cnt_funs(renamed))
print("Added: %d" % a.cnt_funs(added))
print("N Res: %d" % a.cnt_funs(n_res))


#print_added(added)
print_renamed(renamed)

#format_patches = aux.get_patches_fp(ppath + 'diffs/')

#fun_patches = aux.get_patches(ppath + 'fun_diffs/')
#cu_patches = aux.get_patch_lst_by_cu(ppath + 'diffs/')

#analyse_fun_diffs(fun_patches, cu_patches)

