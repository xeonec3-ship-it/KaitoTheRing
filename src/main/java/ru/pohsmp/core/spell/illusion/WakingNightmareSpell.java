package ru.pohsmp.core.spell.illusion;

import io.redspace.ironsspellbooks.api.magic.MagicData;
import io.redspace.ironsspellbooks.api.spells.CastSource;
import io.redspace.ironsspellbooks.api.spells.CastType;
import io.redspace.ironsspellbooks.api.util.AnimationHolder;
import io.redspace.ironsspellbooks.api.util.Utils;
import io.redspace.ironsspellbooks.capabilities.magic.TargetEntityCastData;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import net.minecraft.network.chat.MutableComponent;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.sounds.SoundEvent;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.effect.MobEffectInstance;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.AABB;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.event.server.ServerStoppingEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.network.PacketDistributor;
import ru.pohsmp.core.Reg;
import ru.pohsmp.core.SchoolSeals;
import ru.pohsmp.core.ServerConfig;
import ru.pohsmp.core.fx.Fx;
import ru.pohsmp.core.illusion.Illusions;
import ru.pohsmp.core.net.IlluMsg;
import ru.pohsmp.core.net.Net;
import ru.pohsmp.core.spell.CastAnims;

/**
 * T22 «Кошмар наяву» (Higher): a 3.5 s cast at the creature looked at. For [waking_nightmare] seconds (shortened by Illusion resistance)
 * a player target sees every other living thing around - allies, enemies, mobs - as one faceless monster, no names (its own client hides
 * the real models; the server shows it the monster fx/illusion_nightmare_monster on each, only to it). A mob target just loses whom it
 * fights again and again. The mark over the target's head is shown only to the caster and its allies.
 */
public class WakingNightmareSpell extends IllusionBase {
    public static final String PATH = "waking_nightmare";
    private static final int CAST = 70, MONSTERS_R = 40, MONSTERS_MAX = 32, REFRESH = 54;

    public WakingNightmareSpell() {
        super(PATH, Rank.HIGHER, CAST);
    }

    @Override public CastType getCastType() { return CastType.LONG; }
    @Override public AnimationHolder getCastStartAnimation() { return CastAnims.of("illusion_nightmare_cast"); }
    @Override public AnimationHolder getCastFinishAnimation() { return CastAnims.of("illusion_nightmare_finish"); }
    @Override public Optional<SoundEvent> getCastStartSound() { return Optional.of(SoundEvents.SCULK_SHRIEKER_SHRIEK); }
    @Override public Optional<SoundEvent> getCastFinishSound() { return Optional.empty(); }

    @Override
    public List<MutableComponent> getUniqueInfo(int level, LivingEntity caster) {
        return List.of(ui("time", n(d(ServerConfig.NM_SECONDS))));
    }

    @Override
    public boolean checkPreCastConditions(Level level, int spellLevel, LivingEntity entity, MagicData md) {
        return Utils.preCastTargetHelper(level, entity, md, this, (int) d(ServerConfig.NM_RANGE), 0.35f);
    }

    private static final Map<UUID, int[]> CASTING = new HashMap<>();

    @Override
    public void onServerPreCast(Level level, int spellLevel, LivingEntity caster, MagicData md) {
        super.onServerPreCast(level, spellLevel, caster, md);
        if (!(level instanceof ServerLevel sl)) return;
        LivingEntity t = md != null && md.getAdditionalCastData() instanceof TargetEntityCastData td ? td.getTarget(sl) : null;
        Fx.Spec s = Fx.fx("illusion_nightmare_cast").at(caster.position()).caster(caster);
        if (t != null) s = s.target(t);
        int a = fx(sl, s, "illusion_nightmare_cast");
        int b = -1;
        if (!SchoolSeals.shown(caster)) b = fx(sl, Fx.fx("illusion_nightmare_seal").at(caster.position()).caster(caster), "illusion_nightmare_seal");
        CASTING.put(caster.getUUID(), new int[] {a, b});
    }

    @Override
    public void onServerCastComplete(Level level, int spellLevel, LivingEntity caster, MagicData md, boolean cancelled) {
        int[] f = CASTING.remove(caster.getUUID());
        if (f != null && level instanceof ServerLevel sl) {
            if (cancelled && f[0] >= 0) Fx.stop(sl, f[0], "");
            if (f[1] >= 0) Fx.stop(sl, f[1], "");
        }
        super.onServerCastComplete(level, spellLevel, caster, md, cancelled);
    }

    private static final class Dream {
        final LivingEntity caster, target;
        final ServerLevel sl;
        final long until;
        final List<Integer> marks = new ArrayList<>();
        final Map<Integer, Integer> monsters = new HashMap<>();
        long nextRefresh;

        Dream(LivingEntity caster, LivingEntity target, ServerLevel sl, long until) {
            this.caster = caster;
            this.target = target;
            this.sl = sl;
            this.until = until;
        }
    }

    private static final Map<UUID, Dream> DREAMS = new HashMap<>();

    @Override
    public void onCast(Level level, int spellLevel, LivingEntity caster, CastSource source, MagicData md) {
        if (level instanceof ServerLevel sl)   // owner 19.11: «Кошмар наяву» did not work on a player - what the cast had
            ru.pohsmp.core.PohCore.LOG.info("[pohsmp] waking_nightmare by {}: data={} target={}", caster.getName().getString(),
                    md == null ? null : md.getAdditionalCastData(),
                    md != null && md.getAdditionalCastData() instanceof TargetEntityCastData td0 && td0.getTarget(sl) != null
                            ? td0.getTarget(sl).getName().getString() + " ally=" + Illusions.ally(caster, td0.getTarget(sl)) : "none");
        if (level instanceof ServerLevel sl && md.getAdditionalCastData() instanceof TargetEntityCastData td) {
            LivingEntity t = td.getTarget(sl);
            if (t != null && t.isAlive() && !Illusions.ally(caster, t)) start(sl, caster, t, Illusions.duration(t, ticks(ServerConfig.NM_SECONDS)));
        }
        super.onCast(level, spellLevel, caster, source, md);
    }

    private static void start(ServerLevel sl, LivingEntity caster, LivingEntity t, int ticks) {
        Dream old = DREAMS.remove(t.getUUID());
        if (old != null) end(old);
        Dream d = new Dream(caster, t, sl, Illusions.now() + ticks);
        // the mark: only the caster and its allies see it (manager's decision 3)
        for (ServerPlayer p : sl.players())
            if (p == caster || (Illusions.ally(caster, p) && p.distanceToSqr(t) < 96 * 96)) {
                int m = fx(sl, Fx.fx("illusion_nightmare_mark").at(t.position()).target(t).caster(t).attach(t).duration(ticks).only(p), "illusion_nightmare_mark");
                if (m >= 0) d.marks.add(m);
            }
        t.addEffect(new MobEffectInstance(Reg.WAKING_NIGHTMARE.get(), ticks, 0, false, false, true));
        sl.playSound(null, t.getX(), t.getY() + 1, t.getZ(), SoundEvents.WARDEN_HEARTBEAT, SoundSource.PLAYERS, 1.5f, 0.7f);
        if (t instanceof ServerPlayer p)
            Net.CH.send(PacketDistributor.PLAYER.with(() -> p), new IlluMsg(IlluMsg.ZONE, caster.getId(), ticks, IlluMsg.Z_NIGHTMARE, null, "",
                    t.getX(), t.getY(), t.getZ(), MONSTERS_R, 0));
        DREAMS.put(t.getUUID(), d);
    }

    private static void end(Dream d) {
        for (int m : d.marks) Fx.stop(d.sl, m, "");
        for (int m : d.monsters.values()) Fx.stop(d.sl, m, "");
        d.monsters.clear();
        d.target.removeEffect(Reg.WAKING_NIGHTMARE.get());
        if (d.target instanceof ServerPlayer p)
            Net.CH.send(PacketDistributor.PLAYER.with(() -> p), new IlluMsg(IlluMsg.ZONE_END, d.caster.getId(), 0, IlluMsg.Z_NIGHTMARE, null, "", 0, 0, 0, 0, 0));
    }

    /** A faceless monster on every living thing round the victim, only for the victim (refreshed, as the fx lives 60 ticks). */
    private static void monsters(Dream d, ServerPlayer p) {
        for (int m : d.monsters.values()) Fx.stop(d.sl, m, "");
        d.monsters.clear();
        List<LivingEntity> near = d.sl.getEntitiesOfClass(LivingEntity.class, new AABB(p.blockPosition()).inflate(MONSTERS_R),
                e -> e != p && e.isAlive() && !e.isInvisible() && !(e instanceof net.minecraft.world.entity.decoration.ArmorStand));
        near.sort((a, b) -> Double.compare(a.distanceToSqr(p), b.distanceToSqr(p)));
        for (LivingEntity e : near.subList(0, Math.min(MONSTERS_MAX, near.size()))) {
            int m = fx(d.sl, Fx.fx("illusion_nightmare_monster").at(e.position()).caster(e).attach(e).scale(e.getBbHeight() / 1.95)
                    .duration(REFRESH + 6).only(p), "illusion_nightmare_monster");
            if (m >= 0) d.monsters.put(e.getId(), m);
        }
    }

    static {
        Illusions.onDispel(t -> {
            Dream d = DREAMS.remove(t.getUUID());
            if (d == null) return false;
            end(d);
            return true;
        });
    }

    public static final class Events {
        private Events() {}

        @SubscribeEvent
        public static void onTick(TickEvent.ServerTickEvent e) {
            if (e.phase != TickEvent.Phase.END || DREAMS.isEmpty()) return;
            long now = Illusions.now();
            for (var it = DREAMS.values().iterator(); it.hasNext(); ) {
                Dream d = it.next();
                if (now >= d.until || !d.target.isAlive() || d.target.isRemoved()) {
                    end(d);
                    it.remove();
                    continue;
                }
                if (d.target instanceof ServerPlayer p) {
                    if (now >= d.nextRefresh) {
                        monsters(d, p);
                        d.nextRefresh = now + REFRESH;
                    }
                } else if (d.target instanceof Mob mob && now % 20 == 0) {
                    mob.setTarget(null);   // a mob in a nightmare: everyone is the monster, it cannot hold on to whom it fights
                    mob.getNavigation().stop();
                }
            }
        }

        @SubscribeEvent
        public static void onStopping(ServerStoppingEvent e) {
            DREAMS.clear();
            CASTING.clear();
        }
    }
}
