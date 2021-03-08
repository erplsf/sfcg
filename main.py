from steam.client import SteamClient
from steam.webapi import WebAPI
from bs4 import BeautifulSoup
from functools import reduce
from itertools import chain
import questionary
import os.path
from tomlkit import dumps,loads
from tabulate import tabulate
from copy import deepcopy
import itertools

def fetch_owned_games(api, steamid):
    return api.IPlayerService.GetOwnedGames(steamid=steamid, include_appinfo=True, include_played_free_games=True, appids_filter=[], include_free_sub=True)['response']

def fetch_web_api_key(client):
    session = client.get_web_session()
    r = session.get('https://steamcommunity.com/dev/apikey')
    bs = BeautifulSoup(r.content, 'html.parser')
    key = bs.find(id='bodyContents_ex').p.text.split()[-1]
    return key

def friendify(client):
    return {'name': client.user.name, 'steam_id': client.user.steam_id.as_64}

def fetch_friends(client):
    return map(lambda f: {'name': f.name, 'steam_id': f.steam_id.as_64}, client.friends)

def filter_friends(friends, names_filter):
    return filter(lambda f: True if f['name'] in names_filter else False, friends)

def fetch_users_libraries(api, users):
    return map(lambda f: f | fetch_owned_games(api, f['steam_id']), users)

def find_common_games(users):
    return reduce(lambda f1, f2: f1 & f2, map(lambda f: set(map(lambda g: g['appid'], f['games'])), users))

def questionize_friends(friends_names, preselected_names):
    return map(lambda f: questionary.Choice(title=f['name'], checked=f['name'] in preselected_names), friends_names)

def cache_file_present():
    if os.path.isfile('.cache.toml'):
        return True
    else:
        return False

def merge_to_cache(dct):
    if os.path.isfile('.cache.toml'):
        d = loads(open('.cache.toml').read())
        d = d | dct
        d = dumps(d)
        open('.cache.toml', 'w').write(d)
    else:
        d = dumps(dct)
        open('.cache.toml', 'w').write(d)

def load_from_cache(key):
    if os.path.isfile('.cache.toml'):
        d = loads(open('.cache.toml').read())
        v = d.get(key)
        if v is None:
            return ''
        else:
            return v
    else:
        return ''

def tabulize(users):
    dct = {}
    for user in users:
        for game in user['games']:
            dct[game['name']] = [] if dct.get(game['name']) is None else dct.get(game['name'])
            time_played = round(game['playtime_forever'] / 60, 2)
            dct[game['name']].append(time_played)
    dct = list(map(list, dct.items()))
    dct = map(lambda d: [d[0], *d[-1]], dct) # Ugly expansion
    return dct

def filter_games(users, games_ids):
    def filter_games_for_user(user):
        u = user.copy()
        g = filter(lambda g: g['appid'] in games_ids, u['games'])        
        u['games'] = g
        return u
        
    return map(filter_games_for_user, users)

def filter_zero_games(tabulized_games):
    return filter(lambda r: sum(r[1:]) > 0, tabulized_games)

if __name__ == "__main__":
    save = questionary.confirm(default=True, message="Save your input to a cache file?").ask()
    pre_username = load_from_cache('username')
    pre_password = load_from_cache('password')
    pre_selected_friends = load_from_cache('selected_friends')
    username = questionary.text(default=pre_username, message="Your Steam username?").ask()
    password = questionary.password(default=pre_password, message="Your Steam password?").ask()
    if save:
        merge_to_cache({'username': username, 'password': password})
    cl = SteamClient()
    cl.set_credential_location('.')
    cl.cli_login(username=username, password=password)
    api = WebAPI(key=fetch_web_api_key(cl))
    friends = list(fetch_friends(cl)) # we need to listify it, to be able to use it twice. TODO: Investigate how to clone generator/iterator?

    loop = True
    
    while loop:
        pre_selected_friends = load_from_cache('selected_friends')
        qfriends = list(questionize_friends(deepcopy(friends), pre_selected_friends))
        selected_friends = questionary.checkbox('Select friends to compare',
                                                choices=qfriends).ask()
        
        if save:
            merge_to_cache({'selected_friends': selected_friends})

        filtered_friends = list(filter_friends(friends, selected_friends))
        users = list(chain([friendify(cl)], filtered_friends))
        users_with_games = list(fetch_users_libraries(api, users))
        common_games = list(find_common_games(users_with_games))
        filtered_users_with_games = list(filter_games(users_with_games, common_games))
        columns = ['Game name']
        for u in filtered_users_with_games:
            columns.append(u['name'])
        tabulized_games = tabulize(filtered_users_with_games)
        # TODO: filter/ask for zero-time-games
        if questionary.confirm(default=True, message="Filter out games that every player has zero hours in").ask():
            tabulized_games = filter_zero_games(tabulized_games)
        sort_function = questionary.select("What function to use for sorting?",
                                           choices=['Averaged-player time', 'Owner played time']).ask()
        if sort_function == 'Owner played time':
            tabulized_games = sorted(tabulized_games, key=lambda r: r[1], reverse=True)
        elif sort_function == 'Averaged-player time':
            tabulized_games = sorted(tabulized_games, key=lambda r: sum(r[1:])/len(r[1:]), reverse=True)
        print(tabulate(tabulized_games, headers=columns))

        loop = questionary.confirm(default=True, message="Do you want to do a filter/query again?").ask()

# General flow/ TODO:
# DONE: 0. Get user's web api token
# DONE: 1. Login to steam client (to get user's friends - haven't found any other way atm)
# DONE: 2. Ask user to select a few friends (use questionary from pypy)
# DONE: 3. Loop over friends and set-intersect games libraries
# DONE: 4. Present them to the user with
# 5. ???
# 6. PROFIT!
