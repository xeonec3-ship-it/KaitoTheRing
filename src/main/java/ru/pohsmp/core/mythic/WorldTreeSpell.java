package ru.pohsmp.core.mythic;

import io.redspace.ironsspellbooks.api.registry.SchoolRegistry;
import java.util.HashMap;
import java.util.Iterator;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import net.minecraft.network.chat.MutableComponent;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.sounds.SoundEvent;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.tags.DamageTypeTags;
import net.minecraft.world.effect.MobEffectInstance;
import net.minecraft.world.effect.MobEffects;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.event.entity.living.LivingHurtEvent;
import net.minecraftforge.event.entity.player.AttackEntityEvent;
import net.minecraftforge.event.entity.player.PlayerInteractEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import ru.pohsmp.core.Reg;
import ru.pohsmp.core.ServerConfig;
import ru.pohsmp.core.fx.Fx;
import ru.pohsmp.core.spell.Cutscene;
import ru.pohsmp.core.spell.HigherSpell;

/**
 * T23 «Древо мира» (nature, Mythic). 12 s: a giant tree grows where the caster looks (a model, the world's blocks stay). Then [world_tree]
 * seconds: roots come out under every enemy within the radius, hold it (strong slow, no jumping) and pull it to the trunk; a root breaks
 * after a few hits by its victim (attacks, punches; fire on the victim counts double) and the next one comes no sooner than the cooldown.
 * Allies under the crown get Regeneration II. At the end the tree blooms: spores poison and blind enemies near the trunk.
 */
public class WorldTreeSpell extends MythicT23 {
    public static final String PATH = "world_tree";
    private static final int CAST = 240, FX_ZONE = 400;
    private static final double TRUNK = 3.5;

    public WorldTreeSpell() {
        super(PATH, SchoolRegistry.NATURE_RESOURCE, CAST, Cutscene.WORLD_TREE);
    }

    @Override public Optional<SoundEvent> getCastStartSound() { return Optional.of(SoundEvents.ROOTED_DIRT_PLACE); }

    @Override
    public List<MutableComponent> getUniqueInfo(int level, LivingEntity caster) {
        return List.of(castLine(), line("world_tree.point", n(d(ServerConfig.WT_RANGE))),
                line("world_tree.roots", n(d(ServerConfig.WT_RADIUS)), n(d(ServerConfig.WT_SECONDS))),
                line("world_tree.heal"), line("world_tree.bloom", n(d(ServerConfig.WT_BLOOM_RADIUS))));
    }

    @Override
    protected void aim(ServerLevel sl, LivingEntity caster, Cast c) {
        c.point = ground(sl, caster, lookPoint(sl, caster, d(ServerConfig.WT_RANGE)));
        Vec3 to = c.point.subtract(caster.position()).multiply(1, 0, 1);
        if (to.lengthSqr() > 1) c.dir = to.normalize();
    }

    @Override
    protected Vec3 focus(Cast c) {
        return c.point;
    }

    @Override
    protected int castFx(ServerLevel sl, LivingEntity caster, Cast c) {
        return Fx.play(sl, Fx.fx("world_tree_cast").at(caster.position()).caster(caster).point("tree", c.point));
    }

    @Override
    protected void castTick(ServerLevel sl, LivingEntity caster, Cast c) {
        Vec3 p = c.point;
        switch (c.age) {
            case 22 -> {
                sl.playSound(null, p.x, p.y, p.z, SoundEvents.ROOTED_DIRT_BREAK, SoundSource.PLAYERS, 2f, 0.6f);
                sl.playSound(null, p.x, p.y, p.z, SoundEvents.AZALEA_PLACE, SoundSource.PLAYERS, 2f, 0.7f);
            }
            case 140 -> sl.playSound(null, p.x, p.y + 20, p.z, SoundEvents.AZALEA_LEAVES_PLACE, SoundSource.PLAYERS, 4f, 0.5f);
            case 234 -> {
                Cutscene.flash(sl, c.watchers, 12, 0xC8FF9A);
                sl.playSound(null, p.x, p.y + 20, p.z, SoundEvents.BEACON_ACTIVATE, SoundSource.PLAYERS, 4f, 0.6f);
            }
            default -> {}
        }
        if (c.age > 60 && c.age < 200 && c.age % 12 == 0)
            sl.playSound(null, p.x, p.y + c.age / 10.0, p.z, SoundEvents.WOOD_PLACE, SoundSource.PLAYERS, 2.5f, 0.4f + sl.random.nextFloat() * 0.2f);
    }

    @Override
    protected void release(ServerLevel sl, LivingEntity caster, Cast c) {
        ZONES.add(new Tree(this, sl, caster, c.point, c.fx));
    }

    // ---------------------------------------------------------------- the tree

    private static final class Root {
        final LivingEntity v;
        final int fx;
        int hp;
        long lastHit;

        Root(LivingEntity v, int fx, int hp) {
            this.v = v;
            this.fx = fx;
            this.hp = hp;
        }
    }

    private static final class Tree implements Zone {
        final WorldTreeSpell spell;
        final ServerLevel sl;
        final LivingEntity caster;
        final Vec3 p;
        final int castFx, life;
        final double r, pull, crown;
        final Map<UUID, Root> roots = new HashMap<>();
        final Map<UUID, Long> wait = new HashMap<>();
        int age;

        Tree(WorldTreeSpell spell, ServerLevel sl, LivingEntity caster, Vec3 p, int castFx) {
            this.spell = spell;
            this.sl = sl;
            this.caster = caster;
            this.p = p;
            this.castFx = castFx;
            this.life = ticks(ServerConfig.WT_SECONDS);
            this.r = d(ServerConfig.WT_RADIUS);
            this.pull = d(ServerConfig.WT_PULL);
            this.crown = d(ServerConfig.WT_CROWN);
        }

        @Override
        public boolean tick() {
            age++;
            long now = sl.getGameTime();
            if (age >= life) {
                bloom();
                return false;
            }
            if (age % 5 == 0)   // new roots under the enemies in the zone
                for (LivingEntity v : HigherSpell.around(sl, p, r, e -> enemy(caster, e))) {
                    if (roots.containsKey(v.getUUID()) || now < wait.getOrDefault(v.getUUID(), 0L) || held(v.getUUID()) != null) continue;
                    int fx = Fx.play(sl, Fx.fx("world_tree_root").at(v.position()).caster(v).attach(v));
                    roots.put(v.getUUID(), new Root(v, fx, i(ServerConfig.WT_ROOT_HITS)));
                    sl.playSound(null, v.getX(), v.getY(), v.getZ(), SoundEvents.ROOTED_DIRT_BREAK, SoundSource.PLAYERS, 1.5f, 0.7f);
                }
            for (Iterator<Root> it = roots.values().iterator(); it.hasNext(); ) {
                Root rt = it.next();
                LivingEntity v = rt.v;
                if (!v.isAlive() || v.isRemoved() || v.level() != sl || HigherSpell.friendly(caster, v)
                        || v.position().distanceToSqr(p) > r * r * 1.3) {
                    Fx.stop(sl, rt.fx, "");
                    it.remove();
                    continue;
                }
                hold(rt);
            }
            if (age % 40 == 1)   // allies under the crown
                for (LivingEntity a : HigherSpell.around(sl, p, crown, e -> ally(caster, e))) {
                    a.addEffect(new MobEffectInstance(MobEffects.REGENERATION, 60, 1, false, true, true));
                    Fx.play(sl, Fx.fx("world_tree_heal").at(a.position()).caster(a).attach(a));
                }
            if (age % 30 == 0) sl.playSound(null, p.x, p.y + 12, p.z, SoundEvents.AZALEA_LEAVES_BREAK, SoundSource.AMBIENT, 2f, 0.6f);
            return true;
        }

        void hold(Root rt) {
            LivingEntity v = rt.v;
            if (v.tickCount % 10 == 0) {
                v.addEffect(new MobEffectInstance(Reg.ENTANGLED.get(), 15, 0, false, false, true));
                v.addEffect(new MobEffectInstance(MobEffects.MOVEMENT_SLOWDOWN, 15, 3, false, false, false));
            }
            Vec3 to = p.subtract(v.position()).multiply(1, 0, 1);
            double dist = to.length();
            Vec3 m = v.getDeltaMovement();
            double y = Math.min(m.y, 0);   // no jumping out
            if (dist > TRUNK) {
                Vec3 step = to.scale(pull / dist);
                v.setDeltaMovement(step.x, y, step.z);
            } else v.setDeltaMovement(0, y, 0);
            v.hurtMarked = true;
        }

        boolean hit(LivingEntity v, int amount) {
            Root rt = roots.get(v.getUUID());
            if (rt == null) return false;
            long now = sl.getGameTime();
            if (now - rt.lastHit < 8) return true;
            rt.lastHit = now;
            rt.hp -= amount;
            sl.playSound(null, v.getX(), v.getY(), v.getZ(), SoundEvents.WOOD_HIT, SoundSource.PLAYERS, 1.2f, 0.8f);
            if (rt.hp <= 0) {
                Fx.stop(sl, rt.fx, "");
                Fx.play(sl, Fx.fx("world_tree_root_break").at(v.position()));
                sl.playSound(null, v.getX(), v.getY(), v.getZ(), SoundEvents.WOOD_BREAK, SoundSource.PLAYERS, 1.5f, 0.7f);
                roots.remove(v.getUUID());
                wait.put(v.getUUID(), now + ticks(ServerConfig.WT_ROOT_COOLDOWN));
                v.removeEffect(Reg.ENTANGLED.get());
                v.removeEffect(MobEffects.MOVEMENT_SLOWDOWN);
                say(v, "world_tree.root_broken");
            }
            return true;
        }

        void bloom() {
            stop();
            Fx.play(sl, Fx.fx("world_tree_bloom").at(p).caster(caster));
            if (life != FX_ZONE && castFx >= 0) Fx.stop(sl, castFx, "");
            double br = d(ServerConfig.WT_BLOOM_RADIUS);
            sl.playSound(null, p.x, p.y + 4, p.z, SoundEvents.SPORE_BLOSSOM_BREAK, SoundSource.PLAYERS, 4f, 0.6f);
            sl.playSound(null, p.x, p.y + 4, p.z, SoundEvents.CHERRY_LEAVES_BREAK, SoundSource.PLAYERS, 4f, 0.5f);
            for (LivingEntity v : HigherSpell.around(sl, p, br, e -> enemy(caster, e))) {
                v.addEffect(new MobEffectInstance(MobEffects.POISON, 120, 1));
                v.addEffect(new MobEffectInstance(MobEffects.BLINDNESS, 60, 0));
            }
        }

        @Override
        public void stop() {
            for (Root rt : roots.values()) {
                Fx.stop(sl, rt.fx, "");
                rt.v.removeEffect(Reg.ENTANGLED.get());
            }
            roots.clear();
        }
    }

    private static Tree held(UUID v) {
        for (Zone z : ZONES) if (z instanceof Tree t && t.roots.containsKey(v)) return t;
        return null;
    }

    private static void strike(LivingEntity v, int amount) {
        Tree t = held(v.getUUID());
        if (t != null) t.hit(v, amount);
    }

    public static final class Events {
        private Events() {}

        @SubscribeEvent
        public static void onAttack(AttackEntityEvent e) {
            if (!e.getEntity().level().isClientSide && !ZONES.isEmpty()) strike(e.getEntity(), 1);
        }

        @SubscribeEvent
        public static void onPunch(PlayerInteractEvent.LeftClickBlock e) {
            if (!e.getLevel().isClientSide && !ZONES.isEmpty()) strike(e.getEntity(), 1);
        }

        @SubscribeEvent
        public static void onHurt(LivingHurtEvent e) {
            if (!ZONES.isEmpty() && !e.getEntity().level().isClientSide && e.getSource().is(DamageTypeTags.IS_FIRE)) strike(e.getEntity(), 2);
        }
    }
}
