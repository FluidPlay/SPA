import logging
import random
import time
from decimal import *

log = logging.getLogger(__name__)


class BattleManager(object):

    battle = {}
    battle_users = {}

    def __init__(self, battle_cmds, server, host):
        self.battle_cmds = battle_cmds
        self.server = server
        self.host = host
        self.lobby = host.Lobby
        self.MapsRandom = {'Pos': 0, 'List': {}}

    def refresh(self):
        if self.lobby.battle_id:
            self.battle = self.lobby.battles[self.lobby.battle_id] if self.lobby.battle_id else {}
            self.battle_users = self.lobby.battle_users if self.lobby.battle_id else {}
        else:
            self.battle = {}
            self.battle_users = {}
            log.warning("self.lobby.battle_id doesn't exist")

    def open_battle(self):
        mod_name = self.host.battle['Mod']
        map_name = self.host.battle['Map']
        unitsync_mod = self.host.get_unitsync_mod(mod_name)
        if not unitsync_mod:
            return [False, 'Mod doesn\'t exist']
        unitsync_map = self.host.get_unitsync_map(map_name)
        if not unitsync_map:
            return [False, 'Map doesn\'t exist']
        desc = self.host.battle['BattleDescription']
        password = self.host.battle['BattlePassword']
        self.lobby.open_battle(
            mod_name, unitsync_mod['Hash'], map_name, unitsync_map['Hash'], desc, 16, password=password)
        self.host.host_command_wait('OPENBATTLE')
        self.lobby.battle_enable_all_units()
        return [True, 'Battle opened']

    def close_battle(self):
        self.lobby.close_battle()
        self.host.host_command_wait('BATTLECLOSED')
        return [True, 'Battle Closed']

    def ring(self, search_user=None):
        self.refresh()
        if search_user:
            user = self._search_user_in_battle(search_user)
            if not user:
                return [False, 'User "' + str(search_user) + '" is not in this battle']
            self.lobby.ring(user)
            return [True, 'Ringing "' + str(user) + '"']
        else:
            for user in self.battle_users:
                if self.battle_users[user]['Spectator'] == 0 and self.battle_users[user]['Ready'] == 0:
                    self.lobby.ring(user)
            return [True, 'Ringing all unready users']

    def add_bot(self, team, ally, search_side, color, bot_name):
        if not self.lobby.battle_id:
            return [False, 'No battle open']
        self.refresh()
        AI_short_name = None
        mod = self.host.get_unitsync_mod(self.battle['Mod'])

        side = self.LogicFunctionSearchMatch(search_side, mod['Sides'], 0, 0)
        if not side:
            return [False, 'Side "' + str(search_side) + '" doesn\'t exist']

        for AI in mod['AI']:
            if mod['AI'][AI]['shortName'] == bot_name:
                name = mod['AI'][AI]['name']
                AI_short_name = bot_name
                if 'version' in mod['AI'][AI]:
                    try:
                        version = float(mod['AI'][AI]['version'])
                    except:
                        version = None
                    if version:
                        name = name + ' (v. ' + str(version) + ')'
        if AI_short_name:
            self.lobby.add_bot('BOT' + str(team) + ' ' + str(
                self.battle_status(0, team - 1, ally - 1, 0, 0, 0, side)) + ' ' + str(
                self._battle_color(color)) + ' ' + AI_short_name)
            self.host.host_command_wait('ADDBOT')
            return [True, name]
        return [False, 'No AI found with that name']

    def info(self):
        self.refresh()
        result = ['Battle information']
        for alias in self.battle_users:
            if not alias == self.lobby.user:
                User = self.battle_users[alias]
                try:
                    R = str(self.host.Spring.is_user_ready(alias))
                    A = str(self.host.Spring.is_user_alive(alias))
                except:
                    R = 'N/A'
                    A = 'N/A'
                result.append(alias + '   ' + 'A:' + A + '   R:' + R)
        return [True, result]

    def spec(self, search_user):
        user = self._search_user_in_battle(search_user)
        if not user:
            return [False, 'User "' + str(search_user) + '" is not in this battle']
        self.lobby.send('FORCESPECTATORMODE ' + str(user))
        return [True, 'User "' + str(user) + '" spectated']

    def kick(self, search_user):
        self.refresh()
        if self.lobby.user.lower() == search_user.lower():
            return [False, 'Can\'t kick the host... use !terminate']
        user = self._search_user_in_battle(search_user)
        if not user:
            return [False, 'User "' + str(search_user) + '" is not in this battle']
        if self.lobby.battle_users[user]['AI']:
            self.lobby.remove_bot(user)
            self.host.Spring.SpringTalk('/kick ' + user)
            return [True, 'AI "' + str(user) + '" kicked']
        else:
            self.lobby.kick_user(user)
            self.host.Spring.SpringTalk('/kick ' + user)
            return [True, 'User "' + str(user) + '" kicked']

    def kick_bots(self):
        self.refresh()
        result = []
        for User in self.battle['Users']:
            if User in self.lobby.battle_users:
                if self.lobby.battle_users[User]['AI']:
                    self.lobby.remove_bot(User)
                    self.host.Spring.SpringTalk('/kick ' + User)
                    result.append('AI "' + User + '" kicked')
        if result:
            return [True, result]
        else:
            return [True, 'No AI\'s in the battle']

    def fix_id(self):
        self.refresh()
        current_id = 0
        AIs = []
        for user in self.battle_users:
            if not self.battle_users[user]['Spectator'] and not self.battle_users[user]['AI']:
                self.lobby.force_user_team(user, current_id)
                if current_id < 15:
                    current_id = current_id + 1
            elif self.battle_users[user]['AI']:
                AIs.append(user)
        if len(AIs):
            for AI in AIs:
                self.lobby.update_bot(AI, self.battle_status(0, current_id, self.battle_users[AI]['Ally'], 0,
                                                             self.battle_users[AI]['Handicap'], 0,
                                                             self.battle_users[AI]['Side']),
                                      self._battle_color(self.battle_users[AI]['Color']))
                if current_id < 15:
                    current_id = current_id + 1
        return [True, 'IDs fixed']

    def force_team(self, search_user, team):
        self.refresh()
        if team < 1 or team > 16:
            return [False, 'Team has to be between 1 to 16']
        user = self._search_user_in_battle(search_user)
        if not user:
            return [False, 'User "' + str(search_user) + '" is not in this battle']
        team -= 1
        if self.battle_users[user]['Ally'] != team:
            if self.battle_users[user]['AI']:
                self.lobby.update_bot(user,
                                      self.battle_status(0, self.battle_users[user]['Team'], team, 0,
                                                             self.battle_users[user]['Handicap'], 0,
                                                             self.battle_users[user]['Side']),
                                      self._battle_color(self.battle_users[user]['Color']))
            else:
                self.lobby.force_user_ally(user, team)
        return [True, 'Team changed']

    def force_id(self, search_user, id):
        self.refresh()
        if id < 1 or id > 16:
            return [False, 'ID has to be between 1 to 16']
        user = self._search_user_in_battle(search_user)
        if not user:
            return [False, 'User "' + str(search_user) + '" is not in this battle']
        id -= 1
        if self.battle_users[user]['Team'] != id:
            if self.battle_users[user]['AI']:
                self.lobby.update_bot(user, self.battle_status(0, id, self.battle_users[user]['Ally'], 0,
                                                               self.battle_users[user]['Handicap'], 0,
                                                               self.battle_users[user]['Side']),
                                      self._battle_color(self.battle_users[user]['Color']))
            else:
                self.lobby.force_user_team(user, id)
        return [True, 'ID changed']

    def force_color(self, search_user, color):
        self.refresh()
        if not len(color) == 6 or color.upper().strip('0123456789ABCDEF'):
            return [False, 'Color was not a Hex RGB color']
        user = self._search_user_in_battle(search_user)
        if not user:
            return [False, 'User "' + str(search_user) + '" is not in this battle']
        if not self.battle_users[user]['AI']:
            self.lobby.force_user_color(user, self._battle_color(color))
        else:
            self.lobby.update_bot(user, self.battle_status(0, self.battle_users[user]['Team'],
                                                           self.battle_users[user]['Ally'], 0,
                                                           self.battle_users[user]['Handicap'], 0,
                                                           self.battle_users[user]['Side']),
                                  self._battle_color(color))
        return [True, 'Color changed']

    def switch_map(self, selected_map, action='Fixed'):
        self.refresh()
        pos = 0
        if action == 'Reorder' or len(self.MapsRandom['List']) == 0:
            self.MapsRandom = {'Pos': 0, 'List': {}}
            map_names = self.host.get_unitsync_map('#KEYS#')
            random.seed()
            random.shuffle(map_names)
            i_pos = 0
            for map_name in map_names:
                i_pos += 1
                self.MapsRandom['List'][i_pos] = map_name
            if action == 'Reorder':
                return [True, 'Maps reordered']
        if action == 'Next':
            pos = self.MapsRandom['Pos'] + 1
            if pos > len(self.MapsRandom['List']):
                pos = 1
        elif action == 'Prev':
            pos = self.MapsRandom['Pos'] - 1
            if pos < 1:
                pos = len(self.MapsRandom['List'])
        elif action == 'Random':
            random.seed()
            pos = random.randint(1, len(self.MapsRandom['List']))
        elif action == 'Fixed':
            match = self.LogicFunctionSearchMatch(selected_map, self.host.get_unitsync_map('#KEYS#'))
            if match:
                for MapID in list(self.MapsRandom['List'].keys()):
                    if self.MapsRandom['List'][MapID] == match:
                        pos = MapID
                        break
            else:
                matches = self.LogicFunctionSearchMatch(selected_map, self.host.get_unitsync_map('#KEYS#'), 1)
                if matches:
                    result = ['Multiple maps found, listing the 10 first:']
                    for map_name in matches:
                        result.append(map_name)
                        if len(result) == 11:
                            break
                    return [False, result]

        if pos:
            new_map = self.MapsRandom['List'][pos]
            unitsync_map = self.host.get_unitsync_map(new_map)
            if unitsync_map:
                self.MapsRandom['Pos'] = pos
                self.host.battle['Map'] = new_map
                self.lobby.change_map(new_map, unitsync_map['Hash'])
                self.load_map_defaults()
                self.load_boxes()
                self.host.HandleLocalEvent('BATTLE_MAP_CHANGED', [new_map])
                return [True, 'Map changed to ' + str(new_map)]
        else:
            return [False, 'Map "' + str(selected_map) + '" not found']

    def list_maps(self, search=None):
        result = []
        if search:
            map_names = self.LogicFunctionSearchMatch(search, self.host.get_unitsync_map('#KEYS#'), 1)
            if not map_names:
                return [False, 'No map matching "' + search + '" found']
        else:
            map_names = self.host.get_unitsync_map('#KEYS#')
        for map_name in map_names:
            result.append(map_name)
        result.sort()
        result = ['Maps:'] + result
        return [True, result]

    def list_mods(self, search=None):
        result = []
        if search:
            mods = self.LogicFunctionSearchMatch(search, self.host.get_unitsync_mod('#KEYS#'), 1)
        else:
            mods = self.host.get_unitsync_mod('#KEYS#')
        if mods and not isinstance(mods, list):
            mods = [mods]
        for mod in mods:
            result.append(mod)
        result.sort()
        result = ['Mods:'] + result
        return [True, result]

    def set_mod_option(self, option, value=None):
        log.info(str(option) + '=>' + str(value))
        if not self.lobby.battle_id:
            return [False, 'No battle is open']
        mod = self.host.get_unitsync_mod(self.lobby.battles[self.lobby.battle_id]['Mod'])
        if 'Options' not in mod:
            return [True, 'This mod has no options']
        elif option not in mod['Options']:
            result = ['Valid ModOptions are:']
            for Key in list(mod['Options'].keys()):
                result.append(Key + ' - ' + mod['Options'][Key]['Title'])
            return [False, result]
        elif value is None:
            return [False, self._check_mod_option_value(mod['Options'][option], value, 1)]
        else:
            result = self._check_mod_option_value(mod['Options'][option], value)
            if result['OK']:
                log.debug(str(value) + ' => ' + str(result['value']))
                self.host.battle['ModOptions'][option] = result['value']
                self.update_battle()
                return [True, 'Modoption ' + mod['Options'][option]['Key'] + ' changed to ' + str(result['value'])]
            else:
                return [False, self._check_mod_option_value(mod['Options'][option], value, 1)]

    def set_map_option(self, option, value=None):
        log.info(str(option) + '=>' + str(value))
        if not self.lobby.battle_id:
            return [False, 'No battle is open']
        map_name = self.host.get_unitsync_map(self.lobby.battles[self.lobby.battle_id]['Map'])
        if 'Options' not in map_name:
            return [True, 'This map has no options']
        elif option not in map_name['Options']:
            result = ['Valid MapOptions are:']
            for k in list(map_name['Options'].keys()):
                result.append(k + ' - ' + map_name['Options'][k]['Title'])
            return [False, result]
        elif value is None:
            return [False, self._check_mod_option_value(map_name['Options'][option], value, 1)]
        else:
            result = self._check_mod_option_value(map_name['Options'][option], value)
            if result['OK']:
                log.debug(str(value) + ' => ' + str(result['value']))
                self.host.battle['MapOptions'][option] = result['value']
                self.update_battle()
                return [True, 'Mapoption ' + map_name['Options'][option]['Key'] + ' changed to ' + str(result['value'])]
            else:
                return [False, self._check_mod_option_value(map_name['Options'][option], value, 1)]

    def set_start_pos(self, start_pos):
        log.info(start_pos)
        if start_pos < 4:
            self.host.battle['StartPosType'] = start_pos
            self.update_battle()
            self.load_boxes()
            return [True, 'Start Position set']
        else:
            return [False, 'Start Position must be between 0 and 3']

    def logic_start_battle(self, force_start=False):
        log.info('')
        self.refresh()
        # self.fix_id()

        if not force_start:
            for User in self.battle_users:
                if not self.battle_users[User]['Ready'] and not self.battle_users[User]['Spectator']:
                    return [False, 'Not all users are ready yet']

        locked = self.lobby.battles[self.lobby.battle_id]['Locked']
        self.lobby.lock_battle(1)
        self.lobby.battle_say('Preparing to start the battle...', 1)
        time.sleep(1)

        if self.host.Spring.start():
            self.lobby.start_battle()
            self.host.host_command_wait('CLIENTSTATUS')
            self.lobby.lock_battle(locked)
            return [True, 'Battle started']
        else:
            self.lobby.lock_battle(locked)
            return [False, 'Battle failed to start']

    def set_handicap(self, search_user, hcp):
        log.info('User:' + str(search_user) + ', hcp:' + str(hcp))
        user = self._search_user_in_battle(search_user)
        if not user:
            return [False, 'User "' + str(search_user) + '" is not in this battle']
        if 0 <= hcp <= 100:
            if self.battle_users[user]['AI']:
                self.lobby.update_bot(user, self.battle_status(0, self.battle_users[user]['Team'],
                                                               self.battle_users[user]['Ally'], 0,
                                                               int(hcp), 0,
                                                               self.battle_users[user]['Side']),
                                      self._battle_color(self.battle_users[user]['Color']))
            else:
                self.lobby.handicap_user(user, hcp)
            return [True, 'OK']
        else:
            return [False, 'Handicap must be in the range of 0 - 100']

    def re_host_with_mod(self, mod=None):
        self.refresh()
        self.server.SpringUnitsync.reload_mods()
        if not mod:
            self.host.battle['Mod'] = self.host.config['MOD']
            self.host.set_default_mod()
            mod = self.host.battle['Mod']
        match = self.LogicFunctionSearchMatch(mod, self.host.get_unitsync_mod('#KEYS#'))
        if match and self.battle['Mod'] == match:
            return [True, '"' + str(match) + '" is already hosted']
        elif match:
            self.host.battle['Mod'] = match
            self.close_battle()
            self.open_battle()
            self.load_boxes()
            return [True, 'Mod changed to "' + match + '"']
        else:
            matches = self.LogicFunctionSearchMatch(mod, self.host.get_unitsync_mod('#KEYS#'), 1)
            if matches:
                result = ['Multiple mods found, listing the 10 first:']
                for mod in matches:
                    result.append(mod)
                    if len(result) == 11:
                        break
                return [False, result]
        return [False, 'Mod "' + str(mod) + '" not found']

    def re_host_with_password(self, password):
        self.refresh()
        self.host.battle['BattlePassword'] = password
        self.close_battle()
        self.open_battle()
        self.load_boxes()
        return [True, 'Password changed']

    def add_box(self, left, top, right, bottom, team=-1):
        self.refresh()
        if left > 100 or top > 100 or right > 100 or bottom > 100 or left < 0 or top < 0 or right < 0 or bottom < 0:
            return [False, 'Box values must be between 0 and 100']
        elif team < -1 or team == 0 or team > 16:
            return [False, 'Team must be between 1 and 16']

        if team == -1:
            for iTeam in range(0, 15):
                if iTeam not in self.battle['Boxes']:
                    team = iTeam
                    break
            if team == -1:
                return [False, 'No team is free, please specify which should be replaced']
        else:
            team = team - 1

        if team in self.battle['Boxes']:
            self.remove_box(team + 1)
        self.lobby.add_box(team, left * 2, top * 2, right * 2, bottom * 2)
        return [True, 'Box added']

    def split_box(self, box_type, size, clear_boxes=0):
        self.set_start_pos(2)
        if box_type not in ['h', 'v', 'c1', 'c2', 'c', 's']:
            return [False, 'The box type is not a valid type']
        if size < 1 or size > 100:
            return [False, 'Size must be between 1 and 100']
        if clear_boxes:
            self.remove_boxes()
        if box_type == 'v':
            self.add_box(0, 0, size, 100, 1)
            self.add_box(100 - size, 0, 100, 100, 2)
        elif box_type == 'h':
            self.add_box(0, 0, 100, size, 1)
            self.add_box(0, 100 - size, 100, 100, 2)
        elif box_type == 'c1':
            self.add_box(100 - size, 0, 100, size, 1)
            self.add_box(0, 100 - size, size, 100, 2)
        elif box_type == 'c2':
            self.add_box(0, 0, size, size, 1)
            self.add_box(100 - size, 100 - size, 100, 100, 2)
        elif box_type == 'c':
            self.add_box(0, 0, size, size, 1)
            self.add_box(100 - size, 100 - size, 100, 100, 2)
            self.add_box(100 - size, 0, 100, size, 3)
            self.add_box(0, 100 - size, size, 100, 4)
        elif box_type == 's':
            self.add_box(0, 0, size, 100, 1)
            self.add_box(100 - size, 0, 100, 100, 2)
            self.add_box(0, 0, 100, size, 3)
            self.add_box(0, 100 - size, 100, 100, 4)
        return [True, 'Boxes added']

    def clear_box(self, box):
        if box < 0 or box > 16:
            return [False, 'Box has to be between 0 and 16']
        elif box:
            self.remove_box(box)
            return [True, 'Box cleared']
        else:
            self.remove_boxes()
            return [True, 'Boxes cleared']

    def remove_box(self, team):
        self.lobby.remove_box(team - 1)

    def remove_boxes(self):
        self.refresh()
        if 'Boxes' in self.battle:
            for team in list(self.battle['Boxes'].keys()):
                self.lobby.remove_box(team)

    def save_boxes(self):
        self.refresh()
        if self.host.battle['StartPosType'] != 2:
            return [False, 'Can only save boxes for "Choose in game"']

        boxes = []
        for Team in list(self.battle['Boxes'].keys()):
            boxes.append(str(Team) + ' ' + str(self.battle['Boxes'][Team][0]) + ' ' + str(
                self.battle['Boxes'][Team][1]) + ' ' + str(self.battle['Boxes'][Team][2]) + ' ' + str(
                self.battle['Boxes'][Team][3]))
        if len(boxes) > 0:
            boxes = '\n'.join(boxes)
            self.server.database.store_boxes(
                self.host.host_id, self.battle['Map'], self.host.battle['Teams'],
                self.host.battle['StartPosType'], boxes)
            return [True, 'Saved']
        else:
            return [False, 'No boxes to save']

    def load_preset(self, preset):
        config = self.server.database.load_preset(self.host.host_id, preset)
        if config:
            for command in config.split('\n'):
                self.host.handle_input('INTERNAL', '!' + command.strip())
            return [True, 'Preset loaded']
        else:
            return [True, 'No preset found for "' + str(preset) + '"']

    def save_preset(self, preset):
        self.refresh()
        config = ['map ' + self.battle['Map'], 'teams ' + str(self.host.battle['Teams'])]
        mod = self.host.get_unitsync_mod(self.battle['Mod'])
        # for team, boxes in self.battle['Boxes'].items():
        #     boxesstr = " ".join(str(b) for b in boxes)
        #     config.append('addbox ' + boxesstr + ' ' + str(team))
        for mod_key in mod['Options'].keys():
            if mod_key in self.host.battle['ModOptions']:
                if str(mod['Options'][mod_key]['Default']) != str(self.host.battle['ModOptions'][mod_key]):
                    config.append('modoption ' + str(mod_key) + ' ' + str(self.host.battle['ModOptions'][mod_key]))
        self.server.database.store_preset(self.host.host_id, preset, '\n'.join(config))
        return [True, 'Saved']

    def set_teams(self, teams):
        if teams > 16 or teams < 2:
            return [False, 'Teams has to be between 2 and 16']
        self.host.battle['Teams'] = teams
        self.battle_cmds.balance.run()
        return [True, 'OK']

    def disable_unit(self, search_unit):
        self.refresh()
        mod = self.host.get_unitsync_mod()

        units = {}
        for Unit in list(mod['Units'].keys()):
            units[Unit] = Unit + ' - ' + mod['Units'][Unit]

        match = self.LogicFunctionSearchMatch(search_unit, units)
        if match:
            if match in mod['Units']:
                self.lobby.disable_units(match)
                return [True, '"' + match + '" has been disabled']
        else:
            matches = self.LogicFunctionSearchMatch(search_unit, units, 1, 0)
            if matches:
                matches = ['Available units:'] + matches
                return [False, matches]
        return [False, 'No match found']

    def enable_all_units(self):
        self.lobby.battle_enable_all_units()
        return [True, 'All units enabled']

    def set_user_color(self, color_user, color):
        if not len(color) == 6 or color.upper().strip('0123456789ABCDEF'):
            return [False, 'Color was not a Hex RGB color']

        db_user = self.server.database.search_user(color_user)

        if not db_user:
            return [False, 'User "' + str(color_user) + '" does not exist']

        self.server.database.update_smurf_color(db_user.id, color)
        return [True, 'Color set']

    def fix_colors(self, color_user=None):
        log.debug(str(color_user))
        self.refresh()
        color_list = ['FF0000', '00FF00', '0000FF', '00FFFF', 'FF00FF', 'FFFF00', '000000', 'FFFFFF', '808080']

        ''' Collect current colors '''
        current_list = {}
        for user in self.battle_users:
            if 'Spectator' in self.battle_users[user] and (
                        not self.battle_users[user]['Spectator'] or self.battle_users[user]['AI']):
                current_list[self.battle_users[user]['Team']] = self.lobby.battle_users[user]['Color']

        if color_user:
            user = self._search_user_in_battle(color_user)
            if not user:
                return [False, 'User "' + str(color_user) + '" is not in this battle']

            db_user = self.server.database.search_user(user)

            if db_user and db_user.color_hex:
                return self.force_color(color_user, db_user.color_hex)

            color_user = user

            for diff in [400, 300, 200, 150, 100, 50, 10, 0]:
                for color in color_list:
                    color_ok = True
                    for Team in list(current_list.keys()):
                        if Team != self.battle_users[color_user]['Team']:
                            color_diff = self._compare_colors(color, current_list[Team])
                            if color_diff <= diff:
                                color_ok = False
                    if color_ok and color != self.lobby.battle_users[color_user]['Color']:
                        self.lobby.battle_users[color_user]['Color'] = color
                        return self.force_color(color_user, color)
        else:
            for user in self.battle_users:
                db_user = self.server.database.search_user(user)
                if db_user and db_user.color_hex:
                    self.force_color(user, db_user.color_hex)
                elif not self.battle_users[user]['Spectator'] or self.battle_users[user]['AI']:
                    for Team in list(current_list.keys()):
                        if Team != self.battle_users[user]['Team']:
                            if self._compare_colors(self.battle_users[user]['Color'], current_list[Team]) < 50:
                                self.fix_colors(user)
            return [True, 'Colors fixed']

    def set_bot_side(self, search_user, search_side):
        user = self._search_user_in_battle(search_user)
        if not user:
            return [False, 'User "' + str(search_user) + '" is not in this battle']
        if self.battle_users[user]['AI']:
            mod = self.host.get_unitsync_mod(self.battle['Mod'])
            side = self.LogicFunctionSearchMatch(search_side, mod['Sides'], 0, 0)
            if not side:
                return [False, 'Side "' + str(search_side) + '" doesn\'t exist']
            self.lobby.update_bot(user, self.battle_status(0, self.battle_users[user]['Team'],
                                                           self.battle_users[user]['Ally'], 0,
                                                           self.battle_users[user]['Handicap'], 0, side),
                                  self._battle_color(self.battle_users[user]['Color']))
            return [True, 'OK']
        else:
            return [False, 'User "' + str(user) + '" is not a bot']

    def _search_user_in_battle(self, user):
        if self.lobby.battle_id:
            match = self.LogicFunctionSearchMatch(user, list(self.lobby.battle_users.keys()))
            if match in self.lobby.battle_users:
                return match
        return False

    def _compare_colors(self, color1, color2):
        diff = 0
        diff += abs(int(color1[4:6], 16) - int(color2[4:6], 16))
        diff += abs(int(color1[2:4], 16) - int(color2[2:4], 16))
        diff += abs(int(color1[0:2], 16) - int(color2[0:2], 16))
        return diff

    def LogicFunctionSearchMatch(self, search, match_list, list_matches=0, dict_return_keys=1):
        log.info('Search: ' + str(search))
        matches = []
        if isinstance(match_list, list):
            for match in match_list:
                if search.lower() in match.lower():
                    if search == match and not list_matches:
                        log.info('Perfect match:' + str(search))
                        return search
                    else:
                        matches.append(match)
        elif isinstance(match_list, dict):
            for match in list(match_list.keys()):
                if search.lower() in match_list[match].lower():
                    if search.lower() == match_list[match].lower() and not list_matches:
                        log.info('Perfect match:' + str(match_list[match]))
                        return match_list[match]
                    elif dict_return_keys:
                        matches.append(match)
                    else:
                        matches.append(match_list[match])
        if len(matches) == 1:
            log.info('Found:' + str(matches[0]))
            return matches[0]
        elif len(matches) and list_matches:
            return matches
        return False

    def load_boxes(self):
        log.info('')
        if self.host.battle['StartPosType'] == 2:
            self.refresh()
            boxes = self.server.database.load_boxes(
                self.host.host_id, self.battle['Map'], self.host.battle['Teams'], self.host.battle['StartPosType'])
            if boxes:
                self.remove_boxes()
                for box in boxes.split('\n'):
                    box = box.split(' ')
                    self.add_box(int(box[1]) // 2, int(box[2]) // 2, int(box[3]) // 2, int(box[4]) // 2,
                                 int(box[0]) + 1)
        else:
            self.remove_boxes()

    def _check_mod_option_value(self, option, value, help_flag=0):
        result = {'OK': 0}
        if option['Type'] == 'Select':
            if value in option['Options']:
                result = {'OK': 1, 'value': value}
            if help_flag == 1:
                result = ['Valid keys for "' + str(option['Title']) + '" are :']
                for Key in option['Options']:
                    result.append(str(Key) + ' - ' + str(option['Options'][Key]))
        elif option['Type'] == 'Numeric':
            try:
                getcontext().prec = 6
                value = float(value)
                log.debug(value)
                log.debug(value >= option['Min'])
                log.debug(value <= option['Max'])
                log.debug(not value % option['Step'])
                log.debug(Decimal((value / option['Step']) % 1))
                if option['Min'] <= value <= option['Max'] and (
                                    Decimal((value / option['Step'])) % 1 == 0 or Decimal(
                            (value / option['Step'])) % 1 == 1):
                    if int(value) == value:
                        value = int(value)
                    result = {'OK': 1, 'value': value}
            except:
                log.error('CRASH')
            if help_flag == 1:
                result = 'Valid values are between ' + str(option['Min']) + ' to ' + str(
                    option['Max']) + ' with a stepping of ' + str(option['Step'])
        elif option['Type'] == 'Boolean':
            try:
                value = int(value)
                if value == 1 or value == 0:
                    result = {'OK': 1, 'value': value}
            except:
                pass
            if help_flag == 1:
                result = 'Valid values for "' + str(option['Title']) + '" are 0 or 1'
        return result

    def battle_status(self, ready, team, ally, spec, hcp, sync, side):
        status = 0
        if ready:    status = status + 2
        tmp = self.lobby.dec2bin(int(team), 4)
        if tmp[0]:    status = status + 4
        if tmp[1]:    status = status + 8
        if tmp[2]:    status = status + 16
        if tmp[3]:    status = status + 32
        tmp = self.lobby.dec2bin(int(ally), 4)
        if tmp[0]:    status = status + 64
        if tmp[1]:    status = status + 128
        if tmp[2]:    status = status + 256
        if tmp[3]:    status = status + 512
        if spec:    status = status + 1024
        tmp = self.lobby.dec2bin(int(hcp), 7)
        if tmp[0]:    status = status + 2048
        if tmp[1]:    status = status + 4096
        if tmp[2]:    status = status + 8192
        if tmp[3]:    status = status + 16384
        if tmp[4]:    status = status + 32768
        if tmp[5]:    status = status + 65536
        if tmp[6]:    status = status + 131072
        # 262144
        # 524288
        # 1048576
        # 2097152
        if sync == 1:
            status = status + 4194304
        elif sync == 2:
            status = status + 8388608

        mod = self.host.get_unitsync_mod()
        side_ok = -1
        for i_side in list(mod['Sides'].keys()):
            if mod['Sides'][i_side] == side:
                side_ok = i_side
        if side_ok == -1:
            side_ok = int(side)
        tmp = self.lobby.dec2bin(int(side_ok), 4)
        if tmp[0]:    status = status + 16777216
        if tmp[1]:    status = status + 33554432
        if tmp[2]:    status = status + 67108864
        if tmp[3]:    status = status + 134217728

        return status

    def _battle_color(self, hex_color):
        return int(hex_color[4:6] + hex_color[2:4] + hex_color[0:2], 16)

    def update_battle(self):
        log.info('')
        self.refresh()
        tags = []
        if 'game/startpostype' not in self.battle['ScriptTags'] or self.battle['ScriptTags'][
            'game/startpostype'] != str(self.host.battle['StartPosType']):
            tags.append(['game/startpostype', self.host.battle['StartPosType']])
        if self.lobby.battle_id and 'ModOptions' in self.host.battle:
            for Key in list(self.host.battle['ModOptions'].keys()):
                value = self.host.battle['ModOptions'][Key]
                try:
                    if int(value) == value:
                        value = int(value)
                    tag = ['game/modoptions/' + str(Key).lower(), str(value)]
                except:
                    tag = ['game/modoptions/' + str(Key).lower(), str(value)]
                if tag[0] not in self.battle['ScriptTags'] or self.battle['ScriptTags'][tag[0]] != tag[1]:
                    tags.append(tag)
        if self.lobby.battle_id and 'MapOptions' in self.host.battle:
            for Key in list(self.host.battle['MapOptions'].keys()):
                value = self.host.battle['MapOptions'][Key]
                try:
                    if int(value) == value:
                        value = int(value)
                    tag = ['game/mapoptions/' + str(Key).lower(), str(value)]
                except:
                    tag = ['game/mapoptions/' + str(Key).lower(), str(value)]
                if tag[0] not in self.battle['ScriptTags'] or self.battle['ScriptTags'][tag[0]] != tag[1]:
                    tags.append(tag)
        if len(tags) > 0:
            self.lobby.update_battle_script(tags)

    def load_battle_defaults(self):
        log.info('')
        mod = self.host.get_unitsync_mod(self.host.battle['Mod'])
        if mod and 'Options' in mod and mod['Options']:
            for k in list(mod['Options'].keys()):
                if k not in self.host.battle['ModOptions']:
                    self.host.battle['ModOptions'][k] = mod['Options'][k]['Default']
        self.host.battle['StartPosType'] = 1
        self.load_map_defaults()

    def load_map_defaults(self):
        log.info('')
        map_name = self.host.get_unitsync_map(self.host.battle['Map'])
        self.host.battle['MapOptions'] = {}
        if map_name and 'Options' in map_name and len(map_name['Options']):
            for Key in list(map_name['Options'].keys()):
                if Key not in self.host.battle['MapOptions']:
                    self.host.battle['MapOptions'][Key] = map_name['Options'][Key]['Default']
