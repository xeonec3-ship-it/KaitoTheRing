package ru.pohsmp.core.spell.illusion;

import io.redspace.ironsspellbooks.api.magic.MagicData;
import io.redspace.ironsspellbooks.api.spells.CastSource;
import io.redspace.ironsspellbooks.api.spells.CastType;
import io.redspace.ironsspellbooks.api.spells.SpellRarity;
import io.redspace.ironsspellbooks.api.util.AnimationHolder;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import net.minecraft.network.chat.MutableComponent;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.event.server.ServerStoppingEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.network.PacketDistributor;
import ru.pohsmp.core.ServerConfig;
import ru.pohsmp.core.fx.Fx;
import ru.pohsmp.core.illusion.Copies;
import ru.pohsmp.core.illusion.Illusions;
import ru.pohsmp.core.net.HideMsg;
import ru.pohsmp.core.net.IlluMsg;
import ru.pohsmp.core.net.Net;
import ru.pohsmp.core.spell.CastAnims;

/**
 * T22 «Пелена»: a haze of [veil] radius where the caster stood, for [veil] seconds. Enemy players inside see the caster and its allies
 * (those inside when it rose) doubled: a false silhouette beside each one moves as it does; strikes at it go through as through air.
 * Now and then the real model is gone for a moment (with a faint ripple) while the false one stays. Only the enemies inside see any of it.
 */
public class VeilSpell extends IllusionBase {
    public static final String PATH = "veil";

    public VeilSpell() {
        super(PATH, SpellRarity.RARE, 5, 0, ServerConfig.VEIL_MANA, ServerConfig.VEIL_COOLDOWN);
    }

    @Override public CastType getCastType() { return CastType.INSTANT; }
    @Override public AnimationHolder getCastStartAnimation() { return CastAnims.of("illusion_veil_cast"); }

    private double seconds(int level) {
        return d(ServerConfig.VEIL_SECONDS) * lv(level, 1, 1.5);
    }

    @Override
    public List<MutableComponent> getUniqueInfo(int level, LivingEntity caster) {
        return List.of(ui("radius", n(d(ServerConfig.VEIL_RADIUS)), n(seconds(level))));
    }

    private static final class Veil {
        final LivingEntity caster;
        final ServerLevel sl;
        final Vec3 c;
        final double r;
        final long until;
        final List<LivingEntity> guarded = new ArrayList<>();
        final List<Copies.Copy> doubles = new ArrayList<>();
        final Set<UUID> inside = new HashSet<>();
        final Map<String, Long> nextFlicker = new HashMap<>();
        int fx = -1;

        Veil(LivingEntity caster, ServerLevel sl, Vec3 c, double r, long until) {
            this.caster = caster;
            this.sl = sl;
            this.c = c;
            this.r = r;
            this.until = until;
        }
    }

    private static final List<Veil> VEILS = new ArrayList<>();

    @Override
    public void onCast(Level level, int spellLevel, LivingEntity caster, CastSource source, MagicData md) {
        if (level instanceof ServerLevel sl) {
            int ticks = (int) Math.round(seconds(spellLevel) * 20);
            double r = d(ServerConfig.VEIL_RADIUS);
            Veil v = new Veil(caster, sl, caster.position(), r, Illusions.now() + ticks);
            v.fx = fx(sl, Fx.fx("illusion_veil").at(v.c).caster(caster).duration(ticks), "illusion_veil");
            sl.playSound(null, v.c.x, v.c.y + 1, v.c.z, SoundEvents.AMETHYST_BLOCK_RESONATE, SoundSource.PLAYERS, 1.2f, 1.4f);
            sl.playSound(null, v.c.x, v.c.y + 1, v.c.z, SoundEvents.ALLAY_AMBIENT_WITHOUT_ITEM, SoundSource.PLAYERS, 0.5f, 0.5f);
            v.guarded.add(caster);
            for (ServerPlayer p : sl.players())
                if (p != caster && !p.isSpectator() && p.position().distanceToSqr(v.c) <= r * r && Illusions.ally(caster, p)) v.guarded.add(p);
            List<ServerPlayer> victims = enemiesInside(v);
            for (LivingEntity g : v.guarded) {
                Vec3 side = Vec3.directionFromRotation(0, g.getYRot() + 90).scale(1.3);
                Copies.Copy d = Copies.spawn(g, Copies.Mode.MIRROR, g.position().add(side), null, ticks, 1, 2, victims);
                d.ghost = true;
                v.doubles.add(d);
            }
            for (ServerPlayer p : victims) enter(v, p);
            VEILS.add(v);
            Illusions.logZone("veil", sl, caster, v.c, r);
        }
        super.onCast(level, spellLevel, caster, source, md);
    }

    private static List<ServerPlayer> enemiesInside(Veil v) {
        List<ServerPlayer> out = new ArrayList<>();
        for (ServerPlayer p : v.sl.players())
            if (!p.isSpectator() && p.position().distanceToSqr(v.c) <= v.r * v.r && !Illusions.ally(v.caster, p)) out.add(p);
        return out;
    }

    private static void enter(Veil v, ServerPlayer p) {
        if (!v.inside.add(p.getUUID())) return;
        int left = (int) Math.max(1, v.until - Illusions.now());
        Net.CH.send(PacketDistributor.PLAYER.with(() -> p), new IlluMsg(IlluMsg.ZONE, v.caster.getId(), left, IlluMsg.Z_VEIL, null, "", v.c.x, v.c.y, v.c.z, (float) v.r, 0));
        for (Copies.Copy d : v.doubles) Copies.show(d, p);
    }

    private static void end(Veil v) {
        for (Copies.Copy d : new ArrayList<>(v.doubles)) Copies.gone(d);
        if (v.fx >= 0) Fx.stop(v.sl, v.fx, "");
        for (UUID id : v.inside) {
            ServerPlayer p = v.sl.getServer().getPlayerList().getPlayer(id);
            if (p == null) continue;
            Net.CH.send(PacketDistributor.PLAYER.with(() -> p), new IlluMsg(IlluMsg.ZONE_END, v.caster.getId(), 0, IlluMsg.Z_VEIL, null, "", 0, 0, 0, 0, 0));
            for (LivingEntity g : v.guarded) Net.CH.send(PacketDistributor.PLAYER.with(() -> p), new HideMsg(g.getId(), 0));
        }
    }

    static {
        Illusions.onDispel(t -> {   // Blessing: the veil is gone for this one (the doubles vanish, the real models come back)
            boolean any = false;
            for (Veil v : VEILS)
                if (v.inside.remove(t.getUUID()) && t instanceof ServerPlayer p) {
                    any = true;
                    Net.CH.send(PacketDistributor.PLAYER.with(() -> p), new IlluMsg(IlluMsg.ZONE_END, v.caster.getId(), 0, IlluMsg.Z_VEIL, null, "", 0, 0, 0, 0, 0));
                    for (LivingEntity g : v.guarded) Net.CH.send(PacketDistributor.PLAYER.with(() -> p), new HideMsg(g.getId(), 0));
                    for (Copies.Copy d : new ArrayList<>(v.doubles)) if (d.victims.contains(p.getUUID())) Copies.gone(d);
                }
            return any;
        });
    }

    public static final class Events {
        private Events() {}

        @SubscribeEvent
        public static void onTick(TickEvent.ServerTickEvent e) {
            if (e.phase != TickEvent.Phase.END || VEILS.isEmpty()) return;
            long now = Illusions.now();
            for (var it = VEILS.iterator(); it.hasNext(); ) {
                Veil v = it.next();
                if (now >= v.until || v.caster.isRemoved()) {
                    end(v);
                    it.remove();
                    continue;
                }
                for (ServerPlayer p : enemiesInside(v)) enter(v, p);
                // the real model is gone for a moment now and then (each viewer, each guarded one on its own)
                for (UUID id : v.inside) {
                    ServerPlayer p = v.sl.getServer().getPlayerList().getPlayer(id);
                    if (p == null || p.level() != v.sl) continue;
                    for (LivingEntity g : v.guarded) {
                        if (!g.isAlive()) continue;
                        String k = id + "/" + g.getId();
                        long at = v.nextFlicker.getOrDefault(k, now + 20 + p.getRandom().nextInt(40));
                        if (!v.nextFlicker.containsKey(k)) v.nextFlicker.put(k, at);
                        if (now < at) continue;
                        int len = 8 + p.getRandom().nextInt(14);
                        Net.CH.send(PacketDistributor.PLAYER.with(() -> p), new HideMsg(g.getId(), len));
                        fx(v.sl, Fx.fx("illusion_veil_flicker").at(g.position()).only(p), "illusion_veil_flicker");
                        v.nextFlicker.put(k, now + len + 30 + p.getRandom().nextInt(50));
                    }
                }
            }
        }

        @SubscribeEvent
        public static void onStopping(ServerStoppingEvent e) {
            VEILS.clear();
        }
    }
}
