import logging
import os
import shutil
import socket
import subprocess
import threading
import time

from conf import settings
from utils import current_time, re_lmatch

log = logging.getLogger(__name__)
SPRING_AUTO_HOST_PORT = 9000


class Spring(object):

    def __init__(self, server, host, lobby):
        self.server = server
        self.Host = host
        self.Lobby = lobby
        self.SpringUDP = None
        self.SpringPID = None
        self.SpringOutput = None
        self.SpringError = None
        self.headless = False
        self.HeadlessSpeed = [1, 3]
        log.info('UDP Port: %s', SPRING_AUTO_HOST_PORT)
        self.Game = {}

    def SpringEvent(self, event, data=''):
        log.info(str(event) + '::' + str(data))
        if event == 'USER_CHAT_ALLY':
            if self.Lobby.battle_id and self.Host.config.get('ECHO_GAME_ALLY_CHAT_TO_LOBBY', False):
                self.Lobby.battle_say('<' + str(data[0]) + '> Ally: ' + str(data[1]))
        elif event == 'USER_CHAT_SPEC':
            if self.Lobby.battle_id and self.Host.config.get('ECHO_GAME_SPEC_CHAT_TO_LOBBY', False):
                self.Lobby.battle_say('<' + str(data[0]) + '> Spec: ' + str(data[1]))
        elif event == 'USER_CHAT_PUBLIC':
            self.Host.handle_input('BATTLE_PUBLIC', data[1], data[0])
            if self.Lobby.battle_id and self.Host.config.get('ECHO_GAME_NORMAL_CHAT_TO_LOBBY', False):
                self.Lobby.battle_say('<' + str(data[0]) + '> ' + str(data[1]))
        elif event == 'BATTLE_STARTED':
            self.Host.HostCmds.notifications('BATTLE_STARTED')
        elif event == 'BATTLE_SCRIPT_CREATED':
            self.Game = data
            self.Game['TimeCreated'] = current_time()
            self.Game['Deaths'] = []
        elif event == 'GAME_START':
            self.Game['TimeStart'] = current_time()
        elif event == 'GAME_END':
            self.Game['TimeEnd'] = current_time()
            self.server.database.store_battle(
                self.Lobby.users[self.Lobby.user]['ID'], self.Game['Game'],
                self.Game['Map'], self.Game['TimeCreated'], self.Game['GameID'], self.Game)
        elif event == 'USER_DIED':
            self.Game['Deaths'].append([data, current_time()])
        elif event == 'GAMEOUTPUT_GAMEID':
            self.Game['GameID'] = data
        elif event == 'GAMEOUTPUT_DEMOLOCATION':
            self.Game['Demo'] = data

    def user_is_playing(self, user):
        if self.SpringUDP and self.SpringUDP.active:
            return self.SpringUDP.is_user_playing(user)

    def user_is_spectating(self, user):
        if self.SpringUDP and self.SpringUDP.active:
            return self.SpringUDP.is_user_spectating(user)
        return False

    def start(self, reason='UNKNOWN'):
        log.info('Spring::Start (' + reason + ')')

        script_uri = os.path.join(settings.TEMP_PATH, 'script.txt')
        self.generate_battle_script(script_uri)
        config_uri = os.path.join(settings.TEMP_PATH, 'spring.cfg')
        self.generate_spring_config(config_uri)

        self.SpringPID = subprocess.Popen(
            [self.Host.get_spring_binary(self.headless), '-C' + config_uri, script_uri],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )

        self.SpringEvent('BATTLE_STARTED')
        self.SpringOutput = SpringOutput(self)
        self.SpringOutput.start()
        self.SpringError = SpringError(self)
        self.SpringError.start()
        self.SpringUDP = SpringUDP(self)
        self.SpringUDP.start()

        return True

    def stop(self, reason='UNKNOWN', message=''):
        log.info('Spring::Stop (' + reason + '::' + message + ')')
        if self.SpringUDP:
            try:
                self.SpringUDP.terminate(message)
            except Exception as e:
                log.warning('Error killing SpringUDP: ' + str(e))

        if self.SpringPID:
            try:
                self.SpringPID.terminate()
                if self.SpringPID.wait() is None:
                    self.SpringPID.kill()
                self.SpringPID = None
            except Exception as e:
                log.error('Error killing Spring: ' + str(e), 1)

        if self.SpringOutput:
            try:
                self.SpringOutput.terminate(message)
            except Exception as e:
                log.error('Error killing SpringOutput: ' + str(e), 1)

        if self.SpringError:
            try:
                self.SpringError.terminate(message)
            except Exception as e:
                log.error('Error killing SpringError: ' + str(e), 1)

        self.Lobby.stop_battle()

        if 'Demo' in self.Game and 'GameID' in self.Game and os.path.exists(self.Game['Demo']):
            try:
                new_file = settings.DEMOS_PATH + self.Game['GameID'] + '.sdfz'
                new_file = os.path.expanduser(new_file)
                shutil.move(self.Game['Demo'], new_file)
                log.info('Demo moved from %s to %s', self.Game['Demo'], new_file)
            except Exception as e:
                log.error('Error moving demo: ' + str(e) + ' original: ' + self.Game['Demo'])
        return True

    def SpringTalk(self, UDP_Command):
        log.info('Spring::SpringTalk=' + str(UDP_Command))
        try:
            self.SpringUDP.Talk(UDP_Command)
        except:
            return False

    def generate_spring_config(self, file_path):
        log.info(str(file_path))
        file = open(file_path, 'w')
        file.write('LinkIncomingMaxPacketRate=128\n')
        file.write('LinkIncomingMaxWaitingPackets=1024\n')
        file.write('LinkIncomingPeakBandwidth=65536\n')
        file.write('LinkIncomingSustainedBandwidth=4096\n')
        file.write('LinkOutgoingBandwidth=131072\n')
        file.close()

    def generate_battle_script(self, file_path):
        log.info('Spring::generate_battle_script::' + str(file_path))
        battle = self.Lobby.battles[self.Lobby.battle_id]
        unitsync_mod = self.Host.get_unitsync_mod(battle['Mod'])
        self.headless = False
        for User in battle['Users']:
            if not User == self.Lobby.user and self.Lobby.battle_users[User]['AI'] and self.Lobby.battle_users[User]['AIOwner'] == self.Lobby.user:
                self.headless = True
        result = {}

        file = open(file_path, 'w')
        file.write('[GAME]\n')
        file.write('{\n')
        file.write('\tMapname=' + str(battle['Map']) + ';\n')
        result['Map'] = battle['Map']
        file.write('\t[modoptions]\n')
        file.write('\t{\n')
        if 'ModOptions' in self.Host.battle:
            for Key in list(self.Host.battle['ModOptions'].keys()):
                value = self.Host.battle['ModOptions'][Key]
                file.write('\t\t' + Key + '=' + str(value) + ';\n')
                if Key == 'minspeed':
                    self.HeadlessSpeed[0] = self.Host.battle['ModOptions'][Key]
                if Key == 'maxspeed':
                    self.HeadlessSpeed[1] = self.Host.battle['ModOptions'][Key]
        file.write('\t}\n')
        file.write('\tStartPosType=' + str(self.Host.battle['StartPosType']) + ';\n')
        result['StartPosType'] = str(self.Host.battle['StartPosType'])
        result['Game'] = str(battle['Mod'])
        file.write('\tGameType=' + str(battle['Mod']) + ';\n')
        file.write('\tHostIP=' + str(self.Lobby.ip) + ';\n')
        file.write('\tHostPort=' + str(self.Lobby.battle_port) + ';\n')
        if self.headless:
            # FP.write('\tMyPlayerName=' + str(self.Lobby.user) + ';\n')
            file.write('\tAutohostPort=' + str(SPRING_AUTO_HOST_PORT) + ';\n')
            file.write('\tIsHost=1;\n')
            iP = 1
        else:
            file.write('\tAutoHostName=' + str(self.Lobby.user) + ';\n')
            file.write('\tAutoHostCountryCode=' + str(self.Lobby.users[self.Lobby.user]['Country']) + ';\n')
            file.write('\tAutoHostRank=' + str(self.Lobby.users[self.Lobby.user]['Rank']) + ';\n')
            file.write('\tAutoHostAccountId=' + str(self.Lobby.users[self.Lobby.user]['ID']) + ';\n')
            file.write('\tAutohostPort=' + str(SPRING_AUTO_HOST_PORT) + ';\n')
            file.write('\tIsHost=1;\n')
            iP = 0

        for User in battle['Users']:
            if not User == self.Lobby.user and not self.Lobby.battle_users[User]['AI']:
                iP = iP + 1
        file.write('\tNumPlayers=' + str(iP) + ';\n')

        iP = 0
        iT = 0
        iA = 0
        iAI = 0
        Teams = {}
        Allys = {}
        Players = {}
        AIs = {}

        if self.headless:
            Players[self.Lobby.user] = iP
            file.write('\t[PLAYER' + str(iP) + ']\n')
            file.write('\t{\n')
            file.write('\t\tName=' + str(self.Lobby.user) + ';\n')
            file.write('\t\tPassword=2DD5A5ED;\n')
            file.write('\t\tSpectator=1;\n')
            file.write('\t}\n')
            iP = iP + 1

        result['Teams'] = {}
        for User in battle['Users']:
            if User != self.Lobby.user:
                if self.Lobby.battle_users[User]['Team'] not in Teams:
                    Teams[self.Lobby.battle_users[User]['Team']] = iT
                    result['Teams'][iT] = []
                    iT = iT + 1

                if not self.Lobby.battle_users[User]['AI']:
                    Players[User] = iP
                    file.write('\t[PLAYER' + str(iP) + ']\n')
                    file.write('\t{\n')
                    file.write('\t\tName=' + str(User) + ';\n')
                    file.write('\t\tcountryCode=' + str(self.Lobby.users[User]['Country']) + ';\n')
                    file.write('\t\tRank=' + str(self.Lobby.users[User]['Rank']) + ';\n')
                    file.write('\t\tPassword=' + str(self.Lobby.battle_users[User]['Password']) + ';\n')
                    file.write('\t\tSpectator=' + str(self.Lobby.battle_users[User]['Spectator']) + ';\n')
                    file.write('\t\tTeam=' + str(Teams[self.Lobby.battle_users[User]['Team']]) + ';\n')
                    file.write('\t}\n')
                    result['Teams'][Teams[self.Lobby.battle_users[User]['Team']]].append(
                        [User, self.Lobby.battle_users[User]['Spectator'], self.Lobby.users[User]['ID'],
                         self.Lobby.users[User]['Rank']])
                    iP = iP + 1

        for User in battle['Users']:
            if User != self.Lobby.user:
                if self.Lobby.battle_users[User]['AI']:
                    AIs[User] = iAI
                    file.write('\t[AI' + str(iAI) + ']\n')
                    file.write('\t{\n')
                    file.write('\t\tName=' + str(User) + ';\n')
                    file.write('\t\tShortName=' + str(self.Lobby.battle_users[User]['AIDLL']) + ';\n')
                    file.write('\t\tTeam=' + str(Teams[self.Lobby.battle_users[User]['Team']]) + ';\n')
                    file.write('\t\tHost=' + str(Players[self.Lobby.battle_users[User]['AIOwner']]) + ';\n')
                    file.write('\t}\n')
                    result['Teams'][Teams[self.Lobby.battle_users[User]['Team']]].append(
                        [User, 0, 'AI', self.Lobby.battle_users[User]['AIDLL'],
                         Players[self.Lobby.battle_users[User]['AIOwner']]])
                    iAI = iAI + 1

        file.write('\tNumTeams=' + str(len(Teams)) + ';\n')

        result['Allies'] = {}
        for User in battle['Users']:
            if User != self.Lobby.user and (
                            self.Lobby.battle_users[User]['Spectator'] == 0 or self.Lobby.battle_users[User]['AI']):
                if self.Lobby.battle_users[User]['Ally'] not in Allys:
                    Allys[self.Lobby.battle_users[User]['Ally']] = iA
                    result['Allies'][iA] = []
                    iA = iA + 1

                file.write('\t[TEAM' + str(Teams[self.Lobby.battle_users[User]['Team']]) + ']\n')
                file.write('\t{\n')
                if self.Lobby.battle_users[User]['AI']:
                    file.write('\t\tTeamLeader=0;\n')
                else:
                    file.write('\t\tTeamLeader=' + str(Players[User]) + ';\n')
                file.write('\t\tAllyTeam=' + str(Allys[self.Lobby.battle_users[User]['Ally']]) + ';\n')
                file.write('\t\tRgbColor=' + str(
                    round(int(self.Lobby.battle_users[User]['Color'][0:2], 16) / 255.0, 5)) + ' ' + str(
                    round(int(self.Lobby.battle_users[User]['Color'][2:4], 16) / 255.0, 5)) + ' ' + str(
                    round(int(self.Lobby.battle_users[User]['Color'][4:6], 16) / 255.0, 5)) + ';\n')
                try:
                    file.write('\t\tSide=' + unitsync_mod['Sides'][self.Lobby.battle_users[User]['Side']] + ';\n')
                except Exception as Error:
                    file.write('\t\tSide=0;\n')
                    log.error('FAULTY_SIDE::' + str(self.Lobby.battle_users[User]['Side']), 1)
                file.write('\t\tHandicap=' + str(self.Lobby.battle_users[User]['Handicap']) + ';\n')
                file.write('\t}\n')
                user_side = self.Lobby.battle_users[User].get('Side') or 0
                if user_side not in unitsync_mod['Sides']:
                    user_side = 0
                result['Allies'][Allys[self.Lobby.battle_users[User]['Ally']]].append(
                    [Teams[self.Lobby.battle_users[User]['Team']],
                     unitsync_mod['Sides'][user_side],
                     self.Lobby.battle_users[User]['Handicap'], self.Lobby.battle_users[User]['Color']])
        for Ally in list(battle['Boxes'].keys()):
            if Ally not in Allys:
                Allys[Ally] = iA
                iA += 1

        file.write('\tNumAllyTeams=' + str(len(Allys)) + ';\n')
        for Ally in Allys:
            file.write('\t[ALLYTEAM' + str(Allys[Ally]) + ']\n')
            file.write('\t{\n')
            file.write('\t\tNumAllies=0;\n')
            if str(self.Host.battle['StartPosType']) == '2' and Ally in battle['Boxes']:
                file.write('\t\tStartRectLeft=' + str(round(float(battle['Boxes'][Ally][0]) / 200, 2)) + ';\n')
                file.write('\t\tStartRectTop=' + str(round(float(battle['Boxes'][Ally][1]) / 200, 2)) + ';\n')
                file.write('\t\tStartRectRight=' + str(round(float(battle['Boxes'][Ally][2]) / 200, 2)) + ';\n')
                file.write('\t\tStartRectBottom=' + str(round(float(battle['Boxes'][Ally][3]) / 200, 2)) + ';\n')
            file.write('\t}\n')

        if len(battle['DisabledUnits']) > 0:
            file.write('\tNumRestrictions=' + str(len(battle['DisabledUnits'])) + ';\n')
            iUnit = 0
            file.write('\t[RESTRICT]\n')
            file.write('\t{\n')
            for Unit in list(battle['DisabledUnits'].keys()):
                file.write('\t\tUnit' + str(iUnit) + '=' + str(Unit) + ';\n')
                file.write('\t\tLimit' + str(iUnit) + '=0;\n')
                iUnit += 1
            file.write('\t}\n')
        else:
            file.write('\tNumRestrictions=0;\n')

        file.write('\t[MAPOPTIONS]\n')
        file.write('\t{\n')
        if 'MapOptions' in self.Host.battle:
            for Key in list(self.Host.battle['MapOptions'].keys()):
                file.write('\t\t' + str(Key) + '=' + str(self.Host.battle['MapOptions'][Key]) + ';\n')
        file.write('\t}\n')
        file.write('}\n')
        file.close()
        self.SpringEvent('BATTLE_SCRIPT_CREATED', result)


class SpringUDP(threading.Thread):
    def __init__(self, ClassSpring):
        threading.Thread.__init__(self)
        self.Spring = ClassSpring
        self.active = True
        self.Socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.Socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.ServerAddr = None
        self.SpringUsers = {}  # [ID] = Alias
        self.Users = {}  # [Alias] = {'Ready', 'Alive', 'InGame'}

    def run(self):
        log.info('SpringUDP start')
        self.Socket.bind(('', SPRING_AUTO_HOST_PORT))
        self.Socket.settimeout(1)
        while self.active:
            try:
                data, self.ServerAddr = self.Socket.recvfrom(8192)
            except socket.timeout:
                continue
            if data and data[0] != 0:
                code = data[0]
                try:
                    if code == 1:  # Game stop
                        self.Spring.SpringEvent('SERVER_QUIT')
                        self.Spring.stop('UDP_SERVER_QUIT', 'Spring sent SERVER_QUIT')
                    elif code == 2:  # Game start
                        if self.Spring.headless:
                            self.Talk('/setminspeed 1')
                            self.Talk('/setmaxspeed 1')
                            self.Talk('/setminspeed ' + str(self.Spring.HeadlessSpeed[0]))
                            self.Talk('/setmaxspeed ' + str(self.Spring.HeadlessSpeed[1]))
                        for User in list(self.Users.keys()):
                            if self.Users[User]['Alive']:
                                self.Users[User]['Playing'] = 1
                        self.Spring.SpringEvent('GAME_START')
                    elif code == 3:  # Battle ended
                        self.Spring.Lobby.battle_say('Battle ended', 1)
                        for User in list(self.Users.keys()):
                            self.Users[User]['Playing'] = 0
                        self.Spring.SpringEvent('GAME_END')
                    elif code == 4:  # Information
                        info = data[1:].decode('utf-8')
                        self.Spring.SpringEvent('INFORMATION', info)
                        info = info.split(' ')
                        if info[0] == 'Player' and info[2] == 'finished':
                            if info[1] not in self.Users:
                                self.Users[info[1]] = {'Ready': 0, 'Playing': 0, 'Alive': 0, 'InGame': 1}
                            self.Users[info[1]]['Alive'] = 1
                            self.Spring.SpringEvent('PLAYER_JOINED', info[1])
                        elif info[0] == 'Spectator' and info[2] == 'finished':
                            self.Spring.SpringEvent('SPECTATOR_JOINED', info[1])
                            if info[1] not in self.Users:
                                self.Users[info[1]] = {'Ready': 0, 'Playing': 0, 'Alive': 0, 'InGame': 1}
                    elif code == 10:  # User joined
                        user = data[2:].decode('utf-8')
                        self.Spring.SpringEvent('USER_JOINED', user)
                        self.SpringUsers[data[1]] = user
                        self.Users[self.get_user_from_id(data[1])]['InGame'] = 1
                    elif code == 11:  # User left
                        User = self.get_user_from_id(data[1])
                        self.Spring.SpringEvent('USER_LEFT', User)
                        if User in self.Users:
                            self.Users[User]['InGame'] = 0
                    elif code == 12:  # User ready
                        self.Spring.SpringEvent('USER_READY', self.get_user_from_id(data[1]))
                        self.Users[self.get_user_from_id(data[1])]['Ready'] = 1
                        self.Users[self.get_user_from_id(data[1])]['Alive'] = 1
                    elif code == 13:  # Battle chat
                        message = str(data[3:].decode('latin1'))
                        if data[2] == 252:  # Ally chat
                            self.Spring.SpringEvent('USER_CHAT_ALLY', [self.get_user_from_id(data[1]), message])
                        if data[2] == 253:  # Spec chat
                            self.Spring.SpringEvent('USER_CHAT_SPEC', [self.get_user_from_id(data[1]), message])
                        if data[2] == 254:  # Public chat
                            self.Spring.SpringEvent('USER_CHAT_PUBLIC', [self.get_user_from_id(data[1]), message])
                    elif code == 14:  # User died
                        self.Spring.SpringEvent('USER_DIED', self.get_user_from_id(data[1]))
                        self.Users[self.get_user_from_id(data[1])]['Alive'] = 0
                    else:
                        if not code == 20 and not code == 60:
                            try:
                                log.warning(
                                    'UNKNOWN_UDP::' + str(code) + '::' + str(data[1]) + '::' + str(
                                        data[2:]))
                            except:
                                try:
                                    log.warning(
                                        'UNKNOWN_UDP::' + str(code) + '::' + str(data[1]))
                                except:
                                    log.warning('UNKNOWN_UDP::' + str(code))
                except Exception as Error:
                    log.error('CRASH::' + str(code) + ' => ' + str(Error), 1)
        log.info('UDP run finished')

    def get_user_from_id(self, user_id):
        try:
            user_id = int(user_id)
        except ValueError:
            log.error('Invalid user id "' + str(user_id) + '"')
        if user_id in self.SpringUsers:
            return self.SpringUsers[user_id]
        log.error('No user found for "' + str(user_id) + '"')

    def is_user_ready(self, user):
        log.info('Is Ready::' + str(user))
        if user in self.Users:
            return self.Users[user]['Ready']
        return False

    def is_user_alive(self, user):
        log.info('is_user_alive::' + str(user))
        if user in self.Users:
            return self.Users[user]['Alive']
        return False

    def is_user_spectating(self, user):
        log.info('IsSpectating::' + str(user))
        if user in self.Users and self.Users[user]['InGame'] and not self.Users[user]['Playing']:
            return True
        return False

    def is_user_playing(self, user):
        log.info('IsPlaying::' + str(user))
        if user in self.Users and self.Users[user]['InGame'] and self.Users[user]['Playing']:
            return True
        return False

    def add_user(self, user, password):
        log.info('User:' + str(user) + ', password:' + str(password))
        self.Talk('/ADDUSER ' + str(user) + ' ' + str(password))

    def Talk(self, message, try_attempt=0):
        log.info(str(message))
        if self.active:
            try:
                self.Socket.sendto(message.encode('latin1'), self.ServerAddr)
            except:
                log.error('Socket send failed (try: ' + str(try_attempt) + ')')
                if try_attempt < 10:
                    time.sleep(0.05)
                    self.Talk(message, try_attempt + 1)
                else:
                    self.Spring.stop('UDP_TALK_FAILED', 'SpringUDP lost connection to spring')

    def terminate(self, message=''):
        log.info(str(message))
        self.active = False
        self.Talk('/QUIT')
        try:
            log.info('Close UDP socket')
            self.Socket.close()
        except:
            log.error('FAILED: Close UDP socket')


class SpringOutput(threading.Thread):
    def __init__(self, spring):
        threading.Thread.__init__(self)
        self.spring = spring
        self.active = True
        self.PID = self.spring.SpringPID

    def run(self):
        log.info('SpringOutput start')
        while self.active:
            line = self.PID.stdout.readline().decode('latin1')
            if line:
                log.debug('DEBUG_GAME ' + line)
                if 'GameID:' in line:
                    self.spring.SpringEvent('GAMEOUTPUT_GAMEID', re_lmatch('[a-fA-F0-9]{32}', line))
                elif 'recording demo: ' in line:
                    file_path = line.split("recording demo: ", 1)[1].rstrip()
                    self.spring.SpringEvent('GAMEOUTPUT_DEMOLOCATION', file_path)
            else:
                self.active = False

    def terminate(self, message=''):
        log.info(str(message))
        self.active = False


class SpringError(threading.Thread):
    def __init__(self, spring):
        threading.Thread.__init__(self)
        self.spring = spring
        self.active = True
        self.PID = self.spring.SpringPID

    def run(self):
        log.info('SpringError start')
        while self.active:
            line = self.PID.stderr.readline()
            if line:
                log.error('DEBUG_GAME_ERROR ' + line)
            else:
                self.active = False

    def terminate(self, message=''):
        log.info(str(message))
        self.active = False
