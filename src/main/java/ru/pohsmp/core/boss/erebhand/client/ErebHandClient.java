package ru.pohsmp.core.boss.erebhand.client;

import java.util.HashMap;
import java.util.Map;
import net.minecraft.client.Minecraft;
import net.minecraft.client.multiplayer.ClientLevel;
import net.minecraft.client.renderer.entity.EntityRendererProvider;
import net.minecraft.util.Mth;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.client.event.ClientPlayerNetworkEvent;
import net.minecraftforge.client.event.EntityRenderersEvent;
import net.minecraftforge.client.event.RenderPlayerEvent;
import net.minecraftforge.common.MinecraftForge;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import ru.pohsmp.core.boss.BossMath;
import ru.pohsmp.core.boss.client.BossCam;
import ru.pohsmp.core.boss.client.BossCam.Shot;
import ru.pohsmp.core.boss.erebhand.ErebHand;
import ru.pohsmp.core.boss.erebhand.ErebHandEntity;
import ru.pohsmp.core.boss.erebhand.ErebHandMath;
import ru.pohsmp.core.boss.erebhand.ErebHandReflection;

/**
 * T31 client: the renderers (Ereb and his reflections — one look; the giant hand; the mask shards with their players' faces), the false
 * arena of «Длань Лжи» (while this player is held in the giant fist, every other player looks like Ereb to it), the camera plans of the
 * scenes (E — Ereb, «forward» — his look; his body is player-sized: eyes ≈ +1.7, chest ≈ +1.3; the ghost hand over his right shoulder
 * up to ≈ +3.4).
 */
public final class ErebHandClient {
    private ErebHandClient() {}

    @SuppressWarnings({"unchecked", "rawtypes"})
    public static void renderers(EntityRenderersEvent.RegisterRenderers e) {
        e.registerEntityRenderer((EntityType) ErebHand.TYPE.get(), c -> new ErebHandRenderer((EntityRendererProvider.Context) c));
        e.registerEntityRenderer((EntityType) ErebHand.REFLECTION.get(), c -> new ErebHandRenderer((EntityRendererProvider.Context) c));
        e.registerEntityRenderer(ErebHand.GIANT.get(), ErebHandGiantRenderer::new);
        e.registerEntityRenderer(ErebHand.SHARD.get(), ErebHandShardRenderer::new);
        e.registerEntityRenderer(ErebHand.TRAITOR.get(), ErebHandTraitorRenderer::new);
    }

    /** Client setup: camera plans and the false arena events. */
    public static void setup() {
        MinecraftForge.EVENT_BUS.register(ErebHandClient.class);
        plans();
    }

    // ---------------------------------------------------------------- «Длань Лжи»: the false arena (allies drawn as him)

    private static final Map<Integer, ErebHandReflection> DOUBLES = new HashMap<>();
    private static ErebHandEntity liar;

    @SubscribeEvent
    public static void onTick(TickEvent.ClientTickEvent e) {
        if (e.phase != TickEvent.Phase.END) return;
        Minecraft mc = Minecraft.getInstance();
        liar = null;
        if (mc.level == null || mc.player == null) {
            DOUBLES.clear();
            return;
        }
        for (ErebHandEntity b : mc.level.getEntitiesOfClass(ErebHandEntity.class, mc.player.getBoundingBox().inflate(96)))
            if (mc.player.getUUID().equals(b.falseArena())) liar = b;
        if (liar == null) {
            DOUBLES.clear();
            return;
        }
        for (var it = DOUBLES.entrySet().iterator(); it.hasNext(); ) {
            var en = it.next();
            if (!(mc.level.getEntity(en.getKey()) instanceof Player p)) {
                it.remove();
                continue;
            }
            ErebHandReflection d = en.getValue();
            d.tickCount++;
            d.setMask(liar.mask());
            d.setMaskOff(liar.maskOff());
            d.walkAnimation.setSpeed(p.walkAnimation.speed());
            d.walkAnimation.update(p.walkAnimation.speed(), 1);
        }
    }

    @SubscribeEvent
    public static void onRenderPlayer(RenderPlayerEvent.Pre e) {
        Minecraft mc = Minecraft.getInstance();
        Player p = e.getEntity();
        if (liar == null || p == mc.player || !(p.level() instanceof ClientLevel lvl)) return;
        ErebHandReflection d = DOUBLES.computeIfAbsent(p.getId(), k -> ErebHand.REFLECTION.get().create(lvl));
        if (d == null) return;
        e.setCanceled(true);
        float pt = e.getPartialTick();
        d.setPos(p.getX(), p.getY(), p.getZ());
        d.xo = p.xo;
        d.yo = p.yo;
        d.zo = p.zo;
        d.setYRot(p.getYRot());
        d.yRotO = p.yRotO;
        d.setXRot(p.getXRot());
        d.xRotO = p.xRotO;
        d.yBodyRot = p.yBodyRot;
        d.yBodyRotO = p.yBodyRotO;
        d.yHeadRot = p.yHeadRot;
        d.yHeadRotO = p.yHeadRotO;
        d.hurtTime = p.hurtTime;
        d.attackAnim = p.attackAnim;
        d.oAttackAnim = p.oAttackAnim;
        mc.getEntityRenderDispatcher().getRenderer(d).render(d, Mth.lerp(pt, p.yRotO, p.getYRot()), pt, e.getPoseStack(), e.getMultiBufferSource(),
                e.getPackedLight());
    }

    @SubscribeEvent
    public static void onLogout(ClientPlayerNetworkEvent.LoggingOut e) {
        DOUBLES.clear();
        liar = null;
    }

    // ---------------------------------------------------------------- camera plans

    private static double sine(double k) {
        return BossMath.sine(k);
    }

    private static void plans() {
        // «Появление» 5.5 s: the hand forms over his shoulder → he is there → bow → salute (title) → «Вот мы и снова встретились»
        BossCam.plan("ereb_hand.intro", ErebHandMath.INTRO)
                .shot(0, (k, t, c) -> Shot.of(c.orbit(c.focus, 20 + 20 * sine(k), 9, 3.5), c.focus.add(0, 2.6, 0)))
                .shot(ErebHandMath.INTRO_HAND, (k, t, c) -> {   // in on the hand forming over the right shoulder
                    double s = sine(k);
                    return Shot.of(c.orbit(c.focus, 40, 9 - 4 * s, 3.5 - 0.8 * s), c.rel(c.focus, 0.2, -0.5, 3.0));
                })
                .cut(ErebHandMath.INTRO_FORM, (k, t, c) ->   // he stands: front-side, chest; the bow
                        Shot.of(c.orbit(c.focus, 30, 4.8 + 0.8 * sine(BossMath.clamp01((t - ErebHandMath.INTRO_BOW) / 16.0)), 1.6), c.focus.add(0, 1.4, 0)))
                .cut(ErebHandMath.INTRO_TITLE, (k, t, c) -> Shot.of(c.rel(c.focus, 3.6, 0, 0.8), c.focus.add(0, 1.9, 0)))   // salute: low, up at him
                .shot(ErebHandMath.INTRO_SPEAK, (k, t, c) -> Shot.of(c.rel(c.focus, 2.6, 0.3, 1.7), c.focus.add(0, 1.7, 0)));   // the phrase: the half mask

        // «Длань Лжи»: «Длань» to the sky (on him), then from beside the victim up into the sky as the giant hand comes down; extra = victim
        BossCam.plan("ereb_hand.hand_of_lies", ErebHandMath.HOL_CATCH + 14)
                .shot(0, (k, t, c) -> Shot.of(c.orbit(c.b, 25, 3.8, 1.2), c.b.add(0, 2.6 + 0.8 * sine(k), 0)))
                .cut(ErebHandMath.HOL_DESCEND, (k, t, c) -> {
                    Vec3 v = c.extra != null ? c.extra.getPosition(c.pt) : c.focus;
                    double fall = ErebHandMath.giantFall((int) Math.min(ErebHandMath.HOL_FALL, t - ErebHandMath.HOL_DESCEND));
                    double shake = t >= ErebHandMath.HOL_CATCH && t < ErebHandMath.HOL_CATCH + 5 ? 0.3 : 0;
                    return Shot.of(c.orbit(v, 140, 7, 1.2), v.add(0, 2 + fall * 0.7, 0)).shake(shake);
                });

        // «Падение маски» 2 s: the half mask close, the hand tears it off, back out as it bursts
        BossCam.plan("ereb_hand.mask_fall", 40)
                .shot(0, (k, t, c) -> Shot.of(c.rel(c.b, 1.9, 0.25, 1.75), c.b.add(0, 1.72, 0)))
                .shot(ErebHandMath.MASK_TEAR, (k, t, c) -> {
                    double s = sine(k);
                    return Shot.of(c.rel(c.b, 1.9 + 2.4 * s, 0.25, 1.75 + 0.8 * s), c.b.add(0, 1.9 + 0.6 * s, 0)).shake(t < ErebHandMath.MASK_SHATTER + 4 && t >= ErebHandMath.MASK_SHATTER ? 0.15 : 0);
                });

        // «Сон Бабочки: Полное Раскрытие» 4 s: the swarm round him, the hand opens over his head, the white flash on `cast`
        BossCam.plan("ereb_hand.full_reveal", ErebHandMath.REVEAL)
                .shot(0, (k, t, c) -> Shot.of(c.orbit(c.b, 35 * sine(k), 4.5, 1.5), c.b.add(0, 1.5, 0)))
                .shot(ErebHandMath.REVEAL_OPEN, (k, t, c) -> {
                    double s = sine(k);
                    return Shot.of(c.orbit(c.b, 35, 4.5 + 5 * s, 1.5 + 4 * s), c.b.add(0, 2.2 + 1.2 * s, 0));
                });

        // «Ложный рассвет» (⚠ TEMP, till the visual assistant's events): on one knee under a brightening sky, then up and out
        BossCam.plan("ereb_hand.false_dawn", ErebHandMath.DAWN_SCENE)
                .shot(0, (k, t, c) -> Shot.of(c.rel(c.b, 3.2, 0.4, 1.0), c.b.add(0, 1.1, 0)))
                .shot(20, (k, t, c) -> {
                    double s = sine(k);
                    return Shot.of(c.orbit(c.b, 20 * s, 3.2 + 4 * s, 1.0 + 3 * s), c.b.add(0, 1.2 + 2 * s, 0));
                });

        // ложная смерть 5 s: he staggers, the hand breaks, the phrase (close), the bow, the butterflies (out and up)
        BossCam.plan("ereb_hand.false_death", ErebHandMath.DEATH)
                .shot(0, (k, t, c) -> Shot.of(c.orbit(c.b, 20, 4.5, 1.8), c.b.add(0, 2.0, 0)))
                .cut(ErebHandMath.DEATH_SPEAK - 4, (k, t, c) -> Shot.of(c.rel(c.b, 2.4, 0.2, 1.7), c.b.add(0, 1.7, 0)))
                .shot(ErebHandMath.DEATH_SMILE, (k, t, c) -> Shot.of(c.rel(c.b, 3.4, -0.6, 1.5), c.b.add(0, 1.4, 0)))
                .shot(ErebHandMath.DEATH_VANISH - 6, (k, t, c) -> {
                    double s = sine(k);
                    return Shot.of(c.orbit(c.b, -30 * s, 3.4 + 4.5 * s, 1.5 + 3 * s), c.b.add(0, 1.4 + 2.5 * s, 0));
                });

        // the finisher, only the victim's camera: from beside the victim on his face and the hand; a tremble on the squeeze
        BossCam.plan("ereb_hand.finisher", ErebHandMath.FIN_CAM)
                .shot(0, (k, t, c) -> {
                    Vec3 v = c.extra != null ? c.extra.getPosition(c.pt) : c.focus;
                    double shake = t >= ErebHandMath.FIN_SQUEEZE && t < ErebHandMath.FIN_SQUEEZE + 5 ? 0.14 : 0;
                    return Shot.of(c.orbit(v, 75, 2.6 + 0.6 * sine(k), 1.9), c.b.add(0, 2.0, 0)).shake(shake);
                });
    }
}
