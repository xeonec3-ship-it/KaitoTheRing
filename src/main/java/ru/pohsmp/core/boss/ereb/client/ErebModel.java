package ru.pohsmp.core.boss.ereb.client;

import io.redspace.ironsspellbooks.entity.mobs.abstract_spell_casting_mob.AbstractSpellCastingMob;
import io.redspace.ironsspellbooks.entity.mobs.abstract_spell_casting_mob.AbstractSpellCastingMobModel;
import net.minecraft.client.Minecraft;
import net.minecraft.resources.ResourceLocation;
import ru.pohsmp.core.PohCore;
import org.joml.Vector2f;
import ru.pohsmp.core.boss.ClothSway;
import ru.pohsmp.core.boss.client.ClothClient;
import ru.pohsmp.core.boss.ereb.ErebBody;
import software.bernie.geckolib.core.animatable.model.CoreGeoBone;
import software.bernie.geckolib.core.animation.AnimationState;

/**
 * Ereb (and his reflections): geo/entity/ereb.geo.json (Iron's casting-mob bones + the four coat tails), textures/entity/ereb/ereb.png
 * (ereb_smile.png while he smiles in the finale), animations/entity/ereb.animation.json (Iron's casting animations + ereb_*). The coat
 * tails follow the legs of Iron's procedural walk (the visual assistant's formula; our ereb_* animations do not touch them).
 */
public class ErebModel extends AbstractSpellCastingMobModel {
    public static final ResourceLocation MODEL = new ResourceLocation(PohCore.MODID, "geo/entity/ereb.geo.json");
    public static final ResourceLocation TEXTURE = new ResourceLocation(PohCore.MODID, "textures/entity/ereb/ereb.png");
    public static final ResourceLocation TEXTURE_SMILE = new ResourceLocation(PohCore.MODID, "textures/entity/ereb/ereb_smile.png");
    public static final ResourceLocation ANIMATIONS = new ResourceLocation(PohCore.MODID, "animations/entity/ereb.animation.json");

    @Override
    public ResourceLocation getModelResource(AbstractSpellCastingMob e) {
        return MODEL;
    }

    @Override
    public ResourceLocation getTextureResource(AbstractSpellCastingMob e) {
        return e instanceof ErebBody b && b.smiling() ? TEXTURE_SMILE : TEXTURE;
    }

    @Override
    public ResourceLocation getAnimationResource(AbstractSpellCastingMob e) {
        return ANIMATIONS;
    }

    @Override
    public void setCustomAnimations(AbstractSpellCastingMob entity, long instanceId, AnimationState<AbstractSpellCastingMob> state) {
        super.setCustomAnimations(entity, instanceId, state);
        if (Minecraft.getInstance().isPaused() || !(entity instanceof ErebBody b) || b.playingAction()) return;
        // GeckoLib axes (mgr_anim_check_T26_T30, 4.2; ClothSway): the back tails follow a leg going back (rotX < 0), the front ones only
        // a leg going forward (rotX > 0) — never through it; their rest angles are in the model. Deltas only, through Iron's
        // transformStack (rest pose again before the next frame): bone.setRotX(getRotX() + …) piled up frame after frame (spinning
        // tails in Iron's casts), and the leg bone did not hold Iron's walk yet — ClothClient adds it.
        Vector2f limb = getLimbSwing(entity, entity.walkAnimation, state.getPartialTick());
        ClothClient.push(transformStack, this::bone, ClothSway.solve(ClothClient.leg(entity, bone("right_leg"), limb, true),
                ClothClient.leg(entity, bone("left_leg"), limb, false)));
    }

    private CoreGeoBone bone(String name) {
        return getAnimationProcessor().getBone(name);
    }

}
