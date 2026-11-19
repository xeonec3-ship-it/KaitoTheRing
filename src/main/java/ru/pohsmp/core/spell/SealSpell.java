package ru.pohsmp.core.spell;

import io.redspace.ironsspellbooks.api.magic.MagicData;
import io.redspace.ironsspellbooks.api.spells.CastSource;
import io.redspace.ironsspellbooks.api.spells.CastType;
import io.redspace.ironsspellbooks.api.util.Utils;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.network.chat.MutableComponent;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.sounds.SoundEvent;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.effect.MobEffect;
import net.minecraft.world.effect.MobEffectInstance;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.registries.ForgeRegistries;
import ru.pohsmp.core.DivineEvents;
import ru.pohsmp.core.Reg;
import ru.pohsmp.core.fx.Fx;

/**
 * Rune mage: 1.5 s cast, a circle of 6 runes under the target. For 8 s no Iron's or MNA casting and no drinking.
 * Stepping out of the circle breaks the nearest rune: 6 damage and the target is thrown back inside.
 */
public class SealSpell extends HigherSpell {
    public static final String PATH = "forbidding_seal";
    private static final int CAST = 30, LIFE = 160;
    private static final double R = 2.6, DMG = 6;
    public static final int COLOR = 0xFF3B3B;
    private static final ResourceLocation MNA_SILENCE = new ResourceLocation("mna", "silence");
    private static final Map<UUID, Integer> TELE = new HashMap<>();

    public SealSpell() {
        super(PATH, CAST);
    }

    @Override public CastType getCastType() { return CastType.LONG; }
    @Override public Optional<SoundEvent> getCastStartSound() { return Optional.of(SoundEvents.ENCHANTMENT_TABLE_USE); }
    @Override public Optional<SoundEvent> getCastFinishSound() { return Optional.empty(); }

    @Override
    public List<MutableComponent> getUniqueInfo(int spellLevel, LivingEntity caster) {
        return List.of(ui("silence", LIFE / 20), ui("rune", num(DMG)));
    }

    @Override
    public boolean checkPreCastConditions(Level level, int spellLevel, LivingEntity entity, MagicData md) {
        return Utils.preCastTargetHelper(level, entity, md, this, 24, 0.35f);
    }

    @Override
    public void onServerPreCast(Level level, int spellLevel, LivingEntity entity, MagicData md) {
        super.onServerPreCast(level, spellLevel, entity, md);
        if (!(level instanceof ServerLevel sl)) return;
        LivingEntity t = target(sl, md);
        if (t == null) return;
        Integer old = TELE.put(entity.getUUID(), Fx.play(sl, Fx.fx("higher_seal_cast").at(t.position()).caster(entity).target(t)));
        if (old != null) Fx.stop(sl, old, "");
    }

    @Override
    public void onCast(Level level, int spellLevel, LivingEntity entity, CastSource source, MagicData md) {
        if (level instanceof ServerLevel sl) {
            LivingEntity t = target(sl, md);
            if (t != null && t.isAlive()) seal(sl, entity, t);
        }
        super.onCast(level, spellLevel, entity, source, md);
    }

    @Override
    public void onServerCastComplete(Level level, int spellLevel, LivingEntity entity, MagicData md, boolean cancelled) {
        Integer k = TELE.remove(entity.getUUID());
        if (k != null && level instanceof ServerLevel sl) Fx.stop(sl, k, "");
        super.onServerCastComplete(level, spellLevel, entity, md, cancelled);
    }

    private static void seal(ServerLevel sl, LivingEntity caster, LivingEntity t) {
        Vec3 c = t.position();
        t.removeEffect(Reg.SEAL.get());
        t.addEffect(new MobEffectInstance(Reg.SEAL.get(), LIFE, 0, false, true, true));
        if (ForgeRegistries.MOB_EFFECTS.containsKey(MNA_SILENCE)) {
            MobEffect s = ForgeRegistries.MOB_EFFECTS.getValue(MNA_SILENCE);
            if (s != null) t.addEffect(new MobEffectInstance(s, LIFE, 0, false, false, false));
        }
        // the circle, then one effect per rune (socket, pillar, rune, chain to the target) so a broken rune can be stopped alone
        int ward = Fx.play(sl, Fx.fx("higher_seal").at(c));
        Fx.owner(ward, caster.getUUID());
        int[] runes = new int[6];
        for (int i = 0; i < 6; i++) {
            double a = i * Math.PI / 3;
            runes[i] = Fx.play(sl, Fx.fx("higher_seal_rune_" + i).at(c.add(Math.cos(a) * R, 0, Math.sin(a) * R)).target(t));
            Fx.owner(runes[i], caster.getUUID());
        }
        sl.playSound(null, c.x, c.y, c.z, SoundEvents.BEACON_POWER_SELECT, SoundSource.PLAYERS, 2f, 1.4f);
        sl.playSound(null, c.x, c.y, c.z, SoundEvents.ANVIL_LAND, SoundSource.PLAYERS, 0.7f, 0.6f);
        Tasks.add(new Tasks.Task() {
            int age, mask = 63;

            @Override
            public boolean tick() {
                age++;
                if (!t.isAlive() || t.isRemoved() || t.level() != sl || age >= LIFE || !t.hasEffect(Reg.SEAL.get())) {
                    end();
                    return false;
                }
                if (age % 5 == 0) for (int i = 0; i < 6; i++) if ((mask & (1 << i)) != 0) {
                    double a = i * Math.PI / 3;
                    DivineEvents.particle(sl, ParticleTypes.ENCHANT, c.x + Math.cos(a) * R, c.y + 0.6, c.z + Math.sin(a) * R, 2, 0.1, 0.3);
                }
                double dx = t.getX() - c.x, dz = t.getZ() - c.z;
                if (dx * dx + dz * dz <= R * R && Math.abs(t.getY() - c.y) < 3) return true;
                double ang = Math.atan2(dz, dx);
                int best = -1;
                double bestDiff = 99;
                for (int i = 0; i < 6; i++) {
                    if ((mask & (1 << i)) == 0) continue;
                    double diff = Math.abs(Math.atan2(Math.sin(ang - i * Math.PI / 3), Math.cos(ang - i * Math.PI / 3)));
                    if (diff < bestDiff) {
                        bestDiff = diff;
                        best = i;
                    }
                }
                if (best < 0) return false;
                mask &= ~(1 << best);
                double ra = best * Math.PI / 3, rx = c.x + Math.cos(ra) * R, rz = c.z + Math.sin(ra) * R;
                hurt(sl, caster, t, dmg(DMG));
                Fx.stop(sl, runes[best], "");
                Fx.play(sl, Fx.fx("higher_seal_break").at(new Vec3(rx, c.y, rz)));
                sl.playSound(null, rx, c.y, rz, SoundEvents.GLASS_BREAK, SoundSource.PLAYERS, 1.5f, 0.7f);
                sl.playSound(null, rx, c.y, rz, SoundEvents.ZOMBIE_ATTACK_IRON_DOOR, SoundSource.PLAYERS, 0.8f, 1.2f);
                DivineEvents.particle(sl, ParticleTypes.CRIT, rx, c.y + 0.6, rz, 25, 0.3, 0.3);
                if (t.isAlive()) {
                    double len = Math.sqrt(dx * dx + dz * dz);
                    double back = len < 1e-3 ? 0 : 1.2 / len;
                    place(t, c.x + dx * back, c.y, c.z + dz * back);
                    t.setDeltaMovement(Vec3.ZERO);
                }
                if (mask == 0) {
                    end();
                    return false;
                }
                return true;
            }

            private void end() {
                Fx.stop(sl, ward, "");
                for (int i = 0; i < 6; i++) if ((mask & (1 << i)) != 0) Fx.stop(sl, runes[i], "");
            }
        });
    }
}
