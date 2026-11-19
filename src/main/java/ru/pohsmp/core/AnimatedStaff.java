package ru.pohsmp.core;

import io.redspace.ironsspellbooks.api.events.SpellOnCastEvent;
import io.redspace.ironsspellbooks.api.magic.MagicData;
import java.util.HashMap;
import java.util.Map;
import java.util.UUID;
import java.util.function.Consumer;
import java.util.function.Supplier;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.ai.attributes.Attribute;
import net.minecraft.world.item.ItemStack;
import net.minecraftforge.client.extensions.common.IClientItemExtensions;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.event.entity.player.PlayerEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import software.bernie.geckolib.animatable.GeoItem;
import software.bernie.geckolib.animatable.SingletonGeoAnimatable;
import software.bernie.geckolib.core.animatable.instance.AnimatableInstanceCache;
import software.bernie.geckolib.core.animation.AnimatableManager;
import software.bernie.geckolib.core.animation.AnimationController;
import software.bernie.geckolib.core.animation.RawAnimation;
import software.bernie.geckolib.util.GeckoLibUtil;

/**
 * School staff drawn by GeckoLib (geo/item/&lt;name&gt;.geo.json, animations/item/&lt;name&gt;.animation.json, glow from &lt;name&gt;_glowmask.png).
 * "idle" loops in the hand; "cast" loops while the holder casts any Iron's spell; "flash" plays once when the spell goes off.
 * Triggers come from the server ({@link StaffAnimEvents}); the Downfall staff triggers its own from the Downfall spell.
 */
public class AnimatedStaff extends PohStaff implements GeoItem {
    private static final RawAnimation IDLE = RawAnimation.begin().thenLoop("idle");
    private static final RawAnimation CAST = RawAnimation.begin().thenLoop("cast");
    private static final RawAnimation FLASH = RawAnimation.begin().thenPlay("flash").thenLoop("idle");
    private final AnimatableInstanceCache cache = GeckoLibUtil.createInstanceCache(this);
    public final String model;
    /** Model drawn while the staff's own GeckoLib files are missing (null: always its own). */
    public String fallbackModel;

    public AnimatedStaff(String model, Supplier<Attribute> school, double schoolPct, double powerPct, double regenPct) {
        super(school, schoolPct, powerPct, regenPct);
        this.model = model;
        SingletonGeoAnimatable.registerSyncedAnimatable(this);
    }

    /** Whether the generic cast tracker drives this staff (the Downfall staff is driven by its spell). */
    protected boolean autoAnim() {
        return true;
    }

    /** Server: play "cast" (loops until replaced), "flash", or stop the triggered one (anim null). Returns the stack id or 0. */
    public static long play(LivingEntity holder, String anim) {
        if (!(holder.level() instanceof ServerLevel sl)) return 0;
        ItemStack st = holder.getMainHandItem();
        if (!(st.getItem() instanceof AnimatedStaff staff)) return 0;
        long id = GeoItem.getOrAssignId(st, sl);
        if (anim == null) staff.stopTriggeredAnim(holder, id, "main", "cast");
        else staff.triggerAnim(holder, id, "main", anim);
        return id;
    }

    @Override
    public void registerControllers(AnimatableManager.ControllerRegistrar controllers) {
        controllers.add(new AnimationController<>(this, "main", 6, s -> s.setAndContinue(IDLE))
                .triggerableAnim("cast", CAST).triggerableAnim("flash", FLASH));
    }

    @Override
    public AnimatableInstanceCache getAnimatableInstanceCache() {
        return cache;
    }

    @Override
    public void initializeClient(Consumer<IClientItemExtensions> consumer) {
        consumer.accept(new ru.pohsmp.core.client.GeoStaffClient(this));
    }

    /** Server side: starts "cast" when a player holding an animated staff begins casting, stops it when the cast ends, "flash" on cast. */
    public static final class StaffAnimEvents {
        private StaffAnimEvents() {}

        private static final class Held {
            AnimatedStaff staff;
            long id;
        }

        private static final Map<UUID, Held> CASTING = new HashMap<>();

        private static AnimatedStaff held(LivingEntity e) {
            return e.getMainHandItem().getItem() instanceof AnimatedStaff s && s.autoAnim() ? s : null;
        }

        @SubscribeEvent
        public static void onPlayerTick(TickEvent.PlayerTickEvent e) {
            if (e.phase != TickEvent.Phase.END || !(e.player instanceof ServerPlayer sp)) return;
            boolean casting = MagicData.getPlayerMagicData(sp).isCasting();
            Held h = CASTING.get(sp.getUUID());
            if (casting && h == null) {
                AnimatedStaff s = held(sp);
                if (s == null) return;
                h = new Held();
                h.staff = s;
                h.id = play(sp, "cast");
                CASTING.put(sp.getUUID(), h);
            } else if (!casting && h != null) {
                CASTING.remove(sp.getUUID());
                h.staff.stopTriggeredAnim(sp, h.id, "main", "cast");
            }
        }

        @SubscribeEvent
        public static void onCast(SpellOnCastEvent e) {
            LivingEntity le = e.getEntity();
            if (le.level().isClientSide || held(le) == null) return;
            CASTING.remove(le.getUUID());   // the flash replaces the cast loop; no stop afterwards
            play(le, "flash");
        }

        @SubscribeEvent
        public static void onLogout(PlayerEvent.PlayerLoggedOutEvent e) {
            CASTING.remove(e.getEntity().getUUID());
        }
    }
}
