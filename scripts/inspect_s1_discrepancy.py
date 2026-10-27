import json

for mid in [6, 26, 28, 39, 45, 46]:
    with open(f"Data/Data/Match_Data/{mid}.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    print(f"\n--- Match {mid} JSON ---")
    print("Result in JSON:", data['match_detail'].get('result'))
    teams = data['teams'].get('team', [])
    for t in teams:
        print(f"  Team {t.get('name')}: score={t.get('score')}, pts_total={t.get('points', {}).get('total')}")
