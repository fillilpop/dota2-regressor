import pandas as pd

data_exp = pd.read_csv("radiant_exp_adv.csv")
data_gold = pd.read_csv("radiant_gold_adv.csv")
data_fights = pd.read_csv("teamfights.csv")
data_draft = pd.read_csv('draft_timings.csv')
data_main = pd.read_csv('main_metadata.csv')
data_obj = pd.read_csv('objectives.csv')
data_main = data_main[['match_id','radiant_win']]
draft = data_draft[data_draft['pick'] == True].copy()

def assign_team(x):
    return 'radiant' if x < 50 else 'dire'

draft['team'] = draft['active_team'].map({2: 'radiant', 3: 'dire'})

draft['pick_index'] = draft.groupby(['match_id', 'team'])['order'].rank(method='first').astype(int) - 1

radiant_picks = draft[draft['team'] == 'radiant'].pivot(
    index='match_id',
    columns='pick_index',
    values='hero_id'
).add_prefix('r_hero_').drop(columns=["r_hero_5", "r_hero_6", "r_hero_7"])

dire_picks = draft[draft['team'] == 'dire'].pivot(
    index='match_id',
    columns='pick_index',
    values='hero_id'
).add_prefix('d_hero_').drop(columns=["d_hero_5", "d_hero_6", "d_hero_7"])


gold = data_gold[data_gold['minute'].isin([5, 10, 15])].copy()
wide_gold = gold.pivot(
    index='match_id',
    columns='minute',
    values=['gold']
)

# убираем многоуровневые названия колонок (делаем плоские)
wide_gold.columns = [f"{prefix}_t{minute}" for prefix, minute in wide_gold.columns]


exp = data_exp[data_gold['minute'].isin([5, 10, 15])].copy()
wide_exp = exp.pivot(
    index='match_id',
    columns='minute',
    values=['exp']
)

# убираем многоуровневые названия колонок (делаем плоские)
wide_exp.columns = [f"{prefix}_t{minute}" for prefix, minute in wide_exp.columns]

obj = data_obj[data_obj['time'] < 900].copy()
obj.rename(columns={'player_slot':'action_team'}, inplace=True)
obj["action_team"] = obj['action_team'].apply(assign_team)
fb = obj[obj['type'] == 'CHAT_MESSAGE_FIRSTBLOOD'].groupby('match_id')['time'].min().reset_index()
fb.rename(columns={'time': 'fb_time'}, inplace=True)
fb_team = obj[obj['type'] == 'CHAT_MESSAGE_FIRSTBLOOD'].sort_values('time').drop_duplicates('match_id', keep='first')[['match_id', 'action_team']]
fb_team.rename(columns={'action_team': 'fb_team'}, inplace=True)

fb_merged = fb.merge(fb_team, on='match_id', how='left')


towers = obj[obj['type'] == 'building_kill'].groupby(['match_id', 'action_team']).size().unstack(fill_value=0).reset_index()
towers.rename(columns={'radiant': 'towers_radiant_t15', 'dire': 'towers_dire_t15'}, inplace=True)

roshan = obj[obj['type'] == 'CHAT_MESSAGE_ROSHAN_KILL'][['match_id']].drop_duplicates()
roshan['roshan_by_15'] = 1

# Собираем всё вместе
features = fb_merged.merge(towers, on='match_id', how='left')
features = features.merge(roshan, on='match_id', how='left').fillna(0)

# Приводим типы
features['roshan_by_15'] = features['roshan_by_15'].astype(int)
features['towers_radiant_t15'] = features['towers_radiant_t15'].astype(int)
features['towers_dire_t15'] = features['towers_dire_t15'].astype(int)

data_all = data_main.merge(features, on='match_id', how='left').merge(wide_gold, on='match_id', how='left')
data_all = data_all.merge(wide_exp, on='match_id', how='left')
data_all = data_all.merge(radiant_picks, on='match_id', how='left').merge(dire_picks, on='match_id', how='left')
data_all.to_csv('dota_features', index=False)