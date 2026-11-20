package ru.pohsmp.core.boss.cult.client;

import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.math.Axis;
import io.redspace.ironsspellbooks.entity.mobs.abstract_spell_casting_mob.AbstractSpellCastingMob;
import io.redspace.ironsspellbooks.entity.mobs.abstract_spell_casting_mob.AbstractSpellCastingMobModel;
import io.redspace.ironsspellbooks.entity.mobs.abstract_spell_casting_mob.AbstractSpellCastingMobRenderer;
import net.minecraft.client.Minecraft;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.entity.EntityRenderer;
import net.minecraft.client.renderer.entity.EntityRendererProvider;
import net.minecraft.client.renderer.texture.OverlayTexture;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.item.ItemDisplayContext;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.client.event.EntityRenderersEvent;
import ru.pohsmp.core.PohCore;
import ru.pohsmp.core.boss.BossMath;
import ru.pohsmp.core.boss.client.BossCam;
import ru.pohsmp.core.boss.client.BossCam.Shot;
import ru.pohsmp.core.boss.cult.CultLeader;
import ru.pohsmp.core.boss.cult.CultMath;
import ru.pohsmp.core.boss.cult.CultSickleEntity;
import software.bernie.geckolib.renderer.layer.AutoGlowingGeoLayer;

/**
 * T26 client: renderers (the boss, the fire cultists, the thrown sickle) and the camera plans of the scenes by the seconds of
 * docs/specs/tasks/T26_cult_leader_boss.md «Визуал и ролики» (B — the boss, «forward» — its look, G — the fire gap 6.56 behind it,
 * P — the arena centre; heights for the ×1.75 body: head +3.3…3.7, chest +2.6, hands +1.6…2.0).
 */
public final class CultLeaderClient {
    private CultLeaderClient() {}

    @SuppressWarnings({"unchecked", "rawtypes"})
    public static void renderers(EntityRenderersEvent.RegisterRenderers e) {
        e.registerEntityRenderer((EntityType) CultLeader.TYPE.get(), c -> new CultLeaderRenderer((EntityRendererProvider.Context) c));
        e.registerEntityRenderer((EntityType) CultLeader.CULTIST.get(), c -> new CultistRenderer((EntityRendererProvider.Context) c));
        e.registerEntityRenderer(CultLeader.SICKLE.get(), SickleRenderer::new);
    }

    // ---------------------------------------------------------------- renderers

    /** The fire cultist: Iron's casting mob body with the cult robe (geo/entity/fire_cultist.geo.json) and its glow mask. */
    static final class CultistRenderer extends AbstractSpellCastingMobRenderer {
        CultistRenderer(EntityRendererProvider.Context ctx) {
            super(ctx, new AbstractSpellCastingMobModel() {
                @Override
                public ResourceLocation getModelResource(AbstractSpellCastingMob e) {
                    return new ResourceLocation(PohCore.MODID, "geo/entity/fire_cultist.geo.json");
                }

                @Override
                public ResourceLocation getTextureResource(AbstractSpellCastingMob e) {
                    return new ResourceLocation(PohCore.MODID, "textures/entity/cult_leader/fire_cultist.png");
                }
            });
            addRenderLayer(new AutoGlowingGeoLayer<>(this));
        }
    }

    /** «Огненный серп» in flight: the cult_scythe item, ×1.75 like in his hand, spinning ~40° a tick. */
    static final class SickleRenderer extends EntityRenderer<CultSickleEntity> {
        SickleRenderer(EntityRendererProvider.Context ctx) {
            super(ctx);
        }

        @Override
        public void render(CultSickleEntity e, float yaw, float pt, PoseStack ps, MultiBufferSource buf, int light) {
            ps.pushPose();
            ps.mulPose(Axis.YP.rotationDegrees(-yaw));
            ps.mulPose(Axis.XP.rotationDegrees(90));
            ps.mulPose(Axis.ZP.rotationDegrees((e.tickCount + pt) * 40));
            ps.scale(1.75f, 1.75f, 1.75f);
            Minecraft.getInstance().getItemRenderer().renderStatic(new ItemStack(CultLeader.SCYTHE.get()), ItemDisplayContext.FIXED, 0xF000F0,
                    OverlayTexture.NO_OVERLAY, ps, buf, e.level(), e.getId());
            ps.popPose();
            super.render(e, yaw, pt, ps, buf, light);
        }

        @Override
        public ResourceLocation getTextureLocation(CultSickleEntity e) {
            return new ResourceLocation(PohCore.MODID, "textures/item/cult_scythe_3d.png");
        }
    }

    // ---------------------------------------------------------------- camera plans

    private static double sine(double k) {
        return BossMath.sine(k);
    }

    /** Where the boss's body is seen during the intro walk: from G (6.56 behind) to its place, linear over the 175 ticks (Iron's). */
    private static Vec3 walk(BossCam.Ctx c, double t) {
        Vec3 g = c.focus.subtract(c.fwd.scale(6.56));
        return g.lerp(c.focus, BossMath.clamp01(t / CultMath.INTRO));
    }

    /** The boss's own forward now (it turns during «Пепел»). */
    private static Vec3 fwdNow(BossCam.Ctx c) {
        if (c.boss == null) return c.fwd;
        double a = Math.toRadians(c.boss.getViewYRot(c.pt));
        return new Vec3(-Math.sin(a), 0, Math.cos(a));
    }

    public static void setup() {
        // «Появление» 8.75 s
        BossCam.plan("cult_leader.intro", CultMath.INTRO)
                .shot(0, (k, t, c) -> {   // жар: low by the gap, 30° aside, push 10 → 8
                    Vec3 g = c.focus.subtract(c.fwd.scale(6.56));
                    return Shot.of(c.orbit(g, 30, 10 - 2 * sine(k), 1.5), g.add(0, 1.0, 0));
                })
                .cut(30, (k, t, c) -> {   // стена пламени: wide, 20 before him
                    Vec3 g = c.focus.subtract(c.fwd.scale(6.56));
                    return Shot.of(c.rel(c.focus, 20, 0, 4), g.add(0, 3.5, 0));
                })
                .shot(60, (k, t, c) -> {   // выход: in front, backing 9 → 11 with his steps, on his chest
                    Vec3 v = walk(c, t);
                    return Shot.of(c.rel(v, 9 + 2 * sine(k), 0, 2.2), v.add(0, 2.6, 0));
                })
                .cut(120, (k, t, c) -> {   // взмах косой: from below, front-left, up at the head
                    Vec3 v = walk(c, t);
                    return Shot.of(c.orbit(v, 30, 6, 0.8), v.add(0, 3.5, 0)).shake(t < 126 ? 0.05 : 0);
                })
                .shot(132, (k, t, c) -> {   // титр: rising, 12 in front
                    Vec3 v = walk(c, t);
                    return Shot.of(c.rel(v, 12, 0, 2.4 + 0.8 * sine(k)), v.add(0, 2.8, 0));
                });

        // «Смерть» 3.5 s
        BossCam.plan("cult_leader.death", CultMath.DEATH)
                .shot(0, (k, t, c) -> Shot.of(c.orbit(c.b, 90 + 20 * sine(k), 8, 2.4), c.b.add(0, 2.6, 0)))   // удар: side, slow 20° orbit
                .shot(28, (k, t, c) -> Shot.of(c.orbit(c.b, 35, 6, 1.4), c.b.add(0, 2.8 - 0.9 * sine(k), 0)))   // на колени
                .shot(52, (k, t, c) -> Shot.of(c.orbit(c.b, 35, 6, 1.4), c.b.add(0, 1.9, 0)));   // пламя гаснет, пепел: still

        // «Первое Пламя» 6 s (focus = P)
        BossCam.plan("cult_leader.first_flame", CultMath.FF)
                .shot(0, (k, t, c) -> Shot.of(c.orbit(c.b, 30, 8, 1.6), c.b.add(0, 2.0, 0)))   // коса в землю: on his hands
                .cut(32, (k, t, c) -> Shot.of(c.rel(c.b, -5, 0, 1.6), c.focus.add(0, 20 + 6 * sine(k), 0)))   // снизу на печать
                .cut(60, (k, t, c) -> {   // общий план с высоты, from the players' side; a tremble on the pillar (4.0 s)
                    Vec3 me = Minecraft.getInstance().player != null ? Minecraft.getInstance().player.position() : c.rel(c.focus, 26, 0, 0);
                    Vec3 d = me.subtract(c.focus).multiply(1, 0, 1);
                    d = d.lengthSqr() < 1 ? c.fwd : d.normalize();
                    return Shot.of(c.focus.add(d.scale(26)).add(0, 16, 0), c.focus.add(0, 2, 0)).shake(t >= 80 && t < 88 ? 0.15 : 0);
                });

        // «Пепел Меллисто» ≈6 s (the boss is moved by the server; it faces where it rushes, then along the cut)
        BossCam.plan("cult_leader.ash", CultMath.ASH)
                .shot(0, (k, t, c) -> Shot.of(c.rel(c.b, 5.5, 0, 2.8), c.b.add(0, 3.4, 0)))   // крупно рассыпание
                .shot(24, (k, t, c) -> {   // за вихрем
                    Vec3 f = fwdNow(c);
                    return Shot.of(c.b.subtract(f.scale(9)).add(0, 4, 0), c.b.add(0, 2.8, 0));
                })
                .cut(60, (k, t, c) -> {   // из-за спины, along the line; a tremble on the slash (4.5 s)
                    Vec3 f = fwdNow(c);
                    return Shot.of(c.b.subtract(f.scale(6.5)).add(0, 3.8, 0), c.b.add(f.scale(28)).add(0, 1, 0)).shake(t >= 90 && t < 96 ? 0.12 : 0);
                });

        // the finisher, only the victim's camera (2 s): on the boss's head from beside the victim, rising with it
        BossCam.plan("cult_leader.finisher", CultMath.FINISHER_CAM)
                .shot(0, (k, t, c) -> {
                    Entity v = c.extra;
                    Vec3 head = c.b.add(0, 3.5, 0);
                    if (v == null) return Shot.of(c.rel(c.b, 4.5, 0, 2.2), head);
                    Vec3 vp = v.getPosition(c.pt);
                    Vec3 d = vp.subtract(c.b).multiply(1, 0, 1);
                    d = d.lengthSqr() < 1e-3 ? c.fwd : d.normalize();
                    double a = Math.toRadians(15);
                    Vec3 dd = new Vec3(d.x * Math.cos(a) - d.z * Math.sin(a), 0, d.x * Math.sin(a) + d.z * Math.cos(a));
                    double y = Math.max(vp.y + v.getEyeHeight(), c.b.y + 2.0);
                    Vec3 pos = c.b.add(dd.scale(4.5));
                    return Shot.of(new Vec3(pos.x, y, pos.z), head).shake(t >= 28 && t < 32 ? 0.08 : 0);   // the flame at 1.7 s
                });
    }
}
