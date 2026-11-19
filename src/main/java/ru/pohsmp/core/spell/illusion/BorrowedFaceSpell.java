package ru.pohsmp.core.spell.illusion;

import io.redspace.ironsspellbooks.api.events.SpellPreCastEvent;
import io.redspace.ironsspellbooks.api.magic.MagicData;
import io.redspace.ironsspellbooks.api.spells.CastSource;
import io.redspace.ironsspellbooks.api.spells.CastType;
import io.redspace.ironsspellbooks.api.spells.SpellRarity;
import io.redspace.ironsspellbooks.api.util.AnimationHolder;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.network.chat.Component;
import net.minecraft.network.chat.MutableComponent;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.effect.MobEffectInstance;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.EntityHitResult;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.event.entity.living.LivingAttackEvent;
import net.minecraftforge.event.entity.living.LivingDeathEvent;
import net.minecraftforge.event.entity.player.AttackEntityEvent;
import net.minecraftforge.event.entity.player.PlayerEvent;
import net.minecraftforge.event.server.ServerStoppingEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.network.PacketDistributor;
import ru.pohsmp.core.Reg;
import ru.pohsmp.core.ServerConfig;
import ru.pohsmp.core.fx.Fx;
import ru.pohsmp.core.net.IlluMsg;
import ru.pohsmp.core.net.Net;
import ru.pohsmp.core.spell.CastAnims;
import ru.pohsmp.core.spell.Tasks;

/**
 * T22 «Чужое лицо»: for [borrowed_face] seconds everyone sees the caster as someone else - skin and name over the head of another player,
 * or a mob of its height. Whom: the one the caster looks at when casting (a player, or a mob 1.4-2.3 blocks tall), else the last player it
 * looked at (memorySeconds), else a random player online, else a zombie, skeleton or villager. The face changes on tick 8 of the gesture
 * (fx/illusion_borrowed_face); an attack, a cast, death or the time ends it (fx/illusion_borrowed_face_end).
 * The tab list and chat keep the real name (the owner agreed): only what is seen in the world changes.
 */
public class BorrowedFaceSpell extends IllusionBase {
    public static final String PATH = "borrowed_face";
    private static final List<EntityType<?>> MOBS = List.of(EntityType.ZOMBIE, EntityType.SKELETON, EntityType.VILLAGER);
    private static final int SWAP_TICK = 8;

    public BorrowedFaceSpell() {
        super(PATH, SpellRarity.UNCOMMON, 6, 0, ServerConfig.BF_MANA, ServerConfig.BF_COOLDOWN);
    }

    @Override public CastType getCastType() { return CastType.INSTANT; }
    @Override public AnimationHolder getCastStartAnimation() { return CastAnims.of("illusion_borrowed_face"); }

    @Override
    public List<MutableComponent> getUniqueInfo(int level, LivingEntity caster) {
        return List.of(ui("time", n(seconds(level))));
    }

    private double seconds(int level) {
        return d(ServerConfig.BF_SECONDS) * lv(level, 1, 1.5);
    }

    /** A disguise: the player's face (uuid + name) or a mob type. */
    private record Face(UUID player, String name, String mob, long until, int fxEnd) {}

    private static final Map<UUID, Face> FACES = new HashMap<>();
    /** player -> (who it looked at last, when) */
    private static final Map<UUID, UUID> LAST_SEEN = new HashMap<>();
    private static final Map<UUID, Long> LAST_SEEN_AT = new HashMap<>();
    private static long now;

    @Override
    public void onCast(Level level, int spellLevel, LivingEntity caster, CastSource source, MagicData md) {
        if (level instanceof ServerLevel sl) {
            Face f = pick(sl, caster, (long) Math.round(seconds(spellLevel) * 20));
            fx(sl, Fx.fx("illusion_borrowed_face").at(caster.position()).caster(caster).attach(caster), "illusion_borrowed_face");
            sl.playSound(null, caster.getX(), caster.getY() + 1, caster.getZ(), SoundEvents.AMETHYST_BLOCK_CHIME, SoundSource.PLAYERS, 1f, 0.9f);
            sl.playSound(null, caster.getX(), caster.getY() + 1, caster.getZ(), SoundEvents.ILLUSIONER_PREPARE_MIRROR, SoundSource.PLAYERS, 0.7f, 1.2f);
            UUID id = caster.getUUID();
            int[] t = {0};
            Tasks.add(() -> {   // the face changes on tick 8 of the gesture
                if (++t[0] < SWAP_TICK) return true;
                if (!caster.isAlive() || caster.isRemoved()) return false;
                long until = now + f.until();
                Face on = new Face(f.player(), f.name(), f.mob(), until, 0);
                FACES.put(id, on);
                caster.addEffect(new MobEffectInstance(Reg.BORROWED_FACE.get(), (int) f.until(), 0, false, false, true));
                send(caster, PacketDistributor.TRACKING_ENTITY_AND_SELF.with(() -> caster), on);
                if (caster instanceof ServerPlayer sp) sp.displayClientMessage(Component.translatable("ui.pohsmp_core.borrowed_face.as",
                        on.player() != null ? on.name() : Component.translatable(BuiltInRegistries.ENTITY_TYPE.get(new net.minecraft.resources.ResourceLocation(on.mob())).getDescriptionId()).getString())
                        .withStyle(s -> s.withColor(COLOR)), true);
                return false;
            });
        }
        super.onCast(level, spellLevel, caster, source, md);
    }

    /** Whose face: see the class doc. until = length in ticks here. */
    private static Face pick(ServerLevel sl, LivingEntity caster, long ticks) {
        Entity seen = looked(sl, caster, 24);
        if (seen instanceof ServerPlayer p && p != caster) return new Face(p.getUUID(), p.getGameProfile().getName(), null, ticks, 0);
        if (seen instanceof LivingEntity le && !(seen instanceof Player) && le.getBbHeight() >= 1.4 && le.getBbHeight() <= 2.3)
            return new Face(null, null, BuiltInRegistries.ENTITY_TYPE.getKey(le.getType()).toString(), ticks, 0);
        UUID last = LAST_SEEN.get(caster.getUUID());
        Long at = LAST_SEEN_AT.get(caster.getUUID());
        if (last != null && at != null && now - at <= ticks(ServerConfig.BF_MEMORY)) {
            ServerPlayer p = sl.getServer().getPlayerList().getPlayer(last);
            if (p != null) return new Face(p.getUUID(), p.getGameProfile().getName(), null, ticks, 0);
        }
        List<ServerPlayer> others = new ArrayList<>();
        for (ServerPlayer p : sl.getServer().getPlayerList().getPlayers()) if (p != caster && !p.isSpectator()) others.add(p);
        if (!others.isEmpty()) {
            ServerPlayer p = others.get(caster.getRandom().nextInt(others.size()));
            return new Face(p.getUUID(), p.getGameProfile().getName(), null, ticks, 0);
        }
        EntityType<?> m = MOBS.get(caster.getRandom().nextInt(MOBS.size()));
        return new Face(null, null, BuiltInRegistries.ENTITY_TYPE.getKey(m).toString(), ticks, 0);
    }

    /** The living thing on the caster's line of sight (r blocks, walls stop it). */
    private static Entity looked(ServerLevel sl, LivingEntity caster, double r) {
        Vec3 eye = caster.getEyePosition();
        Vec3 end = eye.add(caster.getLookAngle().scale(r));
        var hr = sl.clip(new net.minecraft.world.level.ClipContext(eye, end, net.minecraft.world.level.ClipContext.Block.COLLIDER,
                net.minecraft.world.level.ClipContext.Fluid.NONE, caster));
        if (hr.getType() != net.minecraft.world.phys.HitResult.Type.MISS) end = hr.getLocation();
        EntityHitResult eh = net.minecraft.world.entity.projectile.ProjectileUtil.getEntityHitResult(sl, caster, eye, end, new AABB(eye, end).inflate(1),
                e -> e instanceof LivingEntity && e != caster && !e.isSpectator() && e.isPickable());
        return eh == null ? null : eh.getEntity();
    }

    private static void send(Entity caster, PacketDistributor.PacketTarget to, Face f) {
        int left = (int) Math.max(1, Math.min(Integer.MAX_VALUE, f.until() - now));
        IlluMsg m = f.player() != null
                ? new IlluMsg(IlluMsg.DISGUISE_PLAYER, caster.getId(), left, 0, f.player(), f.name(), 0, 0, 0, 0, 0)
                : new IlluMsg(IlluMsg.DISGUISE_MOB, caster.getId(), left, 0, null, f.mob(), 0, 0, 0, 0, 0);
        Net.CH.send(to, m);
    }

    /** The disguise falls (attack, cast, time, death). */
    public static void end(LivingEntity caster) {
        Face f = FACES.remove(caster.getUUID());
        if (f == null) return;
        caster.removeEffect(Reg.BORROWED_FACE.get());
        if (caster.isRemoved()) return;
        Net.CH.send(PacketDistributor.TRACKING_ENTITY_AND_SELF.with(() -> caster), IlluMsg.of(IlluMsg.DISGUISE_END, caster.getId(), 0));
        if (caster.level() instanceof ServerLevel sl) {
            fx(sl, Fx.fx("illusion_borrowed_face_end").at(caster.position()).caster(caster).attach(caster), "illusion_borrowed_face_end");
            sl.playSound(null, caster.getX(), caster.getY() + 1, caster.getZ(), SoundEvents.AMETHYST_CLUSTER_BREAK, SoundSource.PLAYERS, 0.8f, 1.4f);
        }
        if (caster instanceof ServerPlayer sp) sp.displayClientMessage(Component.translatable("ui.pohsmp_core.borrowed_face.gone").withStyle(s -> s.withColor(COLOR)), true);
    }

    public static boolean disguised(Entity e) {
        return e != null && FACES.containsKey(e.getUUID());
    }

    public static final class Events {
        private Events() {}

        @SubscribeEvent
        public static void onTick(TickEvent.ServerTickEvent e) {
            if (e.phase != TickEvent.Phase.END) return;
            now++;
            if (now % 10 == 0)   // who each player looks at (for a face when no one is in sight)
                for (ServerPlayer p : e.getServer().getPlayerList().getPlayers()) {
                    Entity seen = looked(p.serverLevel(), p, 32);
                    if (seen instanceof ServerPlayer o) {
                        LAST_SEEN.put(p.getUUID(), o.getUUID());
                        LAST_SEEN_AT.put(p.getUUID(), now);
                    }
                }
            if (FACES.isEmpty()) return;
            for (UUID id : new ArrayList<>(FACES.keySet())) {
                Face f = FACES.get(id);
                ServerPlayer p = e.getServer().getPlayerList().getPlayer(id);
                if (p == null) {
                    if (now >= f.until()) FACES.remove(id);
                    continue;
                }
                if (now >= f.until()) end(p);
            }
        }

        @SubscribeEvent
        public static void onAttack(AttackEntityEvent e) {
            if (!e.getEntity().level().isClientSide && disguised(e.getEntity())) end(e.getEntity());
        }

        @SubscribeEvent
        public static void onHurtOther(LivingAttackEvent e) {
            if (e.getEntity().level().isClientSide) return;
            if (e.getSource().getEntity() instanceof LivingEntity a && a != e.getEntity() && disguised(a)) end(a);
        }

        @SubscribeEvent
        public static void onCast(SpellPreCastEvent e) {
            if (!e.getEntity().level().isClientSide && disguised(e.getEntity())) end(e.getEntity());
        }

        @SubscribeEvent
        public static void onDeath(LivingDeathEvent e) {
            if (!e.getEntity().level().isClientSide && disguised(e.getEntity())) end(e.getEntity());
        }

        /** Someone who starts seeing the caster (walked up, relogged) sees the borrowed face at once. */
        @SubscribeEvent
        public static void onTrack(PlayerEvent.StartTracking e) {
            Face f = FACES.get(e.getTarget().getUUID());
            if (f != null && e.getEntity() instanceof ServerPlayer sp) send(e.getTarget(), PacketDistributor.PLAYER.with(() -> sp), f);
        }

        @SubscribeEvent
        public static void onLogin(PlayerEvent.PlayerLoggedInEvent e) {
            Face f = FACES.get(e.getEntity().getUUID());
            if (f != null && e.getEntity() instanceof ServerPlayer sp) send(sp, PacketDistributor.TRACKING_ENTITY_AND_SELF.with(() -> sp), f);
        }

        @SubscribeEvent
        public static void onLogout(PlayerEvent.PlayerLoggedOutEvent e) {
            LAST_SEEN.remove(e.getEntity().getUUID());
            LAST_SEEN_AT.remove(e.getEntity().getUUID());
        }

        @SubscribeEvent
        public static void onStopping(ServerStoppingEvent e) {
            FACES.clear();
            LAST_SEEN.clear();
            LAST_SEEN_AT.clear();
        }
    }
}
