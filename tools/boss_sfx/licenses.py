"""docs/licenses/sounds_bosses.md from tools/boss_sfx/used_sources.json (the CC0 files actually layered into the boss sounds)."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fetch_cc0 import SOURCES, ROOT  # noqa: E402

NAMES = {"common": "Общие (слом блока)", "cult_leader": "Глава Культа", "irina": "Ирина", "aris": "Арис", "martin": "Мартин",
         "ereb": "Эреб", "ereb_hand": "Эреб, Длань Лжи"}


def main():
    used = json.load(open(os.path.join(ROOT, "tools", "boss_sfx", "used_sources.json")))
    by_pack = {}
    for boss, files in used.items():
        for f in files:
            pack = f.split("/")[0]
            by_pack.setdefault(pack, {}).setdefault(f, set()).add(boss)
    src = {s[0]: s for s in SOURCES}
    L = ["# Звуки боссов: источники и лицензии", "",
         "Все `.ogg` в `src/main/resources/assets/pohsmp_core/sounds/boss/**` собраны скриптами `tools/boss_sfx/*.py`:",
         "синтез (numpy: шум, синусы, колокола, свёрточный ревёрб — собственная работа, без лицензионных ограничений)",
         "+ слои из записей ниже. Каждый пак проверен вручную на странице OpenGameArt 21.11.2026: в поле **License(s)** — **CC0**",
         "(CC0 1.0, https://creativecommons.org/publicdomain/zero/1.0/). Атрибуция не требуется, указываем из уважения.",
         "Ванильные звуки Minecraft и звуки Iron's Spells в наши файлы **не вшиты** (их нельзя распространять);",
         "Iron's по-прежнему звучит сам, своим кодом (Глава Культа — атаки косой, шаги, урон).", "",
         "Скачать исходники заново: `python tools/boss_sfx/fetch_cc0.py` (→ `build/boss_sfx_cc0`, в git не попадает).", "",
         "| Пак | Автор | Страница (лицензия) | Использованные файлы → боссы |", "|---|---|---|---|"]
    for pack in sorted(by_pack):
        name, url, page, author = src[pack]
        files = "<br>".join("`%s` → %s" % (f.split("/")[-1], ", ".join(NAMES.get(b, b) for b in sorted(bs)))
                            for f, bs in sorted(by_pack[pack].items()))
        L.append("| %s | %s | %s (CC0) | %s |" % (pack, author, page, files))
    L += ["", "Файл-источник: %s" % "`tools/boss_sfx/fetch_cc0.py` (URL каждого архива)."]
    out = os.path.join(ROOT, "docs", "licenses", "sounds_bosses.md")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, "w", encoding="utf-8").write("\n".join(L) + "\n")


if __name__ == "__main__":
    main()
