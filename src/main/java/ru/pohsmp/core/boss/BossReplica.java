package ru.pohsmp.core.boss;

import io.redspace.ironsspellbooks.api.entity.IMagicEntity;
import io.redspace.ironsspellbooks.api.magic.MagicData;
import io.redspace.ironsspellbooks.api.registry.SpellRegistry;
import io.redspace.ironsspellbooks.api.spells.AbstractSpell;
import io.redspace.ironsspellbooks.api.spells.CastSource;
import io.redspace.ironsspellbooks.capabilities.magic.TargetEntityCastData;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.player.Player;
import ru.pohsmp.core.fx.Fx;
import ru.pohsmp.core.spell.DisintegrationReplicaSpell;
import ru.pohsmp.core.spell.NpcCast;
import ru.pohsmp.core.spell.TargetPose;

/**
 * «Дезинтеграция: Реплика» does not work on any of the five (owner 20.11, balance replica_immune): it is let begin (2 s), then the
 * boss plays its own break animation + fx; on the `break` event the cast is stopped (its seals dissolve by themselves), the caster
 * loses the mana and gets the cooldown as if it had cast; on `speak` its phrase (r32, the on-screen subtitle BossCore.say; not more
 * often than replica_taunt_cooldown). The real Disintegration works as usual. Runs for every boss from BossCore.tick; a boss changes
 * the timings / names / phrase by overriding {@link PohBoss#replicaReaction()}.
 */
public final class BossReplica {
    private BossReplica() {}

    /**
     * delay: ticks after the hold began before the boss reacts; breakAt / speakAt: ticks of its animation; length: the animation;
     * height: of the subtitle over its feet.
     */
    public record Reaction(String animation, String fx, String phraseKey, int delay, int breakAt, int speakAt, int length, double height) {
        /** Defaults for boss id: <id>_replica_break (animation and fx), ui.pohsmp_core.<id>.replica, the T26 timings (2.6 s, break 0.9, speak 1.9). */
        public static Reaction of(String bossId, double height) {
            return new Reaction(bossId + "_replica_break", bossId + "_replica_break", "ui.pohsmp_core." + bossId + ".replica", 40, 18, 38, 52, height);
        }
    }

    static final class State {
        boolean busy;
        long lastTaunt = Long.MIN_VALUE / 2;
    }

    static void tick(BossCore core, PohBoss boss, State st) {
        Mob mob = core.mob;
        if (st.busy || !(mob.level() instanceof ServerLevel sl) || !TargetPose.held(mob) || core.inFinale()) return;
        LivingEntity caster = casterOf(sl, mob);
        if (caster == null) return;
        Reaction r = boss.replicaReaction();
        if (r == null) return;
        st.busy = true;
        core.play(new BossTimeline("replica", r.delay() + r.length())
                .at(r.delay(), () -> {
                    core.lock(r.length(), true, false);
                    if (r.animation() != null && mob instanceof io.redspace.ironsspellbooks.entity.mobs.IAnimatedAttacker a)
                        a.serverTriggerAnimation(r.animation());
                    if (r.fx() != null) Fx.play(sl, Fx.fx(r.fx()).caster(mob).at(mob.position()).yaw(mob.getYRot()));
                    boss.onReplicaBreak(caster);
                })
                .at(r.delay() + r.breakAt(), () -> {
                    core.sound(core.def.id + ".replica_break", 3, 1);   // boss sounds 21.11: at the break itself, not at the reaction start
                    breakCast(caster);
                })
                .at(r.delay() + r.speakAt(), () -> {
                    long now = sl.getGameTime();
                    if (now - st.lastTaunt >= BossConfig.get(BossConfig.REPLICA_TAUNT_COOLDOWN) * 20L) {
                        st.lastTaunt = now;
                        core.say(r.phraseKey(), 32, 60, r.height());
                    }
                })
                .then(() -> st.busy = false));
    }

    /** Whoever is casting the Replica at this mob (a player or an Iron's casting mob), or null (the true Disintegration). */
    static LivingEntity casterOf(ServerLevel sl, Mob mob) {
        for (LivingEntity e : sl.getEntitiesOfClass(LivingEntity.class, mob.getBoundingBox().inflate(64))) {
            MagicData md = e instanceof Player ? MagicData.getPlayerMagicData(e) : e instanceof IMagicEntity m ? m.getMagicData() : null;
            if (md == null || !md.isCasting() || !DisintegrationReplicaSpell.RID.toString().equals(md.getCastingSpellId())) continue;
            if (md.getAdditionalCastData() instanceof TargetEntityCastData td && td.getTarget(sl) == mob) return e;
        }
        return null;
    }

    /** The cast is stopped (its seals dissolve by themselves); a player loses the mana and gets the cooldown as if it had been cast. */
    static void breakCast(LivingEntity caster) {
        if (!caster.isAlive()) return;
        AbstractSpell spell = SpellRegistry.getSpell(DisintegrationReplicaSpell.RID);
        MagicData md = caster instanceof Player ? MagicData.getPlayerMagicData(caster) : null;
        int lvl = md != null ? Math.max(1, md.getCastingSpellLevel()) : 1;
        NpcCast.cancelAny(caster);
        if (caster instanceof ServerPlayer sp && md != null && spell != null && !sp.isCreative()) {
            md.setMana(Math.max(0, md.getMana() - spell.getManaCost(lvl)));
            var mm = io.redspace.ironsspellbooks.IronsSpellbooks.MAGIC_MANAGER;
            if (mm != null) mm.addCooldown(sp, spell, CastSource.SPELLBOOK);
        }
    }
}
