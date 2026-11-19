package ru.pohsmp.core.spell;

import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.network.chat.MutableComponent;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.sounds.SoundEvent;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.effect.MobEffect;
import net.minecraft.world.effect.MobEffectCategory;
import net.minecraft.world.effect.MobEffectInstance;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.phys.Vec3;
import ru.pohsmp.core.DivineEvents;
import ru.pohsmp.core.Reg;
import ru.pohsmp.core.fx.Fx;

/**
 * T21 "Blessing" (divine): a 10 s rite on the player the caster looks at (24 blocks), or on the caster when there is nobody. At the end
 * every harmful effect goes (vanilla and modded, Iron's too, the Divine Backlash of the target as well), fire and frost, our marks
 * (Blood Mark, Hemorrhage, Overload, Spores) and the "Soul Seal". Good effects stay. Not taken: the price of "Downfall" (creation_backlash) —
 * a price, not a curse. The caster's own Divine Backlash for a divine scroll comes after the cleansing, as with the other divine spells.
 * Visuals: fx blessing_cast — the manager's; the camera — scene 9.
 */
public class BlessingSpell extends RiteSpell {
    public static final String PATH = "blessing";

    public BlessingSpell() {
        super(PATH, Cutscene.BLESSING, "blessing");
    }

    @Override public Optional<SoundEvent> getCastStartSound() { return Optional.of(SoundEvents.BEACON_ACTIVATE); }
    @Override public Optional<SoundEvent> getCastFinishSound() { return Optional.empty(); }

    @Override
    public List<MutableComponent> getUniqueInfo(int level, LivingEntity caster) {
        return List.of(ui("cast", CAST / 20), ui("target", (int) RANGE), ui("cleanse"), ui("seal"));
    }

    @Override protected int flashTicks() { return 8; }
    @Override protected int flashColor() { return 0xFFF0B0; }

    @Override
    protected boolean canTarget(LivingEntity caster, LivingEntity t) {
        return t instanceof Player p && !p.isSpectator();
    }

    @Override
    protected LivingEntity fallback(LivingEntity caster) {
        return caster;
    }

    @Override
    protected void castTick(ServerLevel sl, Rite r) {
        Vec3 tc = r.target.position().add(0, r.target.getBbHeight() * 0.6, 0);
        switch (r.age) {
            case 1 -> sl.playSound(null, r.caster.getX(), r.caster.getY(), r.caster.getZ(), SoundEvents.AMETHYST_BLOCK_CHIME, SoundSource.PLAYERS, 2f, 0.8f);
            case 40 -> sl.playSound(null, tc.x, tc.y, tc.z, SoundEvents.BEACON_POWER_SELECT, SoundSource.PLAYERS, 2f, 1.2f);
            case 120 -> sl.playSound(null, tc.x, tc.y, tc.z, SoundEvents.ENCHANTMENT_TABLE_USE, SoundSource.PLAYERS, 2f, 1.3f);
            default -> {}
        }
        if (r.age % 40 == 0) sl.playSound(null, tc.x, tc.y, tc.z, SoundEvents.AMETHYST_BLOCK_CHIME, SoundSource.PLAYERS, 1.2f, 1f + r.age / 400f);
        if (r.age % 4 == 0) {   // feathers of light falling over the target
            DivineEvents.particle(sl, ParticleTypes.END_ROD, tc.x, tc.y + 2.5, tc.z, 2, 0.8, 0.01);
            if (r.age >= 120 && r.age < 180) DivineEvents.particle(sl, ParticleTypes.SMOKE, tc.x, tc.y, tc.z, 3, 0.3, 0.04);   // the darkness leaves
        }
    }

    @Override
    protected void apply(ServerLevel sl, LivingEntity caster, LivingEntity t) {
        Vec3 c = t.position().add(0, t.getBbHeight() * 0.6, 0);
        int removed = cleanse(t);
        Fx.play(sl, Fx.fx("blessing_end").at(t.position()).caster(caster).target(t));
        sl.playSound(null, c.x, c.y, c.z, SoundEvents.BELL_BLOCK, SoundSource.PLAYERS, 3f, 1.4f);
        sl.playSound(null, c.x, c.y, c.z, SoundEvents.PLAYER_LEVELUP, SoundSource.PLAYERS, 1.5f, 1.2f);
        DivineEvents.particle(sl, ParticleTypes.END_ROD, c.x, c.y, c.z, 50, 0.6, 0.2);
        if (t instanceof ServerPlayer p)
            p.displayClientMessage(net.minecraft.network.chat.Component.translatable("ui.pohsmp_core.blessing.done", removed).withStyle(s -> s.withColor(Reg.DIVINE_COLOR)), true);
    }

    /** Takes every curse off: harmful effects, fire, frost, our marks, the Soul Seal. Returns how many effects and states went. */
    public static int cleanse(LivingEntity t) {
        int n = 0;
        List<MobEffect> bad = new ArrayList<>();
        for (MobEffectInstance i : t.getActiveEffects())
            if (i.getEffect().getCategory() == MobEffectCategory.HARMFUL && i.getEffect() != Reg.CREATION_BACKLASH.get()) bad.add(i.getEffect());
        for (MobEffect m : bad) if (t.removeEffect(m)) n++;
        if (t.getRemainingFireTicks() > 0) {
            t.clearFire();
            n++;
        }
        if (t.getTicksFrozen() > 0) {
            t.setTicksFrozen(0);
            n++;
        }
        n += Marks.cleanse(t);
        n += ru.pohsmp.core.illusion.Illusions.cleanse(t);   // T22: every illusion and mark of the school, illusory damage comes back
        if (t instanceof ServerPlayer p && SoulSeal.clear(p)) {
            n++;
            p.displayClientMessage(net.minecraft.network.chat.Component.translatable("ui.pohsmp_core.soul_seal.freed").withStyle(s -> s.withColor(Reg.DIVINE_COLOR)), false);
        }
        return n;
    }
}
