package ru.pohsmp.core;

import net.minecraftforge.common.ForgeConfigSpec;

public final class ServerConfig {
    public static final ForgeConfigSpec SPEC;
    public static final ForgeConfigSpec.IntValue BACKLASH_SECONDS, SLOW_SECONDS, WEAK_SECONDS, NAUSEA_SECONDS;
    public static final ForgeConfigSpec.BooleanValue BLOCK_MANA;
    public static final ForgeConfigSpec.BooleanValue AURA;
    public static final ForgeConfigSpec.DoubleValue DIS_PERCENT;
    public static final ForgeConfigSpec.DoubleValue DIS_FLAT;
    public static final ForgeConfigSpec.IntValue DIS_RANGE;
    public static final ForgeConfigSpec.BooleanValue DIS_KILL;
    public static final ForgeConfigSpec.DoubleValue REPLICA_PERCENT;
    public static final ForgeConfigSpec.DoubleValue HIGHER_MULT;
    // Silent Witch outfit (T19)
    public static final ForgeConfigSpec.DoubleValue SW_CAST, SW_CAST_SILENT, SW_MANA_ROBE, SW_MANA_HOOD, SW_REGEN, SW_RESIST, SW_RESIST_SILENT;
    public static final ForgeConfigSpec.BooleanValue SW_MUTE_CHANT, SW_SILENT_STEPS, SW_NO_VIBRATIONS, SW_TEAM, SW_GATE_MAGIC_IMMUNE;
    public static final ForgeConfigSpec.IntValue SW_BARRIER_COOLDOWN, SW_BARRIER_INVUL, SW_STEALTH_RANGE, SW_EXPOSE_SECONDS;
    public static final ForgeConfigSpec.ConfigValue<String> SW_GATE_SPELL;
    public static final ForgeConfigSpec.DoubleValue GATE_RAY_DAMAGE, GATE_RAY_RADIUS, GATE_AREA, GATE_SET_BONUS;
    public static final ForgeConfigSpec.IntValue GATE_HIT_COOLDOWN, GATE_AIM_INTERVAL, GATE_BEAMS_MIN, GATE_BEAMS_MAX, GATE_SILENCE_SECONDS;
    public static final ForgeConfigSpec.ConfigValue<java.util.List<? extends String>> JOINT_SPELLS;
    public static final ForgeConfigSpec.DoubleValue JOINT_RADIUS, JOINT_WINDOW, JOINT_MULT;
    public static final ForgeConfigSpec.DoubleValue COUNTDOWN_MAX;
    public static final ForgeConfigSpec.DoubleValue STAR_FALL_DAMAGE, STAR_FALL_EDGE;
    public static final ForgeConfigSpec.IntValue SCARLET_CUTS_MIN, SCARLET_CUTS_MAX, SCARLET_INTERVAL, SCARLET_CRACK_DELAY;
    public static final ForgeConfigSpec.DoubleValue SCARLET_DAMAGE, SCARLET_WIDTH, SCARLET_NEAR, SCARLET_FAR,
            SCARLET_SHARD_DAMAGE, SCARLET_SHARD_RADIUS, SCARLET_KNOCK_UP;

    // [silent_staff] - the four Silent Witch staff spells (T20)
    public static final ForgeConfigSpec.IntValue SPEARS_CAST, SPEARS_MANA, SPEARS_TARGETS, SPEARS_HOVER;
    public static final ForgeConfigSpec.DoubleValue SPEARS_COOLDOWN, SPEARS_RANGE, SPEARS_CONE, SPEARS_SPEED, SPEARS_DAMAGE, SPEARS_KNOCKBACK;
    public static final ForgeConfigSpec.IntValue VOLLEY_CAST, VOLLEY_MANA, VOLLEY_SEALS, VOLLEY_PER_TARGET;
    public static final ForgeConfigSpec.DoubleValue VOLLEY_COOLDOWN, VOLLEY_RADIUS, VOLLEY_ARC, VOLLEY_SEAL_RADIUS, VOLLEY_DAMAGE;
    public static final ForgeConfigSpec.IntValue BARRIER_CAST, BARRIER_MANA, BARRIER_SECONDS;
    public static final ForgeConfigSpec.DoubleValue BARRIER_COOLDOWN, BARRIER_RADIUS;
    // [barrier] - both barriers (Barrier spell and the Coven / Closing of Space dome), owner 19.11
    public static final ForgeConfigSpec.BooleanValue BARRIER_KILL_MOBS;
    public static final ForgeConfigSpec.DoubleValue BARRIER_BOSS_PCT;
    // [ember] - T14 forms (manager 19.11)
    public static final ForgeConfigSpec.IntValue EMBER_HITS_TO_BURN, EMBER_HITS_TO_SPECIAL;
    public static final ForgeConfigSpec.IntValue SILENT_PLAYER_AGGRO;
    public static final ForgeConfigSpec.IntValue FLAME_CAST, FLAME_MANA, FLAME_BREATH, FLAME_INTERVAL, FLAME_BURN;
    public static final ForgeConfigSpec.DoubleValue FLAME_COOLDOWN, FLAME_CONE, FLAME_RANGE, FLAME_DAMAGE, FLAME_BURN_DPS;

    // [illusion] - T22 school "Illusions"
    public static final ForgeConfigSpec.DoubleValue IL_RESIST_FLOOR;
    public static final ForgeConfigSpec.IntValue IL_RETURN_TICKS;
    public static final ForgeConfigSpec.IntValue MI_MANA, MI_COPIES, MI_HITS;
    public static final ForgeConfigSpec.DoubleValue MI_COOLDOWN, MI_SECONDS, MI_DAMAGE, MI_DAMAGE_RETURN, MI_SWAP_EVERY, MI_RANGE;
    public static final ForgeConfigSpec.IntValue FS_MANA;
    public static final ForgeConfigSpec.DoubleValue FS_COOLDOWN, FS_SECONDS, FS_DASH;
    public static final ForgeConfigSpec.IntValue VEIL_MANA;
    public static final ForgeConfigSpec.DoubleValue VEIL_COOLDOWN, VEIL_RADIUS, VEIL_SECONDS;
    public static final ForgeConfigSpec.IntValue PP_MANA;
    public static final ForgeConfigSpec.DoubleValue PP_COOLDOWN, PP_RANGE, PP_SECONDS, PP_SHARE;
    public static final ForgeConfigSpec.IntValue BF_MANA;
    public static final ForgeConfigSpec.DoubleValue BF_COOLDOWN, BF_SECONDS, BF_MEMORY;
    public static final ForgeConfigSpec.DoubleValue LAB_RADIUS, LAB_SECONDS, LAB_WALL_DAMAGE, LAB_WALL_RETURN, LAB_PUSH;
    public static final ForgeConfigSpec.DoubleValue NM_RANGE, NM_SECONDS;
    public static final ForgeConfigSpec.DoubleValue BD_RADIUS, BD_SECONDS, BD_COPY_DAMAGE;
    // [nightmare] - T25
    public static final ForgeConfigSpec.DoubleValue IM_DECAY, IM_DAMAGE, IM_RETURN, HOUSE_RANGE, HOUSE_SECONDS, HOUSE_FALL,
            NIGHT_RADIUS, NIGHT_SECONDS, NIGHT_STEP, NA_RADIUS, NA_SECONDS, NA_THICKEN;
    public static final ForgeConfigSpec.IntValue IM_LIMIT_1, IM_LIMIT_2, IM_LIMIT_3, IM_LIMIT_MYTHIC, IM_LIMIT_SERVER, NIGHT_LIGHT;
    // [mythic_t23] - T23 Mythic: World Tree, Abyss Eye, Last Dawn
    public static final ForgeConfigSpec.DoubleValue WT_RANGE, WT_RADIUS, WT_SECONDS, WT_PULL, WT_ROOT_COOLDOWN, WT_CROWN, WT_BLOOM_RADIUS;
    public static final ForgeConfigSpec.IntValue WT_ROOT_HITS;
    public static final ForgeConfigSpec.DoubleValue AE_RADIUS, AE_SECONDS, AE_SANITY, AE_GAZE, AE_GAZE_ANGLE, AE_GAZE_COOLDOWN;
    public static final ForgeConfigSpec.DoubleValue LD_RADIUS, LD_SECONDS, LD_HEAL, LD_BURN, LD_MAGE_WINDOW;

    static {
        ForgeConfigSpec.Builder b = new ForgeConfigSpec.Builder();
        b.comment("T22 school \"Illusions\". Damage is multiplied by the caster's Illusion spell power.",
                "Illusory damage takes health for real, but comes back (smoothly, in returnTicks) if the target lives through the illusion.").push("illusion");
        IL_RESIST_FLOOR = b.comment("Illusion resistance shortens illusions on the victim: time x (2 - resistance), but never below this share").defineInRange("resistFloor", 0.25, 0.0, 1.0);
        IL_RETURN_TICKS = b.comment("Illusory damage comes back over this many ticks").defineInRange("returnTicks", 20, 1, 200);
        b.push("mirror_images");
        MI_MANA = b.comment("Mana cost").defineInRange("mana", 60, 0, 10000);
        MI_COOLDOWN = b.comment("Cooldown (seconds)").defineInRange("cooldown", 30.0, 0.0, 3600.0);
        MI_SECONDS = b.comment("Copies live this long (seconds)").defineInRange("seconds", 20.0, 1.0, 600.0);
        MI_COPIES = b.comment("Copies around the caster").defineInRange("copies", 3, 1, 8);
        MI_HITS = b.comment("Hits a copy takes before it vanishes").defineInRange("hitsToBreak", 3, 1, 20);
        MI_DAMAGE = b.comment("Illusory damage of a copy's strike").defineInRange("copyDamage", 2.0, 0.0, 1000.0);
        MI_DAMAGE_RETURN = b.comment("A copy's illusory damage comes back after this many seconds if the victim lives").defineInRange("copyDamageReturnSeconds", 8.0, 0.5, 600.0);
        MI_SWAP_EVERY = b.comment("The caster swaps places with a random copy about this often (seconds)").defineInRange("swapEverySeconds", 6.0, 0.5, 600.0);
        MI_RANGE = b.comment("Players this close to the caster when it casts (and who come closer later) see the copies").defineInRange("range", 48.0, 4.0, 160.0);
        b.pop();
        b.push("false_step");
        FS_MANA = b.comment("Mana cost").defineInRange("mana", 40, 0, 10000);
        FS_COOLDOWN = b.comment("Cooldown (seconds)").defineInRange("cooldown", 12.0, 0.0, 3600.0);
        FS_SECONDS = b.comment("The caster is gone for enemies this long; the copy runs on meanwhile (seconds)").defineInRange("seconds", 1.5, 0.1, 30.0);
        FS_DASH = b.comment("Dash length (blocks)").defineInRange("dash", 8.0, 0.0, 32.0);
        b.pop();
        b.push("veil");
        VEIL_MANA = b.comment("Mana cost").defineInRange("mana", 70, 0, 10000);
        VEIL_COOLDOWN = b.comment("Cooldown (seconds)").defineInRange("cooldown", 30.0, 0.0, 3600.0);
        VEIL_RADIUS = b.comment("Radius of the haze (blocks)").defineInRange("radius", 6.0, 1.0, 64.0);
        VEIL_SECONDS = b.comment("Lifetime (seconds)").defineInRange("seconds", 10.0, 1.0, 600.0);
        b.pop();
        b.push("phantom_pain");
        PP_MANA = b.comment("Mana cost").defineInRange("mana", 50, 0, 10000);
        PP_COOLDOWN = b.comment("Cooldown (seconds)").defineInRange("cooldown", 20.0, 0.0, 3600.0);
        PP_RANGE = b.comment("Target range (blocks)").defineInRange("range", 24.0, 1.0, 128.0);
        PP_SECONDS = b.comment("Mark lifetime (seconds)").defineInRange("seconds", 6.0, 0.5, 600.0);
        PP_SHARE = b.comment("Every hit on the marked target takes this much more health, as illusory damage (1 = twice as fast)").defineInRange("illusoryShare", 1.0, 0.0, 10.0);
        b.pop();
        b.push("borrowed_face");
        BF_MANA = b.comment("Mana cost").defineInRange("mana", 60, 0, 10000);
        BF_COOLDOWN = b.comment("Cooldown (seconds)").defineInRange("cooldown", 60.0, 0.0, 3600.0);
        BF_SECONDS = b.comment("Disguise lifetime (seconds); an attack or a cast ends it sooner").defineInRange("seconds", 30.0, 1.0, 3600.0);
        BF_MEMORY = b.comment("With no one in sight the caster takes the face of the last player it looked at within this many seconds").defineInRange("memorySeconds", 60.0, 0.0, 3600.0);
        b.pop();
        b.push("mirror_labyrinth");
        LAB_RADIUS = b.comment("Dome radius (blocks)").defineInRange("radius", 14.0, 2.0, 64.0);
        LAB_SECONDS = b.comment("Lifetime (seconds)").defineInRange("seconds", 20.0, 1.0, 600.0);
        LAB_WALL_DAMAGE = b.comment("Illusory damage for walking into a mirror wall").defineInRange("wallDamage", 3.0, 0.0, 1000.0);
        LAB_WALL_RETURN = b.comment("...that comes back after this many seconds").defineInRange("wallDamageReturnSeconds", 10.0, 0.5, 600.0);
        LAB_PUSH = b.comment("Push back out of the wall").defineInRange("push", 0.6, 0.0, 5.0);
        b.pop();
        b.push("waking_nightmare");
        NM_RANGE = b.comment("Target range (blocks)").defineInRange("range", 24.0, 1.0, 128.0);
        NM_SECONDS = b.comment("Lifetime (seconds)").defineInRange("seconds", 12.0, 1.0, 600.0);
        b.pop();
        b.push("butterfly_dream");
        // keys renamed 19.11 (radius 32 -> 64, 25 s -> 120 s): old files get the new values instead of keeping the old ones
        BD_RADIUS = b.comment("Enemies within this radius fall into the dream (blocks)").defineInRange("dreamRadius", 64.0, 2.0, 128.0);
        BD_SECONDS = b.comment("Dream lifetime (seconds)").defineInRange("dreamSeconds", 120.0, 1.0, 600.0);
        BD_COPY_DAMAGE = b.comment("Illusory damage of a dream copy's strike (all damage in the dream is illusory)").defineInRange("copyDamage", 3.0, 0.0, 1000.0);
        b.pop();
        b.pop();
        b.comment("T25 school \"Nightmares\": «Погружение» - the world turns into a nightmare around the victim, only for it (stages 1-3).",
                "Damage is multiplied by the caster's Nightmare spell power.").push("nightmare");
        IM_DECAY = b.comment("A stage falls by one when the victim was not hit by a Nightmare spell for this long (seconds)").defineInRange("stageDecaySeconds", 20.0, 1.0, 600.0);
        IM_LIMIT_1 = b.comment("Nightmares around one victim at stage 1").defineInRange("limitStage1", 2, 0, 64);
        IM_LIMIT_2 = b.comment("... at stage 2").defineInRange("limitStage2", 5, 0, 64);
        IM_LIMIT_3 = b.comment("... at stage 3").defineInRange("limitStage3", 10, 0, 64);
        IM_LIMIT_MYTHIC = b.comment("... in «Пробуждение не наступит» at its deepest").defineInRange("limitMythic", 16, 0, 64);
        IM_LIMIT_SERVER = b.comment("Nightmares on the whole server at once").defineInRange("limitServer", 96, 0, 1000);
        IM_DAMAGE = b.comment("Illusory damage of a hallucination's or a nightmare's strike").defineInRange("illusoryDamage", 3.0, 0.0, 1000.0);
        IM_RETURN = b.comment("...that comes back after this many seconds if the victim lives").defineInRange("illusoryReturnSeconds", 10.0, 0.5, 600.0);
        b.push("house_that_isnt");
        HOUSE_RANGE = b.comment("Target range (blocks)").defineInRange("range", 24.0, 1.0, 128.0);
        HOUSE_SECONDS = b.comment("The victim is in the corridor this long (seconds)").defineInRange("seconds", 60.0, 1.0, 600.0);
        HOUSE_FALL = b.comment("Walking in the corridor the victim cannot step off an edge higher than this (blocks)").defineInRange("maxFall", 3.0, 0.0, 64.0);
        b.pop();
        b.push("endless_night");
        NIGHT_RADIUS = b.comment("Zone radius (blocks)").defineInRange("radius", 24.0, 2.0, 128.0);
        NIGHT_SECONDS = b.comment("Lifetime (seconds)").defineInRange("seconds", 120.0, 1.0, 600.0);
        NIGHT_STEP = b.comment("A victim inside goes one stage deeper this often (seconds)").defineInRange("stageEverySeconds", 8.0, 0.5, 600.0);
        NIGHT_LIGHT = b.comment("Block light at the victim at least this keeps its stage from going deeper").defineInRange("holdingLight", 10, 0, 15);
        b.pop();
        b.push("no_awakening");
        NA_RADIUS = b.comment("Enemies within this radius fall into the nightmare (blocks)").defineInRange("radius", 64.0, 2.0, 128.0);
        NA_SECONDS = b.comment("Lifetime (seconds)").defineInRange("seconds", 300.0, 1.0, 1800.0);
        NA_THICKEN = b.comment("The nightmare thickens one step this often (seconds)").defineInRange("thickenEverySeconds", 60.0, 5.0, 600.0);
        b.pop();
        b.pop();
        b.comment("T23 Mythic spells. Damage is multiplied by the caster's school spell power.").push("mythic_t23");
        b.push("world_tree");
        WT_RANGE = b.comment("The tree grows where the caster looks, up to this far (blocks)").defineInRange("range", 32.0, 4.0, 128.0);
        WT_RADIUS = b.comment("Roots come for enemies within this radius of the trunk (blocks)").defineInRange("radius", 24.0, 2.0, 128.0);
        WT_SECONDS = b.comment("The tree stands this long after the cast (seconds)").defineInRange("seconds", 20.0, 1.0, 600.0);
        WT_PULL = b.comment("A root pulls its victim to the trunk this fast (blocks per tick)").defineInRange("pull", 0.15, 0.0, 2.0);
        WT_ROOT_HITS = b.comment("Hits a root takes before it breaks (fire counts double)").defineInRange("rootHits", 3, 1, 100);
        WT_ROOT_COOLDOWN = b.comment("After a root breaks, a new one comes for that victim no sooner than this (seconds)").defineInRange("rootCooldown", 4.0, 0.0, 600.0);
        WT_CROWN = b.comment("Allies within this radius of the trunk are under the crown: Regeneration II (blocks)").defineInRange("crownRadius", 16.0, 1.0, 128.0);
        WT_BLOOM_RADIUS = b.comment("The bloom's spores: Poison II 6 s and Blindness 3 s to enemies within this radius (blocks)").defineInRange("bloomRadius", 10.0, 1.0, 128.0);
        b.pop();
        b.push("abyss_eye");
        AE_RADIUS = b.comment("Enemy players under the open sky within this radius of the caster (blocks)").defineInRange("radius", 40.0, 2.0, 160.0);
        AE_SECONDS = b.comment("The Eye stays open this long after the cast (seconds)").defineInRange("seconds", 15.0, 1.0, 600.0);
        AE_SANITY = b.comment("Magic damage per second to the exposed").defineInRange("sanityDamage", 1.5, 0.0, 1000.0);
        AE_GAZE = b.comment("Damage for looking at the Eye (and a 1 s freeze)").defineInRange("gazeDamage", 8.0, 0.0, 1000.0);
        AE_GAZE_ANGLE = b.comment("Looking within this angle of the Eye counts as looking at it (degrees)").defineInRange("gazeAngle", 20.0, 1.0, 90.0);
        AE_GAZE_COOLDOWN = b.comment("The gaze strikes the same player no more often than this (seconds)").defineInRange("gazeCooldown", 3.0, 0.0, 600.0);
        b.pop();
        b.push("last_dawn");
        LD_RADIUS = b.comment("Radius of the dawn around the caster (blocks)").defineInRange("radius", 30.0, 2.0, 128.0);
        LD_SECONDS = b.comment("The sun shines this long after the cast (seconds)").defineInRange("seconds", 12.0, 1.0, 600.0);
        LD_HEAL = b.comment("Afterwards allies heal this share of the damage they took in the dawn").defineInRange("healShare", 0.5, 0.0, 10.0);
        LD_BURN = b.comment("Damage per second to the undead and to Blood / Forbidden mages in the light").defineInRange("burnDamage", 1.0, 0.0, 1000.0);
        LD_MAGE_WINDOW = b.comment("A player burns if it cast a Blood or Forbidden spell this recently (seconds)").defineInRange("mageWindow", 30.0, 0.0, 3600.0);
        b.pop();
        b.pop();
        b.push("divine");
        AURA = b.comment("Golden aura around a player casting a Divine-tier scroll").define("aura", true);
        BACKLASH_SECONDS = b.comment("Duration of the Divine Backlash effect after a successful Divine-tier scroll cast (seconds)").defineInRange("backlashSeconds", 60, 1, 3600);
        SLOW_SECONDS = b.comment("Slowness II part, from the start of the effect (seconds, 0 = off)").defineInRange("slowSeconds", 10, 0, 3600);
        WEAK_SECONDS = b.comment("Weakness II part, from the start of the effect (seconds, 0 = off)").defineInRange("weakSeconds", 15, 0, 3600);
        NAUSEA_SECONDS = b.comment("Hidden nausea (no icon) put together with the effect (seconds, 0 = off)").defineInRange("nauseaSeconds", 5, 0, 3600);
        BLOCK_MANA = b.comment("No mana gain of any kind (regeneration, potions) while the effect lasts").define("blockMana", true);
        b.pop();
        b.push("disintegration");
        DIS_PERCENT = b.comment("Damage as a share of the target's max health").defineInRange("damagePercent", 1.0, 0.0, 10.0);
        DIS_FLAT = b.comment("Flat damage added on top").defineInRange("damageFlat", 0.0, 0.0, 100000.0);
        DIS_KILL = b.comment("The target always dies (absorption, resistances and totems do not save it; creative/spectator players are exempt)").define("alwaysKill", true);
        DIS_RANGE = b.comment("Targeting range in blocks").defineInRange("range", 48, 4, 128);
        b.pop();
        b.push("disintegration_replica");
        REPLICA_PERCENT = b.comment("Disintegration: Replica - damage as a share of the target's max health, through armor; never kills (leaves 1 HP)").defineInRange("damagePercent", 0.9, 0.0, 10.0);
        b.pop();
        b.push("higher");
        HIGHER_MULT = b.comment("Damage and healing multiplier for all Higher-school spells").defineInRange("damageMult", 1.0, 0.0, 100.0);
        b.pop();
        b.comment("Silent Witch outfit: hood, robe, robe skirt (T19)").push("silent_witch");
        SW_CAST = b.comment("1. Robe: cast time reduction for every spell (Iron's cast_time_reduction)").defineInRange("castTimeReduction", 0.15, 0.0, 0.9);
        SW_CAST_SILENT = b.comment("1. Robe: total cast time reduction for spells of the Silent school (includes castTimeReduction)").defineInRange("silentCastTimeReduction", 0.25, 0.0, 0.9);
        SW_MUTE_CHANT = b.comment("1. Robe: spells with spoken lines (Replica, Explosion) do not write them to chat").define("muteChants", true);
        SW_MANA_ROBE = b.comment("2. Robe: max mana").defineInRange("maxManaRobe", 100.0, 0.0, 10000.0);
        SW_MANA_HOOD = b.comment("2. Hood: max mana").defineInRange("maxManaHood", 100.0, 0.0, 10000.0);
        SW_REGEN = b.comment("2. Robe + hood: mana regeneration bonus, split equally between the two").defineInRange("manaRegen", 0.25, 0.0, 10.0);
        SW_RESIST = b.comment("3. Skirt + hood: magic resistance (Iron's spell_resist), split equally").defineInRange("spellResist", 0.15, 0.0, 10.0);
        SW_RESIST_SILENT = b.comment("3. Skirt + hood: Silent magic resistance, split equally").defineInRange("silentResist", 0.30, 0.0, 10.0);
        SW_BARRIER_COOLDOWN = b.comment("4. Full set: lethal damage leaves 1 health once per this many seconds").defineInRange("barrierCooldownSeconds", 600, 1, 86400);
        SW_BARRIER_INVUL = b.comment("4. Invulnerability after the barrier saves the wearer (seconds)").defineInRange("barrierInvulnerableSeconds", 3, 0, 60);
        SW_SILENT_STEPS = b.comment("5. Skirt: no step, jump, landing or swim sounds from the wearer").define("silentSteps", true);
        SW_NO_VIBRATIONS = b.comment("5. Skirt: the wearer makes no vibrations (sculk sensors, shriekers, the Warden)").define("noVibrations", true);
        SW_STEALTH_RANGE = b.comment("6. Hood: mobs farther than this do not notice the wearer").defineInRange("stealthRange", 12, 0, 256);
        SW_EXPOSE_SECONDS = b.comment("6. After the wearer attacks or casts, mobs see them normally for this long (seconds)").defineInRange("exposeSeconds", 10, 0, 600);
        SW_TEAM = b.comment("6/11. Also put the wearer in a scoreboard team with nameTagVisibility=never so clients without the mod do not draw the name",
                "(only when the player is in no other team). Off by default (owner 19.11): every wearer lands in ONE team, so minimaps paint",
                "them as teammates (green); and clients without this mod cannot join anyway (the network channel is strict)").define("nameTagTeam", false);
        SW_GATE_SPELL = b.comment("10. The Gate spell id (cast only in the full outfit)").define("gateSpell", "pohsmp_core:silent_gate");
        SW_GATE_MAGIC_IMMUNE = b.comment("10. Full set: no magic damage while casting the Gate").define("gateMagicImmune", true);
        b.pop();
        b.push("silent_gate");
        GATE_AREA = b.comment("Gate: radius of the area the beams hit, under the gate (26 blocks ahead of the caster); owner 19.11: x3").defineInRange("area", 120.0, 2.0, 384.0);
        GATE_RAY_DAMAGE = b.comment("Damage of one volley to a foe (Silent magic: through armor, scaled by Silent spell power, cut by Silent resistance)").defineInRange("rayDamage", 10.0, 0.0, 10000.0);
        GATE_RAY_RADIUS = b.comment("Radius of one ray's hit").defineInRange("rayRadius", 1.5, 0.1, 16.0);
        GATE_AIM_INTERVAL = b.comment("A volley every this many ticks: beams into every foe in the area").defineInRange("volleyInterval", 10, 1, 200);
        GATE_BEAMS_MIN = b.comment("Beams per foe in one volley: from...").defineInRange("beamsMin", 3, 1, 20);
        GATE_BEAMS_MAX = b.comment("...to (the damage counts once per volley)").defineInRange("beamsMax", 5, 1, 20);
        GATE_HIT_COOLDOWN = b.comment("One creature is hit by rays at most once per this many ticks").defineInRange("hitCooldownTicks", 8, 0, 200);
        GATE_SET_BONUS = b.comment("Silent Witch full set (always worn when Gate is cast): ray damage multiplier").defineInRange("setBonus", 1.2, 0.0, 100.0);
        GATE_SILENCE_SECONDS = b.comment("'Silence' after the cast: Gate cannot be cast again for this long (other magic is fine)").defineInRange("silenceSeconds", 180, 0, 86400);
        b.pop();
        b.comment("Silent Witch staff spells: Wind Spears, Silent Volley, Barrier, Black Flame of Worgan.",
                "Damage is multiplied by the caster's Silent spell power (the staff itself gives +25%).").push("silent_staff");
        SILENT_PLAYER_AGGRO = b.comment("Silent Witch magic hurts only hostile creatures; a player counts as hostile to the caster",
                "for this many seconds after hitting the caster (every hit starts it again)").defineInRange("playerAggroSeconds", 60, 0, 3600);
        b.push("wind_spears");
        SPEARS_CAST = b.comment("Cast time (ticks)").defineInRange("castTicks", 20, 0, 1200);
        SPEARS_COOLDOWN = b.comment("Cooldown (seconds)").defineInRange("cooldown", 6.0, 0.0, 3600.0);
        SPEARS_MANA = b.comment("Mana cost").defineInRange("mana", 40, 0, 10000);
        SPEARS_TARGETS = b.comment("Most targets (one spear each)").defineInRange("targets", 5, 1, 32);
        SPEARS_CONE = b.comment("Cone in front of the caster, full angle (degrees)").defineInRange("coneDegrees", 60.0, 1.0, 360.0);
        SPEARS_RANGE = b.comment("Range (blocks)").defineInRange("range", 32.0, 1.0, 128.0);
        SPEARS_HOVER = b.comment("Spears hang over the shoulders before they fly (ticks)").defineInRange("hoverTicks", 10, 0, 200);
        SPEARS_SPEED = b.comment("Spear speed (blocks per tick)").defineInRange("speed", 3.0, 0.1, 16.0);
        SPEARS_DAMAGE = b.comment("Damage of one spear (to the head)").defineInRange("damage", 14.0, 0.0, 10000.0);
        SPEARS_KNOCKBACK = b.comment("Knockback strength").defineInRange("knockback", 0.6, 0.0, 10.0);
        b.pop();
        b.push("silent_volley");
        VOLLEY_CAST = b.comment("Cast time (ticks); the seals appear during it").defineInRange("castTicks", 60, 0, 1200);
        VOLLEY_COOLDOWN = b.comment("Cooldown (seconds)").defineInRange("cooldown", 20.0, 0.0, 3600.0);
        VOLLEY_MANA = b.comment("Mana cost").defineInRange("mana", 100, 0, 10000);
        VOLLEY_SEALS = b.comment("Seals (= arrows)").defineInRange("seals", 24, 1, 128);
        VOLLEY_ARC = b.comment("Arc of the seals behind and to the sides of the caster (degrees)").defineInRange("arcDegrees", 200.0, 10.0, 360.0);
        VOLLEY_SEAL_RADIUS = b.comment("Distance of the seals from the caster (blocks)").defineInRange("sealRadius", 2.5, 0.5, 16.0);
        VOLLEY_RADIUS = b.comment("Enemies within this radius are shot (blocks)").defineInRange("radius", 24.0, 1.0, 128.0);
        VOLLEY_DAMAGE = b.comment("Damage of one arrow").defineInRange("damage", 6.0, 0.0, 10000.0);
        VOLLEY_PER_TARGET = b.comment("Most arrows into one target").defineInRange("perTarget", 6, 1, 128);
        b.pop();
        b.push("sage_barrier");
        BARRIER_CAST = b.comment("Cast time (ticks)").defineInRange("castTicks", 30, 0, 1200);
        BARRIER_COOLDOWN = b.comment("Cooldown (seconds)").defineInRange("cooldown", 40.0, 0.0, 3600.0);
        BARRIER_MANA = b.comment("Mana cost").defineInRange("mana", 120, 0, 10000);
        BARRIER_RADIUS = b.comment("Dome radius (blocks); the dome follows the caster").defineInRange("radius", 5.0, 1.0, 64.0);
        BARRIER_SECONDS = b.comment("Dome lifetime (seconds)").defineInRange("seconds", 8, 1, 3600);
        b.pop();
        b.push("barrier");
        BARRIER_KILL_MOBS = b.comment("Mobs that cross the shell of a barrier die (not players, pets, villagers, golems, CNPC NPCs, allies of the caster,",
                "nor those inside when it rose)").define("killMobs", true);
        BARRIER_BOSS_PCT = b.comment("Bosses are not killed: pushed back off the shell, losing this part of their max health once a second of contact")
                .defineInRange("bossPushDamagePct", 0.2, 0.0, 1.0);
        b.pop();
        b.push("ember");
        EMBER_HITS_TO_BURN = b.comment("Hits of the cold sword that set it burning (form 1). 5 for the Herrscher hits (WOM); 15 if fast dagger hits are used").defineInRange("heatHitsToBurn", 5, 1, 1000);
        EMBER_HITS_TO_SPECIAL = b.comment("Hits of the burning sword that fill the heat for its special attack").defineInRange("hitsToSpecial", 5, 1, 1000);
        b.pop();
        b.push("worgan_flame");
        FLAME_CAST = b.comment("Cast time (ticks); the dragon shadow rises during it").defineInRange("castTicks", 40, 0, 1200);
        FLAME_COOLDOWN = b.comment("Cooldown (seconds)").defineInRange("cooldown", 30.0, 0.0, 3600.0);
        FLAME_MANA = b.comment("Mana cost").defineInRange("mana", 150, 0, 10000);
        FLAME_BREATH = b.comment("Breath duration (ticks)").defineInRange("breathTicks", 60, 1, 1200);
        FLAME_CONE = b.comment("Breath cone, full angle (degrees)").defineInRange("coneDegrees", 40.0, 1.0, 180.0);
        FLAME_RANGE = b.comment("Breath length (blocks)").defineInRange("range", 12.0, 1.0, 64.0);
        FLAME_DAMAGE = b.comment("Damage of one breath hit").defineInRange("damage", 3.0, 0.0, 10000.0);
        FLAME_INTERVAL = b.comment("One breath hit per target every this many ticks").defineInRange("hitInterval", 10, 1, 200);
        FLAME_BURN = b.comment("Black flame burning time (seconds); water does not put it out").defineInRange("burnSeconds", 8, 0, 600);
        FLAME_BURN_DPS = b.comment("Black flame damage per second").defineInRange("burnDamagePerSecond", 1.5, 0.0, 10000.0);
        b.pop();
        b.pop();
        b.push("joint_cast");
        JOINT_SPELLS = b.comment("Joint cast: spells (full ids) two mages can cast together from scrolls. Only long casts (with a cast bar) take part.",
                        "The second mage starts the same spell from a scroll within the window and the radius: both casts end together after",
                        "castTimeMult of the first mage's cast time, the spell takes effect once (from the first mage), the second scroll is spent too.")
                .defineListAllowEmpty(java.util.List.of("spells"), () -> java.util.List.of("pohsmp_core:explosion", "pohsmp_core:heaven_fall",
                        "pohsmp_core:ark", "pohsmp_core:frozen_hour", "pohsmp_core:disintegration"), o -> o instanceof String s && s.contains(":"));
        JOINT_RADIUS = b.comment("Max distance between the two mages (blocks)").defineInRange("radius", 6.0, 1.0, 64.0);
        JOINT_WINDOW = b.comment("The second mage must start within this many seconds of the first one's cast start").defineInRange("windowSeconds", 2.0, 0.05, 30.0);
        JOINT_MULT = b.comment("Cast time of a joint cast as a share of the first mage's cast time").defineInRange("castTimeMult", 0.7, 0.05, 1.0);
        b.pop();
        b.push("countdown");
        COUNTDOWN_MAX = b.comment("Countdown: the repeated hit is capped at this share of the target's max health").defineInRange("maxRepeat", 0.4, 0.0, 100.0);
        b.pop();
        b.push("star_fall");
        STAR_FALL_DAMAGE = b.comment("Star Fall: damage in the centre of the impact (times [higher] damageMult)").defineInRange("damage", 60.0, 0.0, 100000.0);
        STAR_FALL_EDGE = b.comment("Star Fall: share of that damage at the edge of the radius (8 blocks); it falls off linearly from the centre").defineInRange("edgeShare", 0.4, 0.0, 1.0);
        b.pop();
        b.push("scarlet_cut");
        SCARLET_CUTS_MIN = b.comment("Scarlet Cut: fewest cuts in a series").defineInRange("cutsMin", 3, 1, 20);
        SCARLET_CUTS_MAX = b.comment("Most cuts in a series (the count is picked at random between min and max)").defineInRange("cutsMax", 5, 1, 20);
        SCARLET_INTERVAL = b.comment("Ticks between cuts").defineInRange("interval", 4, 1, 40);
        SCARLET_DAMAGE = b.comment("Damage of one cut to everyone it hits (times [higher] damageMult)").defineInRange("damage", 6.0, 0.0, 10000.0);
        SCARLET_WIDTH = b.comment("Width of a cut across the view, blocks").defineInRange("width", 4.0, 0.5, 32.0);
        SCARLET_NEAR = b.comment("A cut hits from this distance in front of the caster...").defineInRange("near", 3.0, 0.0, 32.0);
        SCARLET_FAR = b.comment("...up to this distance, blocks").defineInRange("far", 6.0, 0.5, 64.0);
        SCARLET_CRACK_DELAY = b.comment("Ticks from a cut until its crack bursts (the effect's burst is timed for 20)").defineInRange("crackDelay", 20, 1, 200);
        SCARLET_SHARD_DAMAGE = b.comment("Damage of the crack's burst (times [higher] damageMult)").defineInRange("shardDamage", 4.0, 0.0, 10000.0);
        SCARLET_SHARD_RADIUS = b.comment("The burst hits within this distance of the crack line, blocks").defineInRange("shardRadius", 1.5, 0.1, 16.0);
        SCARLET_KNOCK_UP = b.comment("Upward push of the burst").defineInRange("knockUp", 0.4, 0.0, 5.0);
        b.pop();
        SPEC = b.build();
    }

    private ServerConfig() {}

    /** Value of a server config option, or its default while the config is not loaded (main menu, early tooltips). */
    public static <T> T get(ForgeConfigSpec.ConfigValue<T> v) {
        try {
            return v.get();
        } catch (IllegalStateException e) {
            return v.getDefault();
        }
    }
}
