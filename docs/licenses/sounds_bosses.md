# Звуки боссов: источники и лицензии

Все `.ogg` в `src/main/resources/assets/pohsmp_core/sounds/boss/**` собраны скриптами `tools/boss_sfx/*.py`:
синтез (numpy: шум, синусы, колокола, свёрточный ревёрб — собственная работа, без лицензионных ограничений)
+ слои из записей ниже. Каждый пак проверен вручную на странице OpenGameArt 21.11.2026: в поле **License(s)** — **CC0**
(CC0 1.0, https://creativecommons.org/publicdomain/zero/1.0/). Атрибуция не требуется, указываем из уважения.
Ванильные звуки Minecraft и звуки Iron's Spells в наши файлы **не вшиты** (их нельзя распространять);
Iron's по-прежнему звучит сам, своим кодом (Глава Культа — атаки косой, шаги, урон).

Скачать исходники заново: `python tools/boss_sfx/fetch_cc0.py` (→ `build/boss_sfx_cc0`, в git не попадает).

| Пак | Автор | Страница (лицензия) | Использованные файлы → боссы |
|---|---|---|---|
| 100-CC0-SFX_0 | rubberduck | https://opengameart.org/content/100-cc0-sfx (CC0) | `bell_02.ogg` → Глава Культа<br>`gong_01.ogg` → Глава Культа<br>`gong_02.ogg` → Глава Культа |
| 100-CC0-wood-metal-SFX | rubberduck | https://opengameart.org/content/100-cc0-metal-and-wood-sfx (CC0) | `metal_hit_01.ogg` → Глава Культа<br>`metal_hit_02.ogg` → Глава Культа<br>`metal_hit_03.ogg` → Общие (слом блока), Глава Культа<br>`metal_hit_04.ogg` → Общие (слом блока)<br>`metal_hit_05.ogg` → Общие (слом блока)<br>`wood_hit_02.ogg` → Ирина<br>`wood_hit_04.ogg` → Ирина<br>`wood_hit_06.ogg` → Ирина |
| 25-CC0-bang-sfx | rubberduck | https://opengameart.org/content/25-cc0-bang-firework-sfx (CC0) | `bang_03.ogg` → Глава Культа<br>`bang_05.ogg` → Глава Культа<br>`cannon_02.ogg` → Глава Культа<br>`cannon_03.ogg` → Глава Культа |
| 80-CC0-RPG-SFX_0 | rubberduck | https://opengameart.org/content/80-cc0-rpg-sfx (CC0) | `blade_01.ogg` → Глава Культа<br>`blade_02.ogg` → Глава Культа<br>`blade_03.ogg` → Глава Культа<br>`chain_01.ogg` → Глава Культа<br>`chain_02.ogg` → Глава Культа<br>`creature_roar_01.ogg` → Глава Культа<br>`creature_roar_02.ogg` → Глава Культа<br>`lock_02.ogg` → Глава Культа<br>`spell_fire_01.ogg` → Глава Культа<br>`spell_fire_02.ogg` → Глава Культа<br>`spell_fire_03.ogg` → Глава Культа<br>`spell_fire_04.ogg` → Глава Культа<br>`spell_fire_05.ogg` → Глава Культа<br>`spell_fire_06.ogg` → Глава Культа<br>`spell_fire_07.ogg` → Глава Культа |
| RPGsounds_Kenney | Kenney | https://opengameart.org/content/50-rpg-sound-effects (CC0) | `cloth1.ogg` → Ирина<br>`cloth2.ogg` → Ирина<br>`cloth3.ogg` → Ирина<br>`cloth4.ogg` → Ирина<br>`clothBelt.ogg` → Ирина<br>`clothBelt2.ogg` → Ирина<br>`creak1.ogg` → Ирина<br>`creak2.ogg` → Ирина<br>`creak3.ogg` → Ирина<br>`drawKnife1.ogg` → Ирина<br>`drawKnife2.ogg` → Ирина<br>`drawKnife3.ogg` → Ирина<br>`dropLeather.ogg` → Ирина<br>`footstep00.ogg` → Ирина<br>`footstep02.ogg` → Ирина<br>`footstep04.ogg` → Ирина<br>`footstep06.ogg` → Ирина<br>`handleSmallLeather.ogg` → Глава Культа<br>`knifeSlice.ogg` → Ирина<br>`knifeSlice2.ogg` → Ирина |
| flame.ogg | themightyglider | https://opengameart.org/content/catching-fire (CC0) | `flame.ogg` → Глава Культа |
| footsteps | HaelDB (CC0 option of OGA-BY 3.0 / CC0) | https://opengameart.org/content/footsteps-leather-cloth-armor (CC0) | `step_lth1.ogg` → Ирина<br>`step_lth2.ogg` → Ирина<br>`step_lth33.ogg` → Ирина<br>`step_lth4.ogg` → Ирина |
| sfx_breaking_and_falling | rubberduck | https://opengameart.org/content/75-cc0-breaking-falling-hit-sfx (CC0) | `bfh1_breaking_01.ogg` → Общие (слом блока)<br>`bfh1_breaking_02.ogg` → Общие (слом блока)<br>`bfh1_breaking_03.ogg` → Общие (слом блока)<br>`bfh1_falling_02.ogg` → Глава Культа<br>`bfh1_glass_breaking_02.ogg` → Ирина<br>`bfh1_glass_breaking_03.ogg` → Глава Культа<br>`bfh1_rock_breaking_02.ogg` → Глава Культа<br>`bfh1_rock_falling_03.ogg` → Глава Культа<br>`bfh1_rock_falling_04.ogg` → Глава Культа<br>`bfh1_rock_hit_01.ogg` → Глава Культа |
| swishes | artisticdude | https://opengameart.org/content/swishes-sound-pack (CC0) | `swish-10.wav` → Ирина<br>`swish-11.wav` → Ирина<br>`swish-12.wav` → Ирина<br>`swish-2.wav` → Ирина<br>`swish-3.wav` → Глава Культа<br>`swish-5.wav` → Глава Культа, Ирина<br>`swish-7.wav` → Глава Культа<br>`swish-8.wav` → Глава Культа, Ирина<br>`swish-9.wav` → Глава Культа |
| sword_-_starninjas_1 | StarNinjas | https://opengameart.org/content/20-sword-sound-effects-attacks-and-clashes (CC0) | `sword.3.ogg` → Глава Культа<br>`sword.4.ogg` → Глава Культа |
| water-splash-slime-sfx | rubberduck | https://opengameart.org/content/40-cc0-water-splash-slime-sfx (CC0) | `slime_03.ogg` → Ирина<br>`slime_04.ogg` → Глава Культа, Ирина<br>`slime_05.ogg` → Глава Культа, Ирина |

Файл-источник: `tools/boss_sfx/fetch_cc0.py` (URL каждого архива).
