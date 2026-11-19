package ru.pohsmp.core.ember;

import java.util.HashSet;
import java.util.List;
import java.util.Set;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.InteractionResultHolder;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.SwordItem;
import net.minecraft.world.item.Tiers;
import net.minecraft.world.item.TooltipFlag;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.event.entity.living.LivingHurtEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import ru.pohsmp.core.DivineEvents;
import ru.pohsmp.core.fx.Fx;
import ru.pohsmp.core.spell.HigherSpell;
import ru.pohsmp.core.spell.Tasks;
import ru.pohsmp.core.spell.silent.SilentSpell;

/**
 * T14: the fire sword-whip (working name "Раскалённые угли"), handed out by an admin. Damage of a diamond sword, every hit sets
 * the target on fire. Epic Fight swings it as a sword (data/pohsmp_core/capabilities/weapons/ember_blade.json).
 * <ul>
 * <li>Heat (0..100) grows with hits and cools down without them; the HUD shows it over the hotbar (client/EmberHud).</li>
 * <li>Two hits in a row heat the blade into the whip form: each hit then also lashes a flaming arc 6 blocks long.
 *     Without hits for {@link #COOL_TICKS} the fire goes out.</li>
 * <li>Full heat + right click: special attack by form. Sword form: "Last Ember" — the blade into the ground, three waves of
 *     fire pillars (3/5/7 blocks), the heat to zero, the blade cools down. Whip form: "Fire Vortex" — a full turn of the whip,
 *     a ring of fire r 5 that burns and throws everyone out; the whip stays hot.</li>
 * </ul>
 * Looks (pillar and ring effects, HUD texture, swing animations) — the manager; here they are temporary particles and the
 * fire_whip mesh of the Fire Whip spell.
 */
public class EmberBlade extends SwordItem {
    public static final String NAME = "ember_blade";
    public static final float MAX_HEAT = 100, HEAT_PER_HIT = 14, COOL_PER_SEC = 6;
    public static final int HOT_AFTER = 2, COOL_TICKS = 100, IDLE_TICKS = 40;
    static final double WHIP_LEN = 6, WHIP_HALF = Math.toRadians(50), VORTEX_R = 5;
    static final double[] WAVES = {3, 5, 7};

    private static final String HEAT = "Heat", STREAK = "Streak", LAST = "LastHit", HOT = "Hot";
    private static boolean lashing;   // our own lash/special damage must not count as a new hit

    public EmberBlade() {
        super(Tiers.DIAMOND, 3, -2.4f, new Properties().stacksTo(1).fireResistant());
    }

    // ---------------------------------------------------------------- state in the stack (synced to the client with the stack)

    public static float heat(ItemStack s) {
        CompoundTag t = s.getTag();
        return t == null ? 0 : t.getFloat(HEAT);
    }

    public static boolean hot(ItemStack s) {
        CompoundTag t = s.getTag();
        return t != null && t.getBoolean(HOT);
    }

    private static void set(ItemStack s, float heat, int streak, boolean hot, long last) {
        CompoundTag t = s.getOrCreateTag();
        t.putFloat(HEAT, Math.max(0, Math.min(MAX_HEAT, heat)));
        t.putInt(STREAK, streak);
        t.putBoolean(HOT, hot);
        t.putLong(LAST, last);
    }

    /** Heat changes every second: the stack must not replay the re-equip animation each time. */
    @Override
    public boolean shouldCauseReequipAnimation(ItemStack oldStack, ItemStack newStack, boolean slotChanged) {
        return slotChanged || oldStack.getItem() != newStack.getItem();
    }

    @Override
    public void inventoryTick(ItemStack s, Level level, Entity holder, int slot, boolean selected) {
        if (level.isClientSide || level.getGameTime() % 20 != 0 || s.getTag() == null) return;
        CompoundTag t = s.getTag();
        long idle = level.getGameTime() - t.getLong(LAST);
        float heat = t.getFloat(HEAT);
        boolean hot = t.getBoolean(HOT);
        int streak = t.getInt(STREAK);
        if (idle < IDLE_TICKS || (heat <= 0 && !hot && streak == 0)) return;
        heat -= COOL_PER_SEC;
        if (idle >= COOL_TICKS) {
            if (hot && level instanceof ServerLevel sl)
                sl.playSound(null, holder.getX(), holder.getY(), holder.getZ(), SoundEvents.FIRE_EXTINGUISH, SoundSource.PLAYERS, 0.5f, 1.4f);
            hot = false;
            streak = 0;
        }
        set(s, heat, streak, hot, t.getLong(LAST));
    }

    @Override
    public void appendHoverText(ItemStack s, Level level, List<Component> tip, TooltipFlag flag) {
        tip.add(Component.translatable("item.pohsmp_core.ember_blade.desc1").withStyle(st -> st.withColor(0xFF8A3A)));
        tip.add(Component.translatable("item.pohsmp_core.ember_blade.desc2").withStyle(st -> st.withColor(0xB0B0B0)));
        tip.add(Component.translatable("item.pohsmp_core.ember_blade.desc3").withStyle(st -> st.withColor(0xB0B0B0)));
    }

    // ---------------------------------------------------------------- hits

    /** Any melee hit of the holder with this blade in the main hand (vanilla or an Epic Fight swing). */
    public static final class Events {
        /**
         * Owner 19.11: the heat did not grow. The direct entity of an Epic Fight swing may not be the player himself, so any non-projectile
         * damage by the holder counts. Temporary: each hit goes to the server log (to see in the next check whether the hits arrive).
         */
        @SubscribeEvent(priority = net.minecraftforge.eventbus.api.EventPriority.LOWEST, receiveCanceled = true)
        public static void onHurt(LivingHurtEvent e) {
            if (lashing || !(e.getSource().getEntity() instanceof Player p)) return;
            if (!(p.level() instanceof ServerLevel sl)) return;
            ItemStack s = p.getMainHandItem();
            if (!(s.getItem() instanceof EmberBlade)) return;
            Entity direct = e.getSource().getDirectEntity();
            ru.pohsmp.core.PohCore.LOG.info("[ember] hurt {} by {}: source {}, direct {}, amount {}, cancelled {}, heat {}",
                    e.getEntity().getName().getString(), p.getName().getString(), e.getSource().getMsgId(),
                    direct == null ? "null" : direct.getType().toShortString(), e.getAmount(), e.isCanceled(), heat(s));
            if (e.isCanceled() || direct instanceof net.minecraft.world.entity.projectile.Projectile) return;
            onHit(sl, p, s, e.getEntity());
        }

        /** Temporary: a swing that hits nothing still shows in the log, to tell "no hurt event" from "no swing". */
        @SubscribeEvent
        public static void onAttack(net.minecraftforge.event.entity.player.AttackEntityEvent e) {
            if (e.getEntity().getMainHandItem().getItem() instanceof EmberBlade && !e.getEntity().level().isClientSide)
                ru.pohsmp.core.PohCore.LOG.info("[ember] attack by {} on {}", e.getEntity().getName().getString(), e.getTarget().getName().getString());
        }
    }

    private static void onHit(ServerLevel sl, Player p, ItemStack s, LivingEntity target) {
        long now = sl.getGameTime();
        CompoundTag t = s.getOrCreateTag();
        int streak = now - t.getLong(LAST) <= COOL_TICKS ? t.getInt(STREAK) + 1 : 1;
        boolean wasHot = t.getBoolean(HOT), hot = wasHot || streak >= HOT_AFTER;
        float heat = t.getFloat(HEAT) + HEAT_PER_HIT;
        target.setSecondsOnFire(hot ? 5 : 3);
        set(s, heat, streak, hot, now);
        glow(sl, p, s);
        if (hot && !wasHot) {   // the blade catches fire
            sl.playSound(null, p.getX(), p.getY(), p.getZ(), SoundEvents.FIRECHARGE_USE, SoundSource.PLAYERS, 1f, 0.8f);
            DivineEvents.particle(sl, ParticleTypes.FLAME, p.getX(), p.getY() + 1.2, p.getZ(), 20, 0.4, 0.05);
        }
        if (heat >= MAX_HEAT && t.getFloat(HEAT) < MAX_HEAT)
            sl.playSound(null, p.getX(), p.getY(), p.getZ(), SoundEvents.BLAZE_AMBIENT, SoundSource.PLAYERS, 0.8f, 1.6f);
        if (wasHot) lash(sl, p, target);
    }

    private static float damage(Player p) {
        return (float) p.getAttributeValue(net.minecraft.world.entity.ai.attributes.Attributes.ATTACK_DAMAGE);
    }

    private static void hurt(ServerLevel sl, Player p, LivingEntity e, float dmg, int fire) {
        lashing = true;
        try {
            e.hurt(sl.damageSources().playerAttack(p), dmg);
        } finally {
            lashing = false;
        }
        e.setSecondsOnFire(fire);
    }

    private static Vec3 flat(Vec3 v) {
        Vec3 f = v.multiply(1, 0, 1);
        return f.lengthSqr() < 1e-4 ? new Vec3(0, 0, 1) : f.normalize();
    }

    /** Whip form: the lash sweeps right to left (the 2nd combo lash: left to right) over 4 ticks and burns everyone in the arc but the one already struck. */
    private static void lash(ServerLevel sl, Player p, LivingEntity struck) {
        Vec3 o = p.position().add(0, p.getBbHeight() * 0.6, 0), f = flat(p.getLookAngle());
        double yaw = Math.atan2(f.z, f.x);
        float dmg = damage(p) * 0.6f;
        for (LivingEntity e : HigherSpell.around(sl, p.position(), WHIP_LEN + 1, e -> e != p && e != struck && !HigherSpell.friendly(p, e))) {
            Vec3 d = e.position().subtract(p.position()).multiply(1, 0, 1);
            double dist = d.length();
            if (dist > WHIP_LEN + e.getBbWidth() / 2 || Math.abs(e.getY() - p.getY()) > 3) continue;
            if (dist > 0.5 && Math.acos(Math.max(-1, Math.min(1, d.normalize().dot(f)))) > WHIP_HALF) continue;
            hurt(sl, p, e, dmg, 4);
        }
        sl.playSound(null, o.x, o.y, o.z, SoundEvents.BLAZE_SHOOT, SoundSource.PLAYERS, 0.7f, 1.3f);
        int dir = EmberEpicFight.lashDir(p);   // the 2nd lash of the Epic Fight combo goes left to right
        sweep(sl, o, yaw, -WHIP_HALF * dir, WHIP_HALF * dir, 4, false);
    }

    /** Turns the fire_whip model from a0 to a1 (radians from the facing, + = left) over n ticks, flames along the arc. */
    private static void sweep(ServerLevel sl, Vec3 o, double yaw, double a0, double a1, int n, boolean ring) {
        int whip = Fx.play(sl, Fx.mesh("ember_whip").at(o).yaw(SilentSpell.yawOf(dir(yaw, a0))).duration(n + 15));
        Tasks.add(new Tasks.Task() {
            int age;

            @Override
            public boolean tick() {
                age++;
                double from = a0 + (a1 - a0) * (age - 1) / n, to = a0 + (a1 - a0) * age / n;
                Fx.move(sl, whip, o, SilentSpell.yawOf(dir(yaw, to)));
                double len = ring ? VORTEX_R : WHIP_LEN;
                for (double a = from; Math.abs(a - from) <= Math.abs(to - from); a += Math.signum(a1 - a0) * 0.12)
                    for (double r = 1.5; r <= len; r += 1.5) {
                        double sag = ring ? 0 : Math.sin(r / len * Math.PI) * 0.6;
                        Vec3 q = o.add(dir(yaw, a).scale(r));
                        DivineEvents.particle(sl, ParticleTypes.FLAME, q.x, q.y - sag - (ring ? 0.8 : 0), q.z, 1, 0.03, 0.01);
                    }
                if (age >= n) {
                    Fx.stop(sl, whip, "");
                    return false;
                }
                return true;
            }
        });
    }

    private static Vec3 dir(double yaw, double a) {
        return new Vec3(Math.cos(yaw + a), 0, Math.sin(yaw + a));
    }

    // ---------------------------------------------------------------- special attack (full heat + right click)

    @Override
    public InteractionResultHolder<ItemStack> use(Level level, Player p, InteractionHand hand) {
        ItemStack s = p.getItemInHand(hand);
        if (hand != InteractionHand.MAIN_HAND || heat(s) < MAX_HEAT) return InteractionResultHolder.pass(s);
        if (level instanceof ServerLevel && p instanceof net.minecraft.server.level.ServerPlayer sp) special(sp, s);
        return InteractionResultHolder.sidedSuccess(s, level.isClientSide);
    }

    /**
     * The special attack by form (full heat): plays the Epic Fight animation, spends the heat at once and starts the effect and the
     * damage on the strike of the animation (at once without Epic Fight). Called by the right click now; the Epic Fight weapon skill
     * (owner 19.11: the right click should stay the block) should call this too. Returns false when the heat is not full.
     */
    public static boolean special(net.minecraft.server.level.ServerPlayer p, ItemStack s) {
        if (!(s.getItem() instanceof EmberBlade item) || heat(s) < MAX_HEAT || !(p.level() instanceof ServerLevel sl)) return false;
        boolean vortex = hot(s);
        int delay = EmberEpicFight.playSpecial(p, vortex);
        set(s, 0, vortex ? HOT_AFTER : 0, vortex, sl.getGameTime());   // the heat is spent at once: no double special
        later(delay, () -> {
            if (!p.isAlive() || p.level() != sl) return;
            if (vortex) fireVortex(sl, p, s);
            else lastEmber(sl, p, s);
        });
        p.getCooldowns().addCooldown(item, vortex ? 24 : 40);
        return true;
    }

    /** Runs r after n server ticks (at once when n <= 0). */
    private static void later(int n, Runnable r) {
        if (n <= 0) {
            r.run();
            return;
        }
        Tasks.add(new Tasks.Task() {
            int left = n;

            @Override
            public boolean tick() {
                if (--left > 0) return true;
                r.run();
                return false;
            }
        });
    }

    /** Ticks of fx/ember_last_heat.json when its three waves of pillars rise (the damage goes with them). */
    static final int[] WAVE_TICKS = {4, 12, 20};
    /** Tick of fx/ember_vortex.json when the ring goes out (damage, fire, knock-back). */
    static final int VORTEX_HIT = 4;

    /**
     * Sword form: the blade into the ground in front of the holder, three waves of fire pillars spread out from it, then the blade
     * cools down (fx/ember_last_heat.json, the manager's look).
     */
    private static void lastEmber(ServerLevel sl, Player p, ItemStack s) {
        Vec3 c = p.position().add(flat(p.getLookAngle()).scale(0.9));
        float dmg = damage(p) * 1.2f;
        sl.playSound(null, c.x, c.y, c.z, SoundEvents.ANVIL_LAND, SoundSource.PLAYERS, 0.6f, 0.6f);
        int fx = Fx.play(sl, Fx.fx("ember_last_heat").at(c).yaw(p.getYRot()));
        Set<LivingEntity> burnt = new HashSet<>();
        for (int w = 0; w < WAVES.length; w++) {
            double r = WAVES[w];
            float pitch = 0.6f + w * 0.15f;
            Fx.at(sl, fx, WAVE_TICKS[w], () -> {
                if (!p.isAlive()) return;
                for (LivingEntity e : HigherSpell.around(sl, c, r + 1.2, e -> e != p && !HigherSpell.friendly(p, e))) {
                    double d = Math.sqrt(e.distanceToSqr(c.x, e.getY(), c.z));
                    if (d < r - 1.6 || burnt.contains(e) || Math.abs(e.getY() - c.y) > 3) continue;
                    burnt.add(e);
                    hurt(sl, p, e, dmg, 6);
                }
                sl.playSound(null, c.x, c.y, c.z, SoundEvents.BLAZE_SHOOT, SoundSource.PLAYERS, 1.2f, pitch);
            });
        }
        Fx.at(sl, fx, 22, () -> sl.playSound(null, c.x, c.y, c.z, SoundEvents.FIRE_EXTINGUISH, SoundSource.PLAYERS, 1f, 0.8f));
    }

    // ---------------------------------------------------------------- the glowing blade while heat > 0 (fx/ember_heat.json)

    /** holder -> running ember_heat instance */
    private static final java.util.Map<java.util.UUID, Integer> GLOW = new java.util.HashMap<>();

    /** Starts the glow on the holder's hand once; it watches itself and goes out when the heat is 0 or the blade leaves the hand. */
    static void glow(ServerLevel sl, Player p, ItemStack s) {
        if (GLOW.containsKey(p.getUUID()) || heat(s) <= 0) return;
        int inst = Fx.play(sl, Fx.fx("ember_heat").caster(p).scale(0.6 + 0.4 * heat(s) / MAX_HEAT));
        GLOW.put(p.getUUID(), inst);
        Tasks.add(() -> {
            ItemStack h = p.getMainHandItem();
            if (p.isAlive() && !p.isRemoved() && p.level() == sl && h.getItem() instanceof EmberBlade && heat(h) > 0 && Fx.running(inst)) return true;
            Fx.stop(sl, inst, "");
            GLOW.remove(p.getUUID(), inst);
            return false;
        });
    }

    /**
     * Whip form: a full turn of the whip, a ring of fire r 5 burns and throws everyone out on tick {@link #VORTEX_HIT}; the whip
     * stays hot (fx/ember_vortex.json, the manager's look).
     */
    private static void fireVortex(ServerLevel sl, Player p, ItemStack s) {
        Vec3 c = p.position(), f = flat(p.getLookAngle());
        float dmg = damage(p) * 1.1f;
        sl.playSound(null, c.x, c.y, c.z, SoundEvents.FIRECHARGE_USE, SoundSource.PLAYERS, 1f, 0.6f);
        int fx = Fx.play(sl, Fx.fx("ember_vortex").at(c).yaw(p.getYRot()));
        Fx.at(sl, fx, VORTEX_HIT, () -> {
            if (!p.isAlive()) return;
            for (LivingEntity e : HigherSpell.around(sl, c, VORTEX_R + 0.5, e -> e != p && !HigherSpell.friendly(p, e))) {
                if (Math.abs(e.getY() - c.y) > 3) continue;
                hurt(sl, p, e, dmg, 6);
                Vec3 out = e.position().subtract(c).multiply(1, 0, 1);
                out = out.lengthSqr() < 1e-4 ? f : out.normalize();
                HigherSpell.push(e, out.scale(1.3).add(0, 0.4, 0));
            }
            sl.playSound(null, c.x, c.y, c.z, SoundEvents.BLAZE_SHOOT, SoundSource.PLAYERS, 1.3f, 0.7f);
        });
    }
}
