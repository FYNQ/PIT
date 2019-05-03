import os
import sys
import time
import json
import psutil
import subprocess
import asyncio
import aioredis
import argparse
import threading
import cron_pit

from mydaemon import Daemon

from apscheduler.schedulers.background import BackgroundScheduler


DAEMON_NAME = 'PITREDIS'
DAEMON_STOP_TIMEOUT = 10
PIDFILE = '/tmp/pit_redis.pid'
RUNFILE = '/tmp/pit_redis.run'
DEBUG = 1


global scheduler
global th_cron_pit
global state

def do_cmd(cmd, path):
    process = subprocess.Popen(cmd, cwd=path, shell=True,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)

def cron_pit_running():
    for proc in psutil.process_iter():
        if 'python3' in proc.cmdline() and 'cron_pit.py' in proc.cmdline():
            return True
    return False



class thcpit(threading.Thread):
    def __init__(self):
        print('init thread')
        threading.Thread.__init__(self)
        self._state = False

    def run(self):
        self._state = True
        cron_pit.start()

def do_job():
    print('APTScheduler')
    global th_cron_pit
    if th_cron_pit == False:
        th_cron_pit = thcpit()
        th_cron_pit.start()
    elif th_cron_pit.isAlive() == False:
        th_cron_pit = thcpit()
        th_cron_pit.start()


async def ping_register(name, arch):
    global state
    lstate = 'not_connected'
    pub = None

    while True:
        # check if redis is available
        print('state::lstate    %s::%s' % (state, lstate))
        if lstate == 'not_connected':
            try:
                print('Try to connect')
                #pub = await aioredis.create_connection('redis://pit_redis')
                pub = await aioredis.create_redis('redis://pit_redis')
                state = 'ping_register'
                lstate = 'connected'
            except Exception as exerr:
                print('redis server not available lets try in 5 seconds again ...')
                await asyncio.sleep(5)
                continue

        # redis available and global state ping_register
        if state == 'ping_register' and lstate == 'connected':
            pub = await aioredis.create_redis('redis://pit_redis')
            print("Try to register")
            res = await pub.publish_json('register', { 'name' : name,
                                                       'arch' : arch })
            asyncio.ensure_future(register(name, arch))
            await asyncio.sleep(5)

        # registered no need to keep running
        if state == 'registered' and lstate == 'connected':
            pub.close()
#            sub.close()
            break

async def register(name, arch):
    global state
    pub = None
    sub = None
    data = {'name':name, 'arch':arch}
    while True:
        if state == 'wait_for_connection':
            await asyncio.sleep(5)
            continue

        if state == 'ping_register':
            if pub == None and sub == None:
                pub = await aioredis.create_redis('redis://pit_redis')
                sub = await aioredis.create_redis('redis://pit_redis')
                res = await sub.subscribe('cmd_' + name)
                ch_main = res[0]

            print('ping register')
            message = await ch_main.get_json()
            print("Got Message:", message)
            if 'cmd' in message.keys():
                if message['cmd'] == 'registered':
                    state = 'registered'
                    asyncio.ensure_future(cmd_mux(name, arch))
                    break
        else:
            await asyncio.sleep(5)
            print('sleep')

    print('register done ...')
    sub.close()
    pub.close()


async def cmd_mux(name, arch):
    global state
    global scheduler
    lstate = 'not_connected'
    pub = await aioredis.create_redis('redis://pit_redis')
    sub = await aioredis.create_redis('redis://pit_redis')
    res = await sub.subscribe('cmd_' + name)
    ch_main = res[0]
    print('Listen to cmd_%s' % name)

    while True:
        print('Wait')
        try:
            await ch_main.wait_message()
            message = await ch_main.get_json()
        except:
            asyncio.ensure_future(ping_register(name, arch))
            asyncio.ensure_future(register(name, arch))


        print("Got Message:", message)
        jobf = '/home/user/src/python/jobs.txt'

        if 'get_data' in message.keys():
            if message['get_data'] == 'kconfigs':
                print('get_data - kconfig')
                path = '/home/user/src/kconfigs/%s' % arch
                a = os.listdir(path)
                pub.publish(name, json.dumps({ 'type': 'kconfigs' ,
                                               'data' : '\n'.join(a)}))
            if message['get_data'] == 'results':
                print('get_results')
                path = '/home/user/results/'
                results = os.listdir(path)
                data = {}
                for fname in results:
                    if fname.endswith('.json') or fname.endswith('.csv'):
                        _fname = path + fname
                        if os.path.isdir(_fname):
                            continue
                        if fname.endswith('.json'):
                            with open(_fname) as f:
                                fdata = json.load(f)
                            data.update({fname: fdata})
                        if fname.endswith('.csv'):
                            with open(_fname) as f:
                                fdata = f.readlines()
                            data.update({fname: fdata})

                print("Data send to monitor")
                pub.publish(name, json.dumps({ 'type': 'results',
                                               'data' : data,
                                               'origin': name}))
                continue

            if message['get_data'] == 'jobs':
                print('get_jobs')
                data = {}

                if os.path.isfile(jobf):
                    jobs_data = []
                    with open(jobf, 'r') as f:
                        for line in f:
                            if line.startswith('#'):
                                continue
                            line_s = line.split(' ')
                            jobs_data.append({'version': line_s[0],
                                              'kconfig': line_s[1],
                                              'arch' : line_s[2].strip('\n')})

                        data.update({'jobs': jobs_data})
                else:
                    data = {'jobs': 'None'}
                print("Data jobs send to monitor")
                print(data)
                pub.publish(name, json.dumps({ 'type': 'jobs',
                                               'data' : data,
                                               'origin': name}))
                continue


        if 'cmd' in message.keys():
            if 'add_job' in message['cmd']:
                dest = message['dest']
                job_lst = []
                scheduler.pause()
                jobs = []
                if os.path.isfile(jobf):
                    with open(jobf,'r') as f:
                        jobs = f.readlines()
                for job in jobs:
                    job_lst.append(job.split(' ')[0])

                if not dest['version'] in job_lst:
                    #cron = dest['cron']
                    jobs.append(dest['version'] + ' '
                                + dest['kconfig'] + ' '
                                + arch + '\n')

                    with open(jobf, 'w') as out_file:
                        for line in jobs:
                            out_file.write(line)
                print('Job added to cron_pit')
                scheduler.resume()
            else:
                print('---- MESSAGE ----')
                print(message)

            continue
        if 'type' in message.keys():
            if message['type'] == 'rm_job':
                scheduler.pause()
                jobs = []
                with open('./jobs.txt') as f:
                    for line in f:
                        if line.split(' ')[0] == message['version'] and \
                            line.split(' ')[1] == message['kconfig']:
                            continue
                        else:
                            jobs.append(line)

                    with open('./jobs.txt', 'w') as out_file:
                        for line in jobs:
                            out_file.write(line)
                print('Job added to cron_pit')
                scheduler.resume()


    await sub.unsubscribe('cmd_')
    sub.close()
    pub.close()

def start(name, arch, loop):
    global state
    global scheduler
    scheduler = BackgroundScheduler()
    scheduler.start()
    scheduler.add_job(do_job, 'interval', minutes=1, id='cron_pit')

    state = 'wait_for_connection'
    asyncio.ensure_future(ping_register(name, arch))

    loop.run_forever()
    print("Done")

def get_args():
    try:
        parser =  argparse.ArgumentParser()
        parser.add_argument('action', help='action',
                            choices=['start', 'stop', 'restart'])
        args = parser.parse_args()

        result = (args.action, )
    except Exception as err:
        if DEBUG:
            raise
        else:
            sys.stderr.write('%s\n' % (err))

        result = (None, )

    return result

class PITRedisDaemon(Daemon):
    def run(self):
        # Run while there is no stop request.
        loop = asyncio.get_event_loop()
        while os.path.exists(RUNFILE):
            try:
                pass
            except Exception as err:
                if DEBUG:
                    raise
                else:
                    sys.stderr.write('%s\n' % (err))
            finally:
               # Start
                host = os.environ['HOST']
                arch = os.environ['ARCH']
                start(host, arch, loop)
    def stop():
        global scheduler
        scheduler.shutdown()


if __name__ == '__main__':
    global state
    global scheduler
    global th_cron_pit

    scheduler = None
    th_cron_pit = False
    state = 'wait_for_connection'

    try:
        (action, ) = get_args()

        d = PITRedisDaemon(name=DAEMON_NAME, pidfile=PIDFILE, runfile=RUNFILE,
                     stoptimeout=DAEMON_STOP_TIMEOUT, debug=DEBUG)

        # Action requested.
        if action == 'start':
            d.start()
        elif action == 'stop':
            d.stop()
        elif action == 'restart':
            d.restart()
        else:
            raise NameError('Unknown action')

        sys.exit(0)
    except Exception as err:
        if DEBUG:
            raise
        else:
            sys.stderr.write('%s\n' % err)

        sys.exit(1)

