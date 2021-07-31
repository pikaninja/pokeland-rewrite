import json
with open("data/pokemon.json") as f:
    data = json.load(f)

for index, poke in data.items():
    if evo := poke.get('evolution'):
        poke["evolution"] = int(evo) 

with open("data/pokemon.json", "w") as f:
    json.dump(data, f, indent=4)

