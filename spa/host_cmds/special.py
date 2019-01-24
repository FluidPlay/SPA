import inspect
import logging
import os
import time
from collections import deque

log = logging.getLogger(__name__)


class SpecialCmds(object):
    def __init__(self, host_cmds, server, host):
        self.server = server
        log.info('SpecialCmds Init')
        self.Host = host
        self.HostCmds = host_cmds
        self.commands = {
            # 0 = Field
            # 1 = Return to where (Source, PM, Battle)
            # 2 = Usage example
            # 3 = Usage desc
            # 4 = Category (if available)
            # 5 = Extended help (if available)
            'code': [[], 'PM', '!code', 'Displays the bots code files, bytes and last modified', 'Special'],
            'help': [['OV'], 'PM', '!help <optional term>', 'Displays help', 'Special',
                     ['!help        displays all available commands',
                      '!help he     displays all available commands containing "he"',
                      '!help help   if a single match is found, a more detailed help is displayed (like this)']],
            'terminate': [[], 'PM', '!terminate', 'Shuts down the bot', 'Special'],
            'terminateall': [[], 'PM', '!terminateall', 'Shuts down all bots', 'Special'],
            'infolog': [[], 'PM', '!infolog', 'Returns the last 20 lines from the hosts infolog', 'Special'],
            'showconfig': [[], 'PM', '!showconfig', 'Returns the bot\'s config', 'Special'],
            'battlesay': [['*'], 'BattleMe', '!battlesay <text>', 'The bot says <text> in the battle room'],
            'battlesayme': [['*'], 'BattleMe', '!battlesayme <text>', 'The bot says /me <text> in the battle room'],
            'sleepsay': [['I', '*'], 'Source', '!sleepsay <sleep> <text>', 'Says <text> with a delay of <sleep> sec'],
            'debug': [[], 'PM', '!debug', 'Displays debug information'],
            'sleepunsyncedmaplink': [['OV'], 'BattleMe', '!sleepunsyncedmaplink <optional user>',
                                     'If the <optional user or any user> is unsynced, the maplink is returned'],
            'spawnhost': [[], 'Source', '!spawnhost', 'Spawns another host if any is available', 'Special'],
        }
        for command in self.commands:
            self.HostCmds.commands[command] = self.commands[command]

    def handle_input(self, command, data, user):
        log.debug('Handle Input::%s::%s', command, data)

        if command == 'code':
            path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            result = []
            length = 0
            size = 0
            last_change = 99999999999
            files = []
            for file_name in os.listdir(path):
                if file_name[-3:] == '.py' and file_name != 'unitysync.py':
                    length = max(length, len(file_name))
                    last_change = min(last_change, time.time() - os.path.getmtime(path + '/' + file_name))
                    size = size + os.path.getsize(path + '/' + file_name)
                    files.append(file_name)
            for file in files:
                result.append(
                    self.string_pad(file, length, ' ') + '  ' +
                    self.string_pad(str(os.path.getsize(path + '/' + file)), 8, ' ') + '  ' +
                    str(round((time.time() - os.path.getmtime(path + '/' + file)) / 3600, 1)) + " hours ago")
            result.sort()
            result.append(
                self.string_pad('Summary:', length, ' ') + '  ' + self.string_pad(str(size), 8, ' ') + '  ' + str(
                    round(last_change / 3600, 1)) + " hours ago")
            return [True, result]
        elif command == 'help':
            commands = {}
            matches = 0
            for command in self.HostCmds.commands:
                if command not in self.HostCmds.active_alias:  # Exclude all alias commands
                    line = self.HostCmds.commands[command][2] + '   ' + self.HostCmds.commands[command][3]
                    if len(self.HostCmds.commands[command]) > 4:
                        category = self.HostCmds.commands[command][4]
                    else:
                        category = '*'
                    if category not in commands:
                        commands[category] = []
                    if len(data) == 0:
                        if self.Host.handle_access({'Command': command, 'User': user}, 'INTERNAL_AUTH_CHECK'):
                            commands[category].append(line)
                            matches += 1
                            match = command
                    elif data[0].lower() in line.lower():
                        if self.Host.handle_access({'Command': command, 'User': user}, 'INTERNAL_AUTH_CHECK'):
                            commands[category].append(line)
                            matches += 1
                            match = command
            result = []
            if matches == 1:
                result.append('===!' + match + '===')
                result.append(self.HostCmds.commands[match][2])
                result.append(self.HostCmds.commands[match][3])
                if len(self.HostCmds.commands[match]) > 5:
                    for line in self.HostCmds.commands[match][5]:
                        result.append(' ' + line)
            else:
                if len(commands) > 0:
                    categories = list(commands.keys())
                    categories.sort()
                    for category in categories:
                        if len(commands[category]):
                            if category != '*':
                                result.append('===' + category + '===')
                                commands[category].sort()
                                result = result + commands[category]
                                # Return.append(chr(160))  # No-break space char
                                result.append(" ")  # No-break space char
                    if '*' in commands and len(commands['*']):
                        result.append('===Uncategorized===')
                        commands['*'].sort()
                        result = result + commands['*']
                else:
                    result = 'No help was found for that command'
            return [True, result]
        elif command == 'terminate':
            self.Host.terminate()
            return [True, 'Terminated']
        elif command == 'terminateall':
            self.server.terminate()
            return [True, 'All hosts terminated']
        elif command == 'infolog':
            try:
                file = open('~/.spring/infolog.txt', 'r')
            except IOError as Error:
                log.error('File open failed: ' + str(Error))
                return [False, 'Infolog read failed']
            result = deque([])
            for line in file:
                result.append(line)
                if len(result) > 20:
                    result.popleft()
            file.close()
            return [True, ['Last 20 lines of the infolog:'] + list(result)]
        elif command == 'showconfig':
            result = []
            for k, v in self.Host.config.items():
                if not isinstance(v, dict) and not isinstance(v, list):
                    result.append(k + ' => ' + str(v))
            result.sort()
            return [True, ['Autohost config:'] + result]
        elif command == 'battlesay':
            self.Host.Lobby.battle_say(data[0])
            return [True, 'OK']
        elif command == 'battlesayme':
            self.Host.Lobby.battle_say(data[0], 1)
            return [True, 'OK']
        elif command == 'sleepsay':
            time.sleep(data[0])
            return [True, data[1]]
        elif command == 'debug':
            result = []
            if self.Host.Lobby.battle_id:
                result.append('===BattleUsers===')
                for user in list(self.Host.Lobby.battle_users.keys()):
                    result.append(user + '\t' + str(self.Host.Lobby.battle_users[user]))
            return [True, result]
        elif command == 'sleepunsyncedmaplink':
            time.sleep(1)
            current_map = self.Host.battle['Map']
            time.sleep(4)
            if len(data) == 1:
                users = [data[0]]
            else:
                users = list(self.Host.Lobby.battle_users.keys())
            for user in users:
                if user in self.Host.Lobby.battle_users:
                    for x in range(0, 5):
                        if 'Synced' not in self.Host.Lobby.battle_users[user]:
                            time.sleep(1)
                        elif self.Host.Lobby.battle_users[user]['Synced'] != 1:
                            if current_map == self.Host.battle['Map']:
                                return self.HostCmds.download_cmds.handle_input('maplink', [])
            return [False, '']
        elif command == 'spawnhost':
            # todo spawn custom host ids specified by parameters
            return self.Host.server.spawn_host(self.Host.host_id)

    def string_pad(self, value, length, char='0'):
        while len(value) < length:
            value = value + str(char)
        return value
