LOBBY_SERVER_HOST = 'springrts.com'
LOBBY_SERVER_PORT = 8200
UNITSYNC_PATH = '/Spring/libunitsync.so'
SPRING_DEDICATED_PATH = '/Spring/spring-dedicated'
SPRING_HEADLESS_PATH = '/Spring/spring-headless'

TEMP_PATH = "/tmp/"
MODS_PATH = "~/.spring/games/"
MODS_PUBLIC_PATH = "/var/www/html/mods/"
MAPS_PATH = "~/.spring/maps/"
DEMOS_PATH = "/var/www/html/replays/"

DATABASE_URL = "mysql://morts:XercpWJVSa2JenqA@localhost:3306/spa"

DATABASE = {
    'NAME': 'springrts',
    'USER': 'morts',
    'PASSWORD': 'XercpWJVSa2JenqA',
    'HOST': 'localhost',
    'PORT': '3306'
}

HOSTS = {
    'primary': {
        'ACCOUNT': {
            'USER': 'MORTSHost2',
            'PASSWORD': 'bepid',
            'PORT': 8452
        },
        'MOD': 'Balanced\ Annihilation\ V\d+\.\d+',
        'BATTLE_DESCRIPTION': 'MORTS Official (Max 10 players)',
        'BATTLE_PASSWORD': 'bepid',
        'MAP': 'DeltaSiegePrime Ultimate',
        'LOBBY_CHANNELS': ['autohost', 'bots', 'morts'],

        'ECHO_LOBBY_CHAT_TO_SPRING': False,
        'ECHO_GAME_NORMAL_CHAT_TO_LOBBY': False,
        'ECHO_GAME_ALLY_CHAT_TO_LOBBY': False,
        'ECHO_GAME_SPEC_CHAT_TO_LOBBY': False,

        'ACCESS_COMMANDS': {
            'debug': ['owner'],
            'spawnhost': ['owner'],
            'terminate': ['owner'],
            'terminateall': ['owner'],
            'code': ['owner', 'admin'],
            'udp': ['owner'],
            'start': ['owner', 'admin', '%BattlePlayer%'],
            'kick': ['owner', 'admin', 'operator'],
            'ring': ['admin', 'operator', '%GamePlayer%'],  # '%BattlePlayer%'
            'forcestart': ['owner', 'admin'],
            'password': ['owner', 'admin'],
            'downloadmod': ['owner', 'admin', 'operator'],
            'downloadmap': ['owner', 'admin', 'operator'],
            'savepreset': ['owner', 'admin', 'operator'],
            'showconfig': ['owner', 'admin'],
            'searchuser': ['owner', 'admin'],
        },
        'ACCESS_ROLES': {
            'owner': [
                'YuriHeupa',
            ],
            'admin': [
                '_MaDDoX',
            ],
            'operator': [
            ],
        },
        'EVENT_HOOKS': {
            'LOGININFOEND': ['openbattle'],
            'OPENBATTLE': ['preset default', 'setup v'],
        },
        'ALIAS_COMMANDS': {
            'setup': [
                'split %1 27',
                'modoption mo_armageddontime 40'
            ],
            'test': [
                'modoption maxunits 5000',
                'addbot 2 2 CORE 00BFFF ShardLua',
                'addbot 3 2 CORE FFBFFF ShardLua'
            ],
            'units': [
                'modoption maxunits %1'
            ],
            'metal': [
                'modoption startmetal %1'
            ],
            'energy': [
                'modoption startenergy %1'
            ],
            'listmaps': [
                'maps'
            ],
            'listusers': [
                'admins'
            ],
            'fixids': [
                'fixid'
            ],
            'fix': [
                'fixid'
            ],
        }
    },
    # 'secondary': {
    #     'ACCOUNT': {
    #         'USER': 'MORTSHost2',
    #         'PASSWORD': 'bepid',
    #         'PORT': 8453
    #     },
    #     'MOD': 'Balanced\ Annihilation\ V\d+\.\d+',
    #     'BATTLE_DESCRIPTION': 'MORTS Official 2',
    #     'BATTLE_PASSWORD': 'bepid',
    #     'MAP': 'DeltaSiegeDry',
    #     'LOBBY_CHANNELS': ['autohost', 'bots', 'morts'],
    #
    #     'ECHO_LOBBY_CHAT_TO_SPRING': False,
    #     'ECHO_GAME_NORMAL_CHAT_TO_LOBBY': False,
    #     'ECHO_GAME_ALLY_CHAT_TO_LOBBY': False,
    #     'ECHO_GAME_SPEC_CHAT_TO_LOBBY': False,
    #
    #     'ACCESS_COMMANDS': {
    #         'debug': ['owner'],
    #         'spawnhost': ['owner'],
    #         'terminate': ['owner'],
    #         'terminateall': ['owner'],
    #         'code': ['owner', 'admin'],
    #         'udp': ['owner'],
    #         'start': ['owner', 'admin', '%BattlePlayer%'],
    #         'kick': ['owner', 'admin', 'operator'],
    #         'ring': ['admin', 'operator', '%GamePlayer%'],  # '%BattlePlayer%'
    #         'forcestart': ['owner', 'admin'],
    #         'downloadmod': ['owner', 'admin', 'operator'],
    #         'downloadmap': ['owner', 'admin', 'operator'],
    #         'savepreset': ['owner', 'admin', 'operator'],
    #         'showconfig': ['owner', 'admin'],
    #         'searchuser': ['owner', 'admin'],
    #     },
    #     'ACCESS_ROLES': {
    #         'owner': [
    #             'YuriHeupa',
    #         ],
    #         'admin': [
    #             '_MaDDoX',
    #         ],
    #         'operator': [
    #         ],
    #     },
    #     'EVENT_HOOKS': {
    #         'LOGININFOEND': ['openbattle'],
    #         'OPENBATTLE': ['preset default', 'setup v'],
    #     },
    #     'ALIAS_COMMANDS': {
    #         'setup': [
    #             'split %1 20',
    #             'modoption mo_armageddontime 45'
    #         ],
    #         'test': [
    #             'modoption maxunits 5000',
    #             'addbot 2 2 CORE 00BFFF ShardLua',
    #             'addbot 3 2 CORE FFBFFF ShardLua'
    #         ],
    #         'units': [
    #             'modoption maxunits %1'
    #         ],
    #         'metal': [
    #             'modoption startmetal %1'
    #         ],
    #         'energy': [
    #             'modoption startenergy %1'
    #         ],
    #         'listmaps': [
    #             'maps'
    #         ],
    #         'listusers': [
    #             'admins'
    #         ],
    #         'fixids': [
    #             'fixid'
    #         ],
    #         'fix': [
    #             'fixid'
    #         ],
    #     }
    # },
    'secondary': {
        'ACCOUNT': {
            'USER': 'MORTSHost',
            'PASSWORD': 'bepid',
            'PORT': 8453
        },
        'MOD': 'Total\ Annihilation\ Prime\ \d+\.\d+',
        'BATTLE_DESCRIPTION': 'MORTS Prime',
        'BATTLE_PASSWORD': 'bepid',
        'MAP': 'DeltaSiegePrime Ultimate',
        'LOBBY_CHANNELS': ['autohost', 'bots', 'morts'],

        'ECHO_LOBBY_CHAT_TO_SPRING': False,
        'ECHO_GAME_NORMAL_CHAT_TO_LOBBY': False,
        'ECHO_GAME_ALLY_CHAT_TO_LOBBY': False,
        'ECHO_GAME_SPEC_CHAT_TO_LOBBY': False,

        'ACCESS_COMMANDS': {
            'debug': ['owner'],
            'spawnhost': ['owner'],
            'terminate': ['owner'],
            'terminateall': ['owner'],
            'code': ['owner', 'admin'],
            'udp': ['owner'],
            'start': ['owner', 'admin', '%BattlePlayer%'],
            'kick': ['owner', 'admin', 'operator'],
            'ring': ['owner', 'admin', 'operator', '%GamePlayer%'],  # '%BattlePlayer%'
            'forcestart': ['owner', 'admin'],
            'downloadmod': ['owner', 'admin', 'operator'],
            'downloadmap': ['owner', 'admin', 'operator'],
            'savepreset': ['owner', 'admin', 'operator'],
            'showconfig': ['owner', 'admin'],
            'searchuser': ['owner', 'admin'],
        },
        'ACCESS_ROLES': {
            'owner': [
                'YuriHeupa',
            ],
            'admin': [
                '_MaDDoX',
            ],
            'operator': [
            ],
        },
        'EVENT_HOOKS': {
            'LOGININFOEND': ['openbattle'],
            'OPENBATTLE': ['preset default', 'setup v'],
        },
        'ALIAS_COMMANDS': {
            'setup': [
                'split %1 27',
                'modoption mo_armageddontime 45'
            ],
            'test': [
                'modoption maxunits 5000',
                'addbot 2 2 CORE 00BFFF ShardLua',
                'addbot 3 2 CORE FFBFFF ShardLua'
            ],
            'units': [
                'modoption maxunits %1'
            ],
            'metal': [
                'modoption startmetal %1'
            ],
            'energy': [
                'modoption startenergy %1'
            ],
            'armageddon': [
                'modoption mo_armageddontime %1'
            ],
            'listmaps': [
                'maps'
            ],
            'listusers': [
                'admins'
            ],
            'fixids': [
                'fixid'
            ],
            'fix': [
                'fixid'
            ],
        }
    }
}
