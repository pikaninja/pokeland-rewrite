
CREATE TABLE users(
    --general
    id BIGINT PRIMARY KEY,
    started TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    disabled BOOL DEFAULT FALSE,
    --economy stuff
    bal BIGINT NOT NULL, 
    redeem BIGINT NOT NULL,
    --xp stuff
    xp_share BIGINT ,
    xp_boost_end TIMESTAMP DEFAULT NULL,
    --voting
    last_voted TIMESTAMP DEFAULT NULL,
    total_votes INT DEFAULT 0,
    --settings
    hide_levelup BOOL DEFAULT FALSE
);
CREATE TABLE guilds(
    id BIGINT PRIMARY KEY,
    prefix TEXT DEFAULT NULL,
    compact BOOL DEFAULT NULL
);
CREATE TABLE channels(
    id BIGINT PRIMARY KEY,
    guild_id BIGINT NOT NULL,
    disabled BOOL DEFAULT FALSE
);
CREATE TABLE dex(
    user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    species_id INT NOT NULL,
    count INT NOT NULL,
    shinies INT NOT NULL
);
CREATE TABLE pokemon(
    --general stuffs
    id BIGINT GENERATED BY DEFAULT AS IDENTITY,
    user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    idx INT NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    staff BOOL DEFAULT FALSE,

    --general pokemon info
    species_id INT NOT NULL,
    level INT NOT NULL CHECK(level <= 100 AND level >= 0),
    xp INT NOT NULL,
    nature TEXT NOT NULL,
    shiny BOOL NOT NULL,
    --ivs
    hp_iv INT NOT NULL CHECK(hp_iv <= 31 AND hp_iv >= 0),
    atk_iv INT NOT NULL CHECK(atk_iv <= 31 AND atk_iv >= 0),
    def_iv INT NOT NULL CHECK(def_iv <= 31 AND def_iv >= 0),
    spatk_iv INT NOT NULL CHECK(spatk_iv <= 31 AND spatk_iv >= 0),
    spdef_iv INT NOT NULL CHECK(spdef_iv <= 31 AND spdef_iv >= 0),
    spd_iv INT NOT NULL CHECK(spd_iv <= 31 AND spd_iv >= 0),

    total_iv INT GENERATED ALWAYS AS (hp_iv+atk_iv+def_iv+spatk_iv+spdef_iv+spd_iv) STORED,
    --others
    nick TEXT DEFAULT NULL,
    moves TEXT[4] NOT NULL, 
    favorite BOOL DEFAULT FALSE,
    item TEXT DEFAULT NULL,
    
    PRIMARY KEY(user_id, idx)
);


CREATE INDEX pokemon_idx ON pokemon(idx);
