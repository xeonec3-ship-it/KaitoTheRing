# Каталог звуков магии (по коду, 19.11.2026)

Все места, где заклинания играют ванильные `SoundEvents.*`: заклинание → школа/ступень → место (файл:строка, метод) → роль → текущий ванильный звук → наше событие. Собирается `tools/gen_spell_sounds.py --docs-only`.

Мест: **348**, заклинаний: **77**, наших событий: **293**. Пропущено (уже свои / не магия): 25.

Роли: `cast` — начало каста; `charge` — нарастание во время каста; `release` — выпуск заклинания; `open` — раскрытие (печать, купол, разрыв); `loop` — пока действует (тики); `hit` — удар / взрыв / попадание; `end` — конец / снятие / смерть; `fail` — отказ / ошибка.

## Огонь (`fire`) — треск и рёв пламени, жар

### Раскалённые угли (клинок/плеть) (`ember_blade`) — ступень: —

| место | метод | роль | ванильный звук | наше событие |
|---|---|---|---|---|
| `client/EmberWhipClient.java:278` | `crack` | удар / взрыв / попадание | `FIREWORK_ROCKET_BLAST` | `pohsmp_core:spell.ember_blade.hit_boom` |
| `client/EmberWhipClient.java:279` | `crack` | удар / взрыв / попадание | `LAVA_POP` | `pohsmp_core:spell.ember_blade.hit_fire` |
| `ember/EmberBlade.java:183` | `inventoryTick` | пока действует (тики) | `FIRE_EXTINGUISH` | `pohsmp_core:spell.ember_blade.loop` |
| `ember/EmberBlade.java:252` | `onHit` | удар / взрыв / попадание | `FIRECHARGE_USE` | `pohsmp_core:spell.ember_blade.hit_fire` |
| `ember/EmberBlade.java:261` | `onHit` | удар / взрыв / попадание | `BLAZE_AMBIENT` | `pohsmp_core:spell.ember_blade.hit_fire` |
| `ember/EmberBlade.java:333` | `lash` | удар / взрыв / попадание | `BLAZE_SHOOT` | `pohsmp_core:spell.ember_blade.hit_fire` |
| `ember/EmberBlade.java:386` | `later` | удар / взрыв / попадание | `FIRECHARGE_USE` | `pohsmp_core:spell.ember_blade.hit_fire` |
| `ember/EmberBlade.java:426` | `lastEmber` | удар / взрыв / попадание | `ANVIL_LAND` | `pohsmp_core:spell.ember_blade.hit_slam` |
| `ember/EmberBlade.java:440` | `lastEmber` | удар / взрыв / попадание | `BLAZE_SHOOT` | `pohsmp_core:spell.ember_blade.hit_fire` |
| `ember/EmberBlade.java:443` | `lastEmber` | удар / взрыв / попадание | `FIRE_EXTINGUISH` | `pohsmp_core:spell.ember_blade.hit_hiss` |
| `ember/EmberBlade.java:472` | `fireVortex` | удар / взрыв / попадание | `FIRECHARGE_USE` | `pohsmp_core:spell.ember_blade.hit_fire` |
| `ember/EmberBlade.java:484` | `fireVortex` | удар / взрыв / попадание | `BLAZE_SHOOT` | `pohsmp_core:spell.ember_blade.hit_fire` |

### Взрыв! (`explosion`) — ступень: LEGENDARY

| место | метод | роль | ванильный звук | наше событие |
|---|---|---|---|---|
| `spell/ExplosionSpell.java:68` | `getCastStartSound` | начало каста | `BLAZE_AMBIENT` | `pohsmp_core:spell.explosion.cast` |
| `spell/ExplosionSpell.java:103` | `onServerCastTick` | нарастание во время каста | `BEACON_POWER_SELECT` | `pohsmp_core:spell.explosion.charge_powerup` |
| `spell/ExplosionSpell.java:104` | `onServerCastTick` | нарастание во время каста | `FIRECHARGE_USE` | `pohsmp_core:spell.explosion.charge_fire` |
| `spell/ExplosionSpell.java:115` | `onServerCastTick` | нарастание во время каста | `FIRE_AMBIENT` | `pohsmp_core:spell.explosion.charge_fire` |
| `spell/ExplosionSpell.java:155` | `boom` | удар / взрыв / попадание | `GENERIC_EXPLODE` | `pohsmp_core:spell.explosion.hit_boom` |
| `spell/ExplosionSpell.java:156` | `boom` | удар / взрыв / попадание | `DRAGON_FIREBALL_EXPLODE` | `pohsmp_core:spell.explosion.hit_boom` |
| `spell/ExplosionSpell.java:157` | `boom` | удар / взрыв / попадание | `LIGHTNING_BOLT_THUNDER` | `pohsmp_core:spell.explosion.hit_thunder` |

### Падающее солнце (`falling_sun`) — ступень: COMMON

| место | метод | роль | ванильный звук | наше событие |
|---|---|---|---|---|
| `spell/FallingSunSpell.java:55` | `fall` | выпуск заклинания | `BLAZE_SHOOT` | `pohsmp_core:spell.falling_sun.release` |
| `spell/FallingSunSpell.java:82` | `tick` | удар / взрыв / попадание | `GENERIC_EXPLODE` | `pohsmp_core:spell.falling_sun.hit` |

### Огненная плеть (`fire_whip`) — ступень: COMMON

| место | метод | роль | ванильный звук | наше событие |
|---|---|---|---|---|
| `spell/FireWhipSpell.java:50` | `onCast` | начало каста | `BLAZE_SHOOT` | `pohsmp_core:spell.fire_whip.cast` |
| `spell/FireWhipSpell.java:51` | `onCast` | начало каста | `FIRECHARGE_USE` | `pohsmp_core:spell.fire_whip.cast` |
| `spell/FireWhipSpell.java:87` | `tick` | пока действует (тики) | `FISHING_BOBBER_RETRIEVE` | `pohsmp_core:spell.fire_whip.loop` |

### Падение небес (`heaven_fall`) — ступень: LEGENDARY

| место | метод | роль | ванильный звук | наше событие |
|---|---|---|---|---|
| `spell/HeavenFallSpell.java:59` | `getCastStartSound` | начало каста | `WITHER_AMBIENT` | `pohsmp_core:spell.heaven_fall.cast` |
| `spell/HeavenFallSpell.java:91` | `onServerCastTick` | нарастание во время каста | `AMBIENT_CAVE` | `pohsmp_core:spell.heaven_fall.charge_hum` |
| `spell/HeavenFallSpell.java:98` | `onServerCastTick` | нарастание во время каста | `LIGHTNING_BOLT_THUNDER` | `pohsmp_core:spell.heaven_fall.charge_thunder` |
| `spell/HeavenFallSpell.java:119` | `rain` | удар / взрыв / попадание | `WITHER_SPAWN` | `pohsmp_core:spell.heaven_fall.hit_roar` |
| `spell/HeavenFallSpell.java:172` | `tick` | пока действует (тики) | `BLAZE_SHOOT` | `pohsmp_core:spell.heaven_fall.loop` |
| `spell/HeavenFallSpell.java:187` | `tick` | удар / взрыв / попадание | `GENERIC_EXPLODE` | `pohsmp_core:spell.heaven_fall.hit_boom` |

## Лёд (`ice`) — хрусталь, треск и звон льда, холодный ветер

### Стена ледяных шипов (`frost_spike_wall`) — ступень: COMMON

| место | метод | роль | ванильный звук | наше событие |
|---|---|---|---|---|
| `spell/FrostSpikeWallSpell.java:102` | `build` | начало каста | `GLASS_PLACE` | `pohsmp_core:spell.frost_spike_wall.cast_form` |
| `spell/FrostSpikeWallSpell.java:103` | `build` | начало каста | `AMETHYST_BLOCK_BREAK` | `pohsmp_core:spell.frost_spike_wall.cast_shatter` |
| `spell/FrostSpikeWallSpell.java:123` | `tick` | удар / взрыв / попадание | `GLASS_BREAK` | `pohsmp_core:spell.frost_spike_wall.hit` |

### Ледяные гробницы (`glacial_tombs`) — ступень: UNCOMMON

| место | метод | роль | ванильный звук | наше событие |
|---|---|---|---|---|
| `spell/GlacialTombsSpell.java:58` | `onCast` | начало каста | `GLASS_BREAK` | `pohsmp_core:spell.glacial_tombs.cast_shatter` |
| `spell/GlacialTombsSpell.java:59` | `onCast` | начало каста | `POWDER_SNOW_PLACE` | `pohsmp_core:spell.glacial_tombs.cast_snow` |

## Молния (`lightning`) — разряд, треск электричества, гул и раскат грома

### Ударная волна (`ground_shock`) — ступень: COMMON

| место | метод | роль | ванильный звук | наше событие |
|---|---|---|---|---|
| `spell/GroundShockSpell.java:51` | `onCast` | начало каста | `LIGHTNING_BOLT_IMPACT` | `pohsmp_core:spell.ground_shock.cast` |
| `spell/GroundShockSpell.java:64` | `tick` | пока действует (тики) | `BEEHIVE_WORK` | `pohsmp_core:spell.ground_shock.loop` |

### Громоотвод (`lightning_rod`) — ступень: COMMON

| место | метод | роль | ванильный звук | наше событие |
|---|---|---|---|---|
| `spell/LightningRodSpell.java:47` | `onCast` | начало каста | `TRIDENT_THUNDER` | `pohsmp_core:spell.lightning_rod.cast` |
| `spell/LightningRodSpell.java:62` | `tick` | удар / взрыв / попадание | `LIGHTNING_BOLT_IMPACT` | `pohsmp_core:spell.lightning_rod.hit` |

### Перегрузка (`overload`) — ступень: —

| место | метод | роль | ванильный звук | наше событие |
|---|---|---|---|---|
| `spell/Marks.java:183` | `tickOverload` | удар / взрыв / попадание | `LIGHTNING_BOLT_IMPACT` | `pohsmp_core:spell.overload.hit` |
| `spell/OverloadSpell.java:52` | `onCast` | начало каста | `BEACON_POWER_SELECT` | `pohsmp_core:spell.overload.cast` |

## Святая (`holy`) — колокольчики и светлый хор

### Приговор (`judgement`) — ступень: COMMON

| место | метод | роль | ванильный звук | наше событие |
|---|---|---|---|---|
| `spell/JudgementSpell.java:54` | `onCast` | начало каста | `BELL_RESONATE` | `pohsmp_core:spell.judgement.cast` |
| `spell/JudgementSpell.java:76` | `tick` | удар / взрыв / попадание | `TRIDENT_THUNDER` | `pohsmp_core:spell.judgement.hit` |
| `spell/JudgementSpell.java:77` | `tick` | пока действует (тики) | `BEACON_POWER_SELECT` | `pohsmp_core:spell.judgement.loop` |

### Последний рассвет (`last_dawn`) — ступень: MYTHIC

| место | метод | роль | ванильный звук | наше событие |
|---|---|---|---|---|
| `mythic/LastDawnSpell.java:47` | `getCastStartSound` | начало каста | `BEACON_POWER_SELECT` | `pohsmp_core:spell.last_dawn.cast` |
| `mythic/LastDawnSpell.java:73` | `castTick` | нарастание во время каста | `BEACON_ACTIVATE` | `pohsmp_core:spell.last_dawn.charge_powerup` |
| `mythic/LastDawnSpell.java:74` | `castTick` | нарастание во время каста | `AMETHYST_BLOCK_RESONATE` | `pohsmp_core:spell.last_dawn.charge_resonate` |
| `mythic/LastDawnSpell.java:75` | `castTick` | нарастание во время каста | `BELL_RESONATE` | `pohsmp_core:spell.last_dawn.charge_resonate` |
| `mythic/LastDawnSpell.java:82` | `release` | конец / снятие / смерть | `BELL_BLOCK` | `pohsmp_core:spell.last_dawn.end_bell` |
| `mythic/LastDawnSpell.java:151` | `end` | конец / снятие / смерть | `PLAYER_LEVELUP` | `pohsmp_core:spell.last_dawn.end_fanfare` |
| `mythic/LastDawnSpell.java:171` | `guard` | конец / снятие / смерть | `TOTEM_USE` | `pohsmp_core:spell.last_dawn.end_fanfare` |

### Живой щит (`living_shield`) — ступень: UNCOMMON

| место | метод | роль | ванильный звук | наше событие |
|---|---|---|---|---|
| `spell/LivingShieldSpell.java:48` | `onCast` | начало каста | `BEACON_POWER_SELECT` | `pohsmp_core:spell.living_shield.cast` |

### Святилище (`sanctuary`) — ступень: UNCOMMON

| место | метод | роль | ванильный звук | наше событие |
|---|---|---|---|---|
| `spell/SanctuarySpell.java:48` | `onCast` | начало каста | `BEACON_ACTIVATE` | `pohsmp_core:spell.sanctuary.cast` |
| `spell/SanctuarySpell.java:77` | `tick` | конец / снятие / смерть | `BEACON_DEACTIVATE` | `pohsmp_core:spell.sanctuary.end` |

## Кровь (`blood`) — влажный пульс, сердцебиение, глухо

### Кровный дар (`blood_gift`) — ступень: COMMON

| место | метод | роль | ванильный звук | наше событие |
|---|---|---|---|---|
| `spell/BloodGiftSpell.java:57` | `onCast` | начало каста | `HONEY_DRINK` | `pohsmp_core:spell.blood_gift.cast` |
| `spell/BloodGiftSpell.java:58` | `onCast` | начало каста | `PLAYER_HURT_SWEET_BERRY_BUSH` | `pohsmp_core:spell.blood_gift.cast` |

### Кровавая метка (`blood_mark`) — ступень: UNCOMMON

| место | метод | роль | ванильный звук | наше событие |
|---|---|---|---|---|
| `spell/BloodMarkSpell.java:51` | `onCast` | начало каста | `WARDEN_HEARTBEAT` | `pohsmp_core:spell.blood_mark.cast` |

### Кровотечение (`hemorrhage`) — ступень: COMMON

| место | метод | роль | ванильный звук | наше событие |
|---|---|---|---|---|
| `spell/HemorrhageSpell.java:51` | `onCast` | начало каста | `PLAYER_HURT_SWEET_BERRY_BUSH` | `pohsmp_core:spell.hemorrhage.cast` |

### Магическое безумие (`magic_madness`) — ступень: LEGENDARY

| место | метод | роль | ванильный звук | наше событие |
|---|---|---|---|---|
| `client/PohHud.java:32` | `onClientTick` | пока действует (тики) | `WARDEN_HEARTBEAT` | `pohsmp_core:spell.magic_madness.loop` |
| `spell/MadnessSpell.java:68` | `onCast` | начало каста | `WARDEN_ROAR` | `pohsmp_core:spell.magic_madness.cast` |
| `spell/MadnessSpell.java:91` | `madTick` | пока действует (тики) | `WARDEN_HEARTBEAT` | `pohsmp_core:spell.magic_madness.loop` |

## Эндер (`ender`) — искажённый гул, пространство «плывёт», портал

### Изгнание (`banishment`) — ступень: UNCOMMON

| место | метод | роль | ванильный звук | наше событие |
|---|---|---|---|---|
| `spell/BanishmentSpell.java:57` | `onCast` | начало каста | `ENDERMAN_TELEPORT` | `pohsmp_core:spell.banishment.cast` |
| `spell/BanishmentSpell.java:59` | `onCast` | начало каста | `END_PORTAL_SPAWN` | `pohsmp_core:spell.banishment.cast` |

### Появление Ковена (`coven_arrival`) — ступень: LEGENDARY

| место | метод | роль | ванильный звук | наше событие |
|---|---|---|---|---|
| `spell/CovenArrivalSpell.java:128` | `getCastStartSound` | начало каста | `BEACON_ACTIVATE` | `pohsmp_core:spell.coven_arrival.cast_powerup` |
| `spell/CovenArrivalSpell.java:129` | `getCastFinishSound` | выпуск заклинания | `END_PORTAL_SPAWN` | `pohsmp_core:spell.coven_arrival.release` |
| `spell/CovenArrivalSpell.java:207` | `checkPreCastConditions` | отказ / ошибка | `AMETHYST_BLOCK_RESONATE` | `pohsmp_core:spell.coven_arrival.fail_resonate` |
| `spell/CovenArrivalSpell.java:251` | `toggle` | начало каста | `AMETHYST_BLOCK_CHIME` | `pohsmp_core:spell.coven_arrival.cast_chime` |
| `spell/CovenArrivalSpell.java:375` | `begin` | начало каста | `BEACON_AMBIENT` | `pohsmp_core:spell.coven_arrival.cast_hum` |
| `spell/CovenArrivalSpell.java:400` | `step` | нарастание во время каста | `BEACON_AMBIENT` | `pohsmp_core:spell.coven_arrival.charge_hum` |
| `spell/CovenArrivalSpell.java:401` | `step` | нарастание во время каста | `AMETHYST_BLOCK_RESONATE` | `pohsmp_core:spell.coven_arrival.charge_resonate` |
| `spell/CovenArrivalSpell.java:427` | `step` | нарастание во время каста | `ENDER_EYE_DEATH` | `pohsmp_core:spell.coven_arrival.charge_portal` |
| `spell/CovenArrivalSpell.java:489` | `openCasterPortal` | раскрытие (печать, купол, разрыв) | `END_PORTAL_SPAWN` | `pohsmp_core:spell.coven_arrival.open` |
| `spell/CovenArrivalSpell.java:498` | `openPortal` | раскрытие (печать, купол, разрыв) | `END_PORTAL_SPAWN` | `pohsmp_core:spell.coven_arrival.open` |
| `spell/CovenArrivalSpell.java:505` | `openPortal` | раскрытие (печать, купол, разрыв) | `ENDERMAN_TELEPORT` | `pohsmp_core:spell.coven_arrival.open` |
| `spell/CovenArrivalSpell.java:599` | `exit` | конец / снятие / смерть | `ENDERMAN_TELEPORT` | `pohsmp_core:spell.coven_arrival.end_portal` |
| `spell/CovenArrivalSpell.java:600` | `exit` | конец / снятие / смерть | `AMETHYST_BLOCK_CHIME` | `pohsmp_core:spell.coven_arrival.end_chime` |
| `spell/CovenArrivalSpell.java:622` | `ritual` | нарастание во время каста | `BEACON_POWER_SELECT` | `pohsmp_core:spell.coven_arrival.charge_powerup` |
| `spell/CovenArrivalSpell.java:729` | `onUseItem` | отказ / ошибка | `UI_BUTTON_CLICK` | `pohsmp_core:spell.coven_arrival.fail_click` |

### Застывший час (`frozen_hour`) — ступень: LEGENDARY

| место | метод | роль | ванильный звук | наше событие |
|---|---|---|---|---|
| `spell/FrozenHourSpell.java:77` | `getCastStartSound` | начало каста | `BELL_RESONATE` | `pohsmp_core:spell.frozen_hour.cast` |
| `spell/FrozenHourSpell.java:128` | `stop` | конец / снятие / смерть | `BELL_BLOCK` | `pohsmp_core:spell.frozen_hour.end_bell` |
| `spell/FrozenHourSpell.java:129` | `stop` | конец / снятие / смерть | `BEACON_DEACTIVATE` | `pohsmp_core:spell.frozen_hour.end_powerdown` |
| `spell/FrozenHourSpell.java:200` | `free` | удар / взрыв / попадание | `PLAYER_ATTACK_CRIT` | `pohsmp_core:spell.frozen_hour.hit` |
| `spell/FrozenHourSpell.java:224` | `onServerTick` | пока действует (тики) | `BELL_RESONATE` | `pohsmp_core:spell.frozen_hour.loop` |

### Закрытие Пространства (`space_closure`) — ступень: LEGENDARY

| место | метод | роль | ванильный звук | наше событие |
|---|---|---|---|---|
| `spell/SpaceClosureSpell.java:98` | `getCastStartSound` | начало каста | `END_PORTAL_FRAME_FILL` | `pohsmp_core:spell.space_closure.cast` |
| `spell/SpaceClosureSpell.java:99` | `getCastFinishSound` | выпуск заклинания | `END_PORTAL_SPAWN` | `pohsmp_core:spell.space_closure.release` |
| `spell/SpaceClosureSpell.java:143` | `onServerCastTick` | нарастание во время каста | `RESPAWN_ANCHOR_CHARGE` | `pohsmp_core:spell.space_closure.charge_powerup` |
| `spell/SpaceClosureSpell.java:144` | `onServerCastTick` | нарастание во время каста | `BEACON_AMBIENT` | `pohsmp_core:spell.space_closure.charge_hum` |
| `spell/SpaceClosureSpell.java:197` | `open` | раскрытие (печать, купол, разрыв) | `END_PORTAL_SPAWN` | `pohsmp_core:spell.space_closure.open_portal` |
| `spell/SpaceClosureSpell.java:198` | `open` | раскрытие (печать, купол, разрыв) | `BEACON_POWER_SELECT` | `pohsmp_core:spell.space_closure.open_powerup` |
| `spell/SpaceClosureSpell.java:199` | `open` | раскрытие (печать, купол, разрыв) | `WITHER_SPAWN` | `pohsmp_core:spell.space_closure.open_roar` |
| `spell/SpaceClosureSpell.java:230` | `close` | конец / снятие / смерть | `BEACON_DEACTIVATE` | `pohsmp_core:spell.space_closure.end_powerdown` |
| `spell/SpaceClosureSpell.java:231` | `close` | конец / снятие / смерть | `GLASS_BREAK` | `pohsmp_core:spell.space_closure.end_shatter` |
| `spell/SpaceClosureSpell.java:312` | `hit` | удар / взрыв / попадание | `AMETHYST_BLOCK_RESONATE` | `pohsmp_core:spell.space_closure.hit_resonate` |
| `spell/SpaceClosureSpell.java:313` | `hit` | удар / взрыв / попадание | `RESPAWN_ANCHOR_SET_SPAWN` | `pohsmp_core:spell.space_closure.hit_powerup` |

### Подмена (`swap`) — ступень: COMMON

| место | метод | роль | ванильный звук | наше событие |
|---|---|---|---|---|
| `spell/SwapSpell.java:66` | `onCast` | начало каста | `ENDERMAN_TELEPORT` | `pohsmp_core:spell.swap.cast` |
| `spell/SwapSpell.java:67` | `onCast` | начало каста | `ENDERMAN_TELEPORT` | `pohsmp_core:spell.swap.cast` |

## Природа (`nature`) — дерево, корни, листва

### Хваткий сад (`grasping_garden`) — ступень: UNCOMMON

| место | метод | роль | ванильный звук | наше событие |
|---|---|---|---|---|
| `spell/GraspingGardenSpell.java:74` | `onCast` | начало каста | `ROOTED_DIRT_BREAK` | `pohsmp_core:spell.grasping_garden.cast` |
| `spell/GraspingGardenSpell.java:138` | `tick` | удар / взрыв / попадание | `GENERIC_EXPLODE` | `pohsmp_core:spell.grasping_garden.hit` |

### Облако спор (`spore_cloud`) — ступень: COMMON

| место | метод | роль | ванильный звук | наше событие |
|---|---|---|---|---|
| `spell/SporeCloudSpell.java:47` | `onCast` | начало каста | `AZALEA_LEAVES_BREAK` | `pohsmp_core:spell.spore_cloud.cast` |
| `spell/SporeCloudSpell.java:48` | `onCast` | начало каста | `PUFFER_FISH_BLOW_OUT` | `pohsmp_core:spell.spore_cloud.cast` |
| `spell/SporeCloudSpell.java:69` | `tick` | пока действует (тики) | `MOSS_STEP` | `pohsmp_core:spell.spore_cloud.loop` |

### Древо мира (`world_tree`) — ступень: MYTHIC

| место | метод | роль | ванильный звук | наше событие |
|---|---|---|---|---|
| `mythic/WorldTreeSpell.java:45` | `getCastStartSound` | начало каста | `ROOTED_DIRT_PLACE` | `pohsmp_core:spell.world_tree.cast` |
| `mythic/WorldTreeSpell.java:76` | `castTick` | нарастание во время каста | `ROOTED_DIRT_BREAK` | `pohsmp_core:spell.world_tree.charge_earth` |
| `mythic/WorldTreeSpell.java:77` | `castTick` | нарастание во время каста | `AZALEA_PLACE` | `pohsmp_core:spell.world_tree.charge_leaves` |
| `mythic/WorldTreeSpell.java:79` | `castTick` | нарастание во время каста | `AZALEA_LEAVES_PLACE` | `pohsmp_core:spell.world_tree.charge_leaves` |
| `mythic/WorldTreeSpell.java:82` | `castTick` | нарастание во время каста | `BEACON_ACTIVATE` | `pohsmp_core:spell.world_tree.charge_powerup` |
| `mythic/WorldTreeSpell.java:87` | `castTick` | нарастание во время каста | `WOOD_PLACE` | `pohsmp_core:spell.world_tree.charge_wood` |
| `mythic/WorldTreeSpell.java:146` | `tick` | удар / взрыв / попадание | `ROOTED_DIRT_BREAK` | `pohsmp_core:spell.world_tree.hit_earth` |
| `mythic/WorldTreeSpell.java:164` | `tick` | пока действует (тики) | `AZALEA_LEAVES_BREAK` | `pohsmp_core:spell.world_tree.loop` |
| `mythic/WorldTreeSpell.java:192` | `hit` | удар / взрыв / попадание | `WOOD_HIT` | `pohsmp_core:spell.world_tree.hit_wood` |
| `mythic/WorldTreeSpell.java:196` | `hit` | удар / взрыв / попадание | `WOOD_BREAK` | `pohsmp_core:spell.world_tree.hit_wood` |
| `mythic/WorldTreeSpell.java:211` | `bloom` | удар / взрыв / попадание | `SPORE_BLOSSOM_BREAK` | `pohsmp_core:spell.world_tree.hit_leaves` |
| `mythic/WorldTreeSpell.java:212` | `bloom` | удар / взрыв / попадание | `CHERRY_LEAVES_BREAK` | `pohsmp_core:spell.world_tree.hit_leaves` |

## Мистическая (`eldritch`) — шёпот и низкий гул

### Око бездны (`abyss_eye`) — ступень: MYTHIC

| место | метод | роль | ванильный звук | наше событие |
|---|---|---|---|---|
| `mythic/AbyssEyeSpell.java:43` | `getCastStartSound` | начало каста | `AMBIENT_CAVE` | `pohsmp_core:spell.abyss_eye.cast` |
| `mythic/AbyssEyeSpell.java:70` | `castTick` | нарастание во время каста | `AMBIENT_SOUL_SAND_VALLEY_MOOD` | `pohsmp_core:spell.abyss_eye.charge_hum` |
| `mythic/AbyssEyeSpell.java:71` | `castTick` | нарастание во время каста | `LIGHTNING_BOLT_THUNDER` | `pohsmp_core:spell.abyss_eye.charge_thunder` |
| `mythic/AbyssEyeSpell.java:72` | `castTick` | нарастание во время каста | `WARDEN_HEARTBEAT` | `pohsmp_core:spell.abyss_eye.charge_heart` |
| `mythic/AbyssEyeSpell.java:76` | `castTick` | нарастание во время каста | `WARDEN_SONIC_BOOM` | `pohsmp_core:spell.abyss_eye.charge_boom` |
| `mythic/AbyssEyeSpell.java:81` | `castTick` | нарастание во время каста | `LIGHTNING_BOLT_THUNDER` | `pohsmp_core:spell.abyss_eye.charge_thunder` |
| `mythic/AbyssEyeSpell.java:145` | `tick` | пока действует (тики) | `AMBIENT_CAVE` | `pohsmp_core:spell.abyss_eye.loop_hum` |
| `mythic/AbyssEyeSpell.java:153` | `tick` | пока действует (тики) | `WARDEN_ROAR` | `pohsmp_core:spell.abyss_eye.loop_roar` |
| `mythic/AbyssEyeSpell.java:168` | `tick` | пока действует (тики) | `WARDEN_HEARTBEAT` | `pohsmp_core:spell.abyss_eye.loop_heart` |

## Вызывание (`evocation`) — магический металл: гонг, щиты, вспышка заклятия

### Восемь щитов (`eight_shields`) — ступень: COMMON

| место | метод | роль | ванильный звук | наше событие |
|---|---|---|---|---|
| `spell/EightShieldsSpell.java:91` | `onCast` | начало каста | `ARMOR_EQUIP_NETHERITE` | `pohsmp_core:spell.eight_shields.cast_slam` |
| `spell/EightShieldsSpell.java:92` | `onCast` | начало каста | `BEACON_ACTIVATE` | `pohsmp_core:spell.eight_shields.cast_powerup` |
| `spell/EightShieldsSpell.java:110` | `tick` | удар / взрыв / попадание | `GLASS_BREAK` | `pohsmp_core:spell.eight_shields.hit_shatter` |
| `spell/EightShieldsSpell.java:148` | `block` | удар / взрыв / попадание | `AMETHYST_BLOCK_HIT` | `pohsmp_core:spell.eight_shields.hit_chime` |

### Иллюзия (`illusion`) — ступень: UNCOMMON

| место | метод | роль | ванильный звук | наше событие |
|---|---|---|---|---|
| `spell/IllusionSpell.java:86` | `onCast` | начало каста | `ILLUSIONER_MIRROR_MOVE` | `pohsmp_core:spell.illusion.cast` |

### Иллюзия: приманка (`illusion_decoy`) — ступень: —

| место | метод | роль | ванильный звук | наше событие |
|---|---|---|---|---|
| `spell/Marks.java:91` | `boom` | удар / взрыв / попадание | `ILLUSIONER_MIRROR_MOVE` | `pohsmp_core:spell.illusion_decoy.hit_magic` |
| `spell/Marks.java:92` | `boom` | удар / взрыв / попадание | `GENERIC_EXPLODE` | `pohsmp_core:spell.illusion_decoy.hit_boom` |

### Призрачный капкан (`phantom_trap`) — ступень: COMMON

| место | метод | роль | ванильный звук | наше событие |
|---|---|---|---|---|
| `spell/PhantomTrapSpell.java:57` | `onCast` | начало каста | `ILLUSIONER_PREPARE_MIRROR` | `pohsmp_core:spell.phantom_trap.cast` |
| `spell/PhantomTrapSpell.java:81` | `tick` | пока действует (тики) | `CHAIN_PLACE` | `pohsmp_core:spell.phantom_trap.loop` |
| `spell/PhantomTrapSpell.java:82` | `tick` | удар / взрыв / попадание | `EVOKER_FANGS_ATTACK` | `pohsmp_core:spell.phantom_trap.hit` |

## Ветер (`wind`) — порывы и свист воздуха

### Вихревой заслон (`gale_ward`) — ступень: COMMON

| место | метод | роль | ванильный звук | наше событие |
|---|---|---|---|---|
| `spell/GaleWardSpell.java:45` | `onCast` | начало каста | `ELYTRA_FLYING` | `pohsmp_core:spell.gale_ward.cast` |
| `spell/GaleWardSpell.java:59` | `tick` | пока действует (тики) | `PHANTOM_FLAP` | `pohsmp_core:spell.gale_ward.loop` |

### Метка ветра (`wind_mark`) — ступень: COMMON

| место | метод | роль | ванильный звук | наше событие |
|---|---|---|---|---|
| `spell/WindMarkSpell.java:49` | `onCast` | начало каста | `ENDER_DRAGON_FLAP` | `pohsmp_core:spell.wind_mark.cast` |
| `spell/WindMarkSpell.java:74` | `tick` | пока действует (тики) | `PHANTOM_FLAP` | `pohsmp_core:spell.wind_mark.loop` |

## Высшая (`higher`) — алый звон: металлический гонг с обратным наплывом, кольцевое «дрожание»

### Без пепла (`ashless_flame`) — ступень: HIGHER

| место | метод | роль | ванильный звук | наше событие |
|---|---|---|---|---|
| `spell/AshlessSpell.java:46` | `getCastStartSound` | начало каста | `FIRECHARGE_USE` | `pohsmp_core:spell.ashless_flame.cast` |
| `spell/AshlessSpell.java:97` | `erupt` | выпуск заклинания | `BLAZE_SHOOT` | `pohsmp_core:spell.ashless_flame.release_fire` |
| `spell/AshlessSpell.java:98` | `erupt` | выпуск заклинания | `SOUL_ESCAPE` | `pohsmp_core:spell.ashless_flame.release_soul` |
| `spell/AshlessSpell.java:99` | `erupt` | выпуск заклинания | `GENERIC_EXPLODE` | `pohsmp_core:spell.ashless_flame.release_boom` |
| `spell/AshlessSpell.java:119` | `tick` | пока действует (тики) | `FIRECHARGE_USE` | `pohsmp_core:spell.ashless_flame.loop` |

### Кровавая луна (`blood_moon`) — ступень: HIGHER

| место | метод | роль | ванильный звук | наше событие |
|---|---|---|---|---|
| `spell/BloodMoonSpell.java:35` | `getCastFinishSound` | выпуск заклинания | `WITHER_SPAWN` | `pohsmp_core:spell.blood_moon.release` |
| `spell/BloodMoonSpell.java:74` | `tick` | пока действует (тики) | `WARDEN_HEARTBEAT` | `pohsmp_core:spell.blood_moon.loop` |

### Обратный отсчёт (`countdown`) — ступень: HIGHER

| место | метод | роль | ванильный звук | наше событие |
|---|---|---|---|---|
| `spell/CountdownSpell.java:67` | `getCastStartSound` | начало каста | `ENCHANTMENT_TABLE_USE` | `pohsmp_core:spell.countdown.cast_magic` |
| `spell/CountdownSpell.java:102` | `start` | начало каста | `BEACON_ACTIVATE` | `pohsmp_core:spell.countdown.cast_powerup` |
| `spell/CountdownSpell.java:103` | `start` | начало каста | `NOTE_BLOCK_CHIME` | `pohsmp_core:spell.countdown.cast_chime` |
| `spell/CountdownSpell.java:119` | `tick` | пока действует (тики) | `NOTE_BLOCK_HAT` | `pohsmp_core:spell.countdown.loop` |
| `spell/CountdownSpell.java:152` | `repeat` | удар / взрыв / попадание | `BELL_BLOCK` | `pohsmp_core:spell.countdown.hit_bell` |
| `spell/CountdownSpell.java:153` | `repeat` | удар / взрыв / попадание | `GLASS_BREAK` | `pohsmp_core:spell.countdown.hit_shatter` |
| `spell/CountdownSpell.java:187` | `onDamage` | удар / взрыв / попадание | `NOTE_BLOCK_HAT` | `pohsmp_core:spell.countdown.hit_click` |
| `spell/CountdownSpell.java:188` | `onDamage` | удар / взрыв / попадание | `AMETHYST_BLOCK_HIT` | `pohsmp_core:spell.countdown.hit_chime` |

### Вечная метель (`eternal_blizzard`) — ступень: HIGHER

| место | метод | роль | ванильный звук | наше событие |
|---|---|---|---|---|
| `spell/EternalBlizzardSpell.java:47` | `getCastFinishSound` | выпуск заклинания | `POWDER_SNOW_PLACE` | `pohsmp_core:spell.eternal_blizzard.release` |
| `spell/EternalBlizzardSpell.java:68` | `open` | раскрытие (печать, купол, разрыв) | `POWDER_SNOW_BREAK` | `pohsmp_core:spell.eternal_blizzard.open_snow` |
| `spell/EternalBlizzardSpell.java:69` | `open` | раскрытие (печать, купол, разрыв) | `GLASS_BREAK` | `pohsmp_core:spell.eternal_blizzard.open_shatter` |
| `spell/EternalBlizzardSpell.java:70` | `open` | раскрытие (печать, купол, разрыв) | `ELYTRA_FLYING` | `pohsmp_core:spell.eternal_blizzard.open_whoosh` |
| `spell/EternalBlizzardSpell.java:94` | `tick` | пока действует (тики) | `POWDER_SNOW_STEP` | `pohsmp_core:spell.eternal_blizzard.loop_snow` |
| `spell/EternalBlizzardSpell.java:95` | `tick` | пока действует (тики) | `ELYTRA_FLYING` | `pohsmp_core:spell.eternal_blizzard.loop_whoosh` |
| `spell/EternalBlizzardSpell.java:98` | `tick` | пока действует (тики) | `POWDER_SNOW_BREAK` | `pohsmp_core:spell.eternal_blizzard.loop_snow` |

### Звезда судьбы (`fate_star`) — ступень: HIGHER

| место | метод | роль | ванильный звук | наше событие |
|---|---|---|---|---|
| `spell/FateStarSpell.java:45` | `getCastFinishSound` | выпуск заклинания | `AMETHYST_BLOCK_RESONATE` | `pohsmp_core:spell.fate_star.release` |
| `spell/FateStarSpell.java:71` | `cast` | начало каста | `AMETHYST_BLOCK_CHIME` | `pohsmp_core:spell.fate_star.cast` |
| `spell/FateStarSpell.java:91` | `tick` | пока действует (тики) | `AMETHYST_BLOCK_CHIME` | `pohsmp_core:spell.fate_star.loop` |
| `spell/FateStarSpell.java:100` | `impact` | удар / взрыв / попадание | `FIREWORK_ROCKET_LARGE_BLAST` | `pohsmp_core:spell.fate_star.hit` |
| `spell/FateStarSpell.java:101` | `impact` | удар / взрыв / попадание | `GENERIC_EXPLODE` | `pohsmp_core:spell.fate_star.hit` |

### Печать запрета (`forbidding_seal`) — ступень: HIGHER

| место | метод | роль | ванильный звук | наше событие |
|---|---|---|---|---|
| `spell/SealSpell.java:46` | `getCastStartSound` | начало каста | `ENCHANTMENT_TABLE_USE` | `pohsmp_core:spell.forbidding_seal.cast` |
| `spell/SealSpell.java:102` | `seal` | раскрытие (печать, купол, разрыв) | `BEACON_POWER_SELECT` | `pohsmp_core:spell.forbidding_seal.open_powerup` |
| `spell/SealSpell.java:103` | `seal` | раскрытие (печать, купол, разрыв) | `ANVIL_LAND` | `pohsmp_core:spell.forbidding_seal.open_slam` |
| `spell/SealSpell.java:137` | `tick` | удар / взрыв / попадание | `GLASS_BREAK` | `pohsmp_core:spell.forbidding_seal.hit_shatter` |
| `spell/SealSpell.java:138` | `tick` | удар / взрыв / попадание | `ZOMBIE_ATTACK_IRON_DOOR` | `pohsmp_core:spell.forbidding_seal.hit_slam` |

### Совместный каст (`joint_cast`) — ступень: —

| место | метод | роль | ванильный звук | наше событие |
|---|---|---|---|---|
| `spell/JointCast.java:158` | `merge` | начало каста | `AMETHYST_BLOCK_RESONATE` | `pohsmp_core:spell.joint_cast.cast` |

### Млечный путь (`milky_way`) — ступень: HIGHER

| место | метод | роль | ванильный звук | наше событие |
|---|---|---|---|---|
| `spell/MilkyWaySpell.java:64` | `getCastStartSound` | начало каста | `BEACON_ACTIVATE` | `pohsmp_core:spell.milky_way.cast` |
| `spell/MilkyWaySpell.java:96` | `start` | начало каста | `BEACON_ACTIVATE` | `pohsmp_core:spell.milky_way.cast` |
| `spell/MilkyWaySpell.java:117` | `onServerCastTick` | нарастание во время каста | `AMETHYST_BLOCK_RESONATE` | `pohsmp_core:spell.milky_way.charge_resonate` |
| `spell/MilkyWaySpell.java:119` | `onServerCastTick` | нарастание во время каста | `BEACON_POWER_SELECT` | `pohsmp_core:spell.milky_way.charge_powerup` |
| `spell/MilkyWaySpell.java:121` | `onServerCastTick` | нарастание во время каста | `ELDER_GUARDIAN_CURSE` | `pohsmp_core:spell.milky_way.charge_roar` |
| `spell/MilkyWaySpell.java:124` | `onServerCastTick` | нарастание во время каста | `WARDEN_SONIC_CHARGE` | `pohsmp_core:spell.milky_way.charge_powerup` |
| `spell/MilkyWaySpell.java:161` | `launch` | выпуск заклинания | `END_PORTAL_SPAWN` | `pohsmp_core:spell.milky_way.release_portal` |
| `spell/MilkyWaySpell.java:162` | `launch` | выпуск заклинания | `WARDEN_SONIC_BOOM` | `pohsmp_core:spell.milky_way.release_boom` |
| `spell/MilkyWaySpell.java:182` | `tick` | конец / снятие / смерть | `BEACON_DEACTIVATE` | `pohsmp_core:spell.milky_way.end` |
| `spell/MilkyWaySpell.java:191` | `tick` | пока действует (тики) | `AMETHYST_BLOCK_RESONATE` | `pohsmp_core:spell.milky_way.loop` |
| `spell/MilkyWaySpell.java:226` | `tick` | удар / взрыв / попадание | `AMETHYST_CLUSTER_BREAK` | `pohsmp_core:spell.milky_way.hit` |
| `spell/MilkyWaySpell.java:245` | `tick` | пока действует (тики) | `AMETHYST_BLOCK_RESONATE` | `pohsmp_core:spell.milky_way.loop` |
| `spell/MilkyWaySpell.java:249` | `tick` | удар / взрыв / попадание | `AMETHYST_BLOCK_BREAK` | `pohsmp_core:spell.milky_way.hit` |

### Зеркальная темница (`mirror_prison`) — ступень: HIGHER

| место | метод | роль | ванильный звук | наше событие |
|---|---|---|---|---|
| `spell/MirrorPrisonSpell.java:55` | `getCastFinishSound` | выпуск заклинания | `ILLUSIONER_MIRROR_MOVE` | `pohsmp_core:spell.mirror_prison.release` |
| `spell/MirrorPrisonSpell.java:82` | `onCast` | начало каста | `GLASS_PLACE` | `pohsmp_core:spell.mirror_prison.cast_form` |
| `spell/MirrorPrisonSpell.java:83` | `onCast` | начало каста | `AMETHYST_BLOCK_RESONATE` | `pohsmp_core:spell.mirror_prison.cast_resonate` |
| `spell/MirrorPrisonSpell.java:84` | `onCast` | начало каста | `ILLUSIONER_MIRROR_MOVE` | `pohsmp_core:spell.mirror_prison.cast_magic` |
| `spell/MirrorPrisonSpell.java:94` | `release` | конец / снятие / смерть | `GLASS_BREAK` | `pohsmp_core:spell.mirror_prison.end` |

### Колыбель кошмара (`nightmare_cradle`) — ступень: HIGHER

| место | метод | роль | ванильный звук | наше событие |
|---|---|---|---|---|
| `spell/CradleSpell.java:39` | `getCastStartSound` | начало каста | `ILLUSIONER_PREPARE_BLINDNESS` | `pohsmp_core:spell.nightmare_cradle.cast` |
| `spell/CradleSpell.java:96` | `sleep` | начало каста | `ILLUSIONER_CAST_SPELL` | `pohsmp_core:spell.nightmare_cradle.cast` |
| `spell/CradleSpell.java:112` | `tick` | удар / взрыв / попадание | `GLASS_BREAK` | `pohsmp_core:spell.nightmare_cradle.hit` |
| `spell/CradleSpell.java:116` | `tick` | пока действует (тики) | `SOUL_ESCAPE` | `pohsmp_core:spell.nightmare_cradle.loop_soul` |
| `spell/CradleSpell.java:127` | `tick` | пока действует (тики) | `WARDEN_ROAR` | `pohsmp_core:spell.nightmare_cradle.loop_roar` |

### Клинки забвения (`oblivion_blades`) — ступень: HIGHER

| место | метод | роль | ванильный звук | наше событие |
|---|---|---|---|---|
| `spell/OblivionBladesSpell.java:37` | `getCastFinishSound` | выпуск заклинания | `ENCHANTMENT_TABLE_USE` | `pohsmp_core:spell.oblivion_blades.release` |
| `spell/OblivionBladesSpell.java:83` | `tick` | пока действует (тики) | `PLAYER_ATTACK_SWEEP` | `pohsmp_core:spell.oblivion_blades.loop` |
| `spell/OblivionBladesSpell.java:102` | `tick` | удар / взрыв / попадание | `PLAYER_ATTACK_STRONG` | `pohsmp_core:spell.oblivion_blades.hit` |

### Алый разрез (`scarlet_cut`) — ступень: HIGHER

| место | метод | роль | ванильный звук | наше событие |
|---|---|---|---|---|
| `spell/ScarletCutSpell.java:100` | `cut` | удар / взрыв / попадание | `PLAYER_ATTACK_SWEEP` | `pohsmp_core:spell.scarlet_cut.hit_whoosh` |
| `spell/ScarletCutSpell.java:101` | `cut` | удар / взрыв / попадание | `AMETHYST_BLOCK_BREAK` | `pohsmp_core:spell.scarlet_cut.hit_shatter` |
| `spell/ScarletCutSpell.java:133` | `burst` | удар / взрыв / попадание | `GLASS_BREAK` | `pohsmp_core:spell.scarlet_cut.hit_shatter` |
| `spell/ScarletCutSpell.java:134` | `burst` | удар / взрыв / попадание | `GENERIC_EXPLODE` | `pohsmp_core:spell.scarlet_cut.hit_boom` |

### Школа: Высшая (`school_higher`) — ступень: школа

| место | метод | роль | ванильный звук | наше событие |
|---|---|---|---|---|
| `Reg.java:102` | `Reg` | начало каста | `AMETHYST_BLOCK_RESONATE` | `pohsmp_core:school.higher.cast` |

### Сингулярность (`singularity`) — ступень: HIGHER

| место | метод | роль | ванильный звук | наше событие |
|---|---|---|---|---|
| `spell/SingularitySpell.java:40` | `getCastFinishSound` | выпуск заклинания | `WARDEN_SONIC_CHARGE` | `pohsmp_core:spell.singularity.release` |
| `spell/SingularitySpell.java:63` | `open` | раскрытие (печать, купол, разрыв) | `BEACON_ACTIVATE` | `pohsmp_core:spell.singularity.open` |
| `spell/SingularitySpell.java:90` | `tick` | пока действует (тики) | `BEACON_AMBIENT` | `pohsmp_core:spell.singularity.loop` |
| `spell/SingularitySpell.java:100` | `collapse` | удар / взрыв / попадание | `GENERIC_EXPLODE` | `pohsmp_core:spell.singularity.hit_boom` |
| `spell/SingularitySpell.java:101` | `collapse` | удар / взрыв / попадание | `ENDERMAN_TELEPORT` | `pohsmp_core:spell.singularity.hit_portal` |

### Падение звезды (`star_fall`) — ступень: HIGHER

| место | метод | роль | ванильный звук | наше событие |
|---|---|---|---|---|
| `spell/StarFallSpell.java:64` | `getCastStartSound` | начало каста | `BEACON_ACTIVATE` | `pohsmp_core:spell.star_fall.cast` |
| `spell/StarFallSpell.java:110` | `begin` | начало каста | `BEACON_ACTIVATE` | `pohsmp_core:spell.star_fall.cast` |
| `spell/StarFallSpell.java:120` | `tick` | пока действует (тики) | `AMETHYST_BLOCK_CHIME` | `pohsmp_core:spell.star_fall.loop_chime` |
| `spell/StarFallSpell.java:123` | `tick` | пока действует (тики) | `FIREWORK_ROCKET_LAUNCH` | `pohsmp_core:spell.star_fall.loop_whoosh` |
| `spell/StarFallSpell.java:124` | `tick` | пока действует (тики) | `BEACON_POWER_SELECT` | `pohsmp_core:spell.star_fall.loop_powerup` |
| `spell/StarFallSpell.java:126` | `tick` | пока действует (тики) | `ELYTRA_FLYING` | `pohsmp_core:spell.star_fall.loop_whoosh` |
| `spell/StarFallSpell.java:141` | `impact` | удар / взрыв / попадание | `GENERIC_EXPLODE` | `pohsmp_core:spell.star_fall.hit_boom` |
| `spell/StarFallSpell.java:142` | `impact` | удар / взрыв / попадание | `LIGHTNING_BOLT_THUNDER` | `pohsmp_core:spell.star_fall.hit_thunder` |
| `spell/StarFallSpell.java:143` | `impact` | удар / взрыв / попадание | `AMETHYST_CLUSTER_BREAK` | `pohsmp_core:spell.star_fall.hit_shatter` |

### Вознесение ветра (`wind_ascension`) — ступень: HIGHER

| место | метод | роль | ванильный звук | наше событие |
|---|---|---|---|---|
| `spell/AscensionSpell.java:40` | `getCastFinishSound` | выпуск заклинания | `BEACON_ACTIVATE` | `pohsmp_core:spell.wind_ascension.release` |
| `spell/AscensionSpell.java:67` | `rise` | начало каста | `PHANTOM_FLAP` | `pohsmp_core:spell.wind_ascension.cast` |
| `spell/AscensionSpell.java:103` | `beam` | удар / взрыв / попадание | `AMETHYST_CLUSTER_BREAK` | `pohsmp_core:spell.wind_ascension.hit_shatter` |
| `spell/AscensionSpell.java:104` | `beam` | удар / взрыв / попадание | `FIREWORK_ROCKET_TWINKLE` | `pohsmp_core:spell.wind_ascension.hit_chime` |
| `spell/AscensionSpell.java:114` | `land` | удар / взрыв / попадание | `BEACON_DEACTIVATE` | `pohsmp_core:spell.wind_ascension.hit_powerdown` |
| `spell/AscensionSpell.java:115` | `land` | удар / взрыв / попадание | `AMETHYST_BLOCK_CHIME` | `pohsmp_core:spell.wind_ascension.hit_chime` |

### Разлом мира (`world_rift`) — ступень: HIGHER

| место | метод | роль | ванильный звук | наше событие |
|---|---|---|---|---|
| `spell/WorldRiftSpell.java:42` | `getCastStartSound` | начало каста | `WARDEN_DIG` | `pohsmp_core:spell.world_rift.cast_earth` |
| `spell/WorldRiftSpell.java:61` | `onCast` | начало каста | `GENERIC_EXPLODE` | `pohsmp_core:spell.world_rift.cast_boom` |
| `spell/WorldRiftSpell.java:77` | `tick` | удар / взрыв / попадание | `DRIPSTONE_BLOCK_BREAK` | `pohsmp_core:spell.world_rift.hit` |
| `spell/WorldRiftSpell.java:92` | `tick` | пока действует (тики) | `WITHER_SHOOT` | `pohsmp_core:spell.world_rift.loop` |

## Божественная (`divine`) — золотой хор и большой колокол

### Ковчег (`ark`) — ступень: LEGENDARY

| место | метод | роль | ванильный звук | наше событие |
|---|---|---|---|---|
| `spell/ArkSpell.java:66` | `getCastStartSound` | начало каста | `BEACON_ACTIVATE` | `pohsmp_core:spell.ark.cast_powerup` |
| `spell/ArkSpell.java:67` | `getCastFinishSound` | выпуск заклинания | `BELL_RESONATE` | `pohsmp_core:spell.ark.release` |
| `spell/ArkSpell.java:108` | `onCast` | начало каста | `BEACON_POWER_SELECT` | `pohsmp_core:spell.ark.cast_powerup` |
| `spell/ArkSpell.java:109` | `onCast` | начало каста | `BELL_BLOCK` | `pohsmp_core:spell.ark.cast_bell` |
| `spell/ArkSpell.java:129` | `tick` | конец / снятие / смерть | `BEACON_DEACTIVATE` | `pohsmp_core:spell.ark.end_powerdown` |
| `spell/ArkSpell.java:170` | `onDeath` | конец / снятие / смерть | `BELL_BLOCK` | `pohsmp_core:spell.ark.end_bell` |

### Благословение (`blessing`) — ступень: —

| место | метод | роль | ванильный звук | наше событие |
|---|---|---|---|---|
| `spell/BlessingSpell.java:37` | `getCastStartSound` | начало каста | `BEACON_ACTIVATE` | `pohsmp_core:spell.blessing.cast` |
| `spell/BlessingSpell.java:62` | `castTick` | нарастание во время каста | `AMETHYST_BLOCK_CHIME` | `pohsmp_core:spell.blessing.charge_chime` |
| `spell/BlessingSpell.java:63` | `castTick` | нарастание во время каста | `BEACON_POWER_SELECT` | `pohsmp_core:spell.blessing.charge_powerup` |
| `spell/BlessingSpell.java:64` | `castTick` | нарастание во время каста | `ENCHANTMENT_TABLE_USE` | `pohsmp_core:spell.blessing.charge_magic` |
| `spell/BlessingSpell.java:67` | `castTick` | нарастание во время каста | `AMETHYST_BLOCK_CHIME` | `pohsmp_core:spell.blessing.charge_chime` |
| `spell/BlessingSpell.java:79` | `apply` | удар / взрыв / попадание | `BELL_BLOCK` | `pohsmp_core:spell.blessing.hit_bell` |
| `spell/BlessingSpell.java:80` | `apply` | удар / взрыв / попадание | `PLAYER_LEVELUP` | `pohsmp_core:spell.blessing.hit_fanfare` |

### Дезинтеграция (`disintegration`) — ступень: LEGENDARY

| место | метод | роль | ванильный звук | наше событие |
|---|---|---|---|---|
| `spell/DisintegrationSpell.java:94` | `getCastStartSound` | начало каста | `BEACON_ACTIVATE` | `pohsmp_core:spell.disintegration.cast` |
| `spell/DisintegrationSpell.java:226` | `startHold` | начало каста | `BEACON_ACTIVATE` | `pohsmp_core:spell.disintegration.cast` |
| `spell/DisintegrationSpell.java:256` | `tickHold` | нарастание во время каста | `AMETHYST_BLOCK_CHIME` | `pohsmp_core:spell.disintegration.charge_chime` |
| `spell/DisintegrationSpell.java:257` | `tickHold` | нарастание во время каста | `AMETHYST_BLOCK_RESONATE` | `pohsmp_core:spell.disintegration.charge_resonate` |
| `spell/DisintegrationSpell.java:259` | `tickHold` | нарастание во время каста | `BEACON_AMBIENT` | `pohsmp_core:spell.disintegration.charge_hum` |
| `spell/DisintegrationSpell.java:260` | `tickHold` | нарастание во время каста | `BEACON_POWER_SELECT` | `pohsmp_core:spell.disintegration.charge_powerup` |
| `spell/DisintegrationSpell.java:261` | `tickHold` | нарастание во время каста | `TRIDENT_THUNDER` | `pohsmp_core:spell.disintegration.charge_thunder` |
| `spell/DisintegrationSpell.java:277` | `finish` | удар / взрыв / попадание | `WARDEN_SONIC_BOOM` | `pohsmp_core:spell.disintegration.hit_boom` |
| `spell/DisintegrationSpell.java:278` | `finish` | удар / взрыв / попадание | `BEACON_DEACTIVATE` | `pohsmp_core:spell.disintegration.hit_powerdown` |
| `spell/DisintegrationSpell.java:279` | `finish` | удар / взрыв / попадание | `GENERIC_EXPLODE` | `pohsmp_core:spell.disintegration.hit_boom` |

### Божественная отдача (`divine_backlash`) — ступень: —

| место | метод | роль | ванильный звук | наше событие |
|---|---|---|---|---|
| `DivineEvents.java:57` | `onPlayerTick` | пока действует (тики) | `BELL_BLOCK` | `pohsmp_core:spell.divine_backlash.loop_bell` |
| `DivineEvents.java:73` | `onCast` | начало каста | `BELL_BLOCK` | `pohsmp_core:spell.divine_backlash.cast` |
| `DivineEvents.java:106` | `aura` | пока действует (тики) | `AMETHYST_BLOCK_CHIME` | `pohsmp_core:spell.divine_backlash.loop_chime` |

### Божественное табу (`divine_taboo`) — ступень: LEGENDARY

| место | метод | роль | ванильный звук | наше событие |
|---|---|---|---|---|
| `spell/TabooSpell.java:113` | `getCastStartSound` | начало каста | `BEACON_ACTIVATE` | `pohsmp_core:spell.divine_taboo.cast_powerup` |
| `spell/TabooSpell.java:114` | `getCastFinishSound` | выпуск заклинания | `BELL_RESONATE` | `pohsmp_core:spell.divine_taboo.release` |
| `spell/TabooSpell.java:138` | `onServerCastTick` | нарастание во время каста | `BELL_RESONATE` | `pohsmp_core:spell.divine_taboo.charge` |
| `spell/TabooSpell.java:164` | `onCast` | начало каста | `BEACON_POWER_SELECT` | `pohsmp_core:spell.divine_taboo.cast_powerup` |
| `spell/TabooSpell.java:165` | `onCast` | начало каста | `BELL_BLOCK` | `pohsmp_core:spell.divine_taboo.cast_bell` |
| `spell/TabooSpell.java:177` | `tick` | конец / снятие / смерть | `BEACON_DEACTIVATE` | `pohsmp_core:spell.divine_taboo.end` |

### Школа: Божественная (`school_divine`) — ступень: школа

| место | метод | роль | ванильный звук | наше событие |
|---|---|---|---|---|
| `Reg.java:90` | `Reg` | начало каста | `BEACON_ACTIVATE` | `pohsmp_core:school.divine.cast` |

### Поглощение души (`soul_devour`) — ступень: LEGENDARY

| место | метод | роль | ванильный звук | наше событие |
|---|---|---|---|---|
| `spell/SoulDevourSpell.java:67` | `getCastStartSound` | начало каста | `SCULK_SHRIEKER_SHRIEK` | `pohsmp_core:spell.soul_devour.cast_roar` |
| `spell/SoulDevourSpell.java:108` | `start` | начало каста | `WARDEN_HEARTBEAT` | `pohsmp_core:spell.soul_devour.cast_heart` |
| `spell/SoulDevourSpell.java:146` | `onServerCastTick` | нарастание во время каста | `WARDEN_HEARTBEAT` | `pohsmp_core:spell.soul_devour.charge_heart` |
| `spell/SoulDevourSpell.java:147` | `onServerCastTick` | нарастание во время каста | `SOUL_ESCAPE` | `pohsmp_core:spell.soul_devour.charge_soul` |
| `spell/SoulDevourSpell.java:149` | `onServerCastTick` | нарастание во время каста | `SCULK_SHRIEKER_SHRIEK` | `pohsmp_core:spell.soul_devour.charge_roar` |
| `spell/SoulDevourSpell.java:151` | `onServerCastTick` | нарастание во время каста | `ELDER_GUARDIAN_CURSE` | `pohsmp_core:spell.soul_devour.charge_roar` |
| `spell/SoulDevourSpell.java:154` | `onServerCastTick` | нарастание во время каста | `WARDEN_SONIC_CHARGE` | `pohsmp_core:spell.soul_devour.charge_powerup` |
| `spell/SoulDevourSpell.java:189` | `devour` | удар / взрыв / попадание | `WARDEN_SONIC_BOOM` | `pohsmp_core:spell.soul_devour.hit_boom` |
| `spell/SoulDevourSpell.java:190` | `devour` | удар / взрыв / попадание | `SOUL_ESCAPE` | `pohsmp_core:spell.soul_devour.hit_soul` |

### Печать души (`soul_seal`) — ступень: —

| место | метод | роль | ванильный звук | наше событие |
|---|---|---|---|---|
| `spell/SoulSeal.java:98` | `deny` | отказ / ошибка | `CHAIN_PLACE` | `pohsmp_core:spell.soul_seal.fail_chain` |
| `spell/SoulSeal.java:99` | `deny` | отказ / ошибка | `AMETHYST_BLOCK_RESONATE` | `pohsmp_core:spell.soul_seal.fail_resonate` |
| `spell/SoulSealSpell.java:33` | `getCastStartSound` | начало каста | `BEACON_ACTIVATE` | `pohsmp_core:spell.soul_seal.cast` |
| `spell/SoulSealSpell.java:60` | `castTick` | нарастание во время каста | `RESPAWN_ANCHOR_CHARGE` | `pohsmp_core:spell.soul_seal.charge_powerup` |
| `spell/SoulSealSpell.java:61` | `castTick` | нарастание во время каста | `ENCHANTMENT_TABLE_USE` | `pohsmp_core:spell.soul_seal.charge_magic` |
| `spell/SoulSealSpell.java:62` | `castTick` | нарастание во время каста | `CHAIN_PLACE` | `pohsmp_core:spell.soul_seal.charge_chain` |
| `spell/SoulSealSpell.java:63` | `castTick` | нарастание во время каста | `ELDER_GUARDIAN_CURSE` | `pohsmp_core:spell.soul_seal.charge_roar` |
| `spell/SoulSealSpell.java:67` | `castTick` | нарастание во время каста | `CHAIN_STEP` | `pohsmp_core:spell.soul_seal.charge_chain` |
| `spell/SoulSealSpell.java:68` | `castTick` | нарастание во время каста | `AMETHYST_BLOCK_RESONATE` | `pohsmp_core:spell.soul_seal.charge_resonate` |
| `spell/SoulSealSpell.java:77` | `apply` | удар / взрыв / попадание | `ANVIL_LAND` | `pohsmp_core:spell.soul_seal.hit_slam` |
| `spell/SoulSealSpell.java:78` | `apply` | удар / взрыв / попадание | `BELL_BLOCK` | `pohsmp_core:spell.soul_seal.hit_bell` |
| `spell/SoulSealSpell.java:79` | `apply` | удар / взрыв / попадание | `BEACON_DEACTIVATE` | `pohsmp_core:spell.soul_seal.hit_powerdown` |

## Запретная (Мироздание) (`forbidden`) — искажение реальности: реверс, «цифровой» распад, тишина и разрыв

### Низвержение (`downfall`) — ступень: LEGENDARY

| место | метод | роль | ванильный звук | наше событие |
|---|---|---|---|---|
| `spell/DownfallSpell.java:88` | `getCastStartSound` | начало каста | `BEACON_ACTIVATE` | `pohsmp_core:spell.downfall.cast` |
| `spell/DownfallSpell.java:137` | `start` | начало каста | `BEACON_ACTIVATE` | `pohsmp_core:spell.downfall.cast` |
| `spell/DownfallSpell.java:165` | `tickFx` | нарастание во время каста | `AMBIENT_CAVE` | `pohsmp_core:spell.downfall.charge_hum` |
| `spell/DownfallSpell.java:167` | `tickFx` | нарастание во время каста | `WITHER_SPAWN` | `pohsmp_core:spell.downfall.charge_roar` |
| `spell/DownfallSpell.java:169` | `tickFx` | нарастание во время каста | `END_PORTAL_SPAWN` | `pohsmp_core:spell.downfall.charge_portal` |
| `spell/DownfallSpell.java:173` | `tickFx` | нарастание во время каста | `ELDER_GUARDIAN_CURSE` | `pohsmp_core:spell.downfall.charge_roar` |
| `spell/DownfallSpell.java:177` | `tickFx` | нарастание во время каста | `WARDEN_SONIC_CHARGE` | `pohsmp_core:spell.downfall.charge_powerup` |
| `spell/DownfallSpell.java:178` | `tickFx` | нарастание во время каста | `WARDEN_SONIC_CHARGE` | `pohsmp_core:spell.downfall.charge_powerup` |
| `spell/DownfallSpell.java:180` | `tickFx` | нарастание во время каста | `END_GATEWAY_SPAWN` | `pohsmp_core:spell.downfall.charge_portal` |
| `spell/DownfallSpell.java:261` | `openRift` | раскрытие (печать, купол, разрыв) | `END_PORTAL_SPAWN` | `pohsmp_core:spell.downfall.open_portal` |
| `spell/DownfallSpell.java:262` | `openRift` | раскрытие (печать, купол, разрыв) | `GENERIC_EXPLODE` | `pohsmp_core:spell.downfall.open_boom` |
| `spell/DownfallSpell.java:280` | `tick` | пока действует (тики) | `PORTAL_AMBIENT` | `pohsmp_core:spell.downfall.loop_hum` |
| `spell/DownfallSpell.java:284` | `tick` | пока действует (тики) | `END_PORTAL_FRAME_FILL` | `pohsmp_core:spell.downfall.loop_powerup` |
| `spell/DownfallSpell.java:303` | `swallow` | удар / взрыв / попадание | `PORTAL_TRAVEL` | `pohsmp_core:spell.downfall.hit` |
| `spell/DownfallSpell.java:314` | `send` | удар / взрыв / попадание | `PORTAL_TRAVEL` | `pohsmp_core:spell.downfall.hit` |

### Стёртое имя (`erased_name`) — ступень: —

| место | метод | роль | ванильный звук | наше событие |
|---|---|---|---|---|
| `client/illusion/ErasedClient.java:67` | `onTick` | пока действует (тики) | `AMBIENT_BASALT_DELTAS_LOOP` | `pohsmp_core:spell.erased_name.loop` |
| `erased/ErasedNameSpell.java:59` | `getCastStartSound` | начало каста | `BOOK_PAGE_TURN` | `pohsmp_core:spell.erased_name.cast_paper` |
| `erased/ErasedNameSpell.java:148` | `onServerCastTick` | нарастание во время каста | `BOOK_PAGE_TURN` | `pohsmp_core:spell.erased_name.charge_paper` |
| `erased/ErasedNameSpell.java:151` | `onServerCastTick` | нарастание во время каста | `BOOK_PUT` | `pohsmp_core:spell.erased_name.charge_paper` |
| `erased/ErasedNameSpell.java:152` | `onServerCastTick` | нарастание во время каста | `ENCHANTMENT_TABLE_USE` | `pohsmp_core:spell.erased_name.charge_magic` |
| `erased/ErasedNameSpell.java:154` | `onServerCastTick` | нарастание во время каста | `SCULK_CATALYST_BLOOM` | `pohsmp_core:spell.erased_name.charge_wet` |
| `erased/ErasedNameSpell.java:157` | `onServerCastTick` | нарастание во время каста | `PLAYER_ATTACK_SWEEP` | `pohsmp_core:spell.erased_name.charge_whoosh` |
| `erased/ErasedNameSpell.java:161` | `onServerCastTick` | нарастание во время каста | `SAND_BREAK` | `pohsmp_core:spell.erased_name.charge_paper` |
| `erased/ErasedNameSpell.java:171` | `onCast` | начало каста | `ELYTRA_FLYING` | `pohsmp_core:spell.erased_name.cast_whoosh` |

### Школа: Запретная (Мироздание) (`school_forbidden`) — ступень: школа

| место | метод | роль | ванильный звук | наше событие |
|---|---|---|---|---|
| `Reg.java:114` | `Reg` | начало каста | `END_PORTAL_SPAWN` | `pohsmp_core:school.forbidden.cast` |

## Безмолвная (`silent`) — чистый хрустальный звон

### Барьер (страж оболочки) (`barrier_guard`) — ступень: —

| место | метод | роль | ванильный звук | наше событие |
|---|---|---|---|---|
| `spell/BarrierGuard.java:59` | `kill` | удар / взрыв / попадание | `AMETHYST_CLUSTER_BREAK` | `pohsmp_core:spell.barrier_guard.hit_shatter` |
| `spell/BarrierGuard.java:60` | `kill` | удар / взрыв / попадание | `SOUL_ESCAPE` | `pohsmp_core:spell.barrier_guard.hit_soul` |
| `spell/BarrierGuard.java:155` | `repel` | удар / взрыв / попадание | `AMETHYST_BLOCK_RESONATE` | `pohsmp_core:spell.barrier_guard.hit_resonate` |
| `spell/BarrierGuard.java:233` | `crack` | удар / взрыв / попадание | `GLASS_BREAK` | `pohsmp_core:spell.barrier_guard.hit_shatter` |
| `spell/BarrierGuard.java:240` | `tick` | пока действует (тики) | `AMETHYST_BLOCK_CHIME` | `pohsmp_core:spell.barrier_guard.loop` |

### Школа: Безмолвная (`school_silent`) — ступень: школа

| место | метод | роль | ванильный звук | наше событие |
|---|---|---|---|---|
| `Reg.java:129` | `Reg` | начало каста | `AMETHYST_BLOCK_CHIME` | `pohsmp_core:school.silent.cast` |

### Посох Безмолвной (`silent_staff`) — ступень: LEGENDARY

| место | метод | роль | ванильный звук | наше событие |
|---|---|---|---|---|
| `spell/silent/SilentStaffSpell.java:45` | `getCastFinishSound` | выпуск заклинания | `AMETHYST_BLOCK_CHIME` | `pohsmp_core:spell.silent_staff.release` |

### Безмолвная ведьма (`silent_witch`) — ступень: —

| место | метод | роль | ванильный звук | наше событие |
|---|---|---|---|---|
| `silent/SilentWitchEvents.java:152` | `onDeath` | конец / снятие / смерть | `AMETHYST_BLOCK_RESONATE` | `pohsmp_core:spell.silent_witch.end` |

### Ветряные копья (`wind_spears`) — ступень: —

| место | метод | роль | ванильный звук | наше событие |
|---|---|---|---|---|
| `spell/silent/WindSpearsSpell.java:124` | `tick` | пока действует (тики) | `PLAYER_ATTACK_SWEEP` | `pohsmp_core:spell.wind_spears.loop` |
| `spell/silent/WindSpearsSpell.java:184` | `strike` | удар / взрыв / попадание | `AMETHYST_BLOCK_BREAK` | `pohsmp_core:spell.wind_spears.hit` |

### Чёрное пламя Ворганы (`worgan_flame`) — ступень: —

| место | метод | роль | ванильный звук | наше событие |
|---|---|---|---|---|
| `spell/silent/WorganFlameSpell.java:162` | `breathe` | начало каста | `ENDER_DRAGON_SHOOT` | `pohsmp_core:spell.worgan_flame.cast` |
| `spell/silent/WorganFlameSpell.java:178` | `tick` | пока действует (тики) | `FIRE_AMBIENT` | `pohsmp_core:spell.worgan_flame.loop` |

## Иллюзии (`illusion`) — стекло и зеркала, мерцающее эхо

### Чужое лицо (`borrowed_face`) — ступень: UNCOMMON

| место | метод | роль | ванильный звук | наше событие |
|---|---|---|---|---|
| `spell/illusion/BorrowedFaceSpell.java:88` | `onCast` | начало каста | `AMETHYST_BLOCK_CHIME` | `pohsmp_core:spell.borrowed_face.cast_chime` |
| `spell/illusion/BorrowedFaceSpell.java:89` | `onCast` | начало каста | `ILLUSIONER_PREPARE_MIRROR` | `pohsmp_core:spell.borrowed_face.cast_magic` |
| `spell/illusion/BorrowedFaceSpell.java:160` | `end` | конец / снятие / смерть | `AMETHYST_CLUSTER_BREAK` | `pohsmp_core:spell.borrowed_face.end` |

### Сон бабочки (`butterfly_dream`) — ступень: MYTHIC

| место | метод | роль | ванильный звук | наше событие |
|---|---|---|---|---|
| `spell/illusion/ButterflyDreamSpell.java:72` | `getCastStartSound` | начало каста | `AMETHYST_BLOCK_RESONATE` | `pohsmp_core:spell.butterfly_dream.cast` |
| `spell/illusion/ButterflyDreamSpell.java:139` | `onServerCastTick` | нарастание во время каста | `AMETHYST_CLUSTER_BREAK` | `pohsmp_core:spell.butterfly_dream.charge_shatter` |
| `spell/illusion/ButterflyDreamSpell.java:140` | `onServerCastTick` | нарастание во время каста | `GLASS_BREAK` | `pohsmp_core:spell.butterfly_dream.charge_shatter` |
| `spell/illusion/ButterflyDreamSpell.java:141` | `onServerCastTick` | нарастание во время каста | `BEACON_POWER_SELECT` | `pohsmp_core:spell.butterfly_dream.charge_powerup` |
| `spell/illusion/ButterflyDreamSpell.java:144` | `onServerCastTick` | нарастание во время каста | `GLASS_BREAK` | `pohsmp_core:spell.butterfly_dream.charge_shatter` |
| `spell/illusion/ButterflyDreamSpell.java:149` | `onServerCastTick` | нарастание во время каста | `AMETHYST_BLOCK_RESONATE` | `pohsmp_core:spell.butterfly_dream.charge_resonate` |
| `spell/illusion/ButterflyDreamSpell.java:256` | `dream` | удар / взрыв / попадание | `AMETHYST_BLOCK_CHIME` | `pohsmp_core:spell.butterfly_dream.hit_chime` |
| `spell/illusion/ButterflyDreamSpell.java:356` | `ripple` | удар / взрыв / попадание | `AMETHYST_BLOCK_CHIME` | `pohsmp_core:spell.butterfly_dream.hit_chime` |
| `spell/illusion/ButterflyDreamSpell.java:372` | `dreamDeath` | конец / снятие / смерть | `AMETHYST_BLOCK_BREAK` | `pohsmp_core:spell.butterfly_dream.end` |
| `spell/illusion/ButterflyDreamSpell.java:440` | `wakeFx` | конец / снятие / смерть | `GLASS_BREAK` | `pohsmp_core:spell.butterfly_dream.end` |
| `spell/illusion/ButterflyDreamSpell.java:548` | `onTick` | удар / взрыв / попадание | `GLASS_BREAK` | `pohsmp_core:spell.butterfly_dream.hit_shatter` |
| `spell/illusion/ButterflyDreamSpell.java:549` | `onTick` | удар / взрыв / попадание | `AMETHYST_CLUSTER_BREAK` | `pohsmp_core:spell.butterfly_dream.hit_shatter` |

### Ложный шаг (`false_step`) — ступень: UNCOMMON

| место | метод | роль | ванильный звук | наше событие |
|---|---|---|---|---|
| `spell/illusion/FalseStepSpell.java:78` | `onCast` | начало каста | `AMETHYST_BLOCK_CHIME` | `pohsmp_core:spell.false_step.cast` |

### Иллюзорные копии (`illusion_copies`) — ступень: —

| место | метод | роль | ванильный звук | наше событие |
|---|---|---|---|---|
| `client/illusion/Copies.java:86` | `handle` | удар / взрыв / попадание | `PLAYER_HURT` | `pohsmp_core:spell.illusion_copies.hit_wet` |
| `illusion/IllusionAllies.java:111` | `onInteract` | удар / взрыв / попадание | `AMETHYST_BLOCK_CHIME` | `pohsmp_core:spell.illusion_copies.hit_chime` |
| `illusion/Illusions.java:247` | `onTick` | пока действует (тики) | `AMETHYST_BLOCK_CHIME` | `pohsmp_core:spell.illusion_copies.loop` |

### Отражения (`mirror_images`) — ступень: RARE

| место | метод | роль | ванильный звук | наше событие |
|---|---|---|---|---|
| `spell/illusion/MirrorImagesSpell.java:78` | `onCast` | начало каста | `AMETHYST_BLOCK_CHIME` | `pohsmp_core:spell.mirror_images.cast_chime` |
| `spell/illusion/MirrorImagesSpell.java:79` | `onCast` | начало каста | `ILLUSIONER_MIRROR_MOVE` | `pohsmp_core:spell.mirror_images.cast_magic` |

### Зеркальный лабиринт (`mirror_labyrinth`) — ступень: HIGHER

| место | метод | роль | ванильный звук | наше событие |
|---|---|---|---|---|
| `spell/illusion/MirrorLabyrinthSpell.java:55` | `getCastStartSound` | начало каста | `AMETHYST_BLOCK_RESONATE` | `pohsmp_core:spell.mirror_labyrinth.cast_resonate` |
| `spell/illusion/MirrorLabyrinthSpell.java:118` | `onCast` | начало каста | `GLASS_BREAK` | `pohsmp_core:spell.mirror_labyrinth.cast_shatter` |
| `spell/illusion/MirrorLabyrinthSpell.java:119` | `onCast` | начало каста | `AMETHYST_BLOCK_RESONATE` | `pohsmp_core:spell.mirror_labyrinth.cast_resonate` |
| `spell/illusion/MirrorLabyrinthSpell.java:190` | `onTick` | удар / взрыв / попадание | `GLASS_BREAK` | `pohsmp_core:spell.mirror_labyrinth.hit` |

### Фантомная боль (`phantom_pain`) — ступень: UNCOMMON

| место | метод | роль | ванильный звук | наше событие |
|---|---|---|---|---|
| `spell/illusion/PhantomPainSpell.java:74` | `onCast` | начало каста | `AMETHYST_BLOCK_CHIME` | `pohsmp_core:spell.phantom_pain.cast_chime` |
| `spell/illusion/PhantomPainSpell.java:75` | `onCast` | начало каста | `ALLAY_AMBIENT_WITHOUT_ITEM` | `pohsmp_core:spell.phantom_pain.cast_soul` |
| `spell/illusion/PhantomPainSpell.java:89` | `mark` | удар / взрыв / попадание | `AMETHYST_CLUSTER_HIT` | `pohsmp_core:spell.phantom_pain.hit` |

### Школа: Иллюзии (`school_illusion`) — ступень: школа

| место | метод | роль | ванильный звук | наше событие |
|---|---|---|---|---|
| `Reg.java:141` | `Reg` | начало каста | `AMETHYST_BLOCK_RESONATE` | `pohsmp_core:school.illusion.cast` |

### Пелена (`veil`) — ступень: RARE

| место | метод | роль | ванильный звук | наше событие |
|---|---|---|---|---|
| `spell/illusion/VeilSpell.java:90` | `onCast` | начало каста | `AMETHYST_BLOCK_RESONATE` | `pohsmp_core:spell.veil.cast_resonate` |
| `spell/illusion/VeilSpell.java:91` | `onCast` | начало каста | `ALLAY_AMBIENT_WITHOUT_ITEM` | `pohsmp_core:spell.veil.cast_soul` |

### Кошмар наяву (`waking_nightmare`) — ступень: HIGHER

| место | метод | роль | ванильный звук | наше событие |
|---|---|---|---|---|
| `spell/illusion/WakingNightmareSpell.java:56` | `getCastStartSound` | начало каста | `SCULK_SHRIEKER_SHRIEK` | `pohsmp_core:spell.waking_nightmare.cast_roar` |
| `spell/illusion/WakingNightmareSpell.java:132` | `start` | начало каста | `WARDEN_HEARTBEAT` | `pohsmp_core:spell.waking_nightmare.cast_heart` |

## Пропущено

| место | ванильный звук | почему |
|---|---|---|
| `Reg.java:164` | `WARDEN_HEARTBEAT` | школа Кошмаров — уже свои звуки (nightmare.heartbeat) |
| `silent/SilentWitchArmor.java:179` | `ARMOR_EQUIP_LEATHER` | не магия: звук надевания мантии |
| `nightmare/EndlessNightSpell.java:49` | `WARDEN_HEARTBEAT` | Кошмары — уже свои звуки (nightmare.cast_night) |
| `nightmare/EndlessNightSpell.java:105` | `WARDEN_HEARTBEAT` | Кошмары — уже свои звуки (nightmare.cast_night) |
| `nightmare/EndlessNightSpell.java:106` | `AMBIENT_CAVE` | Кошмары — уже свои звуки (nightmare.cast_night) |
| `nightmare/NightmareMob.java:234` | `ALLAY_AMBIENT_WITHOUT_ITEM` | Кошмары — уже свои звуки (nightmare.*) |
| `nightmare/NightmareMob.java:235` | `VEX_AMBIENT` | Кошмары — уже свои звуки (nightmare.*) |
| `nightmare/NightmareMob.java:250` | `SOUL_ESCAPE` | Кошмары — уже свои звуки (nightmare.*) |
| `nightmare/NightmareMob.java:262` | `ENDERMAN_SCREAM` | Кошмары — уже свои звуки (nightmare.*) |
| `nightmare/NightmareMob.java:283` | `GHAST_SCREAM` | Кошмары — уже свои звуки (nightmare.*) |
| `nightmare/NightmareMob.java:284` | `GHAST_AMBIENT` | Кошмары — уже свои звуки (nightmare.*) |
| `nightmare/NightmareMob.java:293` | `SLIME_SQUISH` | Кошмары — уже свои звуки (nightmare.*) |
| `nightmare/NightmareMob.java:302` | `PHANTOM_FLAP` | Кошмары — уже свои звуки (nightmare.*) |
| `nightmare/NightmareMob.java:314` | `RAVAGER_ROAR` | Кошмары — уже свои звуки (nightmare.*) |
| `nightmare/NightmareMob.java:315` | `WARDEN_ROAR` | Кошмары — уже свои звуки (nightmare.*) |
| `nightmare/NightmareMob.java:319` | `SKELETON_STEP` | Кошмары — уже свои звуки (nightmare.*) |
| `nightmare/NightmareMob.java:323` | `SPIDER_AMBIENT` | Кошмары — уже свои звуки (nightmare.*) |
| `nightmare/NightmareMob.java:329` | `VILLAGER_AMBIENT` | Кошмары — уже свои звуки (nightmare.*) |
| `nightmare/NightmareMob.java:342` | `WARDEN_ROAR` | Кошмары — уже свои звуки (nightmare.*) |
| `nightmare/NightmareMob.java:380` | `PLAYER_HURT` | Кошмары — уже свои звуки (nightmare.*) |
| `nightmare/NightmareMob.java:383` | `EVOKER_FANGS_ATTACK` | Кошмары — уже свои звуки (nightmare.*) |
| `nightmare/NightmareMob.java:384` | `MUD_BREAK` | Кошмары — уже свои звуки (nightmare.*) |
| `nightmare/NightmareMob.java:385` | `PHANTOM_BITE` | Кошмары — уже свои звуки (nightmare.*) |
| `nightmare/NightmareMob.java:406` | `HONEY_BLOCK_SLIDE` | Кошмары — уже свои звуки (nightmare.*) |
| `client/nightmare/NightmareClient.java:88` | `WARDEN_HEARTBEAT` | Кошмары — уже свои звуки (nightmare.heartbeat) |

Также уже свои и не трогаются: музыка Врат (`music.silent_gate*`), Ковена (`music.coven_arrival`), Сна бабочки (`music.butterfly_dream`), все `nightmare.*`.
