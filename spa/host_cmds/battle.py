import logging

from spa.host_cmds.battle_balance import BattleBalance
from spa.host_cmds.battle_manager import BattleManager

log = logging.getLogger(__name__)


class BattleCmds(object):
    def __init__(self, host_cmds, server, host):
        self.server = server
        log.info('BattleCmds Init')
        self.Host = host
        self.host_cmds = host_cmds
        self.logic = BattleManager(self, server, host)
        self.balance = BattleBalance(self, host)
        self.commands = {
            # 0 = Field
            # 1 = Return to where (Source, PM, Battle)
            # 2 = Usage example
            # 3 = Usage desc
            # 4 = Category (if available)
            # 5 = Extended help (if available)
            'map': [['*'], 'BattleMe', '!map <map name>', 'Changes the map to <map name>'],
            'maps': [['O*'], 'PM', '!maps <optional search>', 'Return a list with all the available maps'],
            'mods': [['O*'], 'PM', '!mods <optional search>', 'Return a list with all the available mods'],
            'start': [[], 'BattleMe', '!start', 'Starts the battle if possible'],
            'stop': [[], 'BattleMe', '!stop', 'Stops the battle'],
            'lock': [['OB'], 'BattleMe', '!lock [0/1]', 'Locks/unlocks the battle'],
            'kick': [['V'], 'BattleMe', '!kick <user>', 'Kicks <user> from the battle'],
            'ring': [['OV'], 'BattleMe', '!ring [<user>]', 'Rings a specific user or all unready users'],
            'addbox': [['I', 'I', 'I', 'I', 'OI'], 'Source',
                       '!addbox <Left 0-100> <Top 0-100> <Right 0-100> <Bottom 0-100> <Team 1-16>',
                       'Adds a startbox (if no team is specified, the next empty one is used)'],
            'udp': [['*'], 'Source', '!udp <command>', 'Sends a command to the spring server'],
            'forcestart': [[], 'BattleMe', '!forcestart', 'Force start the battle'],
            'info': [[], 'PM', '!info', 'Returns the status of the current battle'],
            'addbot': [['I', 'I', 'V', 'V6', '*'], 'BattleMe', '!addbot 1 1 CORE FFFFFF ShardLua',
                       'Add a bot to the battle (Team, Ally, Side, Hex RGB Color, Bot)'],
            'spec': [['V'], 'BattleMe', '!spec <User>', 'Spectates the specified user'],
            'fixid': [[], 'BattleMe', '!fixid', 'Fix the player IDs'],
            'balance': [[], 'BattleMe', '!balance', 'Balances the battle users based on rank'],
            'openbattle': [[], 'Source', '!openbattle', 'Opens a battle'],
            'modoption': [['V', 'O*'], ['BattleMeRequester', 'PM'], '!modoption <option> <value>', 'Sets a mod option'],
            'startpos': [['I'], 'Source', '!startpos <0-3>',
                         'Sets the start pos (0 Fixed, 1 Randon, 2 Choose in-game, 3 Choose now)'],
            'hcp': [['V', 'I'], 'Source', '!hcp <user> <hcp>', 'Sets the handicap for the specified user'],
            'mod': [['O*'], 'Source', '!mod <mod>', 'Rehosts with the specified mod, leave empty for settings default'],
            'password': [['V'], 'Source', '!password <password>', 'Rehosts with the specified password'],
            'saveboxes': [[], 'Source', '!saveboxes', 'Saves the current box setup'],
            'kickbots': [[], 'Source', '!kickbots', 'Kicks all bots from the battle'],
            'preset': [['V'], 'Source', '!preset <preset name>', 'Loads the specified preset settings'],
            'savepreset': [['V'], 'Source', '!savepreset <preset name>',
                           'Saves the current battle settings with the <preset name>'],
            'teams': [['OI'], 'Source', '!teams <>|<1-16>', 'Sets or displays the number of teams in the battle'],
            'mapoption': [['V', 'O*'], ['BattleMeRequester', 'PM'], '!mapoption <option> <value>', 'Sets a map option'],
            'disableunit': [['V'], 'Source', '!disableunit <unit>', 'Disbles a unit'],
            'enableunitsall': [[], 'Source', '!enableunitsall', 'Enables all units'],
            'id': [['V', 'I'], 'BattleMe', '!id <user> <new id>', 'Changes a users ID'],
            'team': [['V', 'I'], 'BattleMe', '!team <user> <new id>', 'Changes a users team'],
            'color': [['V', 'V'], 'BattleMe', '!color <user> <Hex color>', 'Changes an user color'],
            'split': [['V', 'I', 'OB'], 'BattleMe', '!split <type> <size> <optional 1 to clear boxes>',
                      'Creates multiple boxes'],
            'clearbox': [['I'], 'BattleMe', '!clearbox <0 = all|1-16>', 'Removes one or all boxes'],
            'fixcolor': [['V'], 'BattleMe', '!fixcolor <user>', 'Fixes the <user>s battle color'],
            'fixcolors': [[], 'BattleMe', '!fixcolors', 'Fixes all users battle colors'],
            'setcolor': [['V', 'V'], 'BattleMe', '!setcolor <user> <Hex color>', 'Define an user color'],
            'botside': [['V', 'V'], 'BattleMe', '!botside <bot> <side>', 'Forces <bot> to switch side to <side>'],
            'nextmap': [[], 'BattleMe', '!nextmap', 'Switches to the next map in the list'],
            'prevmap': [[], 'BattleMe', '!prevmap', 'Switches to the prev map in the list'],
            'randommap': [[], 'BattleMe', '!randommap',
                          'Switches to a random map in the list (does not work with prev/next map)'],
            'reordermaps': [[], 'BattleMe', '!reordermaps', 'Reorders the map list'],
        }
        for command in self.commands:
            self.host_cmds.commands[command] = self.commands[command]

    def handle_input(self, command, data, source):
        log.debug('Handle Input::%s::%s::%s', command, data, source)

        if command == 'map':
            return self.logic.switch_map(data[0])
        elif command == 'maps':
            if len(data) == 1:
                return self.logic.list_maps(data[0])
            else:
                return self.logic.list_maps()
        elif command == 'mods':
            if len(data) == 1:
                return self.logic.list_mods(data[0])
            else:
                return self.logic.list_mods()
        elif command == 'start':
            return self.logic.logic_start_battle()
        elif command == 'stop':
            result = self.Host.Spring.stop()
            return [True, result]
        elif command == 'lock':
            if len(data) == 1:
                lock = data[0]
            else:
                lock = {0: 1, 1: 0}[self.Host.Lobby.battles[self.Host.Lobby.battle_id]['Locked']]
            self.Host.Lobby.lock_battle(lock)
            if lock:
                return [True, 'Battle locked']
            else:
                return [True, 'Battle unlocked']
        elif command == 'kick':
            return self.logic.kick(data[0])
        elif command == 'ring':
            if len(data) == 1:
                return self.logic.ring(data[0])
            else:
                return self.logic.ring()
        elif command == 'addbox':
            if len(data) == 4:
                return self.logic.add_box(data[0], data[1], data[2], data[3])
            else:
                return self.logic.add_box(data[0], data[1], data[2], data[3], data[4])
        elif command == 'udp':
            self.Host.Spring.SpringTalk(data[0])
        elif command == 'forcestart':
            if source == "GameBattle":
                self.Host.Spring.SpringTalk('/forcestart')
            return self.logic.logic_start_battle(force_start=True)
        elif command == 'info':
            return self.logic.info()
        elif command == 'addbot':
            return self.logic.add_bot(data[0], data[1], data[2], data[3], data[4])
        elif command == 'spec':
            return self.logic.spec(data[0])
        elif command == 'fixid':
            return self.logic.fix_id()
        elif command == 'balance':
            return self.balance.run()
        elif command == 'openbattle':
            return self.logic.open_battle()
        elif command == 'modoption':
            if len(data) == 2:
                return self.logic.set_mod_option(data[0], data[1])
            else:
                return self.logic.set_mod_option(data[0])
        elif command == 'startpos':
            return self.logic.set_start_pos(data[0])
        elif command == 'hcp':
            return self.logic.set_handicap(data[0], data[1])
        elif command == 'mod':
            if len(data) == 1:
                return self.logic.re_host_with_mod(data[0])
            else:
                return self.logic.re_host_with_mod()
        elif command == 'password':
            return self.logic.re_host_with_password(data[0])
        elif command == 'saveboxes':
            return self.logic.save_boxes()
        elif command == 'kickbots':
            return self.logic.kick_bots()
        elif command == 'preset':
            return self.logic.load_preset(data[0])
        elif command == 'savepreset':
            return self.logic.save_preset(data[0])
        elif command == 'teams':
            if len(data) == 1:
                return self.logic.set_teams(data[0])
            else:
                return [True, 'No. of teams: ' + str(self.Host.battle['Teams'])]
        elif command == 'mapoption':
            if len(data) == 2:
                return self.logic.set_map_option(data[0], data[1])
            else:
                return self.logic.set_map_option(data[0])
        elif command == 'disableunit':
            return self.logic.disable_unit(data[0])
        elif command == 'enableunitsall':
            return self.logic.enable_all_units()
        elif command == 'id':
            return self.logic.force_id(data[0], data[1])
        elif command == 'team':
            return self.logic.force_team(data[0], data[1])
        elif command == 'color':
            return self.logic.force_color(data[0], data[1])
        elif command == 'split':
            if len(data) == 3:
                return self.logic.split_box(data[0], data[1], data[2])
            else:
                return self.logic.split_box(data[0], data[1])
        elif command == 'clearbox':
            return self.logic.clear_box(data[0])
        elif command == 'setcolor':
            return self.logic.set_user_color(data[0], data[1])
        elif command == 'fixcolor':
            return self.logic.fix_colors(data[0])
        elif command == 'fixcolors':
            return self.logic.fix_colors()
        elif command == 'botside':
            return self.logic.set_bot_side(data[0], data[1])
        elif command == 'nextmap':
            return self.logic.switch_map(None, 'Next')
        elif command == 'prevmap':
            return self.logic.switch_map(None, 'Prev')
        elif command == 'randommap':
            return self.logic.switch_map(None, 'Random')
        elif command == 'reordermaps':
            return self.logic.switch_map(None, 'Reorder')
