import logging

from spa.utils import *
from spa.host_cmds.battle import BattleCmds
from spa.host_cmds.download import DownloadCmds
from spa.host_cmds.special import SpecialCmds
from spa.host_cmds.users import UserCmds
from spa.host_cmds.voting import VotingCmds

log = logging.getLogger(__name__)


class HostCmds(object):
    def __init__(self, server, host):
        self.server = server
        log.info('HostCmds Init')
        self.Host = host
        self.commands = {}
        self.active_alias = {}
        self.battle_cmds = BattleCmds(self, server, host)
        self.special_cmds = SpecialCmds(self, server, host)
        self.download_cmds = DownloadCmds(self, server, host)
        self.user_cmds = UserCmds(self, server, host)
        self.voting_cmds = VotingCmds(self, server, host)
        self.load_alias()

    def handle_input(self, source, command, data, user):
        log.debug('Handle Input::%s::%s::%s', source, command, data)
        try:
            if command in self.battle_cmds.commands:
                return self.battle_cmds.handle_input(command, data, source)
            elif command in self.special_cmds.commands:
                return self.special_cmds.handle_input(command, data, user)
            elif command in self.download_cmds.commands:
                return self.download_cmds.handle_input(command, data)
            elif command in self.user_cmds.commands:
                return self.user_cmds.handle_input(command, data, user)
            elif command in self.voting_cmds.commands:
                return self.voting_cmds.handle_input(command, data, user, source)
            elif command in self.Host.config['ALIAS_COMMANDS']:
                if len(self.Host.config['ALIAS_COMMANDS'][command]) == 1:
                    command = self.Host.config['ALIAS_COMMANDS'][command][0]
                    for iArg in range(0, len(data)):
                        command = command.replace('%' + str(iArg + 1), data[iArg])
                    cmd = lsplit_or_str(command, ' ')
                    data_input = command[len(cmd) + 1:]
                    data_input = parse_input(data_input, self.commands[cmd][0])
                    if data_input[0]:
                        return self.handle_input(source, cmd, data_input[1], user)
                    else:
                        return [False, 'Alias command failed::' + data_input[1]]
                else:
                    result = [True, []]
                    for command in self.Host.config['ALIAS_COMMANDS'][command]:
                        for iArg in range(0, len(data)):
                            command = command.replace('%' + str(iArg + 1), data[iArg])
                        cmd = lsplit_or_str(command, ' ')
                        data_input = command[len(cmd) + 1:]
                        data_input = parse_input(data_input, self.commands[cmd][0])
                        if data_input[0]:
                            cmd_result = self.handle_input(source, cmd, data_input[1], user)
                            if not cmd_result[0]:
                                result[0] = False
                            if isinstance(cmd_result[1], list):
                                for line in cmd_result[1]:
                                    result[1].append(line)
                            else:
                                result[1].append(cmd_result[1])
                        else:
                            result[0] = False
                            result[1].append('Alias command failed::' + data_input[1])
                            break
                    result[1].append('Alias command completed')
                    return result
            else:
                return [False, 'Unknown command "' + str(command) + '"']
        except Exception:
            log.exception('Failed to handle input')
            return [False, 'Internal failure (crashed)']

    def load_alias(self):
        log.info('')
        if 'ALIAS_COMMANDS' in self.Host.config:
            for key in list(self.Host.config['ALIAS_COMMANDS'].keys()):
                iArgs = 0
                for command in self.Host.config['ALIAS_COMMANDS'][key]:
                    if '%' in command:
                        for arg in command.split('%')[1:]:
                            if ' ' in arg:
                                arg = arg[0:arg.index(' '):]
                        try:
                            iArgs = max(iArgs, int(arg))
                        except:
                            continue
                vars = []
                for iVar in range(0, iArgs):
                    vars.append('V')
                self.commands[key] = [vars, 'PM', '!' + key, '!' + key]
                self.active_alias[key] = 1

    def notifications(self, event):
        log.info('Notifications::' + str(event))
        if event == 'BATTLE_ENDED':
            print('* Battle ended')
        elif event == 'BATTLE_STARTED':
            print('* Battle started')
