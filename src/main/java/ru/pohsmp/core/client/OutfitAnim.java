package ru.pohsmp.core.client;

import io.redspace.ironsspellbooks.player.ClientMagicData;
import java.util.HashMap;
import java.util.Map;
import net.minecraft.client.Minecraft;
import net.minecraft.client.model.HumanoidModel;
import net.minecraft.client.model.PlayerModel;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.LivingEntity;
import ru.pohsmp.core.silent.SilentWitch;
import ru.pohsmp.core.silent.SilentWitchArmor;
import software.bernie.geckolib.constant.DataTickets;
import software.bernie.geckolib.core.animation.Animation;
import software.bernie.geckolib.core.animation.AnimationState;
import software.bernie.geckolib.core.animation.RawAnimation;

/**
 * Silent Witch outfit, client side of effects 7 (living cloak) and 9 (Nero).
 * <p>
 * Cloth ("cloak" controller): cast &gt; run (sprinting) &gt; walk (moving) &gt; idle.
 * <p>
 * Nero ("nero" controller, model bones nero* in the body and nero_hood* in the head): sits on the left shoulder (nero_shoulder);
 * when a cast starts jumps onto the hood (nero_jump_up, then nero_head), jumps back when it ends (nero_jump_down); disappears while
 * running and comes back {@link #NERO_BACK} ticks after the run (nero_return); turns into the dragon shadow of "Black Flame of Worgan"
 * (nero_dragon, server message, see {@link SilentWitch#neroDragon}) and comes back after the breath. Outside the full set: nero_hidden.
 */
public final class OutfitAnim {
    private OutfitAnim() {}

    public static final int NERO_BACK = 40;
    public static final RawAnimation CAT_SHOULDER = RawAnimation.begin().thenLoop("nero_shoulder");
    public static final RawAnimation CAT_UP = RawAnimation.begin().then("nero_jump_up", Animation.LoopType.PLAY_ONCE).thenLoop("nero_head");
    public static final RawAnimation CAT_DOWN = RawAnimation.begin().then("nero_jump_down", Animation.LoopType.PLAY_ONCE).thenLoop("nero_shoulder");
    public static final RawAnimation CAT_RETURN = RawAnimation.begin().then("nero_return", Animation.LoopType.PLAY_ONCE).thenLoop("nero_shoulder");
    public static final RawAnimation CAT_DRAGON = RawAnimation.begin().then("nero_dragon", Animation.LoopType.HOLD_ON_LAST_FRAME);
    public static final RawAnimation CAT_HIDDEN = RawAnimation.begin().thenLoop("nero_hidden");

    private enum Cat { HIDDEN, AWAY, DRAGON, HEAD, SHOULDER }

    private static final class State {
        Cat cat;
        RawAnimation anim = CAT_SHOULDER;
        long lastRun = Long.MIN_VALUE / 2;
    }

    private static final Map<Integer, State> STATES = new HashMap<>();
    private static final Map<Integer, Long> DRAGON_UNTIL = new HashMap<>();

    public static boolean casting(LivingEntity e) {
        if (e == Minecraft.getInstance().player) return ClientMagicData.isCasting();
        var d = ClientMagicData.getSyncedSpellData(e);
        return d != null && d.isCasting();
    }

    public static boolean running(Entity e) {
        return e.isSprinting() && moving(e);
    }

    public static boolean moving(Entity e) {
        double dx = e.getX() - e.xo, dz = e.getZ() - e.zo;
        return dx * dx + dz * dz > 0.0004;
    }

    public static RawAnimation pick(AnimationState<SilentWitchArmor> s) {
        Entity e = s.getData(DataTickets.ENTITY);
        if (!(e instanceof LivingEntity le)) return SilentWitchArmor.IDLE;
        if (casting(le)) return SilentWitchArmor.CAST;
        if (running(le)) return SilentWitchArmor.RUN;
        if (moving(le)) return SilentWitchArmor.WALK;
        return SilentWitchArmor.IDLE;
    }

    /** Server message: the wearer's Nero becomes the dragon shadow for this many ticks (0 = back now). */
    public static void dragon(int entityId, int ticks) {
        var level = Minecraft.getInstance().level;
        if (level == null) return;
        if (ticks <= 0) DRAGON_UNTIL.remove(entityId);
        else DRAGON_UNTIL.put(entityId, ClientClock.ticks() + ticks);
    }

    public static RawAnimation cat(AnimationState<SilentWitchArmor> s) {
        Entity e = s.getData(DataTickets.ENTITY);
        if (!(e instanceof LivingEntity le)) return CAT_HIDDEN;
        State st = STATES.computeIfAbsent(e.getId(), k -> new State());
        long now = ClientClock.ticks();
        Long dragonUntil = DRAGON_UNTIL.get(e.getId());
        if (dragonUntil != null && now >= dragonUntil) DRAGON_UNTIL.remove(e.getId());
        if (running(e)) st.lastRun = now;
        Cat want;
        if (!SilentWitch.fullSet(le)) want = Cat.HIDDEN;
        else if (DRAGON_UNTIL.containsKey(e.getId())) want = Cat.DRAGON;
        else if (now - st.lastRun < NERO_BACK) want = Cat.AWAY;
        else if (casting(le)) want = Cat.HEAD;
        else want = Cat.SHOULDER;
        if (want != st.cat) {
            Cat was = st.cat;
            st.cat = want;
            st.anim = switch (want) {
                case HIDDEN, AWAY -> CAT_HIDDEN;
                case DRAGON -> CAT_DRAGON;
                case HEAD -> CAT_UP;
                case SHOULDER -> was == Cat.HEAD ? CAT_DOWN : was == null ? CAT_SHOULDER : CAT_RETURN;
            };
        }
        return st.anim;
    }

    /**
     * Effect 7 with the skirt: the wearer's own legs swing half as far, so a leg does not step out from under the dress
     * (called from the HumanoidModel setupAnim mixin, after vanilla posed the legs).
     */
    public static void legs(HumanoidModel<?> model, LivingEntity e) {
        if (!(model instanceof PlayerModel<?>) || !SilentWitch.skirt(e)) return;
        model.rightLeg.xRot *= 0.5f;
        model.leftLeg.xRot *= 0.5f;
        if (model instanceof PlayerModel<?> pm) {
            pm.rightPants.copyFrom(model.rightLeg);
            pm.leftPants.copyFrom(model.leftLeg);
        }
    }
}
