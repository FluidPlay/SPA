#!/usr/bin/env python
import argparse
import logging
import os
import sys
import time
from threading import RLock

from spa.daemon import Daemon
from spa.database_manager import DatabaseManager
from spa.host import Host
from spa.log import setup_default_logger
from spa.spring_unitsync import SpringUnitsync
from conf import settings

log = logging.getLogger(__name__)


class Server(Daemon):
    # Thread lock
    lock = None
    # Spring Unitsync wrapper
    SpringUnitsync = None
    # Database Manager interface
    database = None

    hosts = {}

    def run(self):
        log.info('Starting server')
        self.lock = RLock()
        self.SpringUnitsync = SpringUnitsync(self)
        self.database = DatabaseManager()
        self.spawn()
        while True:
            try:
                time.sleep(1)
            except SystemExit:
                self.terminate()
            except KeyboardInterrupt:
                self.terminate()
            except Exception as e:
                log.exception(e)

    def terminate(self):
        log.info('Terminating server')
        try:
            for host in self.hosts.values():
                host.terminate()
            sys.exit(0)
        except:
            sys.exit(-1)

    def spawn(self):
        log.info('Spawning hosts')

        for host in settings.HOSTS.keys():
            self.spawn_host(host)

    def get_master_lock(self, host):
        log.info('Request')
        self.lock.acquire()
        host.is_master = True
        log.info('Received')

    def release_master_lock(self, host):
        log.info('Release')
        try:
            self.lock.release()
            host.is_master = False
            log.info('Released')
        except:
            log.error('Release failed', 1)

    def spawn_host(self, host_id):
        log.info("Spawn Host %s", host_id)
        if host_id in settings.HOSTS and host_id not in self.hosts:
            config = settings.HOSTS[host_id]
            host = Host(host_id, self, config)
            self.hosts[host_id] = host
            host.start()
            return [True, 'Started ' + host_id]

    def remove_host(self, account):
        log.info('Removing host')
        del(self.hosts[account])


def main(command):
    setup_default_logger()
    logging.getLogger('spa.database').setLevel(logging.INFO)

    server = Server('server.pid', chdir=os.getcwd())

    if 'stop' == command:
        server.stop()
    elif 'start' == command:
        server.start()
    elif 'stop' == command:
        server.stop()
    elif 'restart' == command:
        server.restart()
    elif 'debug' == command:
        print('Starting without daemon...')
        server.run()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog='SPA', description='Spring Auto Host')
    parser.add_argument('command', choices=('start', 'stop', 'restart', 'debug'))
    args = parser.parse_args()
    main(**vars(args))
