import os
import sys
import csv
import statsapi
import requests
import time
from datetime import date
from datetime import timedelta


def main():
    dataDir = os.path.join(os.getcwd(), 'Data')
    if not os.path.exists(dataDir):
        os.mkdir(dataDir)


    dataCollectionRunTimeStart = time.time()
    dayDelta = timedelta(days=1)
    # day = date.today()
    day = date(year=2019, month=8, day=10)
    numDays = 2
    for _ in range (numDays):
        print(f"Generating game logs for {day}")
        dayTimeStart = time.time()
        games = statsapi.schedule(date=day)
        dayStandingsFormat = day.__format__("%m/%d/%Y")
        numGames = len(games)

        if numGames != 0:
            gameCount = 1
            for game in games:
                gameTimeStart = time.time()
                print(f"Starting game {gameCount}/{numGames}")
                gameID = game['game_id']
                awayId = game['away_id']
                homeId = game['home_id']
                awayScore = game['away_score']
                homeScore = game['home_score']
                awayName = game['away_name']
                homeName = game['home_name']

                dataLogName = "{}_{}_{}_{}_{}.csv".format(homeScore, awayScore, homeName, awayName, day)

                with open(os.path.join(dataDir, dataLogName), "w+", newline='') as file:
                    dataWriter = csv.writer(file, delimiter=' ')
                    records = getWinLossRecords(homeId, awayId, dayStandingsFormat)
                    dataWriter.writerow(records)
                    boxscore = statsapi.boxscore_data(gamePk=gameID)
                    homePlayers, awayPlayers = getLineupIds(boxscore)
                    teams = [matchLineupWithPositions(homePlayers, 'home', boxscore), matchLineupWithPositions(awayPlayers, 'away', boxscore)]
                    useDH = len(teams[0]) == 10

                    for team in teams:
                        for playerID, position in team.items():
                            playerData = statsapi.player_stat_data(personId=playerID, type='career')
                            if position == 'P' and useDH:
                                pitchingStats = getPitcherData(playerData)
                                continue
                            elif position == 'P' and not useDH:
                                generalStats = getPositionPlayerData(playerData, position)
                                pitchingStats = getPitcherData(playerData)
                            elif position == 'DH':
                                generalStats = getBattingData(playerData)
                            else:
                                generalStats = getPositionPlayerData(playerData, position)
                            dataWriter.writerow(generalStats)
                        dataWriter.writerow(pitchingStats)
                print(f"Completed game in {time.time() - gameTimeStart:.3f} sec. Completed {gameCount}/{numGames} games")
                gameCount += 1
        print(f"Completed {numGames} games for {day} in {time.time() - dayTimeStart:.3f} sec")
        day -= dayDelta
    print(f"Completed data collection in {time.time() - dataCollectionRunTimeStart:.3f} sec")


def getWinLossRecords(homeID, awayID, dayFormatted):
    homeW = None
    homeL = None
    foundHome = False
    awayW = None
    awayL = None
    foundAway = False
    standings = statsapi.standings_data(include_wildcard=False, date=dayFormatted)
    for division, values in standings.items():
        if not foundHome or not foundAway:
            for team in values['teams']:
                if team['team_id'] == homeID:
                    homeW = team['w']
                    homeL = team['l']
                    foundHome = True
                    continue
                if team['team_id'] == awayID:
                    awayW = team['w']
                    awayL = team['l']
                    foundAway = True
                    continue
                if foundHome and foundAway:
                    break
        else:
            break
    return [homeW, homeL, awayW, awayL]


def getLineupIds(boxscore):
    homeTeamBox = boxscore['home']
    awayTeamBox = boxscore['away']
    homePlayers = homeTeamBox['battingOrder']
    homePlayers.append(homeTeamBox['pitchers'][0])
    awayPlayers = awayTeamBox['battingOrder']
    awayPlayers.append(awayTeamBox['pitchers'][0])
    return homePlayers, awayPlayers


def matchLineupWithPositions(players, teamType, boxscore):
    team = {}
    for player in players:
        id = 'ID' + str(player)
        try:
            position = boxscore[teamType]['players'][id]['position']['abbreviation']
        except KeyError:
            team = {}
            break
        if player not in team and not (position == 'PH' or (position == 'P' and player != players[-1])):
            team[player] = position
    return team


def getPositionPlayerData(playerData, position):
    generalStats = []
    hittingData = []
    fieldingData = []
    try:
        for statType in playerData['stats']:
            if statType['group'] == 'hitting':
                for _, statValue in statType['stats'].items():
                    hittingData.append(str(statValue))
            elif statType['group'] == 'fielding':
                if statType['stats']['position']['abbreviation'] == position:
                    for statName, statValue in statType['stats'].items():
                        if statName == 'position':
                            continue
                        else:
                            fieldingData.append(str(statValue))
    except KeyError:
        pass
    except TypeError:
        pass
    if hittingData and fieldingData:
        for stat in hittingData:
            generalStats.append(stat)
        for stat in fieldingData:
            generalStats.append(stat)
    elif hittingData and not fieldingData:
        for stat in hittingData:
            generalStats.append(stat)
        for num in range(10):
            generalStats.append('0')
    return generalStats


def getBattingData(playerData):
    return getData(playerData, 'hitting')


def getPitcherData(playerData):
    return getData(playerData, 'pitching')


def getData(playerData, type):
    data = []
    try:
        for statType in playerData['stats']:
            if statType['group'] == type:
                for _, statValue in statType['stats'].items():
                    data.append(str(statValue))
                if len(data) > 0:
                    break
    except KeyError:
        data = []
    except TypeError:
        data = []
    return data


if __name__ == '__main__':
    main()