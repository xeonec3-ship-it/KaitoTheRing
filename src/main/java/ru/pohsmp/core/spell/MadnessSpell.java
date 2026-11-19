package ru.pohsmp.core.spell;

import io.redspace.ironsspellbooks.api.magic.MagicData;
import io.redspace.ironsspellbooks.api.registry.SchoolRegistry;
import io.redspace.ironsspellbooks.api.spells.AbstractSpell;
import io.redspace.ironsspellbooks.api.spells.CastSource;
import io.redspace.ironsspellbooks.api.spells.CastType;
import io.redspace.ironsspellbooks.api.spells.ISpellContainer;
import io.redspace.ironsspellbooks.api.spells.SpellRarity;
import io.redspace.ironsspellbooks.api.spells.SpellSlot;
import io.redspace.ironsspellbooks.api.util.Utils;
import java.util.ArrayList;
import java.util.List;
import net.minecraft.commands.arguments.EntityAnchorArgument;
import net.minecraft.core.particles.DustParticleOptions;
import net.minecraft.network.chat.MutableComponent;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.effect.MobEffectInstance;
import net.minecraft.world.effect.MobEffects;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.event.entity.living.MobEffectEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import org.joml.Vector3f;
import ru.pohsmp.core.DivineEvents;
import ru.pohsmp.core.Reg;

/**
 * Blood, legendary, levels 1-3. Magic Madness: spell power +25/40/60% for 15/20/30 s, but the body is no longer the caster's own:
 * it turns to the nearest creature and walks to it, strikes it, and casts random spells from the caster's spell book
 * (mana is spent as usual). Cannot be ended early. Afterwards 5 s of exhaustion.
 */
public class MadnessSpell extends PohSpell {
    public static final String PATH = "magic_madness";
    public static final double[] POWER = {0.25, 0.40, 0.60};
    private static final int[] SECONDS = {15, 20, 30};
    private static final DustParticleOptions RED = new DustParticleOptions(new Vector3f(0.7f, 0.02f, 0.05f), 1.2f);

    public MadnessSpell() {
        super(PATH, SchoolRegistry.BLOOD_RESOURCE, SpellRarity.LEGENDARY, 3, 60, 20, 60, 10);
    }

    @Override public CastType getCastType() { return CastType.LONG; }
    @Override public boolean allowCrafting() { return false; }

    private static int idx(int l) {
        return Math.max(0, Math.min(2, l - 1));
    }

    @Override
    public List<MutableComponent> getUniqueInfo(int level, LivingEntity caster) {
        return List.of(ui("power", (int) Math.round(POWER[idx(level)] * 100)), ui("time", SECONDS[idx(level)]), ui("control"));
    }

    @Override
    public void onCast(Level level, int spellLevel, LivingEntity caster, CastSource source, MagicData md) {
        if (level instanceof ServerLevel sl) {
            caster.removeEffect(Reg.MADNESS.get());
            caster.addEffect(new MobEffectInstance(Reg.MADNESS.get(), SECONDS[idx(spellLevel)] * 20, idx(spellLevel), false, true, true));
            sl.playSound(null, caster.getX(), caster.getY(), caster.getZ(), SoundEvents.WARDEN_ROAR, SoundSource.PLAYERS, 0.8f, 1.6f);
            DivineEvents.particle(sl, RED, caster.getX(), caster.getY() + 1, caster.getZ(), 60, 0.6, 0);
        }
        super.onCast(level, spellLevel, caster, source, md);
    }

    // ---- the madness itself ----

    private static LivingEntity nearest(ServerLevel sl, LivingEntity me) {
        LivingEntity best = null;
        double bd = 16 * 16;
        for (LivingEntity e : HigherSpell.around(sl, me.position(), 16, e -> e != me && !e.isSpectator()
                && !(e instanceof net.minecraft.world.entity.decoration.ArmorStand) && !(e instanceof Player p && p.isCreative()))) {
            double d = e.distanceToSqr(me);
            if (d < bd) { bd = d; best = e; }
        }
        return best;
    }

    private static void madTick(ServerPlayer sp) {
        ServerLevel sl = sp.serverLevel();
        int t = sp.tickCount;
        if (t % 3 == 0) DivineEvents.particle(sl, RED, sp.getX(), sp.getY() + 0.3 + sp.getRandom().nextDouble() * 1.5, sp.getZ(), 1, 0.3, 0);
        if (t % 40 == 0) sl.playSound(null, sp.getX(), sp.getY(), sp.getZ(), SoundEvents.WARDEN_HEARTBEAT, SoundSource.PLAYERS, 0.7f, 1.2f);
        LivingEntity tgt = nearest(sl, sp);
        if (tgt == null) return;
        Vec3 aim = tgt.position().add(0, tgt.getBbHeight() * 0.6, 0);
        if (t % 2 == 0) sp.lookAt(EntityAnchorArgument.Anchor.EYES, aim);
        double d = sp.distanceTo(tgt);
        if (d > 2.2 && t % 2 == 0 && !sp.isPassenger()) {
            Vec3 dir = tgt.position().subtract(sp.position()).multiply(1, 0, 1).normalize().scale(0.22);
            HigherSpell.push(sp, new Vec3(dir.x, sp.getDeltaMovement().y, dir.z));
        }
        if (d < 3.2 && t % 12 == 0) {
            sp.swing(InteractionHand.MAIN_HAND, true);
            sp.attack(tgt);
        }
        MagicData md = MagicData.getPlayerMagicData(sp);
        if (md.isCasting() || t % 25 != 0 || sp.getRandom().nextFloat() < 0.3f) return;
        ItemStack book = Utils.getPlayerSpellbookStack(sp);
        if (book == null || book.isEmpty() || !ISpellContainer.isSpellContainer(book)) return;
        List<SpellSlot> ok = new ArrayList<>();
        for (SpellSlot s : ISpellContainer.get(book).getActiveSpells()) {
            AbstractSpell sp2 = s.getSpell();
            if (sp2 == null || sp2.getSpellId().equals("pohsmp_core:" + PATH)) continue;
            if (md.getPlayerCooldowns().isOnCooldown(sp2)) continue;
            if (md.getMana() < sp2.getManaCost(s.getLevel())) continue;
            ok.add(s);
        }
        if (ok.isEmpty()) return;
        SpellSlot pick = ok.get(sp.getRandom().nextInt(ok.size()));
        sp.lookAt(EntityAnchorArgument.Anchor.EYES, aim);
        try {
            pick.getSpell().attemptInitiateCast(book, pick.getLevel(), sl, sp, CastSource.SPELLBOOK, true, "spellbook");
        } catch (Exception ignored) {
        }
    }

    public static final class MadnessEvents {
        private MadnessEvents() {}

        private static final java.util.UUID POWER_ID = java.util.UUID.fromString("6f1c6f5e-2b1a-4c51-9a41-0b8f3c5e7a10");

        @SubscribeEvent
        public static void onPlayerTick(TickEvent.PlayerTickEvent e) {
            if (e.phase != TickEvent.Phase.END || !(e.player instanceof ServerPlayer sp)) return;
            MobEffectInstance mad = sp.getEffect(Reg.MADNESS.get());
            var attr = sp.getAttribute(io.redspace.ironsspellbooks.api.registry.AttributeRegistry.SPELL_POWER.get());
            if (attr != null) {
                var cur = attr.getModifier(POWER_ID);
                double want = mad == null ? 0 : POWER[Math.max(0, Math.min(2, mad.getAmplifier()))];
                if (cur != null && (want == 0 || cur.getAmount() != want)) attr.removeModifier(POWER_ID);
                if (want > 0 && (cur == null || cur.getAmount() != want))
                    attr.addTransientModifier(new net.minecraft.world.entity.ai.attributes.AttributeModifier(POWER_ID, "pohsmp madness", want,
                            net.minecraft.world.entity.ai.attributes.AttributeModifier.Operation.ADDITION));
            }
            if (mad != null) madTick(sp);
        }

        @SubscribeEvent
        public static void onExpired(MobEffectEvent.Expired e) {
            if (e.getEffectInstance() == null || e.getEffectInstance().getEffect() != Reg.MADNESS.get()) return;
            LivingEntity le = e.getEntity();
            le.addEffect(new MobEffectInstance(MobEffects.MOVEMENT_SLOWDOWN, 100, 1));
            le.addEffect(new MobEffectInstance(MobEffects.WEAKNESS, 100, 1));
            le.addEffect(new MobEffectInstance(MobEffects.CONFUSION, 60, 0, false, false, false));
        }
    }
}
