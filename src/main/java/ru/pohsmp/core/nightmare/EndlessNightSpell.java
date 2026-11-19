package ru.pohsmp.core.nightmare;

import io.redspace.ironsspellbooks.api.magic.MagicData;
import io.redspace.ironsspellbooks.api.spells.CastSource;
import io.redspace.ironsspellbooks.api.spells.CastType;
import java.util.ArrayList;
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
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.LightLayer;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.event.server.ServerStoppingEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.network.PacketDistributor;
import ru.pohsmp.core.ServerConfig;
import ru.pohsmp.core.fx.Fx;
import ru.pohsmp.core.illusion.Illusions;
import ru.pohsmp.core.net.IlluMsg;
import ru.pohsmp.core.net.Net;

/**
 * T25 «Ночь без рассвета» (Higher): a 3 s cast, then a zone of [endless_night] radius for 2 minutes where the caster stood. Enemies inside
 * have endless night with a red moon (on their own clients) and fall into «Погружение»: stage 1 when they come in, one deeper every
 * [endless_night] seconds. Real light (block light at least [endless_night] holdingLight where they stand) holds their stage.
 * While inside their stage does not fall; after leaving it falls as usual.
 */
public class EndlessNightSpell extends NightmareSpells.Base {
    public static final String PATH = NightmareSpells.NIGHT;
    private static final int CAST = 60;

    public EndlessNightSpell() {
        super(PATH, Rank.HIGHER, CAST);
    }

    @Override public CastType getCastType() { return CastType.LONG; }
    @Override public Optional<SoundEvent> getCastStartSound() { return Optional.of(SoundEvents.WARDEN_HEARTBEAT); }
    @Override public Optional<SoundEvent> getCastFinishSound() { return Optional.empty(); }

    @Override
    public List<MutableComponent> getUniqueInfo(int level, LivingEntity caster) {
        return List.of(ui("zone", n(d(ServerConfig.NIGHT_RADIUS)), n(d(ServerConfig.NIGHT_SECONDS))),
                ui("step", n(d(ServerConfig.NIGHT_STEP))), ui("light", i(ServerConfig.NIGHT_LIGHT)));
    }

    private static final Map<UUID, Integer> CASTING = new HashMap<>();

    @Override
    public void onServerPreCast(Level level, int spellLevel, LivingEntity caster, MagicData md) {
        super.onServerPreCast(level, spellLevel, caster, md);
        if (level instanceof ServerLevel sl)
            CASTING.put(caster.getUUID(), fx(sl, Fx.fx("nightmare_endless_night_cast").at(caster.position()).caster(caster), "nightmare_endless_night_cast"));
    }

    @Override
    public void onServerCastComplete(Level level, int spellLevel, LivingEntity caster, MagicData md, boolean cancelled) {
        Integer f = CASTING.remove(caster.getUUID());
        if (f != null && f >= 0 && cancelled && level instanceof ServerLevel sl) Fx.stop(sl, f, "");
        super.onServerCastComplete(level, spellLevel, caster, md, cancelled);
    }

    private static final class Zone {
        final LivingEntity caster;
        final ServerLevel sl;
        final Vec3 c;
        final double r;
        final long until;
        /** inside -> when it goes one stage deeper */
        final Map<UUID, Long> inside = new HashMap<>();
        /** Blessed here: the night is over for them in this zone */
        final Set<UUID> freed = new HashSet<>();
        int fx = -1;

        Zone(LivingEntity caster, ServerLevel sl, Vec3 c, double r, long until) {
            this.caster = caster;
            this.sl = sl;
            this.c = c;
            this.r = r;
            this.until = until;
        }
    }

    private static final List<Zone> ZONES = new ArrayList<>();

    @Override
    public void onCast(Level level, int spellLevel, LivingEntity caster, CastSource source, MagicData md) {
        if (level instanceof ServerLevel sl) {
            double r = d(ServerConfig.NIGHT_RADIUS);
            int ticks = ticks(ServerConfig.NIGHT_SECONDS);
            Vec3 c = caster.position();
            Zone z = new Zone(caster, sl, c, r, Immersion.now() + ticks);
            z.fx = fx(sl, Fx.fx("nightmare_endless_night").at(c).caster(caster).scale(r / 24.0).duration(ticks), "nightmare_endless_night");
            sl.playSound(null, c.x, c.y + 1, c.z, SoundEvents.WARDEN_HEARTBEAT, SoundSource.PLAYERS, 3f, 0.6f);
            sl.playSound(null, c.x, c.y + 1, c.z, SoundEvents.AMBIENT_CAVE.get(), SoundSource.PLAYERS, 2f, 0.6f);
            ZONES.add(z);
            Illusions.logZone("endless_night", sl, caster, c, r);
        }
        super.onCast(level, spellLevel, caster, source, md);
    }

    private static void night(ServerPlayer p, int ticks) {
        Net.CH.send(PacketDistributor.PLAYER.with(() -> p), new IlluMsg(IlluMsg.NIGHT, p.getId(), ticks, 0, null, "", 0, 0, 0, 0, 0));
    }

    static {
        Illusions.onDispel(t -> {
            boolean any = false;
            for (Zone z : ZONES)
                if (z.inside.remove(t.getUUID()) != null) {
                    z.freed.add(t.getUUID());
                    if (t instanceof ServerPlayer p) night(p, 0);
                    any = true;
                }
            return any;
        });
    }

    public static final class Events {
        private Events() {}

        @SubscribeEvent
        public static void onTick(TickEvent.ServerTickEvent e) {
            if (e.phase != TickEvent.Phase.END || ZONES.isEmpty()) return;
            long now = Immersion.now();
            int step = (int) Math.round(IllusionBaseCfg.step() * 20);
            for (var it = ZONES.iterator(); it.hasNext(); ) {
                Zone z = it.next();
                boolean over = now >= z.until;
                if (!over) {
                    for (ServerPlayer p : z.sl.players()) {
                        UUID id = p.getUUID();
                        boolean in = !p.isSpectator() && !p.isCreative() && p.position().distanceToSqr(z.c) <= z.r * z.r
                                && !Illusions.ally(z.caster, p) && !z.freed.contains(id);
                        Long next = z.inside.get(id);
                        if (in && next == null) {   // walked in
                            z.inside.put(id, now + step);
                            night(p, (int) (z.until - now));
                            if (Immersion.stage(p) < 1) Immersion.deepen(p, 1);
                            else Immersion.touch(p);
                        } else if (!in && next != null) {   // walked out
                            z.inside.remove(id);
                            night(p, 0);
                        } else if (in) {
                            Immersion.touch(p);   // held while inside
                            if (now >= next) {
                                z.inside.put(id, now + step);
                                int light = z.sl.getBrightness(LightLayer.BLOCK, p.blockPosition());
                                if (light < IllusionBaseCfg.light()) Immersion.deepen(p, 1);
                                else p.displayClientMessage(net.minecraft.network.chat.Component.translatable("ui.pohsmp_core.endless_night.held")
                                        .withStyle(s -> s.withColor(0xE8E0D8)), true);
                            }
                        }
                    }
                }
                if (over) {
                    for (UUID id : z.inside.keySet()) {
                        ServerPlayer p = z.sl.getServer().getPlayerList().getPlayer(id);
                        if (p != null) night(p, 0);
                    }
                    if (z.fx >= 0) Fx.stop(z.sl, z.fx, "");
                    it.remove();
                }
            }
        }

        @SubscribeEvent
        public static void onStopping(ServerStoppingEvent e) {
            ZONES.clear();
            CASTING.clear();
        }
    }

    /** The config numbers the static tick reads (the spell's own helpers are instance-side). */
    private static final class IllusionBaseCfg {
        static double step() {
            return ru.pohsmp.core.spell.illusion.IllusionBase.cfg(ServerConfig.NIGHT_STEP::get, 8.0);
        }

        static int light() {
            return ru.pohsmp.core.spell.illusion.IllusionBase.cfg(ServerConfig.NIGHT_LIGHT::get, 10);
        }
    }
}
