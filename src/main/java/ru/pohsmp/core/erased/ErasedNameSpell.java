package ru.pohsmp.core.erased;

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
import java.util.Optional;
import java.util.UUID;
import net.minecraft.network.chat.Component;
import net.minecraft.network.chat.MutableComponent;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.sounds.SoundEvent;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.effect.MobEffectInstance;
import net.minecraft.world.effect.MobEffects;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.event.server.ServerStoppingEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import ru.pohsmp.core.Reg;
import ru.pohsmp.core.fx.Fx;
import ru.pohsmp.core.spell.CastAnims;
import ru.pohsmp.core.spell.Cutscene;
import ru.pohsmp.core.spell.HigherSpell;
import ru.pohsmp.core.spell.PohSpell;

/**
 * T24 «Стёртое имя» (Forbidden school, tier «Мироздание»): 15 s of writing the name of the player looked at (up to 32 blocks) and striking
 * it out, a camera scene for all within 64 (Cutscene.ERASED_NAME). The target must hold: more than 48 blocks away, out of sight longer
 * than 2 s or dead - the cast breaks, nothing spent. On tick 290 the target starts to vanish (fx erased_vanish), on 300 it is erased for
 * 10 minutes ({@link Erased}). Scroll; cooldown 600 s; the Creation backlash like «Низвержение». Oneself, the erased and the just returned
 * cannot be taken.
 */
public class ErasedNameSpell extends PohSpell {
    public static final String PATH = "erased_name";
    public static final int CAST = 300, TAIL = 30, VANISH_AT = 290, BACKLASH_TICKS = 3600;
    public static final double RANGE = 32, HOLD = 48;
    private static final int SIGHT_LOST_MAX = 40;

    public ErasedNameSpell() {
        super(PATH, Reg.FORBIDDEN_ID, SpellRarity.LEGENDARY, 1, 600, CAST, 0, 0);
    }

    @Override public CastType getCastType() { return CastType.LONG; }
    @Override public boolean canBeInterrupted(Player player) { return false; }
    @Override public boolean allowCrafting() { return false; }
    @Override public boolean allowLooting() { return false; }
    @Override public Optional<SoundEvent> getCastStartSound() { return Optional.of(SoundEvents.BOOK_PAGE_TURN); }
    @Override public Optional<SoundEvent> getCastFinishSound() { return Optional.empty(); }
    @Override public AnimationHolder getCastStartAnimation() { return CastAnims.of("erased_name_cast"); }
    @Override public AnimationHolder getCastFinishAnimation() { return CastAnims.of("erased_name_finish"); }

    @Override
    public void onClientPreCast(Level level, int spellLevel, LivingEntity entity, net.minecraft.world.InteractionHand hand, @javax.annotation.Nullable MagicData md) {
        super.onClientPreCast(level, spellLevel, entity, hand, md);
        CastAnims.hideHands(level, entity, getEffectiveCastTime(spellLevel, entity));
    }

    @Override
    public List<MutableComponent> getUniqueInfo(int level, LivingEntity caster) {
        return List.of(ui("cast", CAST / 20), ui("target", (int) RANGE), ui("duration", Erased.DURATION_MS / 60000), ui("forgotten"), ui("lifted"));
    }

    private static void say(LivingEntity e, String key, Object... args) {
        if (e instanceof Player p) p.displayClientMessage(Component.translatable("ui.pohsmp_core.erased_name." + key, args).withStyle(s -> s.withColor(0xE9E4D8)), true);
    }

    @Override
    public boolean checkPreCastConditions(Level level, int spellLevel, LivingEntity entity, MagicData md) {
        if (!Utils.preCastTargetHelper(level, entity, md, this, (int) RANGE, 0.35f)) return false;
        if (level instanceof ServerLevel sl && md.getAdditionalCastData() instanceof TargetEntityCastData td) {
            LivingEntity t = td.getTarget(sl);
            String why = null;
            Object arg = null;
            if (!(t instanceof ServerPlayer tp)) why = "no_target";
            else if (tp == entity) why = "self";
            else if (Erased.isErased(tp)) {
                why = "already";
                arg = tp.getGameProfile().getName();
            } else if (Erased.immune(tp.getUUID())) {
                why = "immune";
                arg = tp.getGameProfile().getName();
            }
            if (why != null) {
                if (arg != null) say(entity, why, arg);
                else say(entity, why);
                md.resetAdditionalCastData();
                return false;
            }
        }
        return super.checkPreCastConditions(level, spellLevel, entity, md);
    }

    // ---------------------------------------------------------------- the cast

    private static final class Cast {
        ServerPlayer target;
        int age, cutKey, fx = -1, lost;
        List<UUID> watchers = new ArrayList<>();
        boolean broken;
    }

    private static final Map<UUID, Cast> CASTS = new HashMap<>();

    @Override
    public void onServerPreCast(Level level, int spellLevel, LivingEntity caster, MagicData md) {
        super.onServerPreCast(level, spellLevel, caster, md);
        if (!(level instanceof ServerLevel sl) || md == null || !(md.getAdditionalCastData() instanceof TargetEntityCastData td)) return;
        if (!(td.getTarget(sl) instanceof ServerPlayer t)) return;
        Cast c = new Cast();
        c.target = t;
        c.cutKey = HigherSpell.key();
        Vec3 d = t.position().subtract(caster.position());
        c.watchers = Cutscene.start(sl, caster, c.cutKey, Cutscene.ERASED_NAME, CAST + TAIL, t.position(), Math.atan2(d.z, d.x), t.getId());
        c.fx = Fx.play(sl, Fx.fx("erased_name_cast").at(caster.position()).caster(caster).target(t).text("name", t.getGameProfile().getName()));
        CASTS.put(caster.getUUID(), c);
    }

    @Override
    public void onServerCastTick(Level level, int spellLevel, LivingEntity caster, MagicData md) {
        super.onServerCastTick(level, spellLevel, caster, md);
        if (!(level instanceof ServerLevel sl)) return;
        Cast c = CASTS.get(caster.getUUID());
        if (c == null || c.broken) return;
        c.age++;
        ServerPlayer t = c.target;
        boolean gone = t.isRemoved() || !t.isAlive() || t.level() != sl || t.distanceTo(caster) > HOLD || t.hasDisconnected();
        if (!gone) c.lost = caster.hasLineOfSight(t) ? 0 : c.lost + 1;
        if (gone || c.lost > SIGHT_LOST_MAX) {
            c.broken = true;
            say(caster, "broken");
            if (caster instanceof ServerPlayer sp) Utils.serverSideCancelCast(sp);
            return;
        }
        Vec3 a = t.position();
        int k = c.age;
        if (k >= 32 && k <= 68 && k % 7 == 0) sl.playSound(null, caster.getX(), caster.getY() + 1, caster.getZ(), SoundEvents.BOOK_PAGE_TURN, SoundSource.PLAYERS, 0.6f, 1.4f + sl.random.nextFloat() * 0.4f);
        switch (k) {
            case 114 -> {
                sl.playSound(null, caster.getX(), caster.getY() + 1, caster.getZ(), SoundEvents.BOOK_PUT, SoundSource.PLAYERS, 1.2f, 0.8f);
                sl.playSound(null, a.x, a.y + 2, a.z, SoundEvents.ENCHANTMENT_TABLE_USE, SoundSource.PLAYERS, 1.5f, 0.6f);
            }
            case 220 -> sl.playSound(null, a.x, a.y + 1, a.z, SoundEvents.SCULK_CATALYST_BLOOM, SoundSource.PLAYERS, 1.5f, 0.5f);
            case VANISH_AT -> {
                Fx.play(sl, Fx.fx("erased_vanish").at(a).caster(t).attach(t));
                sl.playSound(null, caster.getX(), caster.getY() + 1, caster.getZ(), SoundEvents.PLAYER_ATTACK_SWEEP, SoundSource.PLAYERS, 1.2f, 0.5f);
            }
            default -> {}
        }
        if (k >= 230 && k < 276 && k % 9 == 0) sl.playSound(null, a.x, a.y + 1, a.z, SoundEvents.SAND_BREAK, SoundSource.PLAYERS, 0.6f, 0.6f);
    }

    @Override
    public void onCast(Level level, int spellLevel, LivingEntity caster, CastSource source, MagicData md) {
        if (level instanceof ServerLevel sl) {
            Cast c = CASTS.get(caster.getUUID());
            if (c != null && !c.broken && c.target.isAlive() && !c.target.hasDisconnected()) {
                c.age = CAST + 1;
                Erased.erase(c.target, Erased.DURATION_MS);
                sl.playSound(null, c.target.getX(), c.target.getY() + 1, c.target.getZ(), SoundEvents.ELYTRA_FLYING, SoundSource.PLAYERS, 0.4f, 2f);
                backlash(caster, md);
            }
        }
        super.onCast(level, spellLevel, caster, source, md);
    }

    @Override
    public void onServerCastComplete(Level level, int spellLevel, LivingEntity caster, MagicData md, boolean cancelled) {
        Cast c = CASTS.remove(caster.getUUID());
        if (c != null && level instanceof ServerLevel sl) {
            boolean done = c.age > CAST;
            if (!done && c.fx >= 0) Fx.stop(sl, c.fx, "");
            if (done) {   // the empty place: the scene holds its 1.5 s tail, then the camera comes back
                List<UUID> w = c.watchers;
                int key = c.cutKey;
                int[] left = {TAIL};
                ru.pohsmp.core.spell.Tasks.add(() -> {
                    if (--left[0] > 0) return true;
                    Cutscene.end(sl, caster, w, key);
                    return false;
                });
            } else Cutscene.end(sl, caster, c.watchers, c.cutKey);
            if (!done && md != null && caster instanceof ServerPlayer sp) {   // broken: nothing spent - the cooldown goes too
                MagicData.getPlayerMagicData(sp).getPlayerCooldowns().removeCooldown(getSpellId());
                MagicData.getPlayerMagicData(sp).getPlayerCooldowns().syncToPlayer(sp);
            }
        }
        super.onServerCastComplete(level, spellLevel, caster, md, cancelled);
    }

    /** The Creation price, as «Низвержение»: mana 0, 3 min of the backlash (no mana, no spells, -50% health), darkness, nausea. */
    private static void backlash(LivingEntity c, MagicData md) {
        if (md != null) md.setMana(0);
        if (c instanceof ServerPlayer sp) MagicData.getPlayerMagicData(sp).setMana(0);
        c.removeEffect(Reg.CREATION_BACKLASH.get());
        c.addEffect(new MobEffectInstance(Reg.CREATION_BACKLASH.get(), BACKLASH_TICKS, 0, false, true, true));
        c.addEffect(new MobEffectInstance(MobEffects.DARKNESS, 200, 0, false, false, false));
        MobEffectInstance n = new MobEffectInstance(MobEffects.CONFUSION, 160, 0, false, false, false);
        n.setCurativeItems(new ArrayList<>());
        c.addEffect(n);
        if (c.getHealth() > c.getMaxHealth()) c.setHealth(c.getMaxHealth());
    }

    public static final class Events {
        private Events() {}

        @SubscribeEvent
        public static void onStopping(ServerStoppingEvent e) {
            CASTS.clear();
        }
    }
}
