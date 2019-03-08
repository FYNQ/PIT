import os
import json
import csv

def wr_results(tag, jobs_done, kconfig, prefix):
    res_sum_col = []
    res_sum_col_R = []
    res_lines_col = []
    res_lines_col_R = []
    res_patches_col = []
    res_patches_col_R = []
    res_funs_col = []
    res_funs_col_R = []

    res_sum_col.append(["Version","Patches total", "Patches applied", \
                             "Function added", "Function removed", \
                             "Function renamed", "Lines added", \
                             "Lines removed"])
    res_sum_col_R.append(["Version", "Date", "Patches total", \
                             "Patches applied", \
                             "Function added", "Function removed", \
                             "Function renamed", "Lines added", \
                             "Lines removed"])

    for djob in jobs_done[tag][:-1]:
            fname = '/home/user/build/%s/%s/summary_data.json' % (djob, kconfig)
            with open(fname, 'r') as f:
                d = json.load(f)
            res_sum_col.append([d['tag'], d['patches_tot'], d['patches'], \
                    d['funs_add'], d['funs_rm'], d['funs_ren'], d['lines_add'], \
                    d['lines_rm']])

            res_sum_col_R.append([d['tag'], d['date'], d['patches_tot'],   \
                    d['patches'], d['funs_add'], d['funs_rm'], d['funs_ren'], \
                    d['lines_add'], d['lines_rm']])


            res_lines_col.append([d['tag'], d['lines_add'], d['lines_rm']])

            res_lines_col_R.append([d['tag'], d['date'], d['lines_add'], \
                    d['lines_rm']])

            res_patches_col.append([d['tag'], d['patches_tot'], d['patches']])

            res_patches_col_R.append([d['tag'], d['date'], d['patches_tot'], \
                    d['patches']])

            res_funs_col.append([d['tag'], d['funs_add'], d['funs_rm'],\
                    d['funs_ren']])

            res_funs_col_R.append([d['tag'], d['date'],d['funs_add'], \
                    d['funs_rm'], \d['funs_ren']])


    fname = prefix + 'sum_col.json'
    with open(fname, 'w') as f:
        json.dump(res_sum_col, f)

    fname = prefix + 'sum_col_R.json'
    with open(fname, 'w') as f:
        json.dump(res_sum_col_R, f)

    fname = prefix + 'sum_col_R.csv'
    with open(fname, 'w') as f:
        f_csv = csv.writer(f)
        f_csv.writerows(res_sum_col_R)



    fname = prefix + 'lines_col_R.csv'
    with open(fname, 'w') as f:
        f_csv = csv.writer(f)
        f_csv.writerows(res_lines_col_R)

    fname = prefix + 'lines_col.csv'
    with open(fname, 'w') as f:
        f_csv = csv.writer(f)
        f_csv.writerows(res_lines_col_R)

    fname = prefix + 'patches_col.csv'
    with open(fname, 'w') as f:
        f_csv = csv.writer(f)
        f_csv.writerows(res_patches_col_R)

    fname = prefix + 'patches_col_R.csv'
    with open(fname, 'w') as f:
        f_csv = csv.writer(f)
        f_csv.writerows(res_patches_col_R)

    fname = prefix + 'funs_col.csv'
    with open(fname, 'w') as f:
        f_csv = csv.writer(f)
        f_csv.writerows(res_funs_col_R)

    fname = prefix + 'funs_col_R.csv'
    with open(fname, 'w') as f:
        f_csv = csv.writer(f)
        f_csv.writerows(res_funs_col_R)

