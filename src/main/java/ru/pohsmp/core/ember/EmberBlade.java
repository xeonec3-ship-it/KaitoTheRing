package ru.pohsmp.core.ember;

import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.UUID;
import net.minecraft.server.level.ServerPlayer;
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
 * Manager 19.11, three forms in a cycle (item property pohsmp_core:form 0/1/2, the HUD gauge over the hotbar shows the heat):
 * <ul>
 * <li>0 — cold sword: {@code ember.heatHitsToBurn} hits set it burning (the gauge fills towards that).</li>
 * <li>1 — burning sword (ember_blade_hot): {@code ember.hitsToSpecial} more hits fill the heat; full heat + the weapon skill
 *     (without Epic Fight: right click) — "Last Ember": the blade into the ground, three waves of fire pillars (3/5/7 blocks),
 *     then the blade turns into the whip. 10 s without hits — back to cold.</li>
 * <li>2 — whip (ember_whip_handle, Epic Fight TWO_HAND with the lashes): starts at full heat, the heat burns down
 *     {@link #WHIP_DECAY} a second, hits add {@link #WHIP_HIT_HEAT}; "Fire Vortex" (a full turn of the whip, a ring of fire r 5)
 *     costs {@link #VORTEX_COST}. When the heat is gone — back to the cold sword.</li>
 * </ul>
 * Looks (pillar and ring effects, HUD texture, swing animations) — the manager. The whip itself is a physics rope drawn on the
 * client (client/EmberWhipClient, ember/WhipSim): it hangs from the hilt in the whip form, follows the hand of any animation and
 * lashes when the server sends {@link Net.HFx#WHIP} (a lash here, the turn of "Fire Vortex").
 */
public class EmberBlade extends SwordItem {
    public static final String NAME = "ember_blade";
    public static final float MAX_HEAT = 100, WHIP_DECAY = 5, WHIP_HIT_HEAT = 8, VORTEX_COST = 40;
    public static final int COLD = 0, BURNING = 1, WHIP = 2;
    /** Owner 19.11: 10 s without hits — the burning sword goes out, the count of the cold one is lost. */
    public static final int COOL_TICKS = 200;
    /** Ticks of fx/ember_last_heat.json after its start when the blade has turned into the whip. */
    static final int TO_WHIP_AFTER = 24;
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
        int hits, form;
        long last;
    }

    private static int toBurn() {
        try {
            return ru.pohsmp.core.ServerConfig.EMBER_HITS_TO_BURN.get();
        } catch (RuntimeException e) {   // config not loaded yet
            return 15;
        }
    }

    private static int toSpecial() {
        try {
            return ru.pohsmp.core.ServerConfig.EMBER_HITS_TO_SPECIAL.get();
        } catch (RuntimeException e) {
            return 5;
        }
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
        return st(holder).form == WHIP;
    }

    /** The holder's form: {@link #COLD}, {@link #BURNING} or {@link #WHIP}. */
    public static int form(Entity holder) {
        return st(holder).form;
    }

    /** The special attack of the current form can go: Last Ember at full heat, Fire Vortex while the whip has {@link #VORTEX_COST}. */
    public static boolean ready(Entity holder) {
        St s = st(holder);
        return s.form == BURNING ? s.heat >= MAX_HEAT : s.form == WHIP && s.heat >= VORTEX_COST;
    }

    private static void set(Player p, float heat, int hits, int form, long last) {
        St s = SERVER.computeIfAbsent(p.getUUID(), k -> new St());
        heat = Math.max(0, Math.min(MAX_HEAT, heat));
        boolean changed = s.heat != heat || s.form != form, formChanged = s.form != form;
        s.heat = heat;
        s.hits = hits;
        s.form = form;
        s.last = last;
        if (changed) sync(p, null);
        // owner 19.11 «the same animations in both forms»: the stack does not change with the form, so Epic Fight does not
        // re-read the style's idle/walk/run by itself — ask it to on every form change (the attack combo follows the style on each hit)
        if (formChanged && p instanceof net.minecraft.server.level.ServerPlayer sp) EmberEpicFight.formChanged(sp);
    }

    /** To the holder and his watchers, or only to {@code to}. */
    private static void sync(Player p, net.minecraft.server.level.ServerPlayer to) {
        St s = st(p);
        Object msg = new ru.pohsmp.core.net.Net.EmberMsg(p.getId(), s.heat, s.form);
        if (to != null) ru.pohsmp.core.net.Net.CH.send(net.minecraftforge.network.PacketDistributor.PLAYER.with(() -> to), msg);
        else ru.pohsmp.core.net.Net.CH.send(net.minecraftforge.network.PacketDistributor.TRACKING_ENTITY_AND_SELF.with(() -> p), msg);
    }

    /** Client: the state the server sent (Net.EmberMsg). */
    public static void clientSet(int entity, float heat, int form) {
        St s = CLIENT.computeIfAbsent(entity, k -> new St());
        s.heat = heat;
        s.form = form;
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
        if (t.form == COLD && t.hits == 0 && t.heat <= 0) return;
        if (t.last < 0) return;   // Last Ember is turning the blade into the whip
        long idle = level.getGameTime() - t.last;
        float heat = t.heat;
        int form = t.form, hits = t.hits;
        if (form == WHIP) heat -= WHIP_DECAY;   // the whip lasts while the heat does
        else if (idle >= COOL_TICKS) {   // 10 s without hits: the count is lost, the burning sword goes out
            heat = 0;
            hits = 0;
            form = COLD;
        }
        if (form == WHIP && heat <= 0) {
            form = COLD;
            hits = 0;
        }
        if (form != t.form && level instanceof ServerLevel sl)
            sl.playSound(null, holder.getX(), holder.getY(), holder.getZ(), SoundEvents.FIRE_EXTINGUISH, SoundSource.PLAYERS, 0.5f, 1.4f);
        if (heat != t.heat || form != t.form || hits != t.hits) set(p, heat, hits, form, t.last);
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
            Swing w = SWINGS.get(p.getUUID());
            if (w == null) {   // a sword hit, or no Epic Fight: every hit counts
                onHit(sl, p, s, e.getEntity());
                return;
            }
            // an Epic Fight whip swing: one heat per swing; a foe the lash already burnt this swing takes no second hit from the collider
            UUID id = e.getEntity().getUUID();
            if (!w.counted) {
                w.counted = true;
                onHit(sl, p, s, e.getEntity());
            }
            if (w.lashed.contains(id)) e.setCanceled(true);
            else w.hit.add(id);
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
            SWINGS.remove(e.getEntity().getUUID());
        }

        @SubscribeEvent
        public static void onUnload(net.minecraftforge.event.level.LevelEvent.Unload e) {
            if (e.getLevel().isClientSide()) CLIENT.clear();
        }
    }

    private static void onHit(ServerLevel sl, Player p, ItemStack s, LivingEntity target) {
        long now = sl.getGameTime();
        St t = st(p);
        int form = t.form, hits = t.hits + 1;
        float before = t.heat, heat;
        if (t.last < 0) return;   // turning into the whip: hits of the special do not count
        if (form == COLD) {
            int need = toBurn();
            if (hits >= need) {   // the blade catches fire
                form = BURNING;
                hits = 0;
                heat = 0;
                sl.playSound(null, p.getX(), p.getY(), p.getZ(), SoundEvents.FIRECHARGE_USE, SoundSource.PLAYERS, 1f, 0.8f);
                DivineEvents.particle(sl, ParticleTypes.FLAME, p.getX(), p.getY() + 1.2, p.getZ(), 20, 0.4, 0.05);
            } else heat = MAX_HEAT * hits / need;
        } else if (form == BURNING) heat = Math.min(MAX_HEAT, MAX_HEAT * hits / toSpecial());
        else heat = before + WHIP_HIT_HEAT;
        target.setSecondsOnFire(t.form == COLD ? 2 : t.form == BURNING ? 4 : 5);
        set(p, heat, hits, form, now);
        if (form != COLD) glow(sl, p, s);
        if (form == BURNING && heat >= MAX_HEAT && before < MAX_HEAT)   // Last Ember is ready
            sl.playSound(null, p.getX(), p.getY(), p.getZ(), SoundEvents.BLAZE_AMBIENT, SoundSource.PLAYERS, 0.8f, 1.6f);
        if (t.form == WHIP && !EmberEpicFight.ON) lash(sl, p, java.util.Set.of(target.getUUID()));   // with Epic Fight the lash goes on every swing
    }

    // ---------------------------------------------------------------- Epic Fight whip swings (owner 19.11: the whip hit like a plain sword)

    /** One whip swing of the holder: foes struck by the collider, foes burnt by the lash, heat already counted. */
    private static final class Swing {
        final Set<UUID> hit = new HashSet<>(), lashed = new HashSet<>();
        boolean counted;
    }

    private static final java.util.Map<UUID, Swing> SWINGS = new java.util.HashMap<>();

    /** EmberEpicFight: a whip swing (whip1-3) began. */
    static void swingStart(Player p) {
        SWINGS.put(p.getUUID(), new Swing());
    }

    /** EmberEpicFight: the swing left the whip combo. */
    static void swingEnd(Player p) {
        SWINGS.remove(p.getUUID());
    }

    /**
     * EmberEpicFight: the contact moment of a whip swing — the lash burns the 6-block arc whether the collider hit or not (foes the collider
     * already struck this swing are left out); a lash that burns anyone counts as the swing's hit for the heat.
     */
    static void swingContact(ServerPlayer p) {
        Swing w = SWINGS.get(p.getUUID());
        if (w == null || !hot(p) || !(p.level() instanceof ServerLevel sl)) return;
        List<LivingEntity> burnt = lash(sl, p, w.hit);
        for (LivingEntity e : burnt) w.lashed.add(e.getUUID());
        if (!burnt.isEmpty() && !w.counted) {
            w.counted = true;
            onHit(sl, p, p.getMainHandItem(), burnt.get(0));
        }
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

    /** Whip form: the lash sweeps right to left (the 2nd combo lash: left to right) over 4 ticks and burns everyone in the arc but those already struck. Returns the burnt. */
    private static List<LivingEntity> lash(ServerLevel sl, Player p, Set<UUID> struck) {
        Vec3 o = p.position().add(0, p.getBbHeight() * 0.6, 0), f = flat(p.getLookAngle());
        double yaw = Math.atan2(f.z, f.x);
        float dmg = damage(p) * 0.6f;
        List<LivingEntity> burnt = new java.util.ArrayList<>();
        for (LivingEntity e : HigherSpell.around(sl, p.position(), WHIP_LEN + 1, e -> e != p && !struck.contains(e.getUUID()) && !HigherSpell.friendly(p, e))) {
            Vec3 d = e.position().subtract(p.position()).multiply(1, 0, 1);
            double dist = d.length();
            if (dist > WHIP_LEN + e.getBbWidth() / 2 || Math.abs(e.getY() - p.getY()) > 3) continue;
            if (dist > 0.5 && Math.acos(Math.max(-1, Math.min(1, d.normalize().dot(f)))) > WHIP_HALF) continue;
            hurt(sl, p, e, dmg, 4);
            burnt.add(e);
        }
        sl.playSound(null, o.x, o.y, o.z, SoundEvents.BLAZE_SHOOT, SoundSource.PLAYERS, 0.7f, 1.3f);
        int dir = EmberEpicFight.lashDir(p);   // the 2nd lash of the Epic Fight combo goes left to right
        // the whip on every client: the physics rope sweeps from -WHIP_HALF*dir to +WHIP_HALF*dir (client/EmberWhipClient)
        whip(sl, p, LASH, yaw, dir, LASH_TICKS);
        return burnt;
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
        if (EmberEpicFight.ON || hand != InteractionHand.MAIN_HAND || !ready(p)) return InteractionResultHolder.pass(s);
        if (level instanceof ServerLevel && p instanceof net.minecraft.server.level.ServerPlayer sp) special(sp, s);
        return InteractionResultHolder.sidedSuccess(s, level.isClientSide);
    }

    /**
     * The special attack by form (full heat): plays the Epic Fight animation, spends the heat at once and starts the effect and the
     * damage on the strike of the animation (at once without Epic Fight). Called by the Epic Fight weapon skill
     * (EmberEpicFight.Special), without Epic Fight by the right click. Returns false when the form's special is not ready.
     * Last Ember turns the burning sword into the whip at full heat when its pillars are done ({@link #TO_WHIP_AFTER}).
     */
    public static boolean special(net.minecraft.server.level.ServerPlayer p, ItemStack s) {
        if (!(s.getItem() instanceof EmberBlade item) || !ready(p) || !(p.level() instanceof ServerLevel sl)) return false;
        St t = st(p);
        boolean vortex = t.form == WHIP;
        int delay = EmberEpicFight.playSpecial(p, vortex);
        // the heat is spent at once: no double special; last = -1 holds the burning sword (no cooling, no counting) until the whip
        if (vortex) set(p, t.heat - VORTEX_COST, t.hits, WHIP, sl.getGameTime());
        else set(p, 0, 0, BURNING, -1);
        later(delay, () -> {
            if (!p.isAlive() || p.level() != sl) {
                if (!vortex) set(p, 0, 0, COLD, sl.getGameTime());
                return;
            }
            if (vortex) fireVortex(sl, p, s);
            else {
                lastEmber(sl, p, s);
                later(TO_WHIP_AFTER, () -> {
                    if (p.hasDisconnected()) return;   // logged out: the state is already dropped
                    set(p, MAX_HEAT, 0, p.isAlive() ? WHIP : COLD, sl.getGameTime());
                    if (p.isAlive() && p.level() == sl) {
                        sl.playSound(null, p.getX(), p.getY(), p.getZ(), SoundEvents.FIRECHARGE_USE, SoundSource.PLAYERS, 1f, 0.6f);
                        glow(sl, p, p.getMainHandItem());
                    }
                });
            }
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
        if (GLOW.containsKey(p.getUUID()) || form(p) == COLD || !(s.getItem() instanceof EmberBlade)) return;
        int inst = Fx.play(sl, Fx.fx("ember_heat").caster(p).scale(0.6 + 0.4 * heat(p) / MAX_HEAT));
        GLOW.put(p.getUUID(), inst);
        Tasks.add(() -> {
            ItemStack h = p.getMainHandItem();
            if (p.isAlive() && !p.isRemoved() && p.level() == sl && h.getItem() instanceof EmberBlade && form(p) != COLD && Fx.running(inst)) return true;
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
