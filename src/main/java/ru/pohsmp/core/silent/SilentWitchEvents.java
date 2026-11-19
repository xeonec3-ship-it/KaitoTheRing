package ru.pohsmp.core.silent;

import io.redspace.ironsspellbooks.api.events.SpellPreCastEvent;
import io.redspace.ironsspellbooks.api.magic.MagicData;
import io.redspace.ironsspellbooks.damage.SpellDamageSource;
import java.util.HashMap;
import java.util.Map;
import java.util.UUID;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.sounds.SoundEvent;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.tags.DamageTypeTags;
import net.minecraft.world.damagesource.DamageSource;
import net.minecraft.world.effect.MobEffectInstance;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.TamableAnimal;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.Vec3;
import net.minecraft.world.scores.PlayerTeam;
import net.minecraft.world.scores.Scoreboard;
import net.minecraft.world.scores.Team;
import net.minecraftforge.event.PlayLevelSoundEvent;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.event.VanillaGameEvent;
import net.minecraftforge.event.entity.living.LivingAttackEvent;
import net.minecraftforge.event.entity.living.LivingChangeTargetEvent;
import net.minecraftforge.event.entity.living.LivingDeathEvent;
import net.minecraftforge.event.entity.living.LivingHurtEvent;
import net.minecraftforge.event.entity.player.PlayerEvent;
import net.minecraftforge.event.server.ServerStartedEvent;
import net.minecraftforge.eventbus.api.EventPriority;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.network.PacketDistributor;
import ru.pohsmp.core.Reg;
import ru.pohsmp.core.ServerConfig;
import ru.pohsmp.core.fx.Fx;
import ru.pohsmp.core.net.Net;

/**
 * Silent Witch outfit (T19), everything that happens on the server (plus the sound filter, which runs on both sides):
 * 1 mute chants (in the spells), 4 quiet barrier, 5 silent steps and no vibrations, 6 mobs do not notice the wearer from afar,
 * 6/11 name hiding (synced flags, scoreboard team), 8 cast sparks, 10 the Gate bonus.
 */
public final class SilentWitchEvents {
    private SilentWitchEvents() {}

    public static final String TEAM = "pohsmp_silent";
    private static final Map<UUID, Long> EXPOSED_UNTIL = new HashMap<>();
    private static final Map<UUID, Long> INVULNERABLE_UNTIL = new HashMap<>();
    private static final Map<UUID, Integer> CAST_FX = new HashMap<>();

    // ------------------------------------------------------------------ name hiding (6, 11) and cast sparks (8)

    @SubscribeEvent
    public static void onPlayerTick(TickEvent.PlayerTickEvent e) {
        if (e.phase != TickEvent.Phase.END || !(e.player instanceof ServerPlayer sp)) return;
        int f = SilentWitch.flagsOf(sp);
        Integer old = SilentWitch.SERVER.get(sp.getUUID());
        if (old == null || old != f) {
            if (f == 0) SilentWitch.SERVER.remove(sp.getUUID());
            else SilentWitch.SERVER.put(sp.getUUID(), f);
            if ((old == null ? 0 : old) != f) syncAll();
            team(sp, (f & (SilentWitch.NAME_TAG | SilentWitch.NAMELESS)) != 0);
        }
        castSparks(sp);
    }

    private static void syncAll() {
        Net.CH.send(PacketDistributor.ALL.noArg(), new Net.SilentSync(new HashMap<>(SilentWitch.SERVER)));
    }

    /** Vanilla clients (and the name tag even without this mod's client part): a team that never shows name tags. */
    private static void team(ServerPlayer sp, boolean hide) {
        Scoreboard sb = sp.getServer().getScoreboard();
        PlayerTeam cur = sb.getPlayersTeam(sp.getScoreboardName());
        if (hide && ServerConfig.get(ServerConfig.SW_TEAM)) {
            if (cur != null) return;   // never take a player out of a team the server put them in
            PlayerTeam t = sb.getPlayerTeam(TEAM);
            if (t == null) {
                t = sb.addPlayerTeam(TEAM);
                t.setNameTagVisibility(Team.Visibility.NEVER);
            }
            sb.addPlayerToTeam(sp.getScoreboardName(), t);
        } else if (cur != null && TEAM.equals(cur.getName())) {
            sb.removePlayerFromTeam(sp.getScoreboardName(), cur);
        }
    }

    @SubscribeEvent
    public static void onLogin(PlayerEvent.PlayerLoggedInEvent e) {
        if (!(e.getEntity() instanceof ServerPlayer sp)) return;
        SilentWitch.SERVER.remove(sp.getUUID());   // recomputed on the first tick
        team(sp, false);
        Net.CH.send(PacketDistributor.PLAYER.with(() -> sp), new Net.SilentSync(new HashMap<>(SilentWitch.SERVER)));
    }

    @SubscribeEvent
    public static void onLogout(PlayerEvent.PlayerLoggedOutEvent e) {
        UUID id = e.getEntity().getUUID();
        if (e.getEntity() instanceof ServerPlayer sp) team(sp, false);
        EXPOSED_UNTIL.remove(id);
        INVULNERABLE_UNTIL.remove(id);
        Integer fx = CAST_FX.remove(id);
        if (fx != null && e.getEntity().level() instanceof ServerLevel sl) Fx.stop(sl, fx, "");
        if (SilentWitch.SERVER.remove(id) != null) syncAll();
    }

    /** A crash or restart can leave players in the team in scoreboard.dat; they are put back on their first tick. */
    @SubscribeEvent
    public static void onServerStarted(ServerStartedEvent e) {
        SilentWitch.SERVER.clear();
        PlayerTeam t = e.getServer().getScoreboard().getPlayerTeam(TEAM);
        if (t != null) e.getServer().getScoreboard().removePlayerTeam(t);
    }

    /** Effect 8: turquoise sparks circle at the feet while the robe wearer casts. */
    private static void castSparks(ServerPlayer sp) {
        boolean casting = SilentWitch.robe(sp) && MagicData.getPlayerMagicData(sp).isCasting();
        Integer inst = CAST_FX.get(sp.getUUID());
        if (casting && (inst == null || !Fx.running(inst))) {
            CAST_FX.put(sp.getUUID(), Fx.play(sp.serverLevel(), Fx.fx("silent_witch_cast").caster(sp).attach(sp).duration(20 * 600)));
        } else if (!casting && inst != null) {
            CAST_FX.remove(sp.getUUID());
            Fx.stop(sp.serverLevel(), inst, "");
        }
    }

    // ------------------------------------------------------------------ 4. quiet barrier

    @SubscribeEvent(priority = EventPriority.LOW)
    public static void onDeath(LivingDeathEvent e) {
        if (!(e.getEntity() instanceof ServerPlayer sp) || e.isCanceled()) return;
        DamageSource src = e.getSource();
        if (src.is(DamageTypeTags.BYPASSES_INVULNERABILITY)) return;   // /kill and the void still kill
        if (!SilentWitch.fullSet(sp) || sp.hasEffect(Reg.SILENT_BARRIER_COOLDOWN.get())) return;
        e.setCanceled(true);
        sp.setHealth(1.0f);
        sp.clearFire();
        ServerLevel sl = sp.serverLevel();
        int invul = ServerConfig.get(ServerConfig.SW_BARRIER_INVUL) * 20;
        INVULNERABLE_UNTIL.put(sp.getUUID(), sl.getGameTime() + invul);
        sp.invulnerableTime = Math.max(sp.invulnerableTime, invul);
        sp.addEffect(new MobEffectInstance(Reg.SILENT_BARRIER_COOLDOWN.get(), ServerConfig.get(ServerConfig.SW_BARRIER_COOLDOWN) * 20, 0, false, false, true));
        Fx.play(sl, Fx.fx("silent_barrier").caster(sp).attach(sp));
        sl.playSound(null, sp.getX(), sp.getY(), sp.getZ(), SoundEvents.AMETHYST_BLOCK_RESONATE, SoundSource.PLAYERS, 1.2f, 1.4f);
        sl.sendParticles(ParticleTypes.END_ROD, sp.getX(), sp.getY() + 1, sp.getZ(), 30, 0.6, 0.9, 0.6, 0.05);
    }

    @SubscribeEvent(priority = EventPriority.HIGH)
    public static void onAttack(LivingAttackEvent e) {
        LivingEntity v = e.getEntity();
        if (v.level().isClientSide) return;
        if (!e.getSource().is(DamageTypeTags.BYPASSES_INVULNERABILITY)) {
            Long until = INVULNERABLE_UNTIL.get(v.getUUID());
            if (until != null) {
                if (v.level().getGameTime() < until) {
                    e.setCanceled(true);
                    return;
                }
                INVULNERABLE_UNTIL.remove(v.getUUID());
            }
        }
        // 10: no magic damage while casting the Gate in the full set
        if (v instanceof ServerPlayer sp && ServerConfig.get(ServerConfig.SW_GATE_MAGIC_IMMUNE) && isMagic(e.getSource()) && castingGate(sp)) e.setCanceled(true);
    }

    // ------------------------------------------------------------------ 10. the Gate

    public static ResourceLocation gateId() {
        return ResourceLocation.tryParse(ServerConfig.get(ServerConfig.SW_GATE_SPELL));
    }

    public static boolean castingGate(ServerPlayer sp) {
        if (!SilentWitch.fullSet(sp)) return false;
        MagicData md = MagicData.getPlayerMagicData(sp);
        return md.isCasting() && String.valueOf(gateId()).equals(md.getCastingSpellId());
    }

    public static boolean isMagic(DamageSource src) {
        return src instanceof SpellDamageSource || src.is(DamageTypeTags.WITCH_RESISTANT_TO)
                || src.typeHolder().unwrapKey().map(k -> k.location().getPath().endsWith("_magic")).orElse(false);
    }

    @SubscribeEvent
    public static void onHurt(LivingHurtEvent e) {
        if (e.getEntity().level().isClientSide) return;
        Entity atk = e.getSource().getEntity();
        LivingEntity wearer = wearerBehind(atk);
        if (wearer != null) expose(wearer);
        if (atk instanceof LivingEntity le && e.getSource() instanceof SpellDamageSource sds && sds.spell() != null
                && sds.spell().getSpellResource().equals(gateId()) && SilentWitch.fullSet(le))
            e.setAmount(e.getAmount() * (float) (1.0 + ServerConfig.get(ServerConfig.SW_GATE_BONUS)));
    }

    // ------------------------------------------------------------------ 6. mobs do not notice the hooded wearer from afar

    private static LivingEntity wearerBehind(Entity atk) {
        if (atk instanceof LivingEntity le && SilentWitch.hood(le)) return le;
        if (atk instanceof TamableAnimal t && t.getOwner() != null && SilentWitch.hood(t.getOwner())) return t.getOwner();
        return null;
    }

    public static void expose(LivingEntity wearer) {
        EXPOSED_UNTIL.put(wearer.getUUID(), wearer.level().getGameTime() + ServerConfig.get(ServerConfig.SW_EXPOSE_SECONDS) * 20L);
    }

    public static boolean hidden(LivingEntity wearer, Entity from) {
        if (!SilentWitch.hood(wearer)) return false;
        Long until = EXPOSED_UNTIL.get(wearer.getUUID());
        if (until != null && wearer.level().getGameTime() < until) return false;
        double r = ServerConfig.get(ServerConfig.SW_STEALTH_RANGE);
        return from.distanceToSqr(wearer) > r * r;
    }

    @SubscribeEvent
    public static void onChangeTarget(LivingChangeTargetEvent e) {
        if (e.getNewTarget() instanceof Player p && !p.level().isClientSide && hidden(p, e.getEntity())) e.setCanceled(true);
    }

    @SubscribeEvent
    public static void onPreCast(SpellPreCastEvent e) {
        if (!e.getEntity().level().isClientSide && SilentWitch.hood(e.getEntity())) expose(e.getEntity());
    }

    // ------------------------------------------------------------------ 5. silence

    /** No vibrations from the skirt wearer: sculk sensors, shriekers and the Warden do not hear them. */
    @SubscribeEvent
    public static void onGameEvent(VanillaGameEvent e) {
        if (e.getCause() instanceof LivingEntity le && SilentWitch.skirt(le) && ServerConfig.get(ServerConfig.SW_NO_VIBRATIONS)) e.setCanceled(true);
    }

    /**
     * Steps, landings, swimming and splashes of the skirt wearer make no sound for anyone. Player sounds go through Level.playSound
     * at the player's exact position (the server sends them to the others, the wearer's client plays its own), so both sides
     * drop movement sounds that start exactly where a skirt wearer stands.
     */
    @SubscribeEvent
    public static void onSound(PlayLevelSoundEvent.AtPosition e) {
        if (e.getSound() == null || !movementSound(e.getSound().value())) return;
        Level level = e.getLevel();
        if (!level.isClientSide && !ServerConfig.get(ServerConfig.SW_SILENT_STEPS)) return;
        Vec3 at = e.getPosition();
        for (Player p : level.players()) {
            if (Math.abs(p.getX() - at.x) < 1e-4 && Math.abs(p.getY() - at.y) < 1e-4 && Math.abs(p.getZ() - at.z) < 1e-4 && SilentWitch.skirt(p)) {
                e.setCanceled(true);
                return;
            }
        }
    }

    public static boolean movementSound(SoundEvent s) {
        String p = s.getLocation().getPath();
        return p.endsWith(".step") || p.endsWith(".fall") || p.endsWith("small_fall") || p.endsWith("big_fall") || p.contains("swim")
                || p.contains("splash") || p.equals("block.amethyst_block.chime") || p.endsWith(".hit_ground");
    }
}
