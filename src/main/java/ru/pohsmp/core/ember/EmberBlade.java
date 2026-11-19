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
import ru.pohsmp.core.net.Net;
import ru.pohsmp.core.spell.HigherSpell;
import ru.pohsmp.core.spell.Tasks;

/**
 * T14: the fire sword-whip (working name "Раскалённые угли"), handed out by an admin. Damage of a diamond sword, every hit sets
 * the target on fire. Epic Fight swings it as a sword (data/pohsmp_core/capabilities/weapons/ember_blade.json).
 * <ul>
 * <li>Heat (0..100) grows with hits and cools down without them; the HUD shows it over the hotbar (client/EmberHud).</li>
 * <li>Two hits in a row heat the blade into the whip form: each hit then also lashes a flaming arc 6 blocks long.
 *     Without hits for {@link #COOL_TICKS} the fire goes out.</li>
 * <li>Full heat: special attack by form, the Epic Fight weapon skill (without Epic Fight: right click). Sword form: "Last Ember" — the blade into the ground, three waves of
 *     fire pillars (3/5/7 blocks), the heat to zero, the blade cools down. Whip form: "Fire Vortex" — a full turn of the whip,
 *     a ring of fire r 5 that burns and throws everyone out; the whip stays hot.</li>
 * </ul>
 * Looks (pillar and ring effects, HUD texture, swing animations) — the manager. The whip itself is a physics rope drawn on the
 * client (client/EmberWhipClient, ember/WhipSim): it hangs from the hilt in the whip form, follows the hand of any animation and
 * lashes when the server sends {@link Net.HFx#WHIP} (a lash here, the turn of "Fire Vortex").
 */
public class EmberBlade extends SwordItem {
    public static final String NAME = "ember_blade";
    public static final float MAX_HEAT = 100, HEAT_PER_HIT = 14, COOL_PER_SEC = 6;
    /** Owner 19.11: 10 s for each phase — the whip goes back to the sword, and the heat starts to cool, 10 s after the last hit. */
    public static final int HOT_AFTER = 2, COOL_TICKS = 200, IDLE_TICKS = 200;
    static final double WHIP_LEN = 6, WHIP_HALF = Math.toRadians(50), VORTEX_R = 5;
    static final double[] WAVES = {3, 5, 7};

    private static boolean lashing;   // our own lash/special damage must not count as a new hit

    public EmberBlade() {
        super(Tiers.DIAMOND, 3, -2.4f, new Properties().stacksTo(1).fireResistant());
    }

    // ---------------------------------------------------------------- state of the holder: kept by the server, sent to the clients

    /**
     * Owner 19.11: with the state in the stack tag the gauge stayed empty and the model stayed a blade — in creative the client sends its
     * own copy of the slot back and the server's heat was lost. Now the server keeps heat and form per player and sends them
     * (Net.EmberMsg) to the holder and everyone who sees him; the client keeps them per entity id.
     */
    private static final class St {
        float heat;
        int streak;
        boolean hot;
        long last;
    }

    private static final St NONE = new St();
    private static final java.util.Map<java.util.UUID, St> SERVER = new java.util.HashMap<>();
    private static final java.util.Map<Integer, St> CLIENT = new java.util.HashMap<>();

    private static St st(Entity e) {
        if (e == null) return NONE;
        St s = e.level().isClientSide ? CLIENT.get(e.getId()) : SERVER.get(e.getUUID());
        return s == null ? NONE : s;
    }

    /** Heat of the holder (0..MAX_HEAT); on the client — the last value the server sent. */
    public static float heat(Entity holder) {
        return st(holder).heat;
    }

    /** True: the holder's blade is in the whip form. */
    public static boolean hot(Entity holder) {
        return st(holder).hot;
    }

    private static void set(Player p, float heat, int streak, boolean hot, long last) {
        St s = SERVER.computeIfAbsent(p.getUUID(), k -> new St());
        heat = Math.max(0, Math.min(MAX_HEAT, heat));
        boolean changed = s.heat != heat || s.hot != hot;
        s.heat = heat;
        s.streak = streak;
        s.hot = hot;
        s.last = last;
        if (changed) sync(p, null);
    }

    /** To the holder and his watchers, or only to {@code to}. */
    private static void sync(Player p, net.minecraft.server.level.ServerPlayer to) {
        St s = st(p);
        Object msg = new ru.pohsmp.core.net.Net.EmberMsg(p.getId(), s.heat, s.hot);
        if (to != null) ru.pohsmp.core.net.Net.CH.send(net.minecraftforge.network.PacketDistributor.PLAYER.with(() -> to), msg);
        else ru.pohsmp.core.net.Net.CH.send(net.minecraftforge.network.PacketDistributor.TRACKING_ENTITY_AND_SELF.with(() -> p), msg);
    }

    /** Client: the state the server sent (Net.EmberMsg). */
    public static void clientSet(int entity, float heat, boolean hot) {
        St s = CLIENT.computeIfAbsent(entity, k -> new St());
        s.heat = heat;
        s.hot = hot;
    }

    /** Heat changes every second: the stack must not replay the re-equip animation each time. */
    @Override
    public boolean shouldCauseReequipAnimation(ItemStack oldStack, ItemStack newStack, boolean slotChanged) {
        return slotChanged || oldStack.getItem() != newStack.getItem();
    }

    @Override
    public void inventoryTick(ItemStack s, Level level, Entity holder, int slot, boolean selected) {
        if (level.isClientSide || level.getGameTime() % 20 != 0 || !(holder instanceof Player p)) return;
        St t = SERVER.get(p.getUUID());
        if (t == null) return;
        long idle = level.getGameTime() - t.last;
        float heat = t.heat;
        boolean hot = t.hot;
        int streak = t.streak;
        if (heat <= 0 && !hot && streak == 0) return;
        if (idle >= IDLE_TICKS) heat -= COOL_PER_SEC;
        if (idle >= COOL_TICKS) {
            if (hot && level instanceof ServerLevel sl)
                sl.playSound(null, holder.getX(), holder.getY(), holder.getZ(), SoundEvents.FIRE_EXTINGUISH, SoundSource.PLAYERS, 0.5f, 1.4f);
            hot = false;
            streak = 0;
        }
        if (heat != t.heat || hot != t.hot || streak != t.streak) set(p, heat, streak, hot, t.last);
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
        /** Any non-projectile damage by the holder counts (the direct entity of an Epic Fight swing may not be the player himself). */
        @SubscribeEvent(priority = net.minecraftforge.eventbus.api.EventPriority.LOWEST)
        public static void onHurt(LivingHurtEvent e) {
            if (lashing || !(e.getSource().getEntity() instanceof Player p)) return;
            if (!(p.level() instanceof ServerLevel sl)) return;
            ItemStack s = p.getMainHandItem();
            if (!(s.getItem() instanceof EmberBlade)) return;
            if (e.getSource().getDirectEntity() instanceof net.minecraft.world.entity.projectile.Projectile) return;
            onHit(sl, p, s, e.getEntity());
        }

        /** A player who starts seeing the holder gets his form (the whip model and animations). */
        @SubscribeEvent
        public static void onTrack(net.minecraftforge.event.entity.player.PlayerEvent.StartTracking e) {
            if (e.getTarget() instanceof Player p && SERVER.containsKey(p.getUUID()) && e.getEntity() instanceof net.minecraft.server.level.ServerPlayer to)
                sync(p, to);
        }

        @SubscribeEvent
        public static void onLogout(net.minecraftforge.event.entity.player.PlayerEvent.PlayerLoggedOutEvent e) {
            SERVER.remove(e.getEntity().getUUID());
        }

        @SubscribeEvent
        public static void onUnload(net.minecraftforge.event.level.LevelEvent.Unload e) {
            if (e.getLevel().isClientSide()) CLIENT.clear();
        }
    }

    private static void onHit(ServerLevel sl, Player p, ItemStack s, LivingEntity target) {
        long now = sl.getGameTime();
        St t = st(p);
        int streak = now - t.last <= COOL_TICKS ? t.streak + 1 : 1;
        boolean wasHot = t.hot, hot = wasHot || streak >= HOT_AFTER;
        float before = t.heat, heat = before + HEAT_PER_HIT;
        target.setSecondsOnFire(hot ? 5 : 3);
        set(p, heat, streak, hot, now);
        glow(sl, p, s);
        if (hot && !wasHot) {   // the blade catches fire
            sl.playSound(null, p.getX(), p.getY(), p.getZ(), SoundEvents.FIRECHARGE_USE, SoundSource.PLAYERS, 1f, 0.8f);
            DivineEvents.particle(sl, ParticleTypes.FLAME, p.getX(), p.getY() + 1.2, p.getZ(), 20, 0.4, 0.05);
        }
        if (heat >= MAX_HEAT && before < MAX_HEAT)
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
        // the whip on every client: the physics rope sweeps from -WHIP_HALF*dir to +WHIP_HALF*dir (client/EmberWhipClient)
        whip(sl, p, LASH, yaw, dir, LASH_TICKS);
    }

    /** {@link Net.HFx#WHIP} modes (b) and the ticks of a lash / of the vortex turn for the client whip. */
    public static final int LASH = 0, VORTEX = 1, LASH_TICKS = 6, VORTEX_TICKS = 10;

    /** Tells the clients near the holder that the physics whip strikes (they draw it, the crack and its sound are theirs). */
    private static void whip(ServerLevel sl, Player p, int mode, double facing, int dir, int ticks) {
        Net.sendNear(sl, p.getX(), p.getY(), p.getZ(), p.getX(), p.getY(), p.getZ(),
                new Net.HFx(Net.HFx.WHIP, 0, p.getId(), mode, ticks, facing, dir, 0, WHIP_HALF, 0));
    }

    // ---------------------------------------------------------------- special attack (full heat: the Epic Fight weapon skill, EmberEpicFight)

    /** Only without Epic Fight: full heat + right click. With Epic Fight the right click is the guard (owner 19.11). */
    @Override
    public InteractionResultHolder<ItemStack> use(Level level, Player p, InteractionHand hand) {
        ItemStack s = p.getItemInHand(hand);
        if (EmberEpicFight.ON || hand != InteractionHand.MAIN_HAND || heat(p) < MAX_HEAT) return InteractionResultHolder.pass(s);
        if (level instanceof ServerLevel && p instanceof net.minecraft.server.level.ServerPlayer sp) special(sp, s);
        return InteractionResultHolder.sidedSuccess(s, level.isClientSide);
    }

    /**
     * The special attack by form (full heat): plays the Epic Fight animation, spends the heat at once and starts the effect and the
     * damage on the strike of the animation (at once without Epic Fight). Called by the Epic Fight weapon skill
     * (EmberEpicFight.Special), without Epic Fight by the right click. Returns false when the heat is not full.
     */
    public static boolean special(net.minecraft.server.level.ServerPlayer p, ItemStack s) {
        if (!(s.getItem() instanceof EmberBlade item) || heat(p) < MAX_HEAT || !(p.level() instanceof ServerLevel sl)) return false;
        boolean vortex = hot(p);
        int delay = EmberEpicFight.playSpecial(p, vortex);
        set(p, 0, vortex ? HOT_AFTER : 0, vortex, sl.getGameTime());   // the heat is spent at once: no double special
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
        if (GLOW.containsKey(p.getUUID()) || heat(p) <= 0) return;
        int inst = Fx.play(sl, Fx.fx("ember_heat").caster(p).scale(0.6 + 0.4 * heat(p) / MAX_HEAT));
        GLOW.put(p.getUUID(), inst);
        Tasks.add(() -> {
            ItemStack h = p.getMainHandItem();
            if (p.isAlive() && !p.isRemoved() && p.level() == sl && h.getItem() instanceof EmberBlade && heat(p) > 0 && Fx.running(inst)) return true;
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
        whip(sl, p, VORTEX, Math.atan2(f.z, f.x), 1, VORTEX_TICKS);   // the whip goes round with the ring (ember_vortex turns the same way)
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
