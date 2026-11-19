package ru.pohsmp.core.spell.illusion;

import io.redspace.ironsspellbooks.api.magic.MagicData;
import io.redspace.ironsspellbooks.api.spells.CastSource;
import io.redspace.ironsspellbooks.api.spells.CastType;
import io.redspace.ironsspellbooks.api.spells.SpellRarity;
import io.redspace.ironsspellbooks.api.util.AnimationHolder;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import net.minecraft.network.chat.MutableComponent;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.Vec3;
import ru.pohsmp.core.ServerConfig;
import ru.pohsmp.core.fx.Fx;
import ru.pohsmp.core.illusion.Copies;
import ru.pohsmp.core.illusion.Illusions;
import ru.pohsmp.core.spell.CastAnims;
import ru.pohsmp.core.spell.Tasks;

/**
 * T22 «Отражения»: [mirror_images] copies of the caster stand up around it (2.5 blocks, evenly round). They repeat its moves 4-10 ticks
 * late (run, jump, sneak, swing), only the enemies in range see them (and those who come closer later), each takes hitsToBreak hits.
 * About every swapEverySeconds the caster quietly swaps places with a random copy. A copy's swing in reach is illusory damage.
 * No status effect on the caster (owner 19.11).
 */
public class MirrorImagesSpell extends IllusionBase {
    public static final String PATH = "mirror_images";

    public MirrorImagesSpell() {
        super(PATH, SpellRarity.RARE, 5, 0, ServerConfig.MI_MANA, ServerConfig.MI_COOLDOWN);
    }

    @Override public CastType getCastType() { return CastType.INSTANT; }
    @Override public AnimationHolder getCastStartAnimation() { return CastAnims.of("illusion_mirror_images_cast"); }

    private double seconds(int level) {
        return d(ServerConfig.MI_SECONDS) * lv(level, 1, 1.5);
    }

    @Override
    public List<MutableComponent> getUniqueInfo(int level, LivingEntity caster) {
        return List.of(ui("copies", i(ServerConfig.MI_COPIES)), ui("time", n(seconds(level))));
    }

    /** caster -> its running cast (victims that come close later are added) */
    private static final Map<UUID, Run> RUNS = new HashMap<>();

    private static final class Run {
        final List<Copies.Copy> copies = new ArrayList<>();
        final long until;
        long nextSwap;

        Run(long until) {
            this.until = until;
        }
    }

    private static int TAG = 2_000_000;

    @Override
    public void onCast(Level level, int spellLevel, LivingEntity caster, CastSource source, MagicData md) {
        if (level instanceof ServerLevel sl) {
            Copies.clear(caster);
            int ticks = (int) Math.round(seconds(spellLevel) * 20);
            int n = i(ServerConfig.MI_COPIES);
            double range = d(ServerConfig.MI_RANGE);
            List<ServerPlayer> victims = Illusions.victims(sl, caster, range);
            fx(sl, Fx.fx("illusion_mirror_images_cast").at(caster.position()).caster(caster), "illusion_mirror_images_cast");
            sl.playSound(null, caster.getX(), caster.getY() + 1, caster.getZ(), SoundEvents.AMETHYST_BLOCK_CHIME, SoundSource.PLAYERS, 1.2f, 1.1f);
            sl.playSound(null, caster.getX(), caster.getY() + 1, caster.getZ(), SoundEvents.ILLUSIONER_MIRROR_MOVE, SoundSource.PLAYERS, 1f, 1.2f);
            Run run = new Run(Illusions.now() + ticks);
            RUNS.put(caster.getUUID(), run);
            double yaw0 = Math.toRadians(caster.getYRot());
            float dmg = (float) power(caster, d(ServerConfig.MI_DAMAGE));
            int back = (int) Math.round(d(ServerConfig.MI_DAMAGE_RETURN) * 20);
            int tag = ++TAG;
            int[] age = {0};
            Tasks.add(() -> {   // the copies stand up when the air cracks (tick 12 of the cast effect)
                if (++age[0] < 12) return true;
                if (!caster.isAlive() || caster.isRemoved()) return false;
                for (int k = 0; k < n; k++) {
                    double a = yaw0 + Math.PI * 2 * (k + 0.5) / n;
                    Vec3 at = spot(sl, caster, new Vec3(-Math.sin(a) * 2.5, 0, Math.cos(a) * 2.5));
                    int delay = 4 + caster.getRandom().nextInt(7);
                    Copies.Copy c = Copies.spawn(caster, Copies.Mode.MIRROR, at, null, ticks, i(ServerConfig.MI_HITS), delay, victims);
                    c.damage = dmg;
                    c.damageReturn = back;
                    c.tag = tag;
                    run.copies.add(c);
                    for (ServerPlayer v : victims)
                        fx(sl, Fx.fx("illusion_mirror_image_spawn").at(at).only(v), "illusion_mirror_image_spawn");
                }
                for (ServerPlayer v : victims)   // the same flash on the caster, or the real one stands out
                    fx(sl, Fx.fx("illusion_mirror_image_spawn").at(caster.position()).caster(caster).only(v), "illusion_mirror_image_spawn");
                run.nextSwap = Illusions.now() + swapGap(caster);
                return false;
            });
        }
        super.onCast(level, spellLevel, caster, source, md);
    }

    /** A free spot near the wanted offset (the copy should not stand in a wall). */
    private static Vec3 spot(ServerLevel sl, LivingEntity caster, Vec3 off) {
        for (double k = 1; k > 0.2; k -= 0.25) {
            Vec3 p = caster.position().add(off.scale(k));
            if (sl.noCollision(new AABB(p.x - 0.3, p.y + 0.01, p.z - 0.3, p.x + 0.3, p.y + 1.8, p.z + 0.3))) return p;
        }
        return caster.position();
    }

    private static long swapGap(LivingEntity caster) {
        double s = d(ServerConfig.MI_SWAP_EVERY) * (0.7 + caster.getRandom().nextDouble() * 0.6);
        return Math.max(10, Math.round(s * 20));
    }

    static {
        Copies.onGone(c -> {
            Run r = RUNS.get(c.owner.getUUID());
            if (r != null) r.copies.remove(c);
        });
        // Blessing on a victim: the copies are gone for it (they vanish for everyone, it is one illusion)
        Illusions.onDispel(t -> {
            boolean any = false;
            for (Run r : RUNS.values())
                for (Copies.Copy c : new ArrayList<>(r.copies))
                    if (c.victims.contains(t.getUUID())) {
                        Copies.gone(c);
                        any = true;
                    }
            return any;
        });
    }

    public static final class Events {
        private Events() {}

        @net.minecraftforge.eventbus.api.SubscribeEvent
        public static void onTick(net.minecraftforge.event.TickEvent.ServerTickEvent e) {
            if (e.phase == net.minecraftforge.event.TickEvent.Phase.END) tickAll();
        }

        @net.minecraftforge.eventbus.api.SubscribeEvent
        public static void onStopping(net.minecraftforge.event.server.ServerStoppingEvent e) {
            RUNS.clear();
        }
    }

    /** Every tick: late-comers see the copies too, the swaps, the end. */
    private static void tickAll() {
        if (RUNS.isEmpty()) return;
        long now = Illusions.now();
        for (var it = RUNS.entrySet().iterator(); it.hasNext(); ) {
            var en = it.next();
            Run r = en.getValue();
            if (r.copies.isEmpty() && r.nextSwap != 0 || now >= r.until) {
                it.remove();
                continue;
            }
            if (r.copies.isEmpty()) continue;
            LivingEntity o = r.copies.get(0).owner;
            if (!(o.level() instanceof ServerLevel sl)) continue;
            if (now % 10 == 0)
                for (ServerPlayer p : Illusions.victims(sl, o, d(ServerConfig.MI_RANGE)))
                    for (Copies.Copy c : r.copies) Copies.show(c, p);
            if (r.nextSwap > 0 && now >= r.nextSwap) {
                Copies.Copy c = r.copies.get(o.getRandom().nextInt(r.copies.size()));
                Copies.swap(c);
                r.nextSwap = now + swapGap(o);
            }
        }
    }
}
