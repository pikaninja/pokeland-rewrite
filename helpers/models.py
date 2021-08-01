import math
from typing import List
import datetime
from dataclasses import dataclass

@dataclass
class DexEntry:
    user_id: int
    species_id: int
    count: int
    shinies: int

@dataclass
class Channel:
    id: int
    guild_id: int
    spawns_disabled: bool
    disabled: bool

@dataclass
class Guild:
    id: int
    prefix: str
    compact: bool
    redirects: List[int]


@dataclass
class User:
    # general
    id: int
    started: datetime.datetime
    disabled: bool
    order_by: str
    selected: int
    # economy
    bal: int
    redeem: int
    # xp
    xp_share: int
    xp_boost_end: int
    # votes
    last_voted: datetime.datetime
    total_votes: int
    # settings
    hide_levelup: bool


mapping = {
    "atk": "attack",
    "def": "defense",
    "spdef": "special_defense",
    "spatk": "special_attack",
    "spd": "speed",
}


class Pokemon:
    def __init__(self, record, data=None):
        self.record = dict(record)
        self.data_manager = data

    def __setattr__(self, attr, obj):
        if hasattr(self, attr):
            self.record[attr] = obj
        else:
            super().__setattr__(attr, obj)


    @property
    def id(self):
        return self.record["id"]

    @property
    def idx(self):
        return self.record["idx"]

    @property
    def species_id(self):
        return self.record["species_id"]

    @property
    def data(self):
        return self.data_manager.get_species_by_id(self.species_id)

    @property
    def name(self):
        if not self.data:
            return None

        return self.data["name"].title()

    @property
    def shiny(self):
        return self.record["shiny"]

    @property
    def nature(self):
        return self.record["nature"]

    @property
    def item(self):
        return self.record["item"]

    @property
    def level(self):
        return self.record["level"]

    @property
    def xp(self):
        return self.record["xp"]

    @property
    def iv_percent(self):
        return self.record["total_iv"] / 186

    @property
    def hp_iv(self):
        return self.record["hp_iv"]

    @property
    def atk_iv(self):
        return self.record["atk_iv"]

    @property
    def def_iv(self):
        return self.record["def_iv"]

    @property
    def spatk_iv(self):
        return self.record["spatk_iv"]

    @property
    def spdef_iv(self):
        return self.record["spdef_iv"]

    @property
    def spd_iv(self):
        return self.record["spd_iv"]

    @property
    def xp_needed(self):
        return 200 + 25 * self.level

    def stat(self, stat):
        iv = self.record[f"{stat}_iv"]
        if stat == "hp":
            return math.floor(
                (2 * self.data["hp"] + self.hp_iv) * self.level / 100 + self.level + 10
            )

        return math.floor(
            math.floor((2 * self.data[mapping[stat]] + iv) * self.level / 100 + 5)
        )
