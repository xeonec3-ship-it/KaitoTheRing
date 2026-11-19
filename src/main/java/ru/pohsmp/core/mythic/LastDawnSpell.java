package ru.pohsmp.core.mythic;

import io.redspace.ironsspellbooks.api.registry.SchoolRegistry;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.UUID;
import net.minecraft.network.chat.MutableComponent;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.sounds.SoundEvent;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.effect.MobEffectInstance;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.MobType;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.event.entity.living.LivingDamageEvent;
import net.minecraftforge.event.entity.living.LivingDeathEvent;
import net.minecraftforge.eventbus.api.EventPriority;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import ru.pohsmp.core.Reg;
import ru.pohsmp.core.ServerConfig;
import ru.pohsmp.core.fx.Fx;
import ru.pohsmp.core.net.IlluMsg;
import ru.pohsmp.core.spell.Cutscene;
import ru.pohsmp.core.spell.HigherSpell;

/**
 * T23 «Последний рассвет» (holy, Mythic). 10 s: dawn on the horizon, the sun rises ahead of the caster. Then [last_dawn] seconds within the
 * radius it is day (for the eyes, even at night): the caster and its allies cannot die (health stays at 1 at least), every damage they take
 * is written down and afterwards they heal its share over 2 s. The undead and the players who cast Blood or Forbidden magic lately burn in
 * the light.
 */
public class LastDawnSpell extends MythicT23 {
    public static final String PATH = "last_dawn";
    private static final int CAST = 200, FX_ZONE = 240, HEAL_TICKS = 40, SUN_AHEAD = 42, SUN_UP = 9;

    public LastDawnSpell() {
        super(PATH, SchoolRegistry.HOLY_RESOURCE, CAST, Cutscene.LAST_DAWN);
    }

    @Override public Optional<SoundEvent> getCastStartSound() { return Optional.of(SoundEvents.BEACON_POWER_SELECT); }

    @Override
    public List<MutableComponent> getUniqueInfo(int level, LivingEntity caster) {
        return List.of(castLine(), line("last_dawn.zone", n(d(ServerConfig.LD_RADIUS)), n(d(ServerConfig.LD_SECONDS))),
                line("last_dawn.undying", n(d(ServerConfig.LD_HEAL) * 100)), line("last_dawn.burn"));
    }

    @Override
    protected void aim(ServerLevel sl, LivingEntity caster, Cast c) {
        c.point = caster.position();
    }

    @Override
    protected Vec3 focus(Cast c) {
        return c.point.add(c.dir.scale(SUN_AHEAD)).add(0, SUN_UP, 0);
    }

    @Override
    protected int castFx(ServerLevel sl, LivingEntity caster, Cast c) {
        return Fx.play(sl, Fx.fx("last_dawn_cast").at(c.point).caster(caster).yaw((float) Math.toDegrees(Math.atan2(-c.dir.x, c.dir.z))));
    }

    @Override
    protected void castTick(ServerLevel sl, LivingEntity caster, Cast c) {
        Vec3 p = c.point;
        if (c.age == 20) sl.playSound(null, p.x, p.y + 1, p.z, SoundEvents.BEACON_ACTIVATE, SoundSource.PLAYERS, 3f, 0.6f);
        if (c.age % 40 == 0) sl.playSound(null, p.x, p.y + 1, p.z, SoundEvents.AMETHYST_BLOCK_RESONATE, SoundSource.PLAYERS, 3f, 0.8f + c.age / 400f);
        if (c.age == 150) sl.playSound(null, p.x, p.y + 1, p.z, SoundEvents.BELL_RESONATE, SoundSource.PLAYERS, 4f, 1.2f);
    }

    @Override
    protected void release(ServerLevel sl, LivingEntity caster, Cast c) {
        Dawn z = new Dawn(this, sl, caster, c.point, c.fx);
        Cutscene.flash(sl, c.watchers, 6, 0xFFE9B0);
        sl.playSound(null, c.point.x, c.point.y + 2, c.point.z, SoundEvents.BELL_BLOCK, SoundSource.PLAYERS, 5f, 1.4f);
        for (ServerPlayer p : sl.players())
            if (p.distanceToSqr(c.point) < 64 * 64) sky(p, IlluMsg.SKY_DAWN, z.life);
        ZONES.add(z);
    }

    // ---------------------------------------------------------------- the dawn

    static final class Dawn implements Zone {
        final LastDawnSpell spell;
        final ServerLevel sl;
        final LivingEntity caster;
        final Vec3 c;
        final int castFx, life;
        final double r;
        final Set<UUID> inside = new HashSet<>();
        final Map<UUID, Float> taken = new HashMap<>();
        final Map<UUID, LivingEntity> who = new HashMap<>();
        final Map<UUID, Long> lastFx = new HashMap<>();
        int age;

        Dawn(LastDawnSpell spell, ServerLevel sl, LivingEntity caster, Vec3 c, int castFx) {
            this.spell = spell;
            this.sl = sl;
            this.caster = caster;
            this.c = c;
            this.castFx = castFx;
            this.life = ticks(ServerConfig.LD_SECONDS);
            this.r = d(ServerConfig.LD_RADIUS);
        }

        @Override
        public boolean tick() {
            age++;
            if (age >= life) {
                end();
                return false;
            }
            inside.clear();
            for (LivingEntity a : HigherSpell.around(sl, c, r, e -> ally(caster, e))) {
                inside.add(a.getUUID());
                who.put(a.getUUID(), a);
                if (age % 10 == 1) a.addEffect(new MobEffectInstance(Reg.DAWN_GRACE.get(), 25, 0, false, false, true));
            }
            if (age % 20 == 1) {   // the light burns the undead and the dark mages
                long now = sl.getGameTime(), window = ticks(ServerConfig.LD_MAGE_WINDOW);
                float dmg = (float) (d(ServerConfig.LD_BURN) * spell.mult(caster));
                for (LivingEntity v : HigherSpell.around(sl, c, r, e -> enemy(caster, e))) {
                    boolean dark = v.getMobType() == MobType.UNDEAD
                            || v instanceof Player && now - DARK_CAST.getOrDefault(v.getUUID(), Long.MIN_VALUE / 2) <= window;
                    if (!dark) continue;
                    v.setSecondsOnFire(2);
                    v.invulnerableTime = 0;
                    v.hurt(sl.damageSources().inFire(), dmg);
                    Fx.play(sl, Fx.fx("last_dawn_burn").at(v.position()).caster(v).attach(v));
                }
            }
            return true;
        }

        void end() {
            if (life != FX_ZONE && castFx >= 0) Fx.stop(sl, castFx, "");
            double share = d(ServerConfig.LD_HEAL);
            for (Map.Entry<UUID, Float> en : taken.entrySet()) {
                LivingEntity a = who.get(en.getKey());
                if (a == null || !a.isAlive()) continue;
                float per = (float) (en.getValue() * share / HEAL_TICKS);
                if (per <= 0) continue;
                Fx.play(sl, Fx.fx("last_dawn_heal").at(a.position()).caster(a).attach(a));
                sl.playSound(null, a.getX(), a.getY() + 1, a.getZ(), SoundEvents.PLAYER_LEVELUP, SoundSource.PLAYERS, 0.8f, 1.6f);
                int[] left = {HEAL_TICKS};
                ru.pohsmp.core.spell.Tasks.add(() -> {
                    if (!a.isAlive()) return false;
                    a.heal(per);
                    return --left[0] > 0;
                });
            }
        }

        void guard(LivingDamageEvent e) {
            LivingEntity a = e.getEntity();
            taken.merge(a.getUUID(), e.getAmount(), Float::sum);
            who.put(a.getUUID(), a);
            if (a.getHealth() - e.getAmount() < 1) {
                e.setAmount(Math.max(0, a.getHealth() - 1));
                long now = sl.getGameTime();
                if (now - lastFx.getOrDefault(a.getUUID(), 0L) >= 10) {
                    lastFx.put(a.getUUID(), now);
                    Fx.play(sl, Fx.fx("last_dawn_undying").at(a.position()).caster(a).attach(a));
                    sl.playSound(null, a.getX(), a.getY() + 1, a.getZ(), SoundEvents.TOTEM_USE, SoundSource.PLAYERS, 0.6f, 1.6f);
                }
            }
        }
    }

    private static Dawn shelter(LivingEntity e) {
        for (Zone z : ZONES) if (z instanceof Dawn d && d.inside.contains(e.getUUID()) && e.level() == d.sl) return d;
        return null;
    }

    public static final class Events {
        private Events() {}

        @SubscribeEvent(priority = EventPriority.LOWEST)
        public static void onDamage(LivingDamageEvent e) {
            if (ZONES.isEmpty() || e.getEntity().level().isClientSide) return;
            Dawn d = shelter(e.getEntity());
            if (d != null) d.guard(e);
        }

        @SubscribeEvent(priority = EventPriority.HIGHEST)
        public static void onDeath(LivingDeathEvent e) {
            if (ZONES.isEmpty() || e.getEntity().level().isClientSide) return;
            if (e.getSource().is(net.minecraft.tags.DamageTypeTags.BYPASSES_INVULNERABILITY)) return;   // /kill, the void
            if (shelter(e.getEntity()) != null) {
                e.setCanceled(true);
                e.getEntity().setHealth(1);
            }
        }
    }
}
