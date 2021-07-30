import toml
from typing import List, NamedTuple

with open("config.toml") as f:
    config = toml.load(f)

class Config(NamedTuple):
    token: int
    prefix: int
    db_string: str
    extensions: List[str]
    
extensions = [f"cogs.{extension}" for extension in config["bot"]["extensions"]]
extensions.extend(config["bot"]["extra"])
config = Config(config["bot"]["token"], config["bot"]["prefix"], config["database"]["string"], extensions)
