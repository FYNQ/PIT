# PIT
Pacht Impact Test - Check what patch effects your configuration between two kernel versions

# Requirements

Data volumes with the names:

* linux\_src
* pit\_data
* pit\_results

Note: A docker for LINUX stable source volume can be found in the LINUX\_VOL repository.


# Install and start

```
$ ~/PIT/src/docker-compose build  --no-cache pit_x86
$ ~/PIT/src/docker-compose up pit_x86
```

For other architecture and corresponding ports check docker-compose.yml

# Connect with ssh

Connect via to X86\_64 container via port 1233 (user/nopasswd).

```
# ssh user@localhost -p 1233
$ cd /home/user/src/python
$ python3 check_series.py -f v4.13 -l v4.14.67 -k ppc_men_defconfig -a x86_64
```

# Configure CPUs

Modify the CPUs variable to use more/less than 4 cores.

```
/home/user/src/python/conf.py
```

# Run

## check_series.py

Used to run a single series of kernel version e.g. v4.4.10 .. v4.4.12


```
$ cd /home/user/src/python
$ python3 check_series.py -f v4.13 -l v4.14.67 -k ppc_men_defconfig -a x86_64
```

### Results

### Summary

```
cat ~/build/v4.10.2/i7_x86_minimal_defconfig$/summary_data.json

{"tag": "v4.10.2", "lines_rm": 67, "funs_rm": 1, "lines_add": 86, "date": 413693.7638888889, "funs_tot": 17, "patches": 9, "funs_add": 3, "patches_tot": 76, "funs_ren": 2}

```

**Format**

- tag: kernel verion tag
- lines_rm: lines removed
- lines_add: lines added
- funs_added: functions added
- funs_ren: functions renamed
- functions total: functions modified
- patches: patches applied
- patches_tot: patches total


### Functions

```
cat ~/build/v4.10.2/i7_x86_minimal_defconfig$/functions_data.json
```

**Format**
```
[["mem_cgroup_alloc", 1, 1, "mm/memcontrol.c", ["44c95966fb817b0b6f9d17fb0ec524011135d176"], "MOD"], [...

[function, lines added, lines removed, file, [list of commits], function - added/modified], [ ...
```
## cron_pit.py

### Configure

```
$ cd /home/user/src/python
$ cp jobs_example.txt jobs.txt
```

**Format**

kernel base version (e.g. v4.9) | kernel config | architecture

e.g.

```
# comment can be here!
v4.4 i7_x86_64_minimal_defconfig x86_64

```

### Run

```
python3 cron_pit.py

```

### Results


PIT generates output in csv and json format.


**Summary table**

e.g. v4.3_sum_col_R.csv

| Version | Patches total | Patches applied | Function added | Function removed | Function renamed | Lines added | Lines removed | 
| ---- | ---- | ---- | ---- | ---- | ---- | ---- | ---- |
| v4.3 | 11528 | 902 | 340 | 102 | 63 | 6212 | 4878 |
|v4.4-rc1|335|50|11|5|6|346|392|
|v4.4-rc2|234|13|0|0|0|38|20|
|v4.4-rc3|280|42|6|3|1|247|199|
|v4.4-rc4|217|25|2|2|0|168|149|
|v4.4-rc5|260|27|5|0|0|154|86|
|v4.4-rc6|81|2|0|0|0|2|2|
|v4.4-rc7|64|12|3|1|4|65|67|


and:

- v4.3_patches_col_R.csv -> patches total/patches applied
- v4.3_funs_col_R.csv -> functions added/removed/renamed
- v4.3_lines_col_R.csv -> lines added/removed

**NOTE**

As the GCC plugin executes after the preprocessor, pachtes affecting Macros cannot be detected.
