import base64
import binascii
import hashlib
import logging
import socket
import threading
import time

from conf import settings
from utils import lsplit_or_str

log = logging.getLogger(__name__)


class Lobby(threading.Thread):
    def __init__(self, chat_callback, event_callback,
                 internal_event_callback, login_info):
        super().__init__()
        self.callback_chat = chat_callback
        self.event_callback = event_callback
        self.callback_internal_event = internal_event_callback
        self.user = None
        self.password = None
        self.battle_port = None
        self.ip = None
        self.set_login_info(login_info)
        self.class_ping = None  # Ping class
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.active = False
        self.logged_in = False
        self.allow_reconnect = True
        self.logged_in_queue = []

        self.users = {}
        self.battles = {}
        self.battle_users = {}
        self.battle_id = 0
        self.channels = {}

        # I = Int, F = Float, V = String, S = Sentence, BXX = BitMask XX chars, * = Everything else
        self.commands = {
            'TASServer': ['V', 'V', 'I', 'I'],
            'ACCEPTED': ['V'],
            'MOTD': ['S'],  # Ignore
            'LOGININFOEND': [],  # Ignore
            'PONG': [],  # Ignore
            'ADDUSER': ['V', 'V', 'I', '*'],
            'REMOVEUSER': ['V'],
            'CLIENTSTATUS': ['V', 'B7'],
            'BATTLEOPENED': ['I', 'I', 'I', 'V', 'V', 'I', 'I', 'I', 'I', 'I', 'S', 'S', 'S', 'S', 'S'],
            'JOINEDBATTLE': ['I', 'V', 'V'],
            'LEFTBATTLE': ['I', 'V'],
            'BATTLECLOSED': ['I'],
            'UPDATEBATTLEINFO': ['I', 'I', 'I', 'I', 'S'],
            'SAIDPRIVATE': ['V', 'S'],
            'SAIDPRIVATEEX': ['V', 'S'],
            'SAYPRIVATE': ['V', '*'],  # Ignore ECHO reply...
            'SAID': ['V', 'V', 'S'],
            'SAIDEX': ['V', 'V', 'S'],
            'SAIDBATTLE': ['V', 'S'],
            'SAIDBATTLEEX': ['V', 'S'],
            'REQUESTBATTLESTATUS': [],
            'JOINBATTLEREQUEST': ['V', 'V'],
            'JOINBATTLE': ['I', 'I'],
            'CHANNELTOPIC': ['V', 'V', 'I', 'S'],
            'CLIENTBATTLESTATUS': ['V', 'B32', 'I'],
            'OPENBATTLE': ['I'],
            'JOIN': ['V'],
            'CLIENTS': ['V', 'S'],
            'JOINED': ['V', 'V'],
            'LEFT': ['V', 'V'],
            'ADDBOT': ['I', 'V', 'V', 'B32', 'I', 'S'],
            'REMOVEBOT': ['I', 'V'],
            'DENIED': ['S'],
            'UPDATEBOT': ['I', 'V', 'B32', 'I'],
            'SERVERMSG': ['S'],
            'ADDSTARTRECT': ['I', 'I', 'I', 'I', 'I'],
            'REMOVESTARTRECT': ['I'],
            'AGREEMENTEND': [],
            'SETSCRIPTTAGS': ['*'],
            'DISABLEUNITS': ['*'],
            'ENABLEALLUNITS': [],
        }

    def run(self):
        log.info('Lobby start')
        self.connect()
        raw_data = ''
        while self.active:
            info = {"Time": int(time.time()), "Loops": 0}
            while self.active:
                data = self.socket.recv(1).decode('latin1')
                if data:
                    raw_data = raw_data + data
                    lines = raw_data.split("\n")
                    if len(lines) > 1:
                        raw_data = lines[1]
                        self.handle_command(lines[0])
                else:
                    if info["Time"] == int(time.time()):
                        info["Loops"] = info["Loops"] + 1
                        if info["Loops"] > 10:
                            self.reconnect()
                    else:
                        info = {"Time": int(time.time()), "Loops": 0}
                    print("*** No data :/")
        log.info('Lobby run finished')

    def reset_battle(self):
        self.battle_users = {}
        self.battle_id = 0

    def set_login_info(self, login_info):
        log.debug('Loading login info %s', login_info)
        self.user = login_info['USER']
        self.password = login_info['PASSWORD']
        self.battle_port = login_info['PORT']

    def handle_command(self, raw_data, echo=0):
        if echo:
            log.debug('ECHO Command::' + str(raw_data))
        else:
            log.debug('Command::' + str(raw_data))
        command = lsplit_or_str(raw_data, ' ')
        data = raw_data[len(command) + 1:]
        if command in self.commands:
            arg = []
            try:
                for field in self.commands[command]:
                    raw_arg = ''
                    if field == 'I':
                        new_arg = int(lsplit_or_str(data, ' '))
                    if field == 'F':
                        new_arg = float(lsplit_or_str(data, ' '))
                    elif field == 'V':
                        new_arg = str(lsplit_or_str(data, ' '))
                    elif field[0:1] == 'B':
                        raw_arg = lsplit_or_str(data, ' ')
                        new_arg = self.dec2bin(raw_arg, int(field[1:]))
                    elif field == 'S':
                        new_arg = lsplit_or_str(data, '\t')
                    elif field == '*':
                        new_arg = data
                    try:
                        arg.append(new_arg)
                        if len(raw_arg) > 0:
                            new_arg = raw_arg
                        data = data[len(str(new_arg)) + 1:]
                    except:
                        print('\n\nCOMMAND FAILED\n\n')
            except:
                log.exception('WrongFormattedCommand::' + str(raw_data))
                return None
        else:
            log.error('UnknownCommand::' + str(raw_data))

        if command == "TASServer":
            self.login()
        elif command == "ACCEPTED":
            self.set_logged_in()
        elif command == 'LOGININFOEND' or command == 'PONG' or command == 'MOTD':
            pass
        elif command == "ADDUSER":
            if arg[0] not in self.users:
                # Workaround for ChanServ account not having accountID
                account_id = None if arg[3] == "None" else int(arg[3])
                self.users[arg[0]] = {
                    'User': arg[0],
                    'Country': arg[1],
                    'CPU': arg[2],
                    'ID': account_id,
                    'InGame': 0,
                    'Away': 0,
                    'Rank': 0,
                    'Moderator': 0,
                    'Bot': 0,
                    'InBattle': 0,
                }
                self.smurf_detection('Public', arg[0])
            else:
                log.warning('ERROR::User exists' + str(raw_data))
        elif command == "REMOVEUSER":
            if arg[0] in self.users:
                self.smurf_detection('Public', arg[0])
                del (self.users[arg[0]])
            else:
                log.warning('ERROR::User doesn\'t exist::' + str(raw_data))
        elif command == "CLIENTSTATUS":
            if arg[0] in self.users:
                self.users[arg[0]]["InGame"] = arg[1][0]
                self.users[arg[0]]["Away"] = arg[1][1]
                self.users[arg[0]]['Rank'] = arg[1][4] * 4 + arg[1][3] * 2 + arg[1][2]
                self.users[arg[0]]['Moderator'] = arg[1][5]
                self.users[arg[0]]['Bot'] = arg[1][6]
            else:
                log.warning('ERROR::User doesn\'t exists::' + str(raw_data))
        elif command == 'BATTLEOPENED':
            if arg[0] not in self.battles:
                self.battles[arg[0]] = {
                    'ID': arg[0],
                    'Type': {0: 'B', 1: 'R'}[arg[1]],
                    'Nat': arg[2],
                    'Founder': arg[3],
                    'IP': arg[4],
                    'Port': arg[5],
                    'MaxPlayers': arg[6],
                    'Passworded': arg[7],
                    'MinRank': arg[8],
                    'MapHash': arg[9],
                    'engine_name': arg[10],
                    'engine_version': arg[11],
                    'Map': arg[12],
                    'Title': arg[13],
                    'Mod': arg[14],
                    'Users': [arg[3]],
                    'Spectators': 0,
                    'Players': 0,
                    'Locked': 0,
                    'Boxes': {},
                    'ScriptTags': {},
                    'DisabledUnits': {},
                }
                self.users[arg[3]]['InBattle'] = arg[0]
                self.smurf_detection('Public', arg[3], arg[4])
            else:
                log.warning('ERROR::Battle exists::' + str(raw_data))
        elif command == 'OPENBATTLE':
            self.reset_battle()
            self.battle_id = arg[0]
            self.users[self.user]['InBattle'] = arg[0]
            self.battle_users[self.user] = {
                'Spectator': 1,
                'Password': 'Humbug',
                'Team': None,
                'Ally': None,
                'Side': None,
                'Color': '000000',
                'Handicap': None,
                'Synced': 1,
                'Ready': 0,
                'AI': 0,
                'AIOwner': None,
                'AIDLL': None,
            }
        elif command == 'JOINEDBATTLE':
            if arg[0] in self.battles:
                self.battles[arg[0]]['Users'].append(arg[1])
                self.battles[arg[0]]['Players'] = len(self.battles[arg[0]]['Users']) - self.battles[arg[0]][
                    'Spectators']
                if self.battle_id and arg[0] == self.battle_id:
                    self.battle_users[arg[1]] = {
                        'Password': arg[2],
                        'AI': 0,
                        'AIOwner': None,
                        'AIDLL': None,
                    }
                    self.callback_internal_event('USER_JOINED_BATTLE', [arg[1], arg[2]])
            else:
                log.warning('ERROR::Battle doesn\'t exists::' + str(raw_data))
            if arg[1] in self.users:
                self.users[arg[1]]['InBattle'] = arg[0]
            else:
                log.warning('ERROR::User doesn\'t exists::' + str(raw_data))
        elif command == "LEFTBATTLE":
            if arg[0] in self.battles:
                self.battles[arg[0]]['Users'].remove(arg[1])
                self.battles[arg[0]]['Players'] = len(self.battles[arg[0]]['Users']) - self.battles[arg[0]][
                    'Spectators']
                if self.battle_id and self.battle_id == arg[0]:
                    del (self.battle_users[arg[1]])
                    self.update_battle()
                    self.callback_internal_event('USER_LEFT_BATTLE', [arg[1]])
            else:
                log.warning('ERROR::Battle doesn\'t exists::' + str(raw_data))
            if arg[1] in self.users:
                self.users[arg[1]]['InBattle'] = 0
            else:
                log.warning('ERROR::User doesn\'t exists::' + str(raw_data))
        elif command == "BATTLECLOSED":
            if arg[0] in self.battles:
                del (self.battles[arg[0]])
                if self.battle_id == arg[0]:
                    self.reset_battle()
            else:
                log.warning('ERROR::Battle doesn\'t exists::' + str(raw_data))
        elif command == 'UPDATEBATTLEINFO':
            if arg[0] in self.battles:
                self.battles[arg[0]]['Spectators'] = arg[1]
                self.battles[arg[0]]['Players'] = len(self.battles[arg[0]]['Users']) - arg[1]
                self.battles[arg[0]]['Locked'] = arg[2]
                self.battles[arg[0]]['MapHash'] = arg[3]
                self.battles[arg[0]]['Map'] = arg[4]
            else:
                log.warning('ERROR::Battle doesn\'t exists::' + str(raw_data))
        elif command in ['SAIDPRIVATE', 'SAID', 'SAIDEX', 'SAIDBATTLE', 'SAIDBATTLEEX', 'SAIDPRIVATEEX']:
            if arg[0] != self.user:
                self.callback_chat(command, arg)
        elif command == 'REQUESTBATTLESTATUS':
            self.send('MYBATTLESTATUS 4194304 000000')
        elif command == 'JOINBATTLEREQUEST':
            self.send('JOINBATTLEACCEPT ' + str(arg[0]))
            self.smurf_detection('Battle', arg[0], arg[1])
        elif command == 'JOINBATTLE':
            # Server is just telling that someone joined the battle successfully, ignore.
            pass
        elif command == 'CHANNELTOPIC':
            # Client just joined the channel, ignore.
            pass
        elif command == 'CLIENTBATTLESTATUS':
            self.battle_users[arg[0]]['Ready'] = int(arg[1][1])
            self.battle_users[arg[0]]['Team'] = int(arg[1][5]) * 8 + int(arg[1][4]) * 4 + int(arg[1][3]) * 2 + int(
                arg[1][2])
            self.battle_users[arg[0]]['Ally'] = int(arg[1][9]) * 8 + int(arg[1][8]) * 4 + int(arg[1][7]) * 2 + int(
                arg[1][6])
            self.battle_users[arg[0]]['Spectator'] = {0: 1, 1: 0}[int(arg[1][10])]
            self.battle_users[arg[0]]['Handicap'] = int(arg[1][17]) * 64 + int(arg[1][16]) * 32 + int(
                arg[1][15]) * 16 + int(arg[1][14]) * 8 + int(arg[1][13]) * 4 + int(arg[1][12]) * 2 + int(arg[1][11])
            self.battle_users[arg[0]]['Synced'] = int(arg[1][23]) * 2 + int(arg[1][22])
            self.battle_users[arg[0]]['Side'] = int(arg[1][27]) * 8 + int(arg[1][26]) * 4 + int(arg[1][25]) * 2 + int(
                arg[1][24])
            self.battle_users[arg[0]]['Color'] = self.to_hex_color(arg[2])
        elif command == 'JOIN':
            self.channels[arg[0]] = {'Users': {}}
        elif command == 'CLIENTS':
            for User in arg[1].split(' '):
                self.channels[arg[0]]['Users'][User] = User
        elif command == 'JOINED':
            self.channels[arg[0]]['Users'][arg[1]] = arg[1]
        elif command == 'LEFT':
            del (self.channels[arg[0]]['Users'][arg[1]])
        elif command == 'ADDBOT':
            if self.battle_id and arg[0] == self.battle_id:
                self.battles[arg[0]]['Users'].append(arg[1])
                self.battle_users[arg[1]] = {
                    'AI': 1,
                    'AIOwner': arg[2],
                    'AIDLL': arg[5],
                    'Ready': int(arg[3][1]),
                    'Team': int(arg[3][5]) * 8 + int(arg[3][4]) * 4 + int(arg[3][3]) * 2 + int(arg[3][2]),
                    'Ally': int(arg[3][9]) * 8 + int(arg[3][8]) * 4 + int(arg[3][7]) * 2 + int(arg[3][6]),
                    'Spectator': {0: 1, 1: 0}[int(arg[3][10])],
                    'Handicap': int(arg[3][17]) * 64 + int(arg[3][16]) * 32 + int(arg[3][15]) * 16 + int(
                        arg[3][14]) * 8 + int(arg[3][13]) * 4 + int(arg[3][12]) * 2 + int(arg[3][11]),
                    'Synced': int(arg[3][23]) * 2 + int(arg[3][22]),
                    'Side': int(arg[3][27]) * 8 + int(arg[3][26]) * 4 + int(arg[3][25]) * 2 + int(arg[3][24]),
                    'Color': self.to_hex_color(arg[4]),
                }
        elif command == 'REMOVEBOT':
            if arg[0] in self.battles:
                self.battles[arg[0]]['Users'].remove(arg[1])
                if arg[1] in self.battle_users:
                    del (self.battle_users[arg[1]])
            else:
                log.warning('ERROR::Battle doesn\'t exists::' + str(raw_data))
        elif command == 'DENIED':
            log.debug('DENIED::' + str(arg[0]))
            self.reset_battle()
        elif command == 'UPDATEBOT':
            if self.battle_id and arg[0] == self.battle_id:
                self.battle_users[arg[1]]['Ready'] = int(arg[2][1])
                self.battle_users[arg[1]]['Team'] = int(arg[2][5]) * 8 + int(arg[2][4]) * 4 + int(arg[2][3]) * 2 + int(
                    arg[2][2])
                self.battle_users[arg[1]]['Ally'] = int(arg[2][9]) * 8 + int(arg[2][8]) * 4 + int(arg[2][7]) * 2 + int(
                    arg[2][6])
                self.battle_users[arg[1]]['Spectator'] = {0: 1, 1: 0}[int(arg[2][10])]
                self.battle_users[arg[1]]['Handicap'] = int(arg[2][17]) * 64 + int(arg[2][16]) * 32 + int(
                    arg[2][15]) * 16 + int(arg[2][14]) * 8 + int(arg[2][13]) * 4 + int(arg[2][12]) * 2 + int(arg[2][11])
                self.battle_users[arg[1]]['Synced'] = int(arg[2][23]) * 2 + int(arg[2][22])
                self.battle_users[arg[1]]['Side'] = int(arg[2][27]) * 8 + int(arg[2][26]) * 4 + int(
                    arg[2][25]) * 2 + int(arg[2][24])
                self.battle_users[arg[1]]['Color'] = self.to_hex_color(arg[3])
        elif command == 'SERVERMSG':
            if arg[0][0:35] == 'You\'ve been kicked from server by <':
                self.allow_reconnect = False
                self.reset_battle()
                print('KICKED FROM SERVER')
                print(arg[0])
        elif command == 'ADDSTARTRECT':
            self.battles[self.battle_id]['Boxes'][arg[0]] = [arg[1], arg[2], arg[3], arg[4]]
        elif command == 'REMOVESTARTRECT':
            if arg[0] in self.battles[self.battle_id]['Boxes']:
                del self.battles[self.battle_id]['Boxes'][arg[0]]
        elif command == 'AGREEMENTEND':
            self.send('CONFIRMAGREEMENT', 1)
            self.login()
        elif command == 'SETSCRIPTTAGS':
            if self.battle_id:
                for Tag in arg[0].split('\t'):
                    Tag = Tag.split('=')
                    self.battles[self.battle_id]['ScriptTags'][Tag[0].lower()] = Tag[1]
            else:
                log.warning('SETSCRIPTTAGS - no self.battle_id')
        elif command == 'DISABLEUNITS':
            if self.battle_id:
                for Unit in arg[0].split(' '):
                    self.battles[self.battle_id]['DisabledUnits'][Unit.lower()] = Unit
            else:
                log.warning('DISABLEUNITS - no self.battle_id')
        elif command == 'ENABLEALLUNITS':
            if self.battle_id:
                self.battles[self.battle_id]['DisabledUnits'] = {}
            else:
                log.warning('ENABLEALLUNITS - no self.battle_id')

        if command in self.commands:
            self.event_callback(command, arg)

    def login(self):
        log.info('')
        password = base64.b64encode(binascii.a2b_hex(hashlib.md5(self.password.encode('utf-8')).hexdigest())).decode('utf-8')
        self.send("LOGIN " + str(self.user) + " " + password + " 0 " + str(self.ip) + " SPA 1.0\t0\ta b sp p cl", 1)

    def open_battle(self, mod_name, mod_hash, map_name, map_hash, title, max_players,
                    min_rank=0, password='*', battle_type=0, nat=0):
        command = f"OPENBATTLE {battle_type} {nat} {password} {self.battle_port} {max_players} " \
                  f"{mod_hash} {min_rank} {map_hash} spring\t103.0\t{map_name}\t{title}\t{mod_name}"
        self.send(command)

    def close_battle(self):
        self.send('LEAVEBATTLE')

    def change_map(self, map_name, map_hash):
        if self.battle_id:
            self.battles[self.battle_id]['Map'] = map_name
            self.battles[self.battle_id]['MapHash'] = map_hash
            self.update_battle()
        else:
            log.error('self.battle_id doesn\'t exist')

    def battle_say(self, message, me=0):
        if me:
            self.send('SAYBATTLEEX ' + str(message))
        else:
            self.send('SAYBATTLE ' + str(message))

    def start_battle(self):
        self.send('MYSTATUS 1')

    def stop_battle(self):
        self.send('MYSTATUS 0')

    def lock_battle(self, Lock):
        if self.battles[self.battle_id]['Locked'] != Lock:
            self.battles[self.battle_id]['Locked'] = Lock
            self.update_battle()

    def update_battle(self):
        self.send('UPDATEBATTLEINFO ' + str(self.battles[self.battle_id]['Spectators']) + ' ' + str(
            self.battles[self.battle_id]['Locked']) + ' ' + str(self.battles[self.battle_id]['MapHash']) + ' ' + str(
            self.battles[self.battle_id]['Map']))

    def kick_user(self, user):
        self.send('KICKFROMBATTLE ' + str(user))

    def add_bot(self, command):
        self.send('ADDBOT ' + command)

    def remove_bot(self, AI):
        self.send('REMOVEBOT ' + str(AI))

    def force_user_team(self, user, team):
        self.send('FORCETEAMNO ' + str(user) + ' ' + str(team))

    def force_user_ally(self, user, ally):
        self.send('FORCEALLYNO ' + str(user) + ' ' + str(ally))

    def force_user_color(self, user, color):
        self.send('FORCETEAMCOLOR ' + str(user) + ' ' + str(color))

    def ring(self, user):
        self.send('RING ' + str(user))

    def add_box(self, ally, left, top, right, bottom):
        command = 'ADDSTARTRECT ' + str(ally) + ' ' + str(left) + ' ' + str(top) + ' ' + str(right) + ' ' + str(bottom)
        self.send(command)
        self.handle_command(command, 1)

    def remove_box(self, ally):
        command = f"REMOVESTARTRECT {ally}"
        self.send(command)
        self.handle_command(command, 1)

    def user_say(self, user, message):
        self.send('SAYPRIVATE ' + str(user) + ' ' + str(message))

    def join_channel(self, channel, password=''):
        self.send('JOIN ' + str(channel))

    def update_bot(self, AI, battle_status, color):
        self.send('UPDATEBOT ' + str(AI) + ' ' + str(battle_status) + ' ' + str(color))

    def handicap_user(self, user, handicap):
        self.send('HANDICAP ' + str(user) + ' ' + str(handicap))

    def disable_units(self, units):
        if isinstance(units, list):
            units = ' '.join(units)
        command = 'DISABLEUNITS ' + str(units).lower()
        self.send(command)
        self.handle_command(command, 1)

    def battle_enable_all_units(self):
        command = 'ENABLEALLUNITS'
        self.send(command)
        self.handle_command(command, 1)

    def update_battle_script(self, tags):
        script = ''
        i_tags = 0
        for tag in tags:
            i_tags = i_tags + 1
            script = script + tag[0].lower() + '=' + str(tag[1]) + '\t'
            if i_tags == 10:
                self.send('SETSCRIPTTAGS ' + script[0:-1])
                script = ''
                i_tags = 0
        if script:
            self.send('SETSCRIPTTAGS ' + script[0:-1])

    def ping(self):
        self.send('PING')

    def send(self, command, force=0):
        try:
            if self.logged_in or force == 1:
                log.debug("SEND::" + str(command))
                command_bytes = command + "\n"
                self.socket.send(command_bytes.encode('latin1'))
            else:
                log.debug("SEND_QUEUE::" + str(command))
                self.logged_in_queue.append(command)
        except ConnectionResetError:
            log.exception('Send failed:' + command)
            self.reconnect()
        except Exception:
            log.exception('Send failed:' + command)
            self.reconnect()

    def connect(self):
        log.info('')
        self.socket.connect((settings.LOBBY_SERVER_HOST, settings.LOBBY_SERVER_PORT))
        self.active = True
        self.set_ip()
        self.class_ping = LobbyPing(self, self.ping)
        self.users = {}
        self.battles = {}
        self.battle_users = {}
        self.battle_id = 0
        self.channels = {}

    def disconnect(self):
        log.info('')
        if self.logged_in:
            self.logout()
        self.socket.shutdown(socket.SHUT_RDWR)
        self.socket.close()
        self.active = False

    def set_logged_in(self):
        log.info('')
        self.logged_in = True
        if len(self.logged_in_queue):
            for Command in self.logged_in_queue:
                self.send(Command)
            self.logged_in_queue = []
        self.class_ping.start()

    def logout(self):
        log.info('Lobby exit')
        self.send("EXIT")
        self.class_ping.terminate()
        self.logged_in = False

    def terminate(self):
        log.info('')
        self.allow_reconnect = False
        self.disconnect()

    def reconnect(self):
        log.info('')
        self.logged_in = False
        self.active = False
        sleep_time = 1
        while not self.active and self.allow_reconnect:
            self.disconnect()
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.connect()
            time.sleep(sleep_time)
            sleep_time = min(60, sleep_time + 2)

    def dec2bin(self, value, numdigits):
        val = int(value)
        digits = [0 for i in range(numdigits)]
        for i in range(numdigits):
            val, digits[i] = divmod(val, 2)
        return digits

    def to_hex_color(self, colot_int):
        color = "%X" % int(colot_int)
        while len(color) < 6:
            color = str(0) + color
        color = color[4:6] + color[2:4] + color[0:2]
        return color

    def smurf_detection(self, source, user, ip=''):
        if source == 'Public':
            self.callback_internal_event('SMURF_DETECTION_PUBLIC',
                                         [self.users[user]['ID'], user, ip, self.users[user]['Country'],
                                          self.users[user]['CPU']])
        elif source == 'Battle':
            self.callback_internal_event('SMURF_DETECTION_BATTLE',
                                         [self.users[user]['ID'], user, ip, self.users[user]['Country'],
                                          self.users[user]['CPU']])

    def set_ip(self):
        log.debug('Trying to set IP')
        try:
            self.ip = self.socket.getsockname()[0]
        except:
            try:
                self.ip = [ip for ip in socket.gethostbyname_ex(socket.gethostname())[2]
                           if not ip.startswith("127.")][0]
            except:
                self.ip = '127.0.0.1'  # fallback
        log.info('IP:' + str(self.ip))


class LobbyPing(threading.Thread):
    def __init__(self, lobby, ping_func):
        threading.Thread.__init__(self)
        self.lobby = lobby
        self.ping = ping_func
        self.sleep_counter = 0
        self.active = False

    def run(self):
        log.info('Lobby Ping start')
        self.active = True
        self.sleep_counter = 0
        while self.lobby.active and self.active:
            if self.sleep_counter == 25:
                self.sleep_counter = 0
                self.ping()
            self.sleep_counter = self.sleep_counter + 1
            time.sleep(1)
        log.info('LobbyPing run finished')

    def terminate(self):
        log.info('')
        self.active = False
