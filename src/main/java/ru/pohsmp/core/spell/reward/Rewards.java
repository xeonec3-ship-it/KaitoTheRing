package ru.pohsmp.core.spell.reward;

import io.redspace.ironsspellbooks.api.spells.AbstractSpell;
import java.util.function.Supplier;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.MobCategory;
import net.minecraftforge.registries.DeferredRegister;
import net.minecraftforge.registries.RegistryObject;
import ru.pohsmp.core.boss.Bosses;

/** T34: registrations of the six boss reward spells (Reg) and the banner soldier (Bosses.init). */
public final class Rewards {
    private Rewards() {}

    public static RegistryObject<EntityType<BannerSoldierEntity>> SOLDIER;

    /** Called from Bosses.init before its entity register is attached. */
    public static void registerEntities() {
        SOLDIER = Bosses.living("warlord_banner_soldier", BannerSoldierEntity::new, MobCategory.MISC, 0.7f, 2.0f, BannerSoldierEntity::attributes);
    }

    /** Called from Reg (static init of the spell register). */
    public static void registerSpells(DeferredRegister<AbstractSpell> spells) {
        reg(spells, RewardMath.ASHEN_HARVEST, AshenHarvestSpell::new);
        reg(spells, RewardMath.JEALOUS_EMBRACE, JealousEmbraceSpell::new);
        reg(spells, RewardMath.ANVIL_STRIKE, AnvilStrikeSpell::new);
        reg(spells, RewardMath.WARLORD_BANNER, WarlordBannerSpell::new);
        reg(spells, RewardMath.MIRROR_STEP, MirrorStepSpell::new);
        reg(spells, RewardMath.HAND_OF_LIES, HandOfLiesSpell::new);
    }

    private static void reg(DeferredRegister<AbstractSpell> spells, String path, Supplier<AbstractSpell> s) {
        spells.register(path, s);
    }
}
