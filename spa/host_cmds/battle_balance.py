import logging
import math
import random
from operator import itemgetter

log = logging.getLogger(__name__)


class BattleBalance(object):

    battle = {}
    battle_users = {}
    teams = []
    players = 0
    team_rank = {}
    team_players = {}
    player_list = {}
    balance = []
    data = {}

    def __init__(self, battle_cmds, host):
        self.battle_cmds = battle_cmds
        self.host = host
        self.lobby = host.Lobby

    def refresh(self):
        if self.lobby.battle_id:
            self.battle = self.lobby.battles[self.host.Lobby.battle_id]
            self.battle_users = self.lobby.battle_users
        else:
            self.battle = {}
            self.battle_users = {}
            log.warning('self.host.Lobby.battle_id doesn\'t exist')

        self.teams = self.host.battle['Teams']
        self.players = 0
        self.team_rank = {}
        self.team_players = {}
        self.player_list = {}
        self.balance = []
        self.data = {
            'TotalRank': 0,
            'OptimalTeamRank': 0,
            'OptimalTeamPlayers': 0,
        }

    def run(self):
        log.info('')
        self.refresh()

        for iTeam in range(0, self.teams):
            self.team_rank[iTeam] = 0
            self.team_players[iTeam] = 0
        for user in self.battle_users:
            if self.battle_users[user]['AI']:
                self.player_list[user] = 1
            elif 'Spectator' in self.battle_users[user] and not self.battle_users[user]['Spectator']:
                self.player_list[user] = self.lobby.users[user]['Rank']
        self.players = len(self.player_list)
        for user in self.player_list:
            self.data['TotalRank'] = self.data['TotalRank'] + self.player_list[user]
        self.data['OptimalTeamRank'] = int(math.floor(self.data['TotalRank'] / float(self.teams)))
        self.data['OptimalTeamPlayers'] = int(math.floor(self.players / float(self.teams)))

        self.balance_clans()
        self.balance_teams()
        self.balance_players()

        for balance in self.balance:
            self.battle_cmds.logic.force_team(balance[0], balance[1])

        return [True, 'Balancing...']

    def balance_clans(self):
        if not self.players / float(self.teams) > 1:
            return True
        clans = {}
        for user in self.player_list:
            for clan in user.split(']'):
                if clan[0:1] == '[':
                    if clan[1:] not in clans:
                        clans[clan[1:]] = [user]
                    else:
                        clans[clan[1:]].append(user)
        for clan in list(clans.keys()):
            if len(clans[clan]) == 1:
                del (clans[clan])
        if len(clans) == 0:
            return True

        for clan in list(clans.keys()):
            players = len(clans[clan])
            ranks = 0
            for user in clans[clan]:
                ranks += self.player_list[user]
            if players <= self.data['OptimalTeamPlayers']:
                Team = self.get_best_team(players, ranks)
                self.team_players[Team] += players
                self.team_rank[Team] += ranks
                for user in clans[clan]:
                    del (self.player_list[user])
                    self.balance.append([user, Team + 1])

    def balance_teams(self, include_empty_teams=0):
        for team in list(self.team_players.keys()):
            if (self.team_players[team] or include_empty_teams) and self.team_players[team] < self.data['OptimalTeamPlayers']:
                needed_players = self.data['OptimalTeamPlayers'] - self.team_players[team]
                needed_rank = self.data['OptimalTeamRank'] - self.team_rank[team]
                players = self.balance_get_players(needed_players, needed_rank)
                for user in players:
                    self.team_players[team] += 1
                    self.team_rank[team] += self.player_list[user]
                    self.balance.append([user, team + 1])
                    del (self.player_list[user])

    def balance_get_players(self, get_players, get_rank):
        best = get_rank
        best_users = []
        for iRand in range(0, 100):
            random.seed()
            players = list(self.player_list.keys())
            i_players = get_players
            users = []
            rank = 0
            while i_players > 0:
                user = players.pop(random.randint(0, len(players) - 1))
                i_players -= 1
                users.append(user)
                rank += self.player_list[user]
            if rank == get_rank:
                best = 0
                best_users = users[:]
                break
            elif abs(get_rank - rank) < best:
                best = abs(get_rank - rank)
                best_users = users[:]
        return best_users

    def balance_players(self):
        if len(self.player_list) == 0:
            return True
        self.balance_teams(1)

    def get_best_team(self, players, rank):
        teams = {}
        for Team in self.team_players:
            teams[Team] = 0
            """ If a bunch of players are being placed and the team being search has no players, 
                it gets a bonus value of 100k...
            """
            if not self.team_players[Team] and players > 1:
                teams[Team] += 100000

            if self.team_players[Team] + players == self.data['OptimalTeamPlayers']:
                teams[Team] += 10000
            elif self.team_players[Team] + players < self.data['OptimalTeamPlayers']:
                teams[Team] += 1000
            else:
                teams[Team] += 100

        for Team in self.team_rank:
            if self.team_rank[Team] + rank == self.data['OptimalTeamRank'] and self.team_players[Team] + players == \
                    self.data['OptimalTeamPlayers']:
                teams[Team] += 1000
            elif self.team_rank[Team] + players < self.data['OptimalTeamRank']:
                teams[Team] += 100
            else:
                teams[Team] += 10

            # Give bonus to the team with the loest rank
            teams[Team] -= self.team_rank[Team]
        return sorted(list(teams.items()), key=itemgetter(1), reverse=True)[0][0]
