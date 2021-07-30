import csv
import json


def isnumber(v):
    try:
        int(v)
    except ValueError:
        return False
    return True


with open("pokemon.csv") as f:
    reader = csv.DictReader(f)
    datacsv = list(
        {k: int(v) if isnumber(v) else v for k, v in row.items() if v != ""}
        for row in reader
    )

with open("data/pokemon.json") as f:
    data = json.load(f)


for key, value in enumerate(datacsv):
    if str(key + 1) in data:
        if value.get("legendary"):
            data[str(key + 1)]["rarity"] = "legendary"
        if value.get("mythical"):
            data[str(key + 1)]["rarity"] = "mythical"
        if value.get("ultra_beast"):
            data[str(key + 1)]["rarity"] = "ultra_beast"
with open("data/pokemon.json", "w") as f:
    json.dump(data, f, indent=4)
