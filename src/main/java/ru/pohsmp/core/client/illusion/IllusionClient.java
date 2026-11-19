package ru.pohsmp.core.client.illusion;

import java.util.HashMap;
import java.util.Map;
import java.util.UUID;
import net.minecraft.client.Minecraft;
import net.minecraft.client.multiplayer.ClientPacketListener;
import net.minecraft.client.multiplayer.PlayerInfo;
import net.minecraft.client.player.AbstractClientPlayer;
import net.minecraft.client.renderer.entity.EntityRenderer;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.util.Mth;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.EquipmentSlot;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.scores.PlayerTeam;
import net.minecraftforge.client.event.RenderNameTagEvent;
import net.minecraftforge.client.event.RenderPlayerEvent;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.event.level.LevelEvent;
import net.minecraftforge.eventbus.api.Event;
import net.minecraftforge.eventbus.api.EventPriority;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import ru.pohsmp.core.net.IlluMsg;

/**
 * T22 "Illusions" on this client: what the server told this player to see falsely.
 * Disguises («Чужое лицо»): a player with another player's face - the tab entry (skin, arms, cape) through AbstractClientPlayerMixin and
 * the name over the head here; or a mob - the player is not drawn, a client-only mob of that type is drawn in its place, moving with it.
 * Copies and zones go to {@link Copies} and {@link Zones}.
 */
public final class IllusionClient {
    private IllusionClient() {}

    private record Disguise(UUID player, String name, EntityType<?> mob, long until) {}

    private static final Map<Integer, Disguise> DISGUISES = new HashMap<>();
    /** client-only mobs standing in for disguised players */
    private static final Map<Integer, LivingEntity> STAND_INS = new HashMap<>();
    private static long now;

    public static long now() {
        return now;
    }

    public static void handle(IlluMsg m) {
        switch (m.kind) {
            case IlluMsg.DISGUISE_PLAYER -> {
                DISGUISES.put(m.entity, new Disguise(m.other, m.text, null, now + m.ticks));
                STAND_INS.remove(m.entity);
            }
            case IlluMsg.DISGUISE_MOB -> {
                EntityType<?> t = BuiltInRegistries.ENTITY_TYPE.getOptional(ResourceLocation.tryParse(m.text)).orElse(EntityType.ZOMBIE);
                DISGUISES.put(m.entity, new Disguise(null, null, t, now + m.ticks));
                STAND_INS.remove(m.entity);
            }
            case IlluMsg.DISGUISE_END -> {
                DISGUISES.remove(m.entity);
                STAND_INS.remove(m.entity);
            }
            case IlluMsg.COPY_SPAWN, IlluMsg.COPY_MOVE, IlluMsg.COPY_HURT, IlluMsg.COPY_GONE -> Copies.handle(m);
            case IlluMsg.ZONE, IlluMsg.ZONE_END -> Zones.handle(m);
            case IlluMsg.FAKE_HP -> ZoneDraw.fakeLoss = Math.max(0, m.x);
            case IlluMsg.ERASED -> ErasedClient.set(m.ticks);
            case IlluMsg.SKY -> ru.pohsmp.core.client.mythic.SkyClient.set(m.i, m.ticks);
            case IlluMsg.ANIM -> {
                var lvl = Minecraft.getInstance().level;
                if (lvl != null && lvl.getEntity(m.entity) instanceof Player p)
                    io.redspace.ironsspellbooks.player.ClientSpellCastHelper.animatePlayerStart(p, new ResourceLocation("irons_spellbooks", m.text));
            }
            default -> {}
        }
    }

    private static Disguise disguise(Entity e) {
        if (DISGUISES.isEmpty() || e == null) return null;
        Disguise d = DISGUISES.get(e.getId());
        return d != null && now < d.until() ? d : null;
    }

    /** The tab entry whose skin this player is drawn with now, or null for its own (AbstractClientPlayerMixin). */
    public static PlayerInfo faceOf(AbstractClientPlayer p) {
        UUID face = Copies.faceOf(p);
        if (face == null) {
            Disguise d = disguise(p);
            if (d == null || d.player() == null) return null;
            face = d.player();
        }
        ClientPacketListener c = Minecraft.getInstance().getConnection();
        return c == null ? null : c.getPlayerInfo(face);
    }

    /** The name over the head: the borrowed one with that player's team colors; a mob shows none. */
    @SubscribeEvent(priority = EventPriority.HIGH)
    public static void onName(RenderNameTagEvent e) {
        Disguise d = disguise(e.getEntity());
        if (d == null) return;
        if (d.mob() != null) {
            e.setResult(Event.Result.DENY);
            return;
        }
        Component name = Component.literal(d.name());
        var lvl = Minecraft.getInstance().level;
        if (lvl != null) {
            PlayerTeam team = lvl.getScoreboard().getPlayersTeam(d.name());
            if (team != null) name = PlayerTeam.formatNameForTeam(team, name);
        }
        e.setContent(name);
    }

    /** A player disguised as a mob: the mob is drawn instead (same place, turn, walk, swing, hurt flash, hand items). */
    @SubscribeEvent(priority = EventPriority.HIGH)
    public static void onRenderPlayer(RenderPlayerEvent.Pre e) {
        Player p = e.getEntity();
        Disguise d = disguise(p);
        if (d == null || d.mob() == null) return;
        LivingEntity mob = standIn(p, d);
        if (mob == null) return;
        e.setCanceled(true);
        @SuppressWarnings("unchecked")
        EntityRenderer<LivingEntity> r = (EntityRenderer<LivingEntity>) Minecraft.getInstance().getEntityRenderDispatcher().getRenderer(mob);
        float pt = e.getPartialTick();
        try {
            r.render(mob, Mth.lerp(pt, mob.yRotO, mob.getYRot()), pt, e.getPoseStack(), e.getMultiBufferSource(), e.getPackedLight());
        } catch (RuntimeException ex) {   // a renderer that cannot draw a mob outside the world: fall back to the player
            STAND_INS.remove(p.getId());
            DISGUISES.put(p.getId(), new Disguise(null, null, EntityType.ZOMBIE, d.until()));
        }
    }

    private static LivingEntity standIn(Player p, Disguise d) {
        LivingEntity mob = STAND_INS.get(p.getId());
        if (mob == null || mob.getType() != d.mob()) {
            Entity made = d.mob().create(p.level());
            if (!(made instanceof LivingEntity le)) return null;
            mob = le;
            mob.setSilent(true);
            STAND_INS.put(p.getId(), mob);
            follow(mob, p);
            mob.xo = p.xo;
            mob.yo = p.yo;
            mob.zo = p.zo;
        }
        return mob;
    }

    /** Puts the stand-in where the player is, as it moves. */
    private static void follow(LivingEntity mob, Player p) {
        mob.xo = mob.getX();
        mob.yo = mob.getY();
        mob.zo = mob.getZ();
        mob.xOld = mob.getX();
        mob.yOld = mob.getY();
        mob.zOld = mob.getZ();
        mob.setPos(p.getX(), p.getY(), p.getZ());
        mob.yRotO = mob.getYRot();
        mob.xRotO = mob.getXRot();
        mob.setYRot(p.getYRot());
        mob.setXRot(p.getXRot());
        mob.yBodyRotO = mob.yBodyRot;
        mob.yBodyRot = p.yBodyRot;
        mob.yHeadRotO = mob.yHeadRot;
        mob.yHeadRot = p.yHeadRot;
        float moved = (float) Mth.length(p.getX() - p.xo, 0, p.getZ() - p.zo);
        mob.walkAnimation.update(Math.min(moved * 4f, 1f), 0.4f);
        mob.oAttackAnim = mob.attackAnim;
        mob.attackAnim = p.attackAnim;
        mob.swinging = p.swinging;
        mob.swingTime = p.swingTime;
        mob.hurtTime = p.hurtTime;
        mob.hurtDuration = p.hurtDuration;
        mob.setShiftKeyDown(p.isShiftKeyDown());
        mob.setOnGround(p.onGround());
        mob.tickCount = p.tickCount;
        mob.setItemSlot(EquipmentSlot.MAINHAND, p.getMainHandItem().copy());
        mob.setItemSlot(EquipmentSlot.OFFHAND, p.getOffhandItem().copy());
    }

    @SubscribeEvent
    public static void onTick(TickEvent.ClientTickEvent e) {
        if (e.phase != TickEvent.Phase.END) return;
        now++;
        var lvl = Minecraft.getInstance().level;
        if (lvl == null) return;
        if (!DISGUISES.isEmpty()) {
            DISGUISES.values().removeIf(d -> now >= d.until());
            STAND_INS.keySet().removeIf(id -> !DISGUISES.containsKey(id));
            STAND_INS.forEach((id, mob) -> {
                if (lvl.getEntity(id) instanceof Player p) follow(mob, p);
            });
        }
        Copies.tick(lvl);
        Zones.tick(lvl);
    }

    @SubscribeEvent
    public static void onUnload(LevelEvent.Unload e) {
        if (!e.getLevel().isClientSide()) return;
        DISGUISES.clear();
        STAND_INS.clear();
        Copies.clear();
        Zones.clear();
        ZoneDraw.clear();
    }
}
