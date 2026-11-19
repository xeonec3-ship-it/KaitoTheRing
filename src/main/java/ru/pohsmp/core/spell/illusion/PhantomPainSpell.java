package ru.pohsmp.core.spell.illusion;

import io.redspace.ironsspellbooks.api.magic.MagicData;
import io.redspace.ironsspellbooks.api.spells.CastSource;
import io.redspace.ironsspellbooks.api.spells.CastType;
import io.redspace.ironsspellbooks.api.spells.SpellRarity;
import io.redspace.ironsspellbooks.api.util.AnimationHolder;
import io.redspace.ironsspellbooks.api.util.Utils;
import io.redspace.ironsspellbooks.capabilities.magic.TargetEntityCastData;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import net.minecraft.network.chat.Component;
import net.minecraft.network.chat.MutableComponent;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.effect.MobEffectInstance;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.level.Level;
import net.minecraftforge.event.entity.living.LivingDamageEvent;
import net.minecraftforge.event.entity.living.MobEffectEvent;
import net.minecraftforge.eventbus.api.EventPriority;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import ru.pohsmp.core.Reg;
import ru.pohsmp.core.ServerConfig;
import ru.pohsmp.core.fx.Fx;
import ru.pohsmp.core.illusion.Illusions;
import ru.pohsmp.core.spell.CastAnims;

/**
 * T22 «Фантомная боль»: a mark on the creature the caster looks at for [phantom_pain] seconds (shortened by Illusion resistance).
 * Every hit on the marked one takes illusoryShare more health (by default twice as fast): that part is illusory and comes back when
 * the mark is gone, if the target lives. No line to the target: the caster's hand, the mark over the target's head.
 */
public class PhantomPainSpell extends IllusionBase {
    public static final String PATH = "phantom_pain";

    public PhantomPainSpell() {
        super(PATH, SpellRarity.UNCOMMON, 6, 0, ServerConfig.PP_MANA, ServerConfig.PP_COOLDOWN);
    }

    @Override public CastType getCastType() { return CastType.INSTANT; }
    @Override public AnimationHolder getCastStartAnimation() { return CastAnims.of("illusion_phantom_pain_cast"); }

    @Override
    public List<MutableComponent> getUniqueInfo(int level, LivingEntity caster) {
        return List.of(ui("time", n(seconds(level))));
    }

    /** Mark time grows with the level: the config value at level 1, +50% at the top. */
    private double seconds(int level) {
        return d(ServerConfig.PP_SECONDS) * lv(level, 1, 1.5);
    }

    @Override
    public boolean checkPreCastConditions(Level level, int spellLevel, LivingEntity entity, MagicData md) {
        return Utils.preCastTargetHelper(level, entity, md, this, (int) d(ServerConfig.PP_RANGE), 0.35f);
    }

    /** target id -> the mark's effect instance and its tag for the illusory debts. */
    private static final Map<UUID, int[]> MARKS = new HashMap<>();
    private static int TAG = 1_000_000;

    @Override
    public void onCast(Level level, int spellLevel, LivingEntity caster, CastSource source, MagicData md) {
        if (level instanceof ServerLevel sl && md.getAdditionalCastData() instanceof TargetEntityCastData td
                && td.getTarget(sl) != null && td.getTarget(sl).isAlive() && !Illusions.ally(caster, td.getTarget(sl))) {
            LivingEntity t = td.getTarget(sl);
            int ticks = Illusions.duration(t, (int) Math.round(seconds(spellLevel) * 20));
            fx(sl, Fx.fx("illusion_phantom_pain_cast").at(caster.position()).caster(caster), "illusion_phantom_pain_cast");
            sl.playSound(null, caster.getX(), caster.getY() + 1, caster.getZ(), SoundEvents.AMETHYST_BLOCK_CHIME, SoundSource.PLAYERS, 1.2f, 1.3f);
            sl.playSound(null, caster.getX(), caster.getY() + 1, caster.getZ(), SoundEvents.ALLAY_AMBIENT_WITHOUT_ITEM, SoundSource.PLAYERS, 0.4f, 0.6f);
            mark(sl, t, ticks);
        }
        super.onCast(level, spellLevel, caster, source, md);
    }

    private static void mark(ServerLevel sl, LivingEntity t, int ticks) {
        int[] old = MARKS.get(t.getUUID());
        if (old != null && old[0] >= 0) Fx.stop(sl, old[0], "");
        int inst = fx(sl, Fx.fx("illusion_phantom_pain_mark").at(t.position()).target(t).caster(t).attach(t).duration(ticks), "illusion_phantom_pain_mark");
        int tag = old != null ? old[1] : ++TAG;
        MARKS.put(t.getUUID(), new int[] {inst, tag});
        t.addEffect(new MobEffectInstance(Reg.PHANTOM_PAIN.get(), ticks, 0, false, false, true));
        Illusions.extend(t, tag, Illusions.now() + ticks);
        sl.playSound(null, t.getX(), t.getY() + 1, t.getZ(), SoundEvents.AMETHYST_CLUSTER_HIT, SoundSource.PLAYERS, 1f, 1.6f);
    }

    /** The mark is over (ran out, milk, Blessing): its fx goes, the illusory part falls due now. */
    private static void unmark(LivingEntity t) {
        int[] m = MARKS.remove(t.getUUID());
        if (m == null) return;
        if (m[0] >= 0 && t.level() instanceof ServerLevel sl) Fx.stop(sl, m[0], "");
        Illusions.settleNow(t, m[1]);
    }

    static {
        Illusions.onDispel(t -> {
            boolean had = t.hasEffect(Reg.PHANTOM_PAIN.get()) || MARKS.containsKey(t.getUUID());
            unmark(t);
            return had;
        });
    }

    public static final class Events {
        private Events() {}

        /** The marked one loses illusoryShare more of every hit, as illusory damage until the mark ends. */
        @SubscribeEvent(priority = EventPriority.LOWEST)
        public static void onDamage(LivingDamageEvent e) {
            LivingEntity t = e.getEntity();
            if (e.isCanceled() || t.level().isClientSide || e.getAmount() <= 0) return;
            MobEffectInstance mi = t.getEffect(Reg.PHANTOM_PAIN.get());
            int[] m = MARKS.get(t.getUUID());
            if (mi == null || m == null) return;
            double share = IllusionBase.cfg(ServerConfig.PP_SHARE::get, 1.0);
            float a = e.getAmount();
            float h = t.getHealth();
            float extra = (float) (a * share);
            e.setAmount(a + extra);   // a lethal illusory part is a real death
            float owed = Math.min(extra, Math.max(0, h - a));
            Illusions.owe(t, owed, mi.getDuration() + 1, m[1]);
            if (t.level() instanceof ServerLevel sl)
                fx(sl, Fx.fx("illusion_phantom_pain_tick").at(t.position()).target(t).caster(t).attach(t), "illusion_phantom_pain_tick");
            if (t instanceof ServerPlayer sp && owed > 0)
                sp.displayClientMessage(Component.translatable("ui.pohsmp_core.illusion.illusory", n(Math.round(owed * 10) / 10.0),
                        n(Math.round(mi.getDuration() / 2.0) / 10.0)).withStyle(s -> s.withColor(COLOR)), true);
        }

        @SubscribeEvent
        public static void onExpire(MobEffectEvent.Expired e) {
            if (e.getEffectInstance() != null && e.getEffectInstance().getEffect() == Reg.PHANTOM_PAIN.get() && !e.getEntity().level().isClientSide)
                unmark(e.getEntity());
        }

        @SubscribeEvent
        public static void onRemove(MobEffectEvent.Remove e) {
            if (e.getEffect() == Reg.PHANTOM_PAIN.get() && !e.getEntity().level().isClientSide) unmark(e.getEntity());
        }
    }
}
