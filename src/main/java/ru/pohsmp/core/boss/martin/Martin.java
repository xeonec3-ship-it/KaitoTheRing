package ru.pohsmp.core.boss.martin;

import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.MobCategory;
import net.minecraftforge.common.MinecraftForge;
import net.minecraftforge.registries.RegistryObject;
import ru.pohsmp.core.boss.BossDef;
import ru.pohsmp.core.boss.BossNpc;
import ru.pohsmp.core.boss.Bosses;

/**
 * T29 «Мартин, Последний Полководец» (pohsmp_core:martin; docs/specs/tasks/T29_martin_boss.md): definition and registrations.
 * Model ×2 (hitbox 1.4×4.0), three phases («Строй» / «Знамя» 66% / «Последний полководец» 33%), the specials «Приказ стоять насмерть»
 * (50%) and «Атака конницы» (25%) — thresholds from balance_bosses.md [martin] hold_at / cavalry_at, four spells of his own, the
 * finisher; at 5% he blocks the next blow and becomes the peaceful NPC pohsmp_core:martin_npc.
 */
public final class Martin {
    private Martin() {}

    public static final String ID = "martin";
    /** Gold of his title and lines. */
    public static final int COLOR = 0xE8C060;

    public static final BossDef DEF = BossDef.builder(ID)
            .phases(0.66, 0.33)
            .standardBar()
            .color(COLOR)
            .surrender(0.05, ID + "_npc")
            .special("hold_the_line", 0.50)
            .special("cavalry", 0.25)
            .finisher(true)   // owner 20.11: all five finish players off
            .music("music.martin")
            .title("martin")
            .fightRadius(40)
            .build();

    /** Status icons next to the bar (textures/gui/martin/status_*.png): sent as high look bits of the boss (BossCore.lookFlag). */
    public static final int ST_FORMATION = 1 << 8, ST_BANNER = 1 << 9, ST_HOLD = 1 << 10, ST_CAVALRY = 1 << 11, ST_LAST = 1 << 12,
            ST_SHIELD_WALL = 1 << 13, ST_VOLLEY = 1 << 14, ST_DUEL = 1 << 15, ST_WARCRY = 1 << 16;
    /** Bit → icon name, in drawing order. */
    public static final int[] STATUS_BITS = {ST_FORMATION, ST_BANNER, ST_LAST, ST_HOLD, ST_CAVALRY, ST_SHIELD_WALL, ST_VOLLEY, ST_DUEL, ST_WARCRY};
    public static final String[] STATUS_NAMES = {"formation", "banner", "last_warlord", "hold", "cavalry", "shield_wall", "volley", "duel", "warcry"};

    public static RegistryObject<EntityType<MartinEntity>> TYPE;
    public static RegistryObject<EntityType<MartinSoldierEntity>> SOLDIER;
    public static RegistryObject<EntityType<MartinBannerEntity>> BANNER;
    public static RegistryObject<EntityType<BossNpc>> NPC;

    /** Called from Bosses.init before the registers are attached. */
    public static void register() {
        TYPE = Bosses.boss(ID, MartinEntity::new, 1.4f, 4.0f, MartinEntity::attributes);
        SOLDIER = Bosses.living("martin_soldier", MartinSoldierEntity::new, MobCategory.MONSTER, 0.7f, 2.0f, MartinSoldierEntity::attributes);
        BANNER = Bosses.living("martin_banner", MartinBannerEntity::new, MobCategory.MISC, 0.6f, 3.9f, MartinBannerEntity::attributes);
        NPC = Bosses.npc(ID, 1.4f, 4.0f);
    }

    public static void events() {
        MinecraftForge.EVENT_BUS.register(MartinFight.Events.class);
    }
}
