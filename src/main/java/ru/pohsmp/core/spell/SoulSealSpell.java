package ru.pohsmp.core.spell;

import io.redspace.ironsspellbooks.api.util.CameraShakeData;
import io.redspace.ironsspellbooks.api.util.CameraShakeManager;
import java.util.List;
import java.util.Optional;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.network.chat.MutableComponent;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.sounds.SoundEvent;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.phys.Vec3;
import ru.pohsmp.core.DivineEvents;
import ru.pohsmp.core.fx.Fx;

/**
 * T21 "Soul Seal" (divine): a 10 s rite on the player the caster looks at (24 blocks; players only, not oneself, not one already sealed).
 * At the end the seal is pressed into the target's chest: from then on he casts nothing, for good ({@link SoulSeal}); only "Blessing"
 * or an operator takes it off. Visuals: fx soul_seal_cast (circles, the lock over the target, the chains), soul_seal_lock_in (the press),
 * the mark on the chest — the manager's; the camera — scene 8.
 */
public class SoulSealSpell extends RiteSpell {
    public static final String PATH = "soul_seal";

    public SoulSealSpell() {
        super(PATH, Cutscene.SOUL_SEAL, "soul_seal");
    }

    @Override public Optional<SoundEvent> getCastStartSound() { return Optional.of(SoundEvents.BEACON_ACTIVATE); }
    @Override public Optional<SoundEvent> getCastFinishSound() { return Optional.empty(); }

    @Override
    public List<MutableComponent> getUniqueInfo(int level, LivingEntity caster) {
        return List.of(ui("cast", CAST / 20), ui("target", (int) RANGE), ui("forever"), ui("lifted"));
    }

    @Override
    protected boolean canTarget(LivingEntity caster, LivingEntity t) {
        return t instanceof Player p && !p.isSpectator();
    }

    @Override
    protected LivingEntity fallback(LivingEntity caster) {
        return null;
    }

    @Override
    protected String refuse(LivingEntity caster, LivingEntity t) {
        return t instanceof Player p && SoulSeal.sealed(p) ? "ui.pohsmp_core.soul_seal.already" : null;
    }

    @Override
    protected void castTick(ServerLevel sl, Rite r) {
        Vec3 tc = r.target.position().add(0, r.target.getBbHeight() * 0.65, 0);
        switch (r.age) {
            case 1 -> sl.playSound(null, r.caster.getX(), r.caster.getY(), r.caster.getZ(), SoundEvents.RESPAWN_ANCHOR_CHARGE, SoundSource.PLAYERS, 2f, 0.5f);
            case 40 -> sl.playSound(null, tc.x, tc.y, tc.z, SoundEvents.ENCHANTMENT_TABLE_USE, SoundSource.PLAYERS, 2f, 0.4f);
            case 120 -> sl.playSound(null, tc.x, tc.y, tc.z, SoundEvents.CHAIN_PLACE, SoundSource.PLAYERS, 2f, 0.5f);
            case 160 -> sl.playSound(null, tc.x, tc.y, tc.z, SoundEvents.ELDER_GUARDIAN_CURSE, SoundSource.PLAYERS, 1.5f, 0.6f);
            default -> {}
        }
        if (r.age >= 120 && r.age < 190 && r.age % 12 == 0)   // the chains tighten
            sl.playSound(null, tc.x, tc.y, tc.z, SoundEvents.CHAIN_STEP, SoundSource.PLAYERS, 1.5f, 0.5f + (r.age - 120) / 140f);
        if (r.age % 20 == 0) sl.playSound(null, tc.x, tc.y, tc.z, SoundEvents.AMETHYST_BLOCK_RESONATE, SoundSource.PLAYERS, 1.5f, 0.4f + r.age / 400f);
        if (r.age % 3 == 0) DivineEvents.particle(sl, ParticleTypes.ENCHANT, tc.x, tc.y + 1, tc.z, 4, 0.6, 0.4);
    }

    @Override
    protected void apply(ServerLevel sl, LivingEntity caster, LivingEntity target) {
        if (!(target instanceof ServerPlayer p)) return;
        Vec3 c = p.position().add(0, p.getBbHeight() * 0.65, 0);
        Fx.play(sl, Fx.fx("soul_seal_lock_in").at(p.position()).caster(caster).target(p).attach(p));
        sl.playSound(null, c.x, c.y, c.z, SoundEvents.ANVIL_LAND, SoundSource.PLAYERS, 1.5f, 0.5f);
        sl.playSound(null, c.x, c.y, c.z, SoundEvents.BELL_BLOCK, SoundSource.PLAYERS, 3f, 0.5f);
        sl.playSound(null, c.x, c.y, c.z, SoundEvents.BEACON_DEACTIVATE, SoundSource.PLAYERS, 2f, 0.5f);
        DivineEvents.particle(sl, ParticleTypes.END_ROD, c.x, c.y, c.z, 40, 0.3, 0.25);
        CameraShakeManager.addCameraShake(new CameraShakeData(sl, 12, c, 20));
        SoulSeal.seal(p);
        p.displayClientMessage(net.minecraft.network.chat.Component.translatable("ui.pohsmp_core.soul_seal.sealed").withStyle(s -> s.withColor(0x9A7BFF)), false);
        ru.pohsmp.core.PohCore.LOG.info("[pohsmp_core] soul seal: {} sealed {}", caster.getName().getString(), p.getGameProfile().getName());
    }
}
