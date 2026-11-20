package ru.pohsmp.core.boss;

import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.Deque;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import net.minecraft.core.registries.Registries;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.ListTag;
import net.minecraft.nbt.StringTag;
import net.minecraft.nbt.Tag;
import net.minecraft.network.chat.Component;
import net.minecraft.network.chat.Style;
import net.minecraft.network.chat.TextColor;
import net.minecraft.resources.ResourceKey;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.sounds.SoundEvent;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.damagesource.DamageSource;
import net.minecraft.world.damagesource.DamageType;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.ai.attributes.AttributeInstance;
import net.minecraft.world.entity.ai.attributes.AttributeModifier;
import net.minecraft.world.entity.ai.attributes.Attributes;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.registries.ForgeRegistries;
import ru.pohsmp.core.PohCore;

/**
 * The common part of every cult boss (owned by the entity, see {@link PohBoss}): phases by health with the bar flash, the special
 * spells once per fight, scripts by ticks, invulnerability and AI off for scenes, the bar / music / look state sent to the clients,
 * scaling of health by players, the damage tally (who hurt it most), the three finales. Server side only (the client half lives in
 * boss/client and only gets messages).
 */
public final class BossCore {
    public final Mob mob;
    public final BossDef def;
    private final PohBoss boss;

    private int phase;
    private float lastFrac = 1;
    private final Set<String> usedSpecials = new HashSet<>();
    private final Deque<BossDef.Special> pending = new ArrayDeque<>();
    private Vec3 arena;
    private boolean started, finale, dead;
    private int lockTicks;
    private boolean lockInvulnerable, aiOff;
    private boolean barVisible, pulse, musicOn;
    private int look;
    /** Damage dealt to the boss by each player: (game time, amount), the last top_damage_window_seconds kept. */
    private final Map<UUID, Deque<double[]>> damageBy = new HashMap<>();
    private final List<BossTimeline> scripts = new ArrayList<>();
    private long nextFinisher;

    public BossCore(PohBoss boss, BossDef def) {
        this.boss = boss;
        this.mob = boss.bossMob();
        this.def = def;
    }

    // ---------------------------------------------------------------- lifecycle

    /** Called by /pohsmp boss right after the entity was added: the arena centre, health and damage from the config, the intro. */
    public void begin(ServerLevel sl, Vec3 arenaCentre) {
        arena = arenaCentre;
        applyConfig(sl);
        boss.onBossIntro();
    }

    /** The fight begins (after the intro): the bar appears, music, AI on. */
    public void startFight() {
        started = true;
        unlock();
        setBar(true);
        music(true);
    }

    public boolean started() {
        return started;
    }

    public boolean inFinale() {
        return finale || dead;
    }

    /** Body from [<boss>] (absolute values), health x players (N in arena_radius + count_radius_extra, at most max_counted_players). */
    private void applyConfig(ServerLevel sl) {
        BossConfig.PerBoss cfg = BossConfig.of(def.id);
        if (cfg == null) return;
        int players = Math.min(playersNear(arenaRadius() + BossConfig.get(BossConfig.COUNT_RADIUS_EXTRA)).stream()
                .filter(p -> !p.isCreative()).toList().size(), BossConfig.get(BossConfig.MAX_COUNTED));
        double mult = BossMath.healthMultiplier(players, BossConfig.get(BossConfig.HP_PER_PLAYER), BossConfig.get(BossConfig.HP_PER_PLAYER_SQ), 0);
        playerMult = mult;
        base(Attributes.MAX_HEALTH, BossConfig.get(cfg.hp) * mult);
        mob.setHealth(mob.getMaxHealth());
        base(Attributes.ARMOR, BossConfig.get(cfg.armor));
        base(Attributes.ARMOR_TOUGHNESS, BossConfig.get(cfg.toughness));
        base(Attributes.KNOCKBACK_RESISTANCE, BossConfig.get(cfg.knockback));
        base(Attributes.MOVEMENT_SPEED, BossConfig.get(cfg.speed));
        base(Attributes.ATTACK_DAMAGE, BossConfig.get(cfg.attack));
        irons("spell_power", BossConfig.get(cfg.spellPower));
        irons("spell_resist", BossConfig.get(cfg.spellResist));
        irons("fire_magic_resist", BossConfig.get(cfg.fireResist));
        irons("ice_magic_resist", BossConfig.get(cfg.iceResist));
        irons("holy_magic_resist", BossConfig.get(cfg.holyResist));
        irons("blood_magic_resist", BossConfig.get(cfg.bloodResist));
        irons("eldritch_magic_resist", BossConfig.get(cfg.eldritchResist));
        PohCore.LOG.info("[boss] {} spawned: {} players, health x{} = {}", def.id, players, mult, mob.getMaxHealth());
    }

    private double playerMult = 1;

    /** The health multiplier the fight began with (summons scale with it). */
    public double playerMultiplier() {
        return playerMult;
    }

    /** arena_radius of [<boss>] (or the fight radius). */
    public double arenaRadius() {
        BossConfig.PerBoss cfg = BossConfig.of(def.id);
        return cfg != null ? BossConfig.get(cfg.arena) : def.fightRadius;
    }

    private void base(net.minecraft.world.entity.ai.attributes.Attribute a, double v) {
        AttributeInstance i = mob.getAttribute(a);
        if (i != null && v >= 0) i.setBaseValue(v);
    }

    private void irons(String id, double v) {
        if (v < 0) return;
        var a = ForgeRegistries.ATTRIBUTES.getValue(new ResourceLocation("irons_spellbooks", id));
        if (a != null) base(a, v);
    }

    public Vec3 arena() {
        return arena != null ? arena : mob.position();
    }

    public int phase() {
        return phase;
    }

    public float healthFrac() {
        return mob.getMaxHealth() <= 0 ? 0 : mob.getHealth() / mob.getMaxHealth();
    }

    // ---------------------------------------------------------------- tick (call from the entity's tick on the server)

    public void tick() {
        if (!(mob.level() instanceof ServerLevel)) return;
        for (int i = 0; i < scripts.size(); i++) {
            BossTimeline s = scripts.get(i);
            if (!s.tick()) scripts.remove(i--);
        }
        if (lockTicks > 0 && --lockTicks == 0) unlock();
        if (!started || dead) return;
        float frac = healthFrac();
        if (!finale) {
            int p = BossMath.phaseOf(frac, def.phases);
            if (p > phase) {
                int from = phase;
                phase = p;
                syncBar(true);
                boss.onBossPhase(from, p);
            }
            if (BossConfig.get(BossConfig.SPECIALS))
                for (BossDef.Special s : def.specials)
                    if (!usedSpecials.contains(s.id()) && frac <= s.at()) {
                        usedSpecials.add(s.id());
                        pending.add(s);
                    }
            if (!pending.isEmpty() && boss.onBossSpecial(pending.peek())) pending.poll();
            if (def.finale != BossDef.Finale.DEATH && frac <= def.finaleAt + 1e-4) startFinale();
        }
        lastFrac = frac;
    }

    // ---------------------------------------------------------------- damage (call from the entity's hurt)

    /**
     * Filters damage dealt to the boss: none while locked invulnerable or after the finale began; for SURRENDER / LEAVE the health
     * never drops under finaleAt (the finale starts there). Records who dealt it. Returns the damage to apply (0 = cancel).
     */
    public float filterDamage(DamageSource src, float amount) {
        if (mob.level().isClientSide) return amount;
        if (finale || (lockTicks > 0 || aiOff) && lockInvulnerable) return 0;
        if (def.finale != BossDef.Finale.DEATH) amount = BossMath.clipToFloor(mob.getHealth(), amount, (float) (def.finaleAt * mob.getMaxHealth()));
        if (amount > 0 && src.getEntity() instanceof Player p)
            damageBy.computeIfAbsent(p.getUUID(), k -> new ArrayDeque<>()).add(new double[] {mob.level().getGameTime(), amount});
        return amount;
    }

    /** The player who dealt the boss the most damage and is still in the fight (alive, within reach); else the nearest. */
    public ServerPlayer strongestEnemy() {
        List<ServerPlayer> near = playersNear(arenaRadius() + 16);
        near.removeIf(Player::isCreative);
        return near.stream().max(Comparator.comparingDouble((ServerPlayer p) -> recentDamage(p.getUUID()))
                .thenComparingDouble(p -> -p.distanceToSqr(mob))).orElse(null);
    }

    /** Damage this player dealt to the boss in the last top_damage_window_seconds. */
    public double recentDamage(UUID player) {
        Deque<double[]> d = damageBy.get(player);
        if (d == null) return 0;
        long from = mob.level().getGameTime() - BossConfig.get(BossConfig.TOP_DAMAGE_WINDOW) * 20L;
        while (!d.isEmpty() && d.peekFirst()[0] < from) d.pollFirst();
        double sum = 0;
        for (double[] e : d) sum += e[1];
        return sum;
    }

    // ---------------------------------------------------------------- locks

    /** For `ticks`: AI off (if noAi) and invulnerable (if invulnerable). The fight around it goes on. */
    public void lock(int ticks, boolean noAi, boolean invulnerable) {
        lockInvulnerable = lockTicks > 0 && lockInvulnerable || invulnerable;   // a softer lock does not lift a running one
        lockTicks = Math.max(lockTicks, ticks);
        if (noAi && !aiOff) {
            aiOff = true;
            boss.setBossAi(false);
        }
    }

    public void unlock() {
        lockTicks = 0;
        lockInvulnerable = false;
        if (aiOff && !finale && !dead) {
            aiOff = false;
            boss.setBossAi(true);
        }
    }

    public boolean locked() {
        return lockTicks > 0 || aiOff;
    }

    // ---------------------------------------------------------------- scripts

    /** Runs a fixed-length script on the boss's clock. Returns it (cancel() to drop). */
    public BossTimeline play(BossTimeline t) {
        scripts.add(t);
        return t;
    }

    public boolean playing(String name) {
        for (BossTimeline t : scripts) if (t.name().equals(name) && !t.done()) return true;
        return false;
    }

    /** True while any script whose name starts with "scene:" runs (specials wait for it). */
    public boolean inScene() {
        for (BossTimeline t : scripts) if (t.name().startsWith("scene:") && !t.done()) return true;
        return false;
    }

    public void cancelScripts() {
        for (BossTimeline t : scripts) t.cancel();
        scripts.clear();
    }

    // ---------------------------------------------------------------- bar, music, look

    public void setBar(boolean visible) {
        barVisible = visible;
        syncBar(false);
    }

    public void setPulse(boolean on) {
        if (pulse == on) return;
        pulse = on;
        syncBar(false);
    }

    private BossNet.Msg barMsg(boolean flash) {
        int flags = (barVisible ? BossNet.BAR_VISIBLE : 0) | (pulse ? BossNet.BAR_PULSE : 0) | (flash ? BossNet.BAR_FLASH : 0);
        BossNet.Msg m = new BossNet.Msg(BossNet.BAR).ints(phase, flags, 0, 0).str(def.id, "");
        m.u = mob.getUUID();
        return m;
    }

    private void syncBar(boolean flash) {
        BossNet.tracking(mob, barMsg(flash));
    }

    public void music(boolean on) {
        musicOn = on;
        if (def.music != null) BossNet.tracking(mob, new BossNet.Msg(BossNet.MUSIC).ints(mob.getId(), on ? 1 : 0, 0, 0).str(PohCore.MODID + ":" + def.music, ""));
    }

    public void setLook(int flags) {
        look = flags;
        BossNet.tracking(mob, new BossNet.Msg(BossNet.LOOK).ints(mob.getId(), flags, 0, 0));
    }

    public void lookFlag(int flag, boolean on) {
        setLook(on ? look | flag : look & ~flag);
    }

    public int look() {
        return look;
    }

    /** Call from the entity's startSeenByPlayer: a late viewer gets the bar, the music and the look. */
    public void onSeen(ServerPlayer p) {
        if (mob.level().isClientSide) return;
        BossNet.to(p, barMsg(false));
        if (musicOn && def.music != null) BossNet.to(p, new BossNet.Msg(BossNet.MUSIC).ints(mob.getId(), 1, 0, 0).str(PohCore.MODID + ":" + def.music, ""));
        if (look != 0) BossNet.to(p, new BossNet.Msg(BossNet.LOOK).ints(mob.getId(), look, 0, 0));
    }

    /** Call from the entity's stopSeenByPlayer. */
    public void onUnseen(ServerPlayer p) {
        BossNet.Msg m = new BossNet.Msg(BossNet.BAR_STOP);
        m.u = mob.getUUID();
        BossNet.to(p, m);
        BossNet.to(p, new BossNet.Msg(BossNet.MUSIC).ints(mob.getId(), 0, 0, 0).str(PohCore.MODID + ":" + def.music, ""));
    }

    // ---------------------------------------------------------------- people

    public List<ServerPlayer> playersNear(double r) {
        List<ServerPlayer> out = new ArrayList<>();
        if (!(mob.level() instanceof ServerLevel sl)) return out;
        Vec3 c = arena != null ? arena : mob.position();
        for (ServerPlayer p : sl.players())
            if (!p.isSpectator() && p.isAlive() && (p.distanceToSqr(c) <= r * r || p.distanceToSqr(mob) <= r * r)) out.add(p);
        return out;
    }

    /** Fighters: players in the fight radius, not creative. */
    public List<ServerPlayer> fighters() {
        List<ServerPlayer> out = playersNear(def.fightRadius);
        out.removeIf(Player::isCreative);
        return out;
    }

    /** A chat line from the boss (its name, its colour) to everyone within r, and the same line over its head for subtitleTicks. */
    public void say(String key, double r, int subtitleTicks, double height) {
        Component line = Component.translatable(key).withStyle(Style.EMPTY.withColor(TextColor.fromRgb(def.color)).withItalic(true));
        Component msg = Component.empty().append(mob.getDisplayName()).append(Component.literal(": ").withStyle(s -> s.withColor(0xAAAAAA))).append(line);
        for (ServerPlayer p : playersNear(r)) {
            p.sendSystemMessage(msg);
            if (subtitleTicks > 0) {
                BossNet.Msg m = new BossNet.Msg(BossNet.SUBTITLE).ints(mob.getId(), subtitleTicks, def.color, 0).str(key, "");
                m.f = (float) height;
                BossNet.to(p, m);
            }
        }
    }

    /** An action bar line to everyone within r (warnings: «Глава Культа выносит приговор…»). */
    public void actionbar(double r, Component c) {
        for (ServerPlayer p : playersNear(r)) p.displayClientMessage(c, true);
    }

    public void sound(String id, float volume, float pitch) {
        sound(mob.position(), id, volume, pitch);
    }

    public void sound(Vec3 at, String id, float volume, float pitch) {
        mob.level().playSound(null, at.x, at.y, at.z, sound(id), SoundSource.HOSTILE, volume, pitch);
    }

    /** pohsmp_core:<id> (sounds.json); works unregistered (the packet carries the location). */
    public static SoundEvent sound(String id) {
        ResourceLocation rl = id.contains(":") ? new ResourceLocation(id) : new ResourceLocation(PohCore.MODID, id);
        SoundEvent reg = ForgeRegistries.SOUND_EVENTS.getValue(rl);
        return reg != null ? reg : SoundEvent.createVariableRangeEvent(rl);
    }

    // ---------------------------------------------------------------- scenes and titles

    /**
     * A camera scene for everyone within r (client: BossCam with the shots registered for sceneId). flags: BossNet.SCENE_*. Only
     * with SCENE_LOCK_INPUT the watchers are held (and not hurt) — the special scenes never stop the fight. focus / yaw: the scene's
     * second point and direction; extra: another entity id (the victim...) or -1. Returns who watches.
     */
    public List<ServerPlayer> scene(String sceneId, int ticks, int flags, double r, Vec3 focus, float yaw, int extra) {
        List<ServerPlayer> who = playersNear(r);
        if (!BossConfig.get(BossConfig.SCENES)) return who;
        for (ServerPlayer p : who) sceneFor(p, sceneId, ticks, flags, focus, yaw, extra);
        return who;
    }

    public void sceneFor(ServerPlayer p, String sceneId, int ticks, int flags, Vec3 focus, float yaw, int extra) {
        if (!BossConfig.get(BossConfig.SCENES)) return;
        BossNet.Msg m = new BossNet.Msg(BossNet.SCENE).ints(mob.getId(), ticks, flags, extra).pos(focus.x, focus.y, focus.z).str(sceneId, "");
        m.f = yaw;
        BossNet.to(p, m);
        if ((flags & BossNet.SCENE_LOCK_INPUT) != 0) BossScenes.protect(p, ticks + 20);
    }

    public void sceneStop(List<ServerPlayer> who, String sceneId) {
        for (ServerPlayer p : who) {
            BossNet.to(p, new BossNet.Msg(BossNet.SCENE_STOP).ints(mob.getId(), 0, 0, 0).str(sceneId, ""));
            BossScenes.unprotect(p);
        }
    }

    /** A title picture (textures/gui/title/<base>_<lang>.png) shown hold ticks, then out in 0.75 s; subKey: a line under it or null. */
    public void title(List<ServerPlayer> who, String base, int hold, String subKey) {
        for (ServerPlayer p : who) BossNet.to(p, new BossNet.Msg(BossNet.TITLE).ints(hold, 0, 0, 0).str(base, subKey));
    }

    // ---------------------------------------------------------------- finales

    /** DEATH: call from the entity's die(): bar and music off, AI off; the entity then plays its death scene. */
    public void onDeath() {
        if (dead) return;
        dead = true;
        cancelScripts();
        pending.clear();
        endBar();
    }

    public boolean dead() {
        return dead;
    }

    private void startFinale() {
        if (finale) return;
        finale = true;
        cancelScripts();
        pending.clear();
        lock(Integer.MAX_VALUE / 2, true, true);
        mob.setTarget(null);
        endBar();
        boss.onBossFinale();
    }

    /** Bar off for everyone, music fades out. */
    public void endBar() {
        barVisible = false;
        BossNet.Msg m = new BossNet.Msg(BossNet.BAR_STOP);
        m.u = mob.getUUID();
        BossNet.tracking(mob, m);
        music(false);
    }

    /** End of a SURRENDER / LEAVE finale scene: the peaceful NPC takes its place, or it vanishes. */
    public void endFinale() {
        if (!(mob.level() instanceof ServerLevel sl)) return;
        if (def.finale == BossDef.Finale.SURRENDER && def.npc != null) {
            EntityType<?> t = ForgeRegistries.ENTITY_TYPES.getValue(new ResourceLocation(PohCore.MODID, def.npc));
            Entity npc = t != null ? t.create(sl) : null;
            if (npc != null) {
                npc.moveTo(mob.getX(), mob.getY(), mob.getZ(), mob.getYRot(), 0);
                npc.setYHeadRot(mob.getYRot());
                if (npc instanceof Mob m) m.setPersistenceRequired();
                sl.addFreshEntity(npc);
            } else PohCore.LOG.warn("[boss] {}: no NPC entity pohsmp_core:{}", def.id, def.npc);
        }
        mob.discard();
    }

    // ---------------------------------------------------------------- finisher bookkeeping

    public boolean finisherReady(long now) {
        return def.finisher && now >= nextFinisher && started && !finale && !dead;
    }

    public void finisherUsed(long now) {
        nextFinisher = now + BossConfig.get(BossConfig.FINISHER_COOLDOWN) * 20L;
    }

    /** The damage type pohsmp_core:<id>_finisher (data/pohsmp_core/damage_type), death.attack.pohsmp_core.<id>_finisher. */
    public DamageSource finisherDamage(ServerLevel sl) {
        ResourceKey<DamageType> k = ResourceKey.create(Registries.DAMAGE_TYPE, new ResourceLocation(PohCore.MODID, def.id + "_finisher"));
        var reg = sl.registryAccess().registryOrThrow(Registries.DAMAGE_TYPE);
        return reg.getHolder(k).map(h -> new DamageSource(h, mob)).orElseGet(() -> sl.damageSources().mobAttack(mob));
    }

    private DamageSource source(String type) {
        ServerLevel sl = (ServerLevel) mob.level();
        ResourceKey<DamageType> k = ResourceKey.create(Registries.DAMAGE_TYPE, new ResourceLocation(PohCore.MODID, type));
        return sl.registryAccess().registryOrThrow(Registries.DAMAGE_TYPE).getHolder(k).map(h -> new DamageSource(h, mob))
                .orElseGet(() -> sl.damageSources().mobAttack(mob));
    }

    /** The bosses' own attacks (pohsmp_core:boss_attack): not scaled by the world's difficulty, armour counts (balance 1.2). */
    public DamageSource attackDamage() {
        return source("boss_attack");
    }

    /** Mechanics (walls, snapped threads...: pohsmp_core:boss_mechanic): through armour and enchantments, a share of the victim's health. */
    public DamageSource mechanicDamage() {
        return source("boss_mechanic");
    }

    // ---------------------------------------------------------------- save

    public void save(CompoundTag tag) {
        CompoundTag t = new CompoundTag();
        t.putInt("phase", phase);
        t.putBoolean("started", started);
        if (arena != null) {
            t.putDouble("ax", arena.x);
            t.putDouble("ay", arena.y);
            t.putDouble("az", arena.z);
        }
        ListTag used = new ListTag();
        for (String s : usedSpecials) used.add(StringTag.valueOf(s));
        t.put("specials", used);
        tag.put("pohsmp_boss", t);
    }

    public void load(CompoundTag tag) {
        if (!tag.contains("pohsmp_boss")) return;
        CompoundTag t = tag.getCompound("pohsmp_boss");
        phase = t.getInt("phase");
        started = t.getBoolean("started");
        if (t.contains("ax")) arena = new Vec3(t.getDouble("ax"), t.getDouble("ay"), t.getDouble("az"));
        for (Tag s : t.getList("specials", Tag.TAG_STRING)) usedSpecials.add(s.getAsString());
        started = true;   // saved mid-intro: the scripts are gone, the fight just goes on
        barVisible = true;
        musicOn = true;
    }
}
