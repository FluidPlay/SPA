import hashlib
import logging
import os
import urllib.error
import urllib.parse
import urllib.request
from xmlrpc.client import ServerProxy

from conf import settings

log = logging.getLogger(__name__)


class DownloadCmds(object):
    def __init__(self, host_cmds, server, host):
        self.server = server
        log.info('DownloadCmds Init')
        self.Host = host
        self.host_cmds = host_cmds
        self.commands = {
            # 0 = Field
            # 1 = Return to where (Source, PM, Battle)
            # 2 = Usage example
            # 3 = Usage desc
            # 4 = Category (if available)
            # 5 = Extended help (if available)
            'downloadsearch': [['*'], 'PM', '!downloadsearch <mod>', 'Searches for the specified file'],
            'downloadmod': [['*'], 'PM', '!downloadmod <mod>', 'Downloads the specified mod'],
            'downloadmap': [['*'], 'PM', '!downloadmap <map>', 'Downloads the specified map'],
            'maplink': [[], 'Source', '!maplink', 'Provides the current maplink'],
            'modlink': [[], 'Source', '!modlink', 'Provides the current modlink'],
        }
        for command in self.commands:
            self.host_cmds.commands[command] = self.commands[command]

        log.info('XMLRPC Init')
        self.XMLRPC_Proxy = ServerProxy('http://api.springfiles.com/xmlrpc.php')

    def handle_input(self, command, Data):
        log.debug('Handle Input::' + str(command) + '::' + str(Data))

        if command == 'downloadsearch':
            results = self.XMLRPC_Proxy.springfiles.search(
                {"logical": "or", "tag": Data[0], "filename": Data[0], "springname": Data[0], "torrent": True,
                 "nosensitive": True})
            if results:
                result = ['Found matcher (top 10 max):']
                for r in results:
                    result.append('* ' + str(r['springname']) + ' (' + str(r['filename']) + ')')
                return [True, result]
            else:
                return [False, 'No matches found for "' + str(Data[0]) + '".']
        elif command == 'downloadmod':
            r = self.XMLRPC_Proxy.springfiles.search(
                {"logical": "or", "tag": Data[0], "filename": Data[0], "springname": Data[0], "torrent": True})
            if not r:
                return [False, 'No match found for "' + str(Data[0]) + '".']
            if not len(r) == 1:
                return [False, 'To many matches found for "' + str(Data[0]) + '", only one match is allowed.']
            else:
                if self.download_file(r[0], 'MOD'):
                    return [True, 'Downloaded the mod "' + str(r[0]['springname']) + '".']
                else:
                    return [False, 'Download failed for the mod "' + str(Data[0]) + '".']
        elif command == 'downloadmap':
            r = self.XMLRPC_Proxy.springfiles.search(
                {"logical": "or", "tag": Data[0], "filename": Data[0], "springname": Data[0], "torrent": True})
            if not r:
                return [False, 'No match found for "' + str(Data[0]) + '".']
            if not len(r) == 1:
                return [False, 'To many matches found for "' + str(Data[0]) + '", only one match is allowed.']
            else:
                if self.download_file(r[0], 'MAP'):
                    return [True, 'Downloaded the map "' + str(r[0]['springname']) + '".']
                else:
                    return [False, 'Download failed for the map "' + str(Data[0]) + '".']
        elif command == 'maplink' or command == 'modlink':
            if command == 'maplink':
                download_type = 'Map'
            else:
                download_type = 'Mod'
            log.info(download_type + 'link:' + str(self.Host.battle[download_type]))
            r = self.XMLRPC_Proxy.springfiles.search(
                {"logical": "or", "tag": self.Host.battle[download_type], "filename": self.Host.battle[download_type],
                 "springname": self.Host.battle[download_type], "torrent": True})

            if not r or not len(r) == 1 or 'mirrors' not in r[0]:
                if not r:
                    log.warning('Download link not found for ' + download_type.lower())
                elif not len(r) == 1:
                    log.warning(
                               'Multiple download links found for ' + download_type.lower() + ' (' + str(len(r)) + ')')
                else:
                    log.warning('No mirror found')
                return [False, 'No download link found for the current ' + download_type.lower()]
            else:
                for Mirror in r[0]['mirrors']:
                    return [True, download_type + ' download link: ' + str(Mirror).replace(' ', '%20')]

    def download_file(self, result, download_type):
        log.info('')
        file_path = getattr(settings, "%sS_PATH" % download_type) + result['filename']
        file_path = os.path.expanduser(file_path)
        if self.download_file_verify(file_path, 'Local', result):
            return True

        if (download_type == 'MAP' and result['category'] == 'map') or (download_type == 'Mod' and result['category'] == 'game'):
            for mirror in result['mirrors']:
                log.info('Download:' + str(mirror))
                urllib.request.urlretrieve(mirror, file_path)
                if self.download_file_verify(file_path, mirror, result):
                    if self.server.SpringUnitsync.load():
                        if download_type == 'MAP':
                            self.host_cmds.battle_cmds.logic.switch_map(None, 'Reorder')
                        return True
                    else:
                        log.error('Unitsync re-load failed')

    def download_file_verify(self, file_path, mirror, result):
        if os.path.exists(file_path) and int(os.path.getsize(file_path)) == int(result['size']):
            if hashlib.md5(open(file_path, 'rb').read()).hexdigest() == result['md5']:
                return True
            else:
                log.warning('Download failed (MD5):' + str(mirror))
        else:
            log.warning('Download failed (size):' + str(mirror))
