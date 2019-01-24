#!/usr/bin/env python

# Version 1.0

import time
import os

from fabric.api import *

##
## available environments
##


def linode():
    env.hosts = ['root@45.79.199.177']
    env.app_root = '/srv/spring/'
    env.restart_script = './runserver.sh'
    env.git_origin = 'git@bitbucket.org:YuriHeupa/springautohost.git'
    env.git_branch = 'master'
    env.virtual = '~/.virtualenvs/spring/bin/activate'


##
## available commands
##

def deploy():
    start = time.time()

    ## validate environment
    if not hasattr(env, 'app_root'):
        print('ERROR: unknown environment.')
        os.sys.exit(1)

    ## clone repository
    command = 'test -d %s.git || git clone %s %s -b %s'
    sudo(command % (env.app_root, env.git_origin, env.app_root, env.git_branch))

    ## update repository
    command = 'cd "%s" && git reset --hard && git pull && git checkout -B %s origin/%s && git pull'
    run(command % (env.app_root, env.git_branch, env.git_branch))

    ## update python packages
    command = 'source %s; cd %s; pip install -r requirements.txt' % (env.virtual, env.app_root)
    run(command)

    ## restart service
    command = 'cd %s; %s ' % (env.app_root, env.restart_script)
    run(command)

    final = time.time()
    puts('execution finished in %.2fs' % (final - start))
