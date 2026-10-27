import json

with open("Data/Data/Match_Data/1.json", "r") as f:
    j = json.load(f)

for t in j['teams']['team']:
    print("Team in JSON:", t['name'], "id:", t['id'], "score:", t['score'])
    print("  stats tackles:", t.get('stats', {}).get('tackles'))
    print("  stats points tackle_points:", t.get('stats', {}).get('points', {}).get('tackle_points'))
    print("  points tackle_points:", t.get('points', {}).get('tackle_points'))
