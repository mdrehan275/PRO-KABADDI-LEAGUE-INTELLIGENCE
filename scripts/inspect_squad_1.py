import json

with open("Data/Data/Match_Data/1.json", "r") as f:
    j = json.load(f)

for t in j['teams']['team']:
    print(f"\nSquad for {t['name']} (id {t['id']}):")
    for p in t.get('squad', []):
        t_pts = p.get('points', {}).get('tackle_points', {}).get('total', 0)
        r_pts = p.get('points', {}).get('raid_points', {}).get('total', 0)
        if t_pts > 0 or r_pts > 0:
            print(f"  {p.get('name')}: raid={r_pts}, tackle={t_pts}")
