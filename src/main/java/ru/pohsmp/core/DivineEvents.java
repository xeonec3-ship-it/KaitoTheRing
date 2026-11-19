package ru.pohsmp.core;

import io.redspace.ironsspellbooks.api.events.ChangeManaEvent;
import io.redspace.ironsspellbooks.api.events.SpellOnCastEvent;
import io.redspace.ironsspellbooks.api.magic.MagicData;
import io.redspace.ironsspellbooks.api.registry.SpellRegistry;
import io.redspace.ironsspellbooks.api.spells.AbstractSpell;
import io.redspace.ironsspellbooks.api.spells.CastSource;
import io.redspace.ironsspellbooks.api.spells.CastType;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.Map;
import java.util.UUID;
import net.minecraft.core.particles.DustParticleOptions;
import net.minecraft.core.particles.ParticleOptions;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.effect.MobEffect;
import net.minecraft.world.effect.MobEffectInstance;
import net.minecraft.world.effect.MobEffects;
import net.minecraft.world.item.ItemStack;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.event.entity.player.PlayerEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import org.joml.Vector3f;

/** Divine-tier scrolls: golden aura while casting, backlash effects after a finished cast. */
public final class DivineEvents {
    private DivineEvents() {}

    private static final class Track {
        String spellId;
        Tier tier;
        int remaining = Integer.MAX_VALUE;
    }

    private static final Map<UUID, Track> TRACK = new HashMap<>();
    private static final DustParticleOptions GOLD = new DustParticleOptions(new Vector3f(1f, 0.82f, 0.3f), 1.3f);

    @SubscribeEvent
    public static void onPlayerTick(TickEvent.PlayerTickEvent e) {
        if (e.phase != TickEvent.Phase.END || !(e.player instanceof ServerPlayer sp)) return;
        MagicData md = MagicData.getPlayerMagicData(sp);
        Track tr = TRACK.get(sp.getUUID());
        if (md.isCasting() && md.getCastSource() == CastSource.SCROLL) {
            String id = md.getCastingSpellId();
            if (tr == null || !id.equals(tr.spellId)) {
                tr = new Track();
                tr.spellId = id;
                tr.tier = scrollTier(sp, md, id);
                TRACK.put(sp.getUUID(), tr);
                if (tr.tier == Tier.DIVINE)
                    sp.level().playSound(null, sp.getX(), sp.getY(), sp.getZ(), SoundEvents.BELL_BLOCK, SoundSource.PLAYERS, 1.5f, 1.4f);
            }
            tr.remaining = md.getCastDurationRemaining();
            if (tr.tier == Tier.DIVINE && ServerConfig.AURA.get()) aura(sp, sp.tickCount);
        } else if (tr != null) {
            TRACK.remove(sp.getUUID());
            if (tr.tier == Tier.DIVINE && tr.remaining <= 2) backlash(sp);
        }
    }

    @SubscribeEvent
    public static void onCast(SpellOnCastEvent e) {
        if (!(e.getEntity() instanceof ServerPlayer sp) || e.getCastSource() != CastSource.SCROLL) return;
        AbstractSpell spell = SpellRegistry.getSpell(e.getSpellId());
        if (spell == null || spell.getCastType() != CastType.INSTANT) return;
        if (scrollTier(sp, MagicData.getPlayerMagicData(sp), e.getSpellId()) != Tier.DIVINE) return;
        sp.level().playSound(null, sp.getX(), sp.getY(), sp.getZ(), SoundEvents.BELL_BLOCK, SoundSource.PLAYERS, 1.5f, 1.4f);
        if (ServerConfig.AURA.get()) for (int i = 0; i < 6; i++) aura(sp, i * 7);
        backlash(sp);
    }

    @SubscribeEvent
    public static void onLogout(PlayerEvent.PlayerLoggedOutEvent e) {
        TRACK.remove(e.getEntity().getUUID());
    }

    /** Tier of the scroll the spell is cast from (the casting item or a hand), or null. */
    public static Tier scrollTier(ServerPlayer sp, MagicData md, String spellId) {
        ItemStack casting = md.getPlayerCastingItem();
        if (spellId.equals(Tier.spellIdOf(casting))) return Tier.of(casting);
        for (InteractionHand h : InteractionHand.values()) {
            ItemStack st = sp.getItemInHand(h);
            if (spellId.equals(Tier.spellIdOf(st))) return Tier.of(st);
        }
        return null;
    }

    private static void aura(ServerPlayer sp, int t) {
        if (t % 2 != 0) return;
        ServerLevel sl = sp.serverLevel();
        double a0 = t * 0.12;
        for (int i = 0; i < 12; i++) {
            double a = a0 + i * Math.PI / 6;
            particle(sl, GOLD, sp.getX() + Math.cos(a) * 1.3, sp.getY() + 0.1, sp.getZ() + Math.sin(a) * 1.3, 1, 0, 0);
        }
        for (int i = 0; i < 2; i++) {
            double a = sp.getRandom().nextDouble() * Math.PI * 2, r = sp.getRandom().nextDouble() * 1.2;
            particle(sl, ParticleTypes.END_ROD, sp.getX() + Math.cos(a) * r, sp.getY() + 0.2, sp.getZ() + Math.sin(a) * r, 1, 0, 0.03);
        }
        if (t % 40 == 0) sl.playSound(null, sp.getX(), sp.getY(), sp.getZ(), SoundEvents.AMETHYST_BLOCK_CHIME, SoundSource.PLAYERS, 1f, 0.8f);
    }

    /** One visible effect; nausea goes along hidden (the screen wobble only exists for vanilla nausea). */
    private static void backlash(ServerPlayer sp) {
        MobEffect eff = Reg.BACKLASH.get();
        sp.removeEffect(eff);
        sp.addEffect(new MobEffectInstance(eff, ServerConfig.BACKLASH_SECONDS.get() * 20, 0, false, true, true));
        int nausea = ServerConfig.NAUSEA_SECONDS.get();
        if (nausea > 0) {
            MobEffectInstance n = new MobEffectInstance(MobEffects.CONFUSION, nausea * 20, 0, false, false, false);
            n.setCurativeItems(new ArrayList<>());
            sp.addEffect(n);
        }
    }

    @SubscribeEvent
    public static void onMana(ChangeManaEvent e) {
        if (e.getNewMana() <= e.getOldMana()) return;
        if ((ServerConfig.BLOCK_MANA.get() && e.getEntity().hasEffect(Reg.BACKLASH.get())) || e.getEntity().hasEffect(Reg.CREATION_BACKLASH.get()))
            e.setNewMana(e.getOldMana());
    }

    /** Particles sent with the "force" flag to everyone within 128 blocks. */
    public static void particle(ServerLevel sl, ParticleOptions opt, double x, double y, double z, int count, double spread, double speed) {
        for (ServerPlayer p : sl.players())
            if (p.distanceToSqr(x, y, z) < 128 * 128) sl.sendParticles(p, opt, true, x, y, z, count, spread, spread, spread, speed);
    }
}
