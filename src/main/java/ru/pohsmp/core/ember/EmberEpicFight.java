package ru.pohsmp.core.ember;

import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ItemStack;
import net.minecraftforge.eventbus.api.IEventBus;
import net.minecraftforge.fml.ModList;
import ru.pohsmp.core.PohCore;
import yesman.epicfight.api.animation.AnimationManager.AnimationAccessor;
import yesman.epicfight.api.animation.AnimationManager.AnimationBuilder;
import yesman.epicfight.api.animation.AnimationManager.AnimationRegistryEvent;
import yesman.epicfight.api.animation.AnimationPlayer;
import yesman.epicfight.api.animation.LivingMotions;
import yesman.epicfight.api.animation.property.AnimationProperty.ActionAnimationProperty;
import yesman.epicfight.api.animation.property.AnimationProperty.AttackAnimationProperty;
import yesman.epicfight.api.animation.types.ActionAnimation;
import yesman.epicfight.api.animation.types.AttackAnimation;
import yesman.epicfight.api.animation.types.BasicAttackAnimation;
import yesman.epicfight.api.animation.types.MovementAnimation;
import yesman.epicfight.api.animation.types.StaticAnimation;
import yesman.epicfight.api.forgeevent.WeaponCapabilityPresetRegistryEvent;
import yesman.epicfight.gameasset.Animations;
import yesman.epicfight.gameasset.Armatures;
import yesman.epicfight.gameasset.ColliderPreset;
import yesman.epicfight.gameasset.EpicFightSkills;
import yesman.epicfight.gameasset.EpicFightSounds;
import yesman.epicfight.world.capabilities.EpicFightCapabilities;
import yesman.epicfight.world.capabilities.entitypatch.player.ServerPlayerPatch;
import yesman.epicfight.world.capabilities.item.CapabilityItem;
import yesman.epicfight.world.capabilities.item.WeaponCapability;

/**
 * T14: Epic Fight side of the fire sword-whip (soft dependency: touched only when Epic Fight is loaded, see {@link #ON}).
 * <ul>
 * <li>Animations (assets/pohsmp_core/animmodels/animations/biped/ember/*.json, made by tools/gen_epicfight_anims.py,
 *     preview tools/ember_anims_preview.html): the special attacks "Last Ember" and "Fire Vortex" and the 3-lash whip combo.</li>
 * <li>Weapon type pohsmp_core:ember_blade (data/pohsmp_core/capabilities/weapons/ember_blade.json): a sword; sword form —
 *     the Epic Fight sword combo, whip form (the blade is hot) — style TWO_HAND with our lashes.</li>
 * </ul>
 * The timings below must match the generator (TIMING there).
 */
public final class EmberEpicFight {
    public static final boolean ON = ModList.get().isLoaded("epicfight");

    /** Animation tick when the blade enters the ground = tick 0 of fx/ember_last_heat.json. */
    public static final int LAST_HEAT_FX_TICK = 7;
    /** Animation tick when fx/ember_vortex.json starts (the whip behind the back, a full turn in 8 ticks). */
    public static final int VORTEX_FX_TICK = 3;

    private EmberEpicFight() {}

    /** Called from PohCore with the mod event bus when Epic Fight is present. */
    public static void init(IEventBus modBus) {
        modBus.addListener(Impl::registerAnimations);
        modBus.addListener(Impl::registerSkill);
        modBus.addListener(Impl::registerWeaponType);
        net.minecraftforge.common.MinecraftForge.EVENT_BUS.addListener(Impl::watchSwing);
    }

    /** Plays the special attack animation for the holder (server). Returns the fx delay in ticks (0 without Epic Fight). */
    public static int playSpecial(ServerPlayer p, boolean vortex) {
        if (!ON) return 0;
        return Impl.playSpecial(p, vortex);
    }

    /** The blade changed form (sword/whip): Epic Fight re-reads the living motions of the style and sends them to the watchers. */
    public static void formChanged(ServerPlayer p) {
        if (ON) Impl.formChanged(p);
    }

    /** Direction of the code lash for the swing in progress: +1 right to left (default), −1 left to right (the 2nd lash). */
    public static int lashDir(Player p) {
        if (!ON || !(p instanceof ServerPlayer sp)) return 1;
        return Impl.lashDir(sp);
    }

    /** Everything that names Epic Fight classes lives here, so the outer class loads without Epic Fight. */
    private static final class Impl {
        static AnimationAccessor<ActionAnimation> LAST_HEAT, FIRE_VORTEX;
        static AnimationAccessor<BasicAttackAnimation> WHIP1, WHIP2, WHIP3;
        static AnimationAccessor<BasicAttackAnimation> SWORD1, SWORD2, SWORD3, SWORD4, SWORD_DASH, SWORD_AIR;
        static AnimationAccessor<StaticAnimation> WHIP_IDLE;

        /**
         * Owner 19.11: "the whip hits like a plain hit though the model goes through the foe" — the whip lashes had the sword collider
         * at the hand (~1.5 blocks). Now a long box along the tool, about the visible whip: ~5.5 blocks, ~1.2 thick, 6 steps per tick so a
         * swing does not skip a target (EF sword: MultiOBBCollider(3, 0.4, 0.4, 0.7, 0, 0, -1), the tip along -Z).
         */
        static final yesman.epicfight.api.collider.Collider WHIP_COLLIDER = new yesman.epicfight.api.collider.MultiOBBCollider(6, 0.6, 0.6, 2.6, 0, 0, -2.8);
        /** Contact start of whip1-3 (seconds, the antic of the animation): the lash goes then. */
        static final float WHIP_CONTACT = 0.15F, WHIP3_CONTACT = 0.20F;

        /** player -> the whip animation seen last tick (to tell a new swing) */
        static final java.util.Map<java.util.UUID, Object> SWING_ANIM = new java.util.HashMap<>();

        /**
         * Server, every player tick: during whip1-3 the lash goes at the contact start of each swing (hit or miss); a new swing (another
         * whip animation, or the same one started again) resets the swing in EmberBlade.
         */
        // ---- manager 19.11: hits from Weapons of Miracles when it is loaded (soft dependency, read by reflection; else ours) ----
        // sword forms 0/1 = the Herrscher combo (auto 1-3, dash Verdammnis, air Ausrottung — as WOM's own Herrscher preset);
        // whip = Blackstar's 1st hit (WOM's Blackstar preset opens with AnimsNapoleon.NAPOLEON_AUTO_1), Moonless's 2nd, Orbit's 3rd.
        static AnimationAccessor<? extends AttackAnimation> S1, S2, S3, S4, SDASH, SAIR, W1, W2, W3;
        static boolean womUsed;
        private static boolean resolved;

        static synchronized void resolve() {
            if (resolved) return;
            resolved = true;
            boolean wom = ModList.get().isLoaded("wom");
            S1 = wom(wom, "AnimsHerrscher", "HERRSCHER_AUTO_1", SWORD1);
            S2 = wom(wom, "AnimsHerrscher", "HERRSCHER_AUTO_2", SWORD2);
            S3 = wom(wom, "AnimsHerrscher", "HERRSCHER_AUTO_3", SWORD3);
            SDASH = wom(wom, "AnimsHerrscher", "HERRSCHER_VERDAMMNIS", SWORD_DASH);
            SAIR = wom(wom, "AnimsHerrscher", "HERRSCHER_AUSROTTUNG", SWORD_AIR);
            W1 = wom(wom, "AnimsNapoleon", "NAPOLEON_AUTO_1", WHIP1);
            W2 = wom(wom, "AnimsMoonless", "MOONLESS_AUTO_2", WHIP2);
            W3 = wom(wom, "AnimsOrbit", "ORBIT_ATTACK_3", WHIP3);
            womUsed = S1 != SWORD1 || W1 != WHIP1;
            S4 = S1 != SWORD1 ? null : SWORD4;   // Herrscher has 3 hits; ours had a 4th finisher
            PohCore.LOG.info("Ember: Epic Fight hits from {}", womUsed ? "Weapons of Miracles (Herrscher / Blackstar, Moonless, Orbit)" : "pohsmp_core");
        }

        @SuppressWarnings("unchecked")
        private static AnimationAccessor<? extends AttackAnimation> wom(boolean on, String cls, String field, AnimationAccessor<? extends AttackAnimation> def) {
            if (!on) return def;
            try {
                Object v = Class.forName("reascer.wom.gameasset.animations.weapons." + cls).getField(field).get(null);
                if (v instanceof AnimationAccessor<?> a && a.get() instanceof AttackAnimation) return (AnimationAccessor<? extends AttackAnimation>) a;
                PohCore.LOG.warn("Ember: WOM {}.{} is not an attack animation", cls, field);
            } catch (Throwable t) {   // WOM renamed something: our own hits stay
                PohCore.LOG.warn("Ember: WOM {}.{} not found ({})", cls, field, t.toString());
            }
            return def;
        }

        /** Start of the first contact of a whip hit (seconds): the lash goes then; from the animation's phases when it is WOM's. */
        static float contact(Object anim) {
            if (anim == WHIP3) return WHIP3_CONTACT;
            if (anim == WHIP1 || anim == WHIP2) return WHIP_CONTACT;
            try {
                if (anim instanceof AnimationAccessor<?> a && a.get() instanceof AttackAnimation at && at.phases.length > 0) return at.phases[0].contact;
            } catch (RuntimeException ignored) {
            }
            return WHIP_CONTACT;
        }

        static void watchSwing(net.minecraftforge.event.TickEvent.PlayerTickEvent e) {
            if (e.phase != net.minecraftforge.event.TickEvent.Phase.END || !(e.player instanceof ServerPlayer p)) return;
            Object anim = null;
            AnimationPlayer pl = null;
            if (p.getMainHandItem().getItem() instanceof EmberBlade && EmberBlade.hot(p)) {
                try {
                    resolve();
                    ServerPlayerPatch patch = EpicFightCapabilities.getEntityPatch(p, ServerPlayerPatch.class);
                    pl = patch == null ? null : patch.getAnimator().getPlayerFor(null);
                    Object real = pl == null ? null : pl.getRealAnimation();
                    if (W1 != null && real != null && (W1.equals(real) || W2.equals(real) || W3.equals(real))) anim = real;
                } catch (RuntimeException ex) {   // an API change in Epic Fight must not break the tick
                    anim = null;
                }
            }
            Object last = SWING_ANIM.get(p.getUUID());
            if (anim == null) {
                if (last != null) {
                    SWING_ANIM.remove(p.getUUID());
                    EmberBlade.swingEnd(p);
                }
                return;
            }
            float t = pl.getElapsedTime(), t0 = pl.getPrevElapsedTime();
            if (!anim.equals(last) || t < t0) EmberBlade.swingStart(p);   // a new lash
            SWING_ANIM.put(p.getUUID(), anim);
            float c = contact(anim);
            if (t >= c && (t0 < c || !anim.equals(last) || t < t0)) EmberBlade.swingContact(p);
        }

        /** A sword-form hit: the sword collider on the right hand, the same attack speed as the whip lashes. */
        static BasicAttackAnimation sword(AnimationAccessor<BasicAttackAnimation> a, float antic, float contact, float recovery) {
            return new BasicAttackAnimation(0.1F, antic, contact, recovery, null, Armatures.BIPED.get().toolR, a, Armatures.BIPED)
                    .addProperty(AttackAnimationProperty.BASIS_ATTACK_SPEED, 1.6F);
        }
        static AnimationAccessor<MovementAnimation> WHIP_WALK, WHIP_RUN;

        static void registerAnimations(AnimationRegistryEvent e) {
            e.newBuilder(PohCore.MODID, Impl::build);
        }

        static void build(AnimationBuilder b) {
            // special attacks: our code does the damage on the fx ticks; the animation only locks the holder in place
            LAST_HEAT = b.nextAccessor("biped/ember/last_heat", a -> new ActionAnimation(0.12F, a, Armatures.BIPED)
                    .addProperty(ActionAnimationProperty.STOP_MOVEMENT, true)
                    .addProperty(ActionAnimationProperty.MOVE_VERTICAL, false));
            FIRE_VORTEX = b.nextAccessor("biped/ember/fire_vortex", a -> new ActionAnimation(0.08F, a, Armatures.BIPED)
                    .addProperty(ActionAnimationProperty.STOP_MOVEMENT, true)
                    .addProperty(ActionAnimationProperty.MOVE_VERTICAL, false));
            // whip combo: the sword collider on the hand starts the hit, EmberBlade.lash adds the 6-block flaming arc
            WHIP1 = b.nextAccessor("biped/ember/whip1", a -> new BasicAttackAnimation(0.1F, 0.15F, 0.30F, 0.45F, WHIP_COLLIDER, Armatures.BIPED.get().toolR, a, Armatures.BIPED)
                    .addProperty(AttackAnimationProperty.BASIS_ATTACK_SPEED, 1.6F));
            WHIP2 = b.nextAccessor("biped/ember/whip2", a -> new BasicAttackAnimation(0.1F, 0.15F, 0.30F, 0.45F, WHIP_COLLIDER, Armatures.BIPED.get().toolR, a, Armatures.BIPED)
                    .addProperty(AttackAnimationProperty.BASIS_ATTACK_SPEED, 1.6F));
            WHIP3 = b.nextAccessor("biped/ember/whip3", a -> new BasicAttackAnimation(0.1F, 0.20F, 0.35F, 0.55F, WHIP_COLLIDER, Armatures.BIPED.get().toolR, a, Armatures.BIPED)
                    .addProperty(AttackAnimationProperty.BASIS_ATTACK_SPEED, 1.6F));
            // sword form combo (owner 19.11: "ordinary hits, with variations"): 4 different hits, a dash hit and an air hit; fire trail in data/
            SWORD1 = b.nextAccessor("biped/ember/sword1", a -> sword(a, 0.15F, 0.30F, 0.45F));   // horizontal cut right to left
            SWORD2 = b.nextAccessor("biped/ember/sword2", a -> sword(a, 0.15F, 0.30F, 0.45F));   // rising backhand, low left to high right
            SWORD3 = b.nextAccessor("biped/ember/sword3", a -> sword(a, 0.15F, 0.30F, 0.45F));   // thrust with a step
            SWORD4 = b.nextAccessor("biped/ember/sword4", a -> sword(a, 0.25F, 0.40F, 0.60F)   // finisher from above with a hop: x1.2
                    .addProperty(yesman.epicfight.api.animation.property.AnimationProperty.AttackPhaseProperty.DAMAGE_MODIFIER,
                            yesman.epicfight.api.utils.math.ValueModifier.multiplier(1.2F)));
            SWORD_DASH = b.nextAccessor("biped/ember/sword_dash", a -> sword(a, 0.15F, 0.30F, 0.45F));
            SWORD_AIR = b.nextAccessor("biped/ember/sword_air", a -> sword(a, 0.15F, 0.30F, 0.45F));
            // whip form motion loops (manager 19.11): idle as the EF static idle, walk/run as EF movement (pace follows the speed)
            WHIP_IDLE = b.nextAccessor("biped/ember/whip_idle", a -> new StaticAnimation(true, a, Armatures.BIPED));
            WHIP_WALK = b.nextAccessor("biped/ember/whip_walk", a -> new MovementAnimation(true, a, Armatures.BIPED));
            WHIP_RUN = b.nextAccessor("biped/ember/whip_run", a -> new MovementAnimation(true, a, Armatures.BIPED));
        }

        static void registerWeaponType(WeaponCapabilityPresetRegistryEvent e) {
            e.getTypeEntry().put(new ResourceLocation(PohCore.MODID, EmberBlade.NAME), item -> {
                resolve();   // the presets are built after the animations are registered: WOM's accessors are there by now
                return WeaponCapability.builder()
                    .category(CapabilityItem.WeaponCategories.SWORD)
                    // forms 0/1 (cold, burning sword): ONE_HAND; form 2 (whip): TWO_HAND
                    .styleProvider(patch -> hot(patch.getOriginal()) ? CapabilityItem.Styles.TWO_HAND : CapabilityItem.Styles.ONE_HAND)
                    .collider(ColliderPreset.SWORD)
                    .hitSound(EpicFightSounds.BLADE_HIT.get())
                    .newStyleCombo(CapabilityItem.Styles.ONE_HAND, S4 == null ? new AnimationAccessor[] {S1, S2, S3, SDASH, SAIR}
                            : new AnimationAccessor[] {S1, S2, S3, S4, SDASH, SAIR})
                    .newStyleCombo(CapabilityItem.Styles.TWO_HAND, W1, W2, W3, Animations.SWORD_DASH, Animations.SWORD_AIR_SLASH)
                    .innateSkill(CapabilityItem.Styles.ONE_HAND, s -> special)
                    .innateSkill(CapabilityItem.Styles.TWO_HAND, s -> special)
                    .livingMotionModifier(CapabilityItem.Styles.ONE_HAND, LivingMotions.BLOCK, Animations.SWORD_GUARD)
                    .livingMotionModifier(CapabilityItem.Styles.TWO_HAND, LivingMotions.BLOCK, Animations.SWORD_GUARD)
                    .livingMotionModifier(CapabilityItem.Styles.TWO_HAND, LivingMotions.IDLE, WHIP_IDLE)
                    .livingMotionModifier(CapabilityItem.Styles.TWO_HAND, LivingMotions.WALK, WHIP_WALK)
                    .livingMotionModifier(CapabilityItem.Styles.TWO_HAND, LivingMotions.RUN, WHIP_RUN);
            });
        }

        static yesman.epicfight.skill.Skill special;

        /**
         * T14 (manager 19.11): the special attack is the weapon innate skill pohsmp_core:ember_special of both forms. No Epic Fight
         * charge: ready only at full heat (the icon stays grey until then); it calls EmberBlade.special.
         */
        static void registerSkill(yesman.epicfight.api.forgeevent.SkillBuildEvent e) {
            special = e.createRegistryWorker(PohCore.MODID).build("ember_special", Special::new,
                    new yesman.epicfight.skill.SkillBuilder<Special>().setCategory(yesman.epicfight.skill.SkillCategories.WEAPON_INNATE)
                            .setActivateType(yesman.epicfight.skill.Skill.ActivateType.ONE_SHOT)
                            .setResource(yesman.epicfight.skill.Skill.Resource.NONE));
        }

        static final class Special extends yesman.epicfight.skill.weaponinnate.WeaponInnateSkill {
            Special(yesman.epicfight.skill.SkillBuilder<? extends yesman.epicfight.skill.weaponinnate.WeaponInnateSkill> b) {
                super(b);
            }

            @Override
            public boolean checkExecuteCondition(yesman.epicfight.skill.SkillContainer c) {
                Player p = (Player) c.getExecutor().getOriginal();
                return p.getMainHandItem().getItem() instanceof EmberBlade && EmberBlade.ready(p);
            }

            @Override
            public void executeOnServer(yesman.epicfight.skill.SkillContainer c, net.minecraft.network.FriendlyByteBuf buf) {
                ServerPlayer p = c.getServerExecutor().getOriginal();
                ItemStack s = p.getMainHandItem();
                if (!(s.getItem() instanceof EmberBlade) || !EmberBlade.ready(p)) return;
                super.executeOnServer(c, buf);
                EmberBlade.special(p, s);
            }
        }

        private static boolean hot(net.minecraft.world.entity.LivingEntity e) {
            return e.getMainHandItem().getItem() instanceof EmberBlade && EmberBlade.hot(e);
        }

        static int playSpecial(ServerPlayer p, boolean vortex) {
            ServerPlayerPatch patch = EpicFightCapabilities.getEntityPatch(p, ServerPlayerPatch.class);
            AnimationAccessor<ActionAnimation> anim = vortex ? FIRE_VORTEX : LAST_HEAT;
            if (patch == null || anim == null) return 0;
            patch.playAnimationSynchronized(anim, 0.0F);
            return vortex ? VORTEX_FX_TICK : LAST_HEAT_FX_TICK;
        }

        static void formChanged(ServerPlayer p) {
            try {
                ServerPlayerPatch patch = EpicFightCapabilities.getEntityPatch(p, ServerPlayerPatch.class);
                if (patch != null) patch.modifyLivingMotionByCurrentItem();
            } catch (RuntimeException ex) {   // an API change in Epic Fight must not break the heat
                PohCore.LOG.warn("Ember: Epic Fight motion refresh failed", ex);
            }
        }

        static int lashDir(ServerPlayer p) {
            try {
                ServerPlayerPatch patch = EpicFightCapabilities.getEntityPatch(p, ServerPlayerPatch.class);
                resolve();
                if (patch == null || W2 == null) return 1;
                AnimationPlayer player = patch.getAnimator().getPlayerFor(null);
                return player != null && W2.equals(player.getRealAnimation()) ? -1 : 1;
            } catch (RuntimeException ex) {   // an API change in Epic Fight must not break the hit
                return 1;
            }
        }
    }
}
