package ru.pohsmp.core.spell;

import io.redspace.ironsspellbooks.api.magic.MagicData;
import io.redspace.ironsspellbooks.api.spells.CastSource;
import io.redspace.ironsspellbooks.api.spells.CastType;
import io.redspace.ironsspellbooks.api.spells.SpellRarity;
import io.redspace.ironsspellbooks.api.util.AnimationHolder;
import io.redspace.ironsspellbooks.api.util.Utils;
import io.redspace.ironsspellbooks.capabilities.magic.TargetEntityCastData;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.ClipContext;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.HitResult;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.event.server.ServerStoppingEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import ru.pohsmp.core.Reg;
import ru.pohsmp.core.fx.Fx;

/**
 * T21: a 10 s divine rite on one target ("Soul Seal", "Blessing"; docs/specs/tasks/T21_soul_seal_blessing.md). The target is the one the
 * caster looks at within {@link #RANGE}; it must stay for the whole cast — farther than {@link #KEEP}, out of sight for more than 1 s,
 * dead or gone, and the cast breaks with nothing spent. The cast has its own cutscene for everyone within 64 (Cutscene, client DownfallCut);
 * after the rite takes effect the camera holds the last shot {@link #HOLD} ticks more before it returns.
 */
public abstract class RiteSpell extends PohSpell {
    public static final int CAST = 200, HOLD = 30, LOST_MAX = 20;
    public static final double RANGE = 24, KEEP = 32;

    protected static final class Rite {
        LivingEntity caster, target;
        int age, lost, fx, cutKey;
        List<UUID> watchers = new ArrayList<>();
    }

    private static final Map<UUID, Rite> RITES = new HashMap<>();
    private final int scene;
    private final String fxCast;
    private final AnimationHolder animCast, animFinish;

    protected RiteSpell(String path, int scene, String anim) {
        super(path, Reg.DIVINE_ID, SpellRarity.LEGENDARY, 1, 0, CAST, 0, 0);
        this.scene = scene;
        this.fxCast = path + "_cast";
        this.animCast = CastAnims.of(anim + "_cast");
        this.animFinish = CastAnims.of(anim + "_finish");
    }

    @Override public CastType getCastType() { return CastType.LONG; }
    @Override public boolean canBeInterrupted(Player player) { return false; }
    @Override public boolean allowCrafting() { return false; }
    @Override public AnimationHolder getCastStartAnimation() { return animCast; }
    @Override public AnimationHolder getCastFinishAnimation() { return animFinish; }

    @Override
    public void onClientPreCast(Level level, int spellLevel, LivingEntity entity, net.minecraft.world.InteractionHand hand, @javax.annotation.Nullable MagicData md) {
        super.onClientPreCast(level, spellLevel, entity, hand, md);
        CastAnims.hideHands(level, entity, getEffectiveCastTime(spellLevel, entity));
    }

    /** Who may be the target (besides being alive, in range and in sight). */
    protected abstract boolean canTarget(LivingEntity caster, LivingEntity t);

    /** No one looked at: the caster itself, or null (then the cast does not start, "Нет цели"). */
    protected abstract LivingEntity fallback(LivingEntity caster);

    /** One more check of the chosen target before the cast starts; returns the refusal text key, or null. */
    protected String refuse(LivingEntity caster, LivingEntity t) {
        return null;
    }

    /** The rite takes effect on the target. */
    protected abstract void apply(ServerLevel sl, LivingEntity caster, LivingEntity target);

    /** The flash on the watchers' screens when the rite takes effect. */
    protected int flashTicks() {
        return 3;
    }

    protected int flashColor() {
        return 0xFFFFFF;
    }

    /** Each tick of the cast (sounds, particles); age 1..CAST. */
    protected void castTick(ServerLevel sl, Rite r) {}

    protected static void say(LivingEntity e, String key) {
        if (e instanceof ServerPlayer sp) sp.displayClientMessage(Component.translatable(key).withStyle(s -> s.withColor(Reg.DIVINE_COLOR)), true);
    }

    @Override
    public boolean checkPreCastConditions(Level level, int spellLevel, LivingEntity caster, MagicData md) {
        if (Utils.preCastTargetHelper(level, caster, md, this, (int) RANGE, 0.35f, false, t -> t != caster && canTarget(caster, t))) {
            if (md.getAdditionalCastData() instanceof TargetEntityCastData td && level instanceof ServerLevel sl) {
                LivingEntity t = td.getTarget(sl);
                String no = t == null ? null : refuse(caster, t);
                if (no != null) {
                    say(caster, no);
                    return false;
                }
            }
            return true;
        }
        LivingEntity self = fallback(caster);
        if (self != null) {
            md.setAdditionalCastData(new TargetEntityCastData(self));
            return true;
        }
        say(caster, "ui.pohsmp_core.rite.no_target");
        return false;
    }

    @Override
    public void onServerPreCast(Level level, int spellLevel, LivingEntity caster, MagicData md) {
        super.onServerPreCast(level, spellLevel, caster, md);
        if (level instanceof ServerLevel sl) start(sl, caster, md);
    }

    private Rite start(ServerLevel sl, LivingEntity caster, MagicData md) {
        LivingEntity t = HigherSpell.target(sl, md);
        if (t == null) return null;
        Rite r = new Rite();
        r.caster = caster;
        r.target = t;
        RITES.put(caster.getUUID(), r);
        r.cutKey = HigherSpell.key();
        Vec3 d = t.position().subtract(caster.position());
        double ang = d.horizontalDistanceSqr() < 1e-4 ? Math.toRadians(caster.getYRot() + 90) : Math.atan2(d.z, d.x);
        r.watchers = Cutscene.start(sl, caster, r.cutKey, scene, CAST, t.position(), ang, t.getId());
        r.fx = Fx.play(sl, Fx.fx(fxCast).at(caster.position()).caster(caster).target(t).duration(CAST));
        return r;
    }

    /** The target still holds: alive, here, within KEEP, and not out of sight for longer than LOST_MAX. */
    private static boolean holds(ServerLevel sl, Rite r) {
        LivingEntity t = r.target;
        if (!t.isAlive() || t.isRemoved() || t.level() != sl) return false;
        if (t == r.caster) return true;
        if (t.distanceToSqr(r.caster) > KEEP * KEEP) return false;
        boolean seen = sl.clip(new ClipContext(r.caster.getEyePosition(), t.getEyePosition(), ClipContext.Block.VISUAL, ClipContext.Fluid.NONE,
                r.caster)).getType() == HitResult.Type.MISS;
        r.lost = seen ? 0 : r.lost + 1;
        return r.lost <= LOST_MAX;
    }

    @Override
    public void onServerCastTick(Level level, int spellLevel, LivingEntity caster, MagicData md) {
        super.onServerCastTick(level, spellLevel, caster, md);
        if (!(level instanceof ServerLevel sl)) return;
        Rite r = RITES.get(caster.getUUID());
        if (r == null) r = start(sl, caster, md);
        if (r == null) return;
        if (!holds(sl, r)) {   // the target is lost: the cast breaks, nothing spent (Iron's takes the scroll and mana only at the end)
            say(caster, "ui.pohsmp_core.rite.lost");
            NpcCast.cancelAny(caster);
            return;
        }
        r.age++;
        castTick(sl, r);
    }

    @Override
    public void onCast(Level level, int spellLevel, LivingEntity caster, CastSource source, MagicData md) {
        if (level instanceof ServerLevel sl) {
            Rite r = RITES.remove(caster.getUUID());
            if (r != null && holds(sl, r)) {
                Cutscene.flash(sl, r.watchers, flashTicks(), flashColor());
                apply(sl, caster, r.target);
                Fx.stop(sl, r.fx, "");
                Tasks.add(new Tasks.Task() {   // the camera holds the last shot a little (spec: 1.5 s after the cast)
                    int left = HOLD;

                    @Override
                    public boolean tick() {
                        if (--left > 0) return true;
                        Cutscene.end(sl, caster, r.watchers, r.cutKey);
                        return false;
                    }
                });
            } else if (r != null) finish(sl, caster, r);
        }
        super.onCast(level, spellLevel, caster, source, md);
    }

    @Override
    public void onServerCastComplete(Level level, int spellLevel, LivingEntity caster, MagicData md, boolean cancelled) {
        Rite r = RITES.remove(caster.getUUID());
        if (level instanceof ServerLevel sl && r != null) finish(sl, caster, r);
        super.onServerCastComplete(level, spellLevel, caster, md, cancelled);
    }

    /** Broken or cancelled: the circles go, the camera comes back (the client glides back in 1 s). */
    private static void finish(ServerLevel sl, LivingEntity caster, Rite r) {
        Fx.stop(sl, r.fx, "");
        Cutscene.end(sl, caster, r.watchers, r.cutKey);
    }

    public static final class RiteEvents {
        private RiteEvents() {}

        @SubscribeEvent
        public static void onServerTick(TickEvent.ServerTickEvent e) {
            if (e.phase != TickEvent.Phase.END || RITES.isEmpty()) return;
            RITES.values().removeIf(r -> {
                boolean gone = !r.caster.isAlive() || r.caster.isRemoved() || (r.caster instanceof Player p && !MagicData.getPlayerMagicData(p).isCasting())
                        || r.age > CAST * 2;
                if (gone && r.caster.level() instanceof ServerLevel sl) finish(sl, r.caster, r);
                return gone;
            });
        }

        @SubscribeEvent
        public static void onStopping(ServerStoppingEvent e) {
            RITES.clear();
        }
    }
}
