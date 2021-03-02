from steam.client import SteamClient
from steam.webapi import WebAPI
from bs4 import BeautifulSoup
from functools import reduce
from itertools import chain

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

if __name__ == "__main__":
    cl = SteamClient()
    cl.cli_login()
    api = WebAPI(key=fetch_web_api_key(cl))
    friends = fetch_friends(cl)
    friends = filter_friends(friends, []) # TODO: actually ask here, for local dev I use static  ist
    users = chain(friends, [friendify(cl)])
    users = fetch_users_libraries(api, users)
    game_ids_set = find_common_games(users)
    print(game_ids_set)

# General flow/ TODO:
# DONE: 0. Get user's web api token
# DONE: 1. Login to steam client (to get user's friends - haven't found any other way atm)
# 2. Ask user to select a few friends (use questionary from pypy)
# DONE: 3. Loop over friends and set-intersect games libraries
# 4. Present them to the user
# 5. ???
# 6. PROFIT!
