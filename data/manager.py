import json
from functools import cached_property


class DataManager:
    def __init__(self, bot=None):
        with open("data/pokemon.json") as f:
            self.og_data = json.load(f)
        self.bot = bot

    def image(self, species_id, shiny=False):
        if self.bot:
            return f"{self.bot.config.image_server_url}/pokemon/{'shiny/' if shiny else ''}{species_id}.png"
        return self.data[species_id]["normal" if not shiny else "shiny"]


    @cached_property
    def data(self):
        mapping = {}
        for id, poke in self.og_data.items():
            mapping[int(id)] = poke
        return mapping

    @cached_property
    def legendary(self):
        return {
            species_id: poke
            for species_id, poke in self.data.items()
            if poke.get("rarity") == "legendary"
        }

    @cached_property
    def mythical(self):
        return {
            species_id: poke
            for species_id, poke in self.data.items()
            if poke.get("rarity") == "mythical"
        }

    @cached_property
    def ultra_beast(self):
        return {
            species_id: poke
            for species_id, poke in self.data.items()
            if poke.get("rarity") == "ultra_beast"
        }

    @cached_property
    def name_to_species(self):
        mapping = {}
        for id, poke in self.data.items():
            mapping[poke["name"]] = poke
            if jp := poke.get("japanese"):
                mapping[jp.lower()] = poke
            if kana := poke.get("kana"):
                mapping[kana] = poke
        return mapping

    def get_species_by_name(self, name):
        return self.name_to_species.get(name)

    def get_species_by_id(self, id):
        return self.data.get(id)
