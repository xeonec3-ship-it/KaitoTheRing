package ru.pohsmp.core.boss.irina.client;

import io.redspace.ironsspellbooks.entity.mobs.abstract_spell_casting_mob.AbstractSpellCastingMob;
import io.redspace.ironsspellbooks.entity.mobs.abstract_spell_casting_mob.AbstractSpellCastingMobModel;
import net.minecraft.resources.ResourceLocation;
import ru.pohsmp.core.PohCore;

/**
 * Irina: geo/entity/irina.geo.json (Iron's mage bones + hat, hood, mantle, sleeves, skirt ribbons, threads), textures/entity/irina
 * (the glow mask irina_glowmask.png goes to AutoGlowingGeoLayer by name), animations/entity/irina.animation.json (body + cloth).
 * Iron's model keeps turning the head to the look; her own idle / walk move the limbs (IrinaEntity.isAnimating on the client).
 */
public class IrinaModel extends AbstractSpellCastingMobModel {
    public static final ResourceLocation MODEL = new ResourceLocation(PohCore.MODID, "geo/entity/irina.geo.json");
    public static final ResourceLocation TEXTURE = new ResourceLocation(PohCore.MODID, "textures/entity/irina/irina.png");
    public static final ResourceLocation ANIMATIONS = new ResourceLocation(PohCore.MODID, "animations/entity/irina.animation.json");

    @Override
    public ResourceLocation getModelResource(AbstractSpellCastingMob e) {
        return MODEL;
    }

    @Override
    public ResourceLocation getTextureResource(AbstractSpellCastingMob e) {
        return TEXTURE;
    }

    @Override
    public ResourceLocation getAnimationResource(AbstractSpellCastingMob e) {
        return ANIMATIONS;
    }
}
