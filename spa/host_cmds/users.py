import logging

log = logging.getLogger(__name__)


class UserCmds(object):
    def __init__(self, host_cmds, server, host):
        self.server = server
        log.info('UserCmds Init')
        self.Host = host
        self.host_cmds = host_cmds
        self.commands = {
            # 0 = Field
            # 1 = Return to where (Source, PM, Battle)
            # 2 = Usage example
            # 3 = Usage desc
            # 4 = Category (if available)
            # 5 = Extended help (if available)
            'searchuser': [['V'], 'PM', '!searchuser <map name>', 'Searches for a user', 'DB query functions'],
            'admins': [[], 'PM', '!admins', 'Return a list with all the admins'],
        }
        for command in self.commands:
            self.host_cmds.commands[command] = self.commands[command]

    def handle_input(self, command, data, user):
        log.debug('Handle Input::%s::%s', command, data)

        if command == 'searchuser':
            data = self.server.database.search_user(data[0])
            if data:
                return [True, data.user + ' => ' + str(data.last_seen)]
            return [False, 'No user found']
        elif command == 'admins':
            result = ["===STAFF LIST==="]
            access_roles = self.Host.config['ACCESS_ROLES']
            for role in access_roles:
                users = access_roles[role]
                if users:
                    result.append(" ")
                    result.append(role.upper() + "S:")
                    for user in users:
                        result.append("-> " + user)
            return [True, result]
