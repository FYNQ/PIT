import os
import datetime

now = datetime.datetime.now()




funs = ['cgroup_disable', 'ext4_journalled_write_end', 'of_irq_init', 'show_free_areas', 'sk_clone_lock', 'arch_get_unmapped_area_topdown', 'perf_pmu_cancel_txn', 'bstr_printf', 'watchdog_set_timeout', 'gfpflags_to_migratetype', 'arpt_do_table', 'talitos_edesc_alloc', 'pci_revert_fw_address', 'print_bin_fmt', 'compute_score', 'request_key_auth_new', '__nft_trace_packet', 'packet_bind_spkt', 'ondemand_readahead', 'run_filter', 'synchronize_sched_expedited_wait','tcp_get_cookie_sock',
        'synchronize_sched_expedited', 'dma_pool_alloc', 'fsl_pci_mcheck_exception', 'mmc_send_tuning', 'task_name', 'ip_do_fragment', 'ext4_writepage', 'nf_tables_newchain', 'posix_acl_xattr_get']


funs_add = []

funs_renamed = ['ext4_set_resv_clusters']

path_validation = '%s/../../doc/validation/' % (os.getcwd())

header = {'header': '',
          'author': '',
          'review': '',
          'data': '',
          'expires': '000',
          'keywords': '',
          'status': 'initial draft',
          'phase': '000',
          'ref': '',
          'qa': '',
          'tracking': '?',
          'format': 'ascii text'}

header['author'] = 'Markus Kreidl'
header['date'] = '%d-%d-%d' % (now.year, now.month, now.day)

def print_val_added(data):
    cnt = 2
    index = []
    for cu in data:
        for fun in data[cu]:
            l = []
            header['header'] = "Validation add lines function %s" % fun
            header['keywords'] = 'added lines, added function %s' % fun
            fname = '%s/functions_added/%s.val' % (path_validation, cnt)
            it = data[cu][fun]
            l.append("# Function : %s\n\n" % fun)
            l.append("# Patch : %s\n\n" % it['pname'])
            l.append("# File : %s\n\n" % cu)
            for i in it['htext']:
                l.append('%s\n'%i)
            l.append('\n# Result:')
            print_val_file(fname, header, l)
            index.append("%d.val\t %s\n" % (cnt, fun))
            cnt += 1

    fname = '%s/functions_added/1.val' % (path_validation)
    header['header'] = "Validation index for added functions"
    header['keywords'] = 'index, validation, added functions'
    print_val_file(fname, header, index)

def print_val_removed(data):
    cnt = 2
    index = []
    for cu in data:
        for fun in data[cu].keys():
            it = data[cu][fun]
            l = []
            header['header'] = "Validation removed function %s" % fun
            header['keywords'] = 'removed function %s' % fun
            fname = '%s/functions_removed/%s.val' % (path_validation, cnt)

            l.append("# Functions: %s\n\n" % (fun))
            l.append("# File: %s\n\n" % it['cu'])
            l.append("# Patch: %s\n\n" % it['pname'])
            l.append("# Lines removed: %d\n\n" % it['len'])
            l.append("# Hunk text:\n\n")
            for i in it['htext']:
                l.append("%s\n" % i)

            print_val_file(fname, header, l)
            index.append("%d.val\t %s\n" % (cnt, fun))
            cnt += 1

    fname = '%s/functions_removed/1.val' % (path_validation)
    header['header'] = "Validation index for removed functions"
    header['keywords'] = 'index, validation, removed functions'
    print_val_file(fname, header, index)


def print_val_renamed(data):
    index = []
    cnt = 2
    index.append("this file")
    for cu in data.keys():
        for fun in data[cu]:
            it = data[cu][fun]
            l = []
            header['header'] = "Validation rename of function %s to %s" %\
                    (it['fun_old'], fun)
            header['keywords'] = 'rename function %s to %s' % \
                    (it['fun_old'], fun)
            fname = '%s/functions_renamed/%s.val' % (path_validation, cnt)

            l.append("# Fun ren: %s -> %s\n\n" % (it['fun_old'], fun))
            l.append("# File: %s\n\n" % it['cu'])
            l.append("# Patch: %s\n\n" % it['pname'])
            l.append("# Hunk text:\n\n")
            for i in it['htext']:
                l.append("%s\n" % i)

            print_val_file(fname, header, l)
            index.append("%d.val\t %s -> %s\n" % (cnt, it['fun_old'], fun))
            cnt += 1

    fname = '%s/functions_renamed/1.val' % (path_validation)
    header['header'] = "Validation index for renamed functions"
    header['keywords'] = 'index, validation, renamed functions'
    print_val_file(fname, header, index)





def print_val_file(fname, info, l):
    if not os.path.isdir(os.path.dirname(fname)):
        os.makedirs(os.path.dirname(fname))

    f = open(fname, 'w')
    f.write("%s\n" % info['header'])
    f.write("Author: %s\n" % info['author'])
    f.write("Review: %s\n" % info['review'])
    f.write("Date: %s\n" % info['date'])
    f.write("Expires: %s\n" % info['expires'])
    f.write("Keywords: %s\n" % info['keywords'])
    f.write("Phase: %s\n" % info['phase'])
    f.write("Ref: %s\n" % info['ref'])
    f.write("QA: %s\n" % info['qa'])
    f.write("Tracking: %s\n" % info['tracking'])
    f.write("Format: %s\n\n\n" % info['format'])
    for i in l:
        f.write('%s' % i)
    f.close()


