import logging

from spa.utils import *

log = logging.getLogger(__name__)


class VotingCmds(object):
    def __init__(self, host_cmds, server, host):
        self.server = server
        log.info('VotingCmds Init')
        self.host = host
        self.host_cmds = host_cmds
        self.commands = {
            # 0 = Field
            # 1 = Return to where (Source, PM, Battle)
            # 2 = Usage example
            # 3 = Usage desc
            # 4 = Category (if available)
            # 5 = Extended help (if available)
            'vote': [['V', 'O*'], 'Source', '!vote', 'Starts a vote', 'Voting'],
            'endvote': [[], 'Source', '!endvote', 'Ends voting', 'Voting'],
        }
        self.votes = {}
        self.vote_command = None
        self.vote_time_start = 0
        self.vote_config = {
            'TimeLimit': 60,
            'SuccessCriteria': [  # Expired, Min % Yes, Max % No
                [0, 51, 49],
                [1, 40, 10],
                [1, 30, 0]
            ]
        }
        for command in self.commands:
            self.host_cmds.commands[command] = self.commands[command]

    def handle_input(self, command, data, user, source):
        log.debug('Handle Input::%s::%s', command, data)

        if command == 'vote':
            voted = 0
            if len(data) == 1 and data[0] == '1' or data[0] == 'y' or data[0] == 'yes':
                if self.vote_command:
                    voted = True
                    self.votes[user] = True
                    self.check_result()
                else:
                    return [False, 'Nothing to vote on']
            elif len(data) == 1 and data[0] == '0' or data[0] == 'n' or data[0] == 'no':
                if self.vote_command:
                    voted = True
                    self.votes[user] = False
                    self.check_result()
                else:
                    return [False, 'Nothing to vote on']
            elif self.vote_command:
                return [False, 'Vote already in progress']
            elif data[0] in self.host_cmds.commands:
                if len(data) == 1:
                    data.append('')
                Input = parse_input(data[1], self.host_cmds.commands[data[0]][0])
                if Input[0]:
                    if data[1]:
                        Cmd = data[0] + ' ' + data[1]
                    else:
                        Cmd = data[0]
                    if self.init_vote(data[0], Input[1], source, user):
                        return [True, 'Vote started for "' + Cmd + '"']
                    else:
                        return [False, 'Can\'t start a vote for "' + Cmd + '"']
                else:
                    return [True, 'Vote command not correct']
            else:
                return [False, 'Command not found']
            if voted:
                return [True, 'Voted (' + str(data[0]) + ')']

            return [True, 'Vote started']
        elif command == 'endvote':
            self.reset_votes()
            return [True, 'Vote aborted']

    def reset_votes(self):
        self.votes = {}
        self.vote_command = None
        self.vote_time_start = 0

    def init_vote(self, command, data, source, user):
        self.vote_command = [command, data, source, user]
        self.vote_time_start = time.time()
        if len(self.list_valid_voters()) < 1:
            self.reset_votes()
            return False
        return True

    def check_result(self, expired=False):
        votes_yes = 0
        votes_no = 0
        voters = self.list_valid_voters()
        votes = len(voters)
        for User in list(voters.keys()):
            if User in self.votes:
                if self.votes[User]:
                    votes_yes += 1
                else:
                    votes_no += 1
        votes_yes_rate = votes_yes / votes * 100
        votes_no_rate = votes_no / votes * 100
        log.debug("Vote result %s", self.votes)
        log.debug("%s votes YES - %s%%", votes_yes_rate)
        log.debug("%s votes NO - %s%%", votes_no_rate)
        success = False
        completed = False
        for SuccessCriteria in self.vote_config['SuccessCriteria']:
            if (expired or not SuccessCriteria[0]) and SuccessCriteria[1] <= votes_yes_rate and SuccessCriteria[2] > votes_no_rate:
                success = True
                completed = True
                break
            elif (expired or not SuccessCriteria[0]) and SuccessCriteria[1] > votes_yes_rate and SuccessCriteria[2] <= votes_no_rate:
                completed = True
                break
        log.debug("Vote completed %s", completed)
        log.debug("Vote success %s", success)
        if success:
            log.debug("Executing command %s", self.vote_command)
            command_result = self.host.HostCmds.handle_input(
                self.vote_command[2], self.vote_command[0], self.vote_command[1], self.vote_command[3])
            log.debug("Command result %s" % command_result)
        if completed:
            self.reset_votes()

    def list_valid_voters(self):
        result = {}
        for user in list(self.host.Lobby.battle_users.keys()):
            if not user == self.host.Lobby.user and self.host.user_access(self.vote_command[0], user, True):
                result[user] = 1
        return result
