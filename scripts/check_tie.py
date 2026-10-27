import pandas as pd

df_m = pd.read_csv('DS_match.csv')
df_t = pd.read_csv('DS_team.csv')
m_winners = []
for mid, g in df_t.groupby('match_id'):
    s0, s1 = g.iloc[0]['score'], g.iloc[1]['score']
    t0, t1 = g.iloc[0]['name'], g.iloc[1]['name']
    w = t0 if s0 > s1 else (t1 if s1 > s0 else 'Tied')
    m_winners.append({'match_id': mid, 'calc_winner': w, 's0': s0, 's1': s1, 't0': t0, 't1': t1})
df_win = pd.DataFrame(m_winners)
m_merged = pd.merge(df_m, df_win, on='match_id')
text_tie = m_merged['result'].str.contains('Tie|Draw', case=False, na=False)
calc_tie = (m_merged['calc_winner'] == 'Tied')
diff = m_merged[text_tie != calc_tie]
for idx, r in diff.iterrows():
    print(f"Match {r['match_id']}: status={r['status']}, result='{r['result']}', {r['t0']}({r['s0']}) vs {r['t1']}({r['s1']}), series={r['series_name']}")
