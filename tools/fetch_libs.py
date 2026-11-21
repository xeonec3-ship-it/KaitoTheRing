"""Downloads the compile-time jars listed in libs/README.md from Modrinth into libs/ (run from the repository root)."""
import io, json, os, urllib.request, zipfile

LIBS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "libs")
# (Modrinth project, version number, file name)
JARS = [
    ("irons-spells-n-spellbooks", "1.20.1-3.16.1", "irons_spellbooks-1.20.1-3.16.1.jar"),
    ("geckolib", "4.8.4", "geckolib-forge-1.20.1-4.8.4.jar"),
    ("jade", "11.13.3+forge", "Jade-1.20.1-Forge-11.13.3.jar"),
    ("wthit", "forge-8.21.2", "wthit-1.20.1-forge-8.21.2.jar"),
    ("the-one-probe", "1.20.1-10.0.5", "theoneprobe-1.20.1-10.0.5.jar"),
    ("journeymap", "1.20.1-6.0.7+forge", "journeymap-forge-1.20.1-6.0.7.jar"),
    ("playeranimator", "1.0.2-rc1+1.20-forge", "player-animation-lib-forge-1.0.2-rc1+1.20.jar"),
    ("epic-fight", "20.14.17-mc1.20.1-forge", "epic-fight-20.14.17-mc1.20.1-forge.jar"),
    ("simple-voice-chat", "forge-1.20.1-2.6.20", "voicechat-forge-1.20.1-2.6.20.jar"),   # T22, build.gradle compileOnly
]
# saved under another name: build.gradle reads libs/ as a flat repository, "blank:<name>:<version>" -> <name>-<version>.jar
SAVE_AS = {"epic-fight-20.14.17-mc1.20.1-forge.jar": "epicfight-1.20.1-20.14.17.jar"}


def url_of(project, version, name):
    q = "https://api.modrinth.com/v2/project/%s/version?loaders=%%5B%%22forge%%22%%5D&game_versions=%%5B%%221.20.1%%22%%5D" % project
    for v in json.load(urllib.request.urlopen(q)):
        if v["version_number"] == version:
            for f in v["files"]:
                if f["filename"] == name:
                    return f["url"]
    raise SystemExit("not found on Modrinth: %s %s" % (project, version))


for project, version, name in JARS:
    data = urllib.request.urlopen(url_of(project, version, name)).read()
    if project == "journeymap":   # only its API jar is needed
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            inner = "META-INF/jarjar/journeymap-api-forge-1.20.1-2.0.0.jar"
            open(os.path.join(LIBS, os.path.basename(inner)), "wb").write(z.read(inner))
            print("ok", os.path.basename(inner))
        continue
    out = SAVE_AS.get(name, name)
    open(os.path.join(LIBS, out), "wb").write(data)
    print("ok", out)
