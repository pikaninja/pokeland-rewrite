import toml
import glob
from typing import List, NamedTuple

with open("config.toml") as f:
    config = toml.load(f)


class Config(NamedTuple):
    token: int
    prefix: int
    db_string: str
    extensions: List[str]
    error_log_channel_id: int
    image_server_url: str
    debug: bool


if config["bot"]["extensions"] == "all":
    extensions = [f"cogs.{extension[5:-3]}" for extension in list(glob.glob("cogs/*.py"))]
else:
    extensions = [f"cogs.{extension}" for extension in config["bot"]["extensions"]]
extensions.extend(config["bot"]["extra"])
config = Config(
    config["bot"]["token"],
    config["bot"]["prefix"],
    config["database"]["string"],
    extensions,
    config["bot"]["error_log_channel_id"],
    config["bot"]["image_server_url"],
    config["bot"]["debug"]
)
