"""Downloads the CC0 sound packs used as layers of the boss sounds into build/boss_sfx_cc0.

Every pack was checked by hand on its OpenGameArt page: License(s) = CC0 (21.11.2026). The list of the files actually used,
with authors and links: docs/licenses/sounds_bosses.md.
"""
import os, urllib.request, zipfile, io, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEST = os.path.join(ROOT, "build", "boss_sfx_cc0")
F = "https://opengameart.org/sites/default/files/"

# (local name, file url, page, author)
SOURCES = [
    ("RPGsounds_Kenney", F + "RPGsounds_Kenney.zip", "https://opengameart.org/content/50-rpg-sound-effects", "Kenney"),
    ("100-CC0-SFX_0", F + "100-CC0-SFX_0.zip", "https://opengameart.org/content/100-cc0-sfx", "rubberduck"),
    ("sfx_100_v2", F + "sfx_100_v2.zip", "https://opengameart.org/content/100-cc0-sfx-2", "rubberduck"),
    ("sfx_breaking_and_falling", F + "sfx_breaking_and_falling.zip", "https://opengameart.org/content/75-cc0-breaking-falling-hit-sfx", "rubberduck"),
    ("100-CC0-wood-metal-SFX", F + "100-CC0-wood-metal-SFX.zip", "https://opengameart.org/content/100-cc0-metal-and-wood-sfx", "rubberduck"),
    ("80-CC0-RPG-SFX_0", F + "80-CC0-RPG-SFX_0.zip", "https://opengameart.org/content/80-cc0-rpg-sfx", "rubberduck"),
    ("80-CC0-creature-SFX_0", F + "80-CC0-creature-SFX_0.zip", "https://opengameart.org/content/80-cc0-creature-sfx", "rubberduck"),
    ("25-CC0-bang-sfx", F + "25-CC0-bang-sfx.zip", "https://opengameart.org/content/25-cc0-bang-firework-sfx", "rubberduck"),
    ("water-splash-slime-sfx", F + "water-splash-slime-sfx.zip", "https://opengameart.org/content/40-cc0-water-splash-slime-sfx", "rubberduck"),
    ("sword_-_starninjas_1", F + "sword_-_starninjas_1.zip", "https://opengameart.org/content/20-sword-sound-effects-attacks-and-clashes", "StarNinjas"),
    ("sword_clash_-_starninjas_0", F + "sword_clash_-_starninjas_0.zip", "https://opengameart.org/content/20-sword-sound-effects-attacks-and-clashes", "StarNinjas"),
    ("swishes", F + "swishes.zip", "https://opengameart.org/content/swishes-sound-pack", "artisticdude"),
    ("footsteps", F + "footsteps.zip", "https://opengameart.org/content/footsteps-leather-cloth-armor", "HaelDB (CC0 option of OGA-BY 3.0 / CC0)"),
    ("winch", F + "winch.zip", "https://opengameart.org/content/chain-winch-sounds", "bart"),
    ("melee_sounds", F + "melee%20sounds.zip", "https://opengameart.org/content/3-melee-sounds", "remaxim (orig. qubodup)"),
    ("metal_steps.ogg", F + "metal_steps.ogg", "https://opengameart.org/content/metal-footsteps-on-concrete", "Thimras"),
    ("Trot.ogg", F + "Trot.ogg", "https://opengameart.org/content/horse-trotting", "EZduzziteh"),
    ("horde_war_drums_by_william_hector.wav", F + "horde_war_drums_by_william_hector.wav", "https://opengameart.org/content/horde-war-drums-loop", "William Hector"),
    ("theircoming.ogg", F + "theircoming.ogg", "https://opengameart.org/content/their-coming-generic-horn-sound", "StumpyStrust"),
    ("theircoming3.ogg", F + "theircoming3.ogg", "https://opengameart.org/content/their-coming-generic-horn-sound", "StumpyStrust"),
    ("forger.ogg", F + "forger.ogg", "https://opengameart.org/content/hammer-on-anvil", "themightyglider"),
    ("blacksmithhammer.wav", F + "blacksmithhammer.wav", "https://opengameart.org/content/blacksmiths-hammer", "VishwaJai"),
    ("flame.ogg", F + "flame.ogg", "https://opengameart.org/content/catching-fire", "themightyglider"),
    ("whoosh2_0.wav", F + "whoosh2_0.wav", "https://opengameart.org/content/air-whoosh", "pyranostudios"),
    ("dungeon_ambient_1.ogg", F + "dungeon_ambient_1.ogg", "https://opengameart.org/content/loopable-dungeon-ambience", "JaggedStone"),
]


def main():
    os.makedirs(DEST, exist_ok=True)
    for name, url, page, author in SOURCES:
        target = os.path.join(DEST, name)
        if os.path.exists(target):
            continue
        print("fetch", url, file=sys.stderr)
        data = urllib.request.urlopen(url).read()
        if url.endswith(".zip"):
            zipfile.ZipFile(io.BytesIO(data)).extractall(target)
        else:
            open(target, "wb").write(data)


if __name__ == "__main__":
    main()
