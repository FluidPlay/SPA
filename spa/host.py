import logging
import threading

import os

from conf import settings
from model import session
from spa import lobby
from spa.utils import *
from spa.host_cmds import HostCmds
from spa.spring import Spring

log = logging.getLogger(__name__)


class Host(threading.Thread):
    def __init__(self, host_id, server, config):
        super().__init__()
        log.info('Host Init')
        self.host_id = host_id
        self.server = server
        self.config = config
        account_config = config['ACCOUNT']

        self.Lobby = lobby.Lobby(
            self.handle_input,
            self.handle_lobby_event,
            self.HandleLocalEvent,
            account_config
        )

        self.HostCmds = HostCmds(server, self)
        self.Spring = Spring(server, self, self.Lobby)
        self.battle = {
            'Mod': self.config['MOD'],
            'Map': self.config['MAP'],
            'BattleDescription': self.config['BATTLE_DESCRIPTION'],
            'BattlePassword': self.config.get('BATTLE_PASSWORD', '*'),
            'StartPosType': None,
            'MapOptions': {},
            'ModOptions': {},
            'Teams': 2,
        }
        self.command_threads = {}
        self.command_thread_id = 0
        self.command_seen = {}
        self.is_master = False

    def run(self):
        log.info('Start host')
        self.Lobby.start()
        for channel in self.config.get('LOBBY_CHANNELS', []):
            self.Lobby.join_channel(channel)
        self.set_default_mod()
        self.HostCmds.battle_cmds.logic.load_battle_defaults()
        log.info('Run finished')

        # Gets and releases the Master lock for the Host thread...
        self.server.get_master_lock(self)
        while self.is_master:
            time.sleep(1)
        self.server.release_master_lock(self)

    def handle_lobby_event(self, event, data):
        log.debug('Handle Lobby Event::' + str(event) + '::' + str(data))
        self.command_seen[event] = 1
        if event == 'DENIED':
            self.terminate('LOGIN_DENIED::' + str(data[0]))

        if 'EVENT_HOOKS' in self.config and event in self.config['EVENT_HOOKS']:
            for command in self.config['EVENT_HOOKS'][event]:
                self.handle_input('INTERNAL', '!' + command)

        if event == 'OPENBATTLE':  # Load the default settings for a battle
            self.HostCmds.battle_cmds.logic.update_battle()

    def HandleLocalEvent(self, event, data):
        log.debug(event + str(data))
        if event == 'SMURF_DETECTION_PUBLIC':
            pass
            # todo verify why it's blocking some hosts
            # if self.is_master:
            #     self.server.database.store_smurf(data[0], data[1], data[2], data[3], data[4])
        elif event == 'SMURF_DETECTION_BATTLE':
            self.server.database.store_smurf(data[0], data[1], data[2], data[3], data[4])
        elif event == 'USER_JOINED_BATTLE':
            if self.Spring.SpringUDP and self.Spring.SpringUDP.active:
                self.Spring.SpringUDP.add_user(data[0], data[1])
            self.handle_input('INTERNAL', '!sleepunsyncedmaplink ' + data[0])
            self.say_welcome(data[0])
        elif event == 'USER_LEFT_BATTLE':
            pass
        elif event == 'BATTLE_MAP_CHANGED':
            self.handle_input('INTERNAL', '!sleepunsyncedmaplink')
        else:
            print('')
            print(event)
            print(data)

    def say_welcome(self, user):
        try:
            with open(os.path.join(os.path.dirname(__file__), os.pardir, 'greeting.txt')) as f:
                welcome_message = "\n".join(l.rstrip() for l in f if l.rstrip() and not l.startswith("#"))
            uptime_seconds = (time.process_time() * 1000)
            uptime = time.gmtime(uptime_seconds)
            uptime_hours = uptime_seconds // (60 * 60)
            uptime_seconds %= (60 * 60)
            uptime_minutes = uptime_seconds // 60
            uptime_seconds %= 60

            uptime_verbose = ""
            if uptime_hours:
                uptime_verbose += "%i hours" % uptime_hours
                if uptime_minutes and uptime_seconds:
                    uptime_verbose += ","
                if uptime_minutes and not uptime_seconds:
                    uptime_verbose += " and "
            if uptime_minutes:
                if uptime_hours:
                    uptime_verbose += " "
                uptime_verbose += "%i minutes" % uptime_minutes
            if uptime_seconds:
                if uptime_hours or uptime_minutes:
                    uptime_verbose += " and "
                uptime_verbose += "%i seconds" % uptime_seconds

            unitsync_mod = self.get_unitsync_mod()
            welcome_message = welcome_message.format(**{
                'player_name': user,
                'server_name': self.config['BATTLE_DESCRIPTION'],
                'uptime_verbose': uptime_verbose,
                'uptime_formatted': time.strftime('%H:%M:%S', uptime),
                'mod_archive': unitsync_mod['Archive']
            })
            for message in welcome_message.split("\n"):
                self.Lobby.battle_say(message, 1)
        except OSError:
            log.warning("Greeting message could not be loaded.")

    def handle_input(self, source, data, user=None):
        log.debug('Handle Input::%s::%s', source, data)

        input_data = {'Raw': source + ' ' + ' '.join(data)}
        if source == 'SAIDPRIVATE':
            input_data['Source'] = 'PM'
            input_data['Return'] = 'PM'
            input_data['User'] = data[0]
            input_data['Input'] = data[1]
        elif source == 'SAIDBATTLE':
            input_data['Source'] = 'Battle'
            input_data['Return'] = 'BattleMe'
            input_data['User'] = data[0]
            input_data['Input'] = data[1]
            if self.Lobby.battle_id and self.config.get('ECHO_LOBBY_CHAT_TO_SPRING', False):
                self.Spring.SpringTalk('<' + input_data['User'] + '> ' + input_data['Input'])
        elif source == 'INTERNAL':
            input_data['Source'] = 'Battle'
            input_data['Return'] = 'BattleMe'
            input_data['User'] = user
            input_data['Input'] = data
        elif source == 'BATTLE_PUBLIC':
            input_data['Source'] = 'GameBattle'
            input_data['Return'] = 'BattleMe'
            input_data['User'] = user
            input_data['Input'] = data
        elif source == 'SAIDBATTLEEX':
            input_data['Source'] = 'BattleMe'
            input_data['Return'] = 'BattleMe'
            input_data['User'] = data[0]
            input_data['Input'] = self.convert_suggestion(data[1])

        if len(input_data) > 2:
            if lsplit_or_str(input_data['Input'], ' ')[0:1] == '!':
                self.command_threads[self.command_thread_id] = HostCommand(
                    self, self.command_thread_id, input_data,  source)
                self.command_thread_id += 1
                self.host_command_thread_cleanup()

    def user_access(self, command, user, vote=False):
        result = False

        access_commands = self.config.get('ACCESS_COMMANDS', {})
        access_roles = self.config.get('ACCESS_ROLES', {})
        if command in access_commands:
            roles_allowed = access_commands[command]
            if self.Lobby.battle_id and self.Lobby.users[self.Lobby.user]['InGame']:
                if vote:
                    vote_group = 3
                else:
                    vote_group = 2
            else:
                if vote:
                    vote_group = 1
                else:
                    vote_group = 0
            # todo review vote access
            # if len(roles_allowed) == 4:
            #     for group in roles_allowed[vote_group]:
            #         groups[group] = True

            if '%BattlePlayer%' in roles_allowed and user in self.Lobby.battle_users and \
                            self.Lobby.battle_users[user]['Spectator'] == 0:
                result = True
            elif '%BattleSpectator%' in roles_allowed and user in self.Lobby.battle_users and \
                            self.Lobby.battle_users[user]['Spectator'] == 1:
                result = True
            elif '%GamePlayer%' in roles_allowed and self.Spring.user_is_playing(user):
                result = True
            elif '%GameSpectator%' in roles_allowed and self.Spring.user_is_spectating(user):
                result = True
            elif user in self.Lobby.users:
                for role in roles_allowed:
                    if role in access_roles and user in access_roles[role]:
                        result = True
        else:
            result = True
        return result

    def handle_access(self, input, source='', vote=False):
        log.debug('HandleAccess::' + str(input['User']) + '::' + str(input['Command']) + '::' + str(vote))
        if source == 'INTERNAL':
            allowed = True
        else:
            allowed = self.user_access(input['Command'], input['User'], vote)

        if source == 'INTERNAL_AUTH_CHECK':
            return allowed
        elif not allowed and not vote:
            return self.handle_access(input, source, True)

        log.debug('HandleAccessResult::' + str(input['User']) + '::' + str(input['Command']) + '==' + str(allowed))
        if allowed:
            if vote:
                input['Data'] = [input['Command']] + input['data']
                input['Command'] = 'vote'
            command_return = self.HostCmds.handle_input(input['Source'], input['Command'], input['Data'], input['User'])
            input['CommandSuccess'] = command_return[0]
            input['Message'] = command_return[1]
        else:
            input['Message'] = 'You have no permissions for command "' + str(input['Command']) + '"'
            input['Return'] = 'PM'
        return input

    def ReturnInput(self, data):
        # If Return is a list, the first option is for successful command and the second for command failure
        if isinstance(data['Return'], list) and len(data['Return']) == 2 and 'CommandSuccess' in data:
            if data['CommandSuccess']:
                data['Return'] = data['Return'][0]
            else:
                data['Return'] = data['Return'][1]

        messages = []
        if isinstance(data['Message'], str):
            messages = [data['Message']]
        elif isinstance(data['Message'], list):
            messages = data['Message']

        if data['Return'][-9:] == 'Requester':
            data['Return'] = data['Return'][0:-9]
            if 'User' in data and data['User']:
                user = data['User']
            else:
                user = '<Unknown>'
            messages[0] = messages[0] + ' (req: ' + user + ')'

        if messages and len(messages) > 0:
            for message in messages:
                if message and len(message) > 0:
                    if data['Return'] == 'PM':
                        self.Lobby.user_say(data['User'], message)
                    elif data['Return'] == 'Battle':
                        self.Lobby.battle_say(message, 0)
                        if data['Source'] == 'PM':
                            self.Lobby.user_say(data['User'], message)
                    elif data['Return'] == 'BattleMe':
                        self.Lobby.battle_say(message, 1)
                        if data['Source'] == 'PM':
                            self.Lobby.user_say(data['User'], message)
                    elif data['Return'] == 'GameBattle':
                        self.Spring.SpringTalk(message)

    def convert_suggestion(self, data):
        info = data.split(' ')
        if len(info) > 1 and info[0] == 'suggests':
            if len(info) > 1 and info[1] == 'that':
                if len(info) > 6 and info[3] == 'changes' and info[4] == 'to' and info[5] == 'ally':
                    data = '!team ' + info[2] + ' ' + re.sub('\D', '', info[6])
                elif len(info) > 6 and info[3] == 'changes' and info[4] == 'to' and info[5] == 'team':
                    data = '!id ' + info[2] + ' ' + re.sub('\D', '', info[6])
                elif len(info) > 5 and info[3] == 'becomes' and info[4] == 'a' and info[5] == 'spectator.':
                    data = '!spec ' + info[2]
            else:
                data = '!map ' + data[9:]
        elif len(info) > 3 and info[0] == 'thinks' and info[2] == 'should':
            if info[3] == 'leave.':
                data = '!kick ' + info[1]
            elif len(info) > 7 and info[3] == 'get' and info[4] == 'a' and info[6] == 'resource' and info[7] == 'bonus':
                data = '!hcp ' + info[1] + ' ' + re.sub('\D', '', info[5])
        elif len(info) > 4 and info[0] == 'suggests' and info[1] == 'that' and info[3] == 'changes' and info[4] == 'colour.':
            data = '!fixcolor ' + info[2]
        return data

    def get_unitsync_mod(self, mod_name=None):
        if not mod_name:
            mod_name = self.battle['Mod']
        if mod_name in self.server.SpringUnitsync.Mods:
            return self.server.SpringUnitsync.Mods[mod_name]
        elif mod_name == '#KEYS#':
            return list(self.server.SpringUnitsync.Mods.keys())

    def get_unitsync_map(self, map_name=None):
        if not map_name:
            map_name = self.battle['Map']
        if map_name in self.server.SpringUnitsync.Maps:
            return self.server.SpringUnitsync.Maps[map_name]
        elif map_name == '#KEYS#':
            return list(self.server.SpringUnitsync.Maps.keys())

    def get_spring_binary(self, headless=False):
        if headless:
            spring_binary_path = settings.SPRING_HEADLESS_PATH
        else:
            spring_binary_path = settings.SPRING_DEDICATED_PATH

        log.info(spring_binary_path)
        return spring_binary_path

    def set_default_mod(self):
        log.info('Mod::' + str(self.battle['Mod']))
        pattern = re.compile(self.battle['Mod'])
        mods = []
        # log.info(self.server.SpringUnitsync.Mods)
        for mod in list(self.server.SpringUnitsync.Mods.keys()):
            if pattern.match(mod):
                mods.append(mod)
        log.info(mods)
        if len(mods) > 0:
            mods.sort(reverse=True)
            self.battle['Mod'] = mods[0]
            log.info('Mod::' + str(self.battle['Mod']))
        else:
            log.warning('No default mod found')

    def terminate(self, reason='', info=''):
        log.info(str(reason) + '::' + str(info))

        if self.Spring.stop('Terminate'):
            log.info('Spring::Stopped OK')
        else:
            log.error('Spring::Stopped Error')

        self.Lobby.terminate()
        self.is_master = False
        self.server.remove_host(self.host_id)

    def host_command_wait(self, lobby_event):
        log.debug(lobby_event)
        i_sleep = 0
        self.command_seen[lobby_event] = 0
        while not self.command_seen[lobby_event]:
            i_sleep += 1
            time.sleep(0.01)
            if i_sleep == 1000:  # 10 seconds, breaking the wait...
                log.warning('Breaking, time limit exceeded')
                return False
        return True

    def host_command_thread_cleanup(self):
        for thread_id in list(self.command_threads.keys()):
            if not self.command_threads[thread_id].active:
                del (self.command_threads[thread_id])


class HostCommand(threading.Thread):
    def __init__(self, host, command_thread_id, input_data, source):
        threading.Thread.__init__(self)
        self.Host = host
        self.CommandThreadID = command_thread_id
        self.active = True
        self.input_data = input_data
        self.source = source
        self.start()

    def run(self):
        log.info('HostCommand start')
        self.handle(self.input_data, self.source)
        session.remove()
        log.info('HostCommand run finished')
        self.active = False

    def handle(self, input_data, source):
        input_data['Command'] = lsplit_or_str(input_data['Input'], ' ')[1:]
        input_data['RawData'] = input_data['Input'][len(input_data['Command']) + 2:]
        input_data['Data'] = []

        if input_data['Command'] in self.Host.HostCmds.commands:
            if self.Host.HostCmds.commands[input_data['Command']][1] == 'Source':
                if input_data['Source'] == 'Battle':
                    input_data['Return'] = 'BattleMe'
                else:
                    input_data['Return'] = input_data['Source']
            else:
                input_data['Return'] = self.Host.HostCmds.commands[input_data['Command']][1]

            extracted = parse_input(input_data['RawData'], self.Host.HostCmds.commands[input_data['Command']][0])
            if not extracted[0]:
                input_data['Message'] = 'ERROR:' + str(extracted[1])
            else:
                input_data['Data'] = extracted[1]
                input_data = self.Host.handle_access(input_data, source)
        else:
            input_data['Message'] = ['UNKNOWN COMMAND ("' + str(input_data['Command']) + '")',
                                     'Use !help to list the available commands']
            input_data['Return'] = 'PM'

        if source != "INTERNAL":
            self.Host.ReturnInput(input_data)
