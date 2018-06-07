import os
import datetime

now = datetime.datetime.now()




funs = ['cgroup_disable', 'ext4_journalled_write_end', 'of_irq_init', 'show_free_areas', 'sk_clone_lock', 'arch_get_unmapped_area_topdown', 'perf_pmu_cancel_txn', 'bstr_printf', 'watchdog_set_timeout', 'gfpflags_to_migratetype', 'arpt_do_table', 'talitos_edesc_alloc', 'pci_revert_fw_address', 'print_bin_fmt', 'compute_score', 'request_key_auth_new', '__nft_trace_packet', 'packet_bind_spkt', 'ondemand_readahead', 'run_filter', 'synchronize_sched_expedited_wait','tcp_get_cookie_sock',
        'synchronize_sched_expedited', 'dma_pool_alloc', 'fsl_pci_mcheck_exception', 'mmc_send_tuning', 'task_name', 'ip_do_fragment', 'ext4_writepage', 'nf_tables_newchain', 'posix_acl_xattr_get']



path_validation = '%s/../validation/' % (os.getcwd())

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
header['date'] '%s-%s-%s' % (now.year, now.month, now.day)

def print_val_added(data):
    cnt = 1
    index = []
    for cu in data:
        for fun in data[cu]:
            l = []
            header['header'] = "Validation add lines function %s" % fun
            header['keywords'] = 'added lines, function: %s' % fun
            fname = '%s/functions_added/%s.val' % (path_validation, cnt)
            it = data[cu][fun]
            l.append("# Function: %s\n" % fun)
            l.append("# Patch   : %s\n" % it['pname'])
            l.append("# File    : %s\n\n" % cu)
            l.append("# Hunk    : %s\n\n" % cu)
            for i in it['htext']:
                l.append('%s\n'%i)
            l.append('\n# Result:')
            print_val_file(fname, )
            cnt += 1
            index.append(fun)


def print_val_renamed(data):
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


def print_val_file(info, fname):
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
    f.close()


