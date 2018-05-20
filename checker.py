

import aux

ppath = '/home/markus/work_ot/PIT/build/v4.3/ppc_men_defconfig/'

format_patches = aux.get_patches_fp(ppath + 'diffs/')
fun_patches = aux.get_patches(ppath + 'fun_diffs/')
cu_patches = aux.get_patch_lst_by_cu(ppath + 'diffs/')


t_fp = fun_patches['___dst_free'].items[0].hunks[0].text

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


"""
class worker:
    def __init__(self, path, tag, next_tag, next_path, arch):

        if not os.path.isdir(path + '/refactor/'):
            os.makedirs(path + "/refactor/")
        if not os.path.exists(path + '/fun_diffs'):
            os.makedirs(path + '/fun_diffs')
        if not os.path.exists(path + '/struct_diffs'):
            os.makedirs(path + '/struct_diffs')
        if not os.path.exists(path + '/debug_data'):
            os.makedirs(path + '/debug_data')

        logger_name = "checker_%s" % tag
        aux.setup_logger(logger_name, path + "/check_series.log")
        self.logger = logging.getLogger(logger_name)
        self.logger.info("Start check_series!")

        self.c_linux = path + "/linux-stable/"
        self.n_linux = next_path + "/linux-stable/"
        self.path = path
        self.tag = tag
        self.next_path = next_path

	gcc_out_cur = cur_path + "/gcc_output"
	gcc_out_next = next_path + "/gcc_output"

        self.fun_len_def_cur = aux.load(gcc_out_cur, 'data_flen')
	self.fun_len_def_next = aux.load(gcc_out_next,'data_flen')

        self.get_fun_decl_p_cur = aux.load(gcc_out_cur, 'data_dlen')
        self.get_fun_decl_p_next = aux.load(gcc_out_next, 'data_dlen')

        self.fun_src_cur = st.get_src(path + "linux-stable/",
                                      self.fun_len_def_cur,
                                      len('.fl'))

        self.fun_src_next = st.get_src(next_path + '/linux-stable/',
                                       self.fun_len_def_next,
                                       len('.fl'))

        self.fun_decl_cur = st.get_src(path + '/linux-stable/',
                                       self.get_fun_decl_p_cur,
                                       len('.dl'))
        self.fun_decl_next = st.get_src(next_path + '/linux-stable/',
                                        self.get_fun_decl_p_next,
                                        len('.dl'))

        fun_diffs, funs, not_res, fun_tot, fun_mod = st.gen_fun_diffs(path,
                                                       self.fun_src_cur,
                                                       self.fun_src_next,
                                                       self.fun_decl_cur,
                                                       self.fun_decl_next)

	gt.mk_git_diff(conf.LINUX_SRC, path, tag, next_tag, funs, self.logger)



"""
