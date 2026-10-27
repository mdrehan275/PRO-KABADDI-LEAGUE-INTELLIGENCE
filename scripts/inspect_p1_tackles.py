import pandas as pd
df_p = pd.read_csv('DS_players.csv')
p1 = df_p[df_p['match_id'] == 1]
for tid, g in p1.groupby('team_id'):
    print(f"Team {tid}:")
    for idx, r in g.iterrows():
        if r['player_tackle_points_total'] > 0:
            print(f"  {r['player_name']} (role: {r['player_role']}): tackles={r['player_tackle_points_total']}")
