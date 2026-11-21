package ru.pohsmp.core.boss;

import java.util.UUID;
import net.minecraft.core.registries.Registries;
import net.minecraft.resources.ResourceKey;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.damagesource.DamageSource;
import net.minecraft.world.damagesource.DamageType;
import net.minecraft.world.entity.LivingEntity;
import net.minecraftforge.common.MinecraftForge;
import net.minecraftforge.event.entity.living.LivingHurtEvent;
import net.minecraftforge.eventbus.api.EventPriority;
import net.minecraftforge.fml.ModList;
import ru.pohsmp.core.PohCore;
import yesman.epicfight.api.forgeevent.EntityStunEvent;
import yesman.epicfight.api.utils.AttackResult;
import yesman.epicfight.gameasset.EpicFightSounds;
import yesman.epicfight.skill.guard.GuardSkill;
import yesman.epicfight.world.capabilities.EpicFightCapabilities;
import yesman.epicfight.world.capabilities.entitypatch.player.ServerPlayerPatch;
import yesman.epicfight.world.damagesource.EpicFightDamageSource;
import yesman.epicfight.world.damagesource.StunType;
import yesman.epicfight.world.entity.eventlistener.PlayerEventListener;
import yesman.epicfight.world.entity.eventlistener.TakeDamageEvent;

/**
 * T32: the cult bosses and Epic Fight 1.20.1 (20.14.x; soft dependency — every Epic Fight class is named only inside {@link Impl},
 * reached only when {@link #ON}). The bosses have no Epic Fight patch of their own (at most its GlobalMobPatch, a
 * HurtableEntityPatch, with the global_stun game rule): a player's guard and parry work on any hit that has an attacker and a
 * position, so nothing has to be registered for them.
 * <ul>
 * <li>Stun immunity (ef_stun_immune): {@link EntityStunEvent} (LivingHurtEvent of Epic Fight, before HurtableEntityPatch#applyStun —
 *     short / long stun, hold, knockdown, neutralize, and the knockback and impact that go with them) is cancelled on a boss.</li>
 * <li>Block: the guard (GuardSkill, TAKE_DAMAGE_EVENT_ATTACK of ServerPlayerPatch) stops pohsmp_core:boss_attack and the vanilla melee
 *     of the bosses; pohsmp_core:boss_mechanic and boss_guard_break are in epicfight:unblockable (GuardSkill#isBlockableSource).</li>
 * <li>Parry (ParryingSkill: TakeDamageEvent.Attack#isParried): damage 0 (the event is cancelled); the attacker reacts only through
 *     LivingEntityPatch#onAttackBlocked, which the bosses do not have — no recoil; ef_parry_no_recoil = false: a short stagger.</li>
 * <li>Our own listener (priority -1: after the guard skills) counts the blocked hits for «Сломать блок» ({@link BossGuardBreak}).</li>
 * <li>Breaking the guard: PlayerPatch#setStamina(0) + LivingEntityPatch#applyStun(NEUTRALIZE) (Epic Fight's own guard break pose).</li>
 * <li>BossGuard: Epic Fight scales a hit after our filter (animation multipliers, innate skills, executions): the lowest
 *     LivingHurtEvent cuts it again ({@link BossGuard#afterExternal}).</li>
 * </ul>
 */
public final class BossEpicFight {
    public static final boolean ON = ModList.get().isLoaded("epicfight");

    private static final UUID LISTENER = UUID.fromString("3e0b6f2a-7c41-4d8e-9b25-61f0a4c3d7e1");
    static final ResourceKey<DamageType> MECHANIC = ResourceKey.create(Registries.DAMAGE_TYPE, new ResourceLocation(PohCore.MODID, "boss_mechanic")),
            GUARD_BREAK = ResourceKey.create(Registries.DAMAGE_TYPE, new ResourceLocation(PohCore.MODID, "boss_guard_break"));

    private BossEpicFight() {}

    /** From Bosses.init when Epic Fight is loaded. */
    static void init() {
        MinecraftForge.EVENT_BUS.addListener(Impl::onStun);
        MinecraftForge.EVENT_BUS.addListener(EventPriority.LOWEST, Impl::onHurt);
        PohCore.LOG.info("[boss] Epic Fight: stun immunity, guard / parry of boss hits, «Сломать блок»");
    }

    /** p holds the Epic Fight guard (a GuardSkill / ParryingSkill is the held skill). False without Epic Fight. */
    public static boolean guarding(ServerPlayer p) {
        if (!ON) return false;
        try {
            return Impl.guarding(p);
        } catch (RuntimeException | LinkageError e) {   // an API change in Epic Fight must not break the fight
            return false;
        }
    }

    /** Breaks p's guard: Epic Fight stamina 0 and its neutralize (guard break) pose; stun ticks for the pose's length. */
    public static void breakGuard(ServerPlayer p, int stunTicks) {
        if (!ON) return;
        try {
            Impl.breakGuard(p, stunTicks);
        } catch (RuntimeException | LinkageError e) {
            PohCore.LOG.warn("[boss] Epic Fight guard break failed: {}", e.toString());
        }
    }

    /** Makes sure our block counter listens to p (idempotent; called every second for the fighters of a boss). */
    public static void listen(ServerPlayer p) {
        if (!ON) return;
        try {
            Impl.listen(p);
        } catch (RuntimeException | LinkageError e) {
            // no counter: the hold time alone starts the Guard Break
        }
    }

    /** Everything that names Epic Fight classes lives here, so the outer class loads without Epic Fight. */
    private static final class Impl {
        static boolean guarding(ServerPlayer p) {
            ServerPlayerPatch patch = EpicFightCapabilities.getEntityPatch(p, ServerPlayerPatch.class);
            return patch != null && patch.isEpicFightMode() && patch.getHoldingSkill() instanceof GuardSkill;
        }

        static void breakGuard(ServerPlayer p, int stunTicks) {
            ServerPlayerPatch patch = EpicFightCapabilities.getEntityPatch(p, ServerPlayerPatch.class);
            if (patch == null) return;
            patch.setStamina(0);
            patch.applyStun(StunType.NEUTRALIZE, stunTicks / 20.0F);
            ru.pohsmp.core.spell.CastLock.interrupt(p);   // owner 21.11: a broken guard ends the cast window
            patch.playSound(EpicFightSounds.NEUTRALIZE_MOBS.get(), 3.0F, 0.0F, 0.1F);
        }

        static void listen(ServerPlayer p) {
            ServerPlayerPatch patch = EpicFightCapabilities.getEntityPatch(p, ServerPlayerPatch.class);
            if (patch == null) return;
            patch.getEventListener().addEventListener(PlayerEventListener.EventType.TAKE_DAMAGE_EVENT_ATTACK, LISTENER, Impl::onAttack, -1);
        }

        /** After the guard skills (priority -1 runs even when they cancelled): blocked / parried / landed boss hits. */
        static void onAttack(TakeDamageEvent.Attack e) {
            DamageSource src = e.getDamageSource();
            BossCore c = BossGuard.core(src.getEntity());
            if (c == null || src.is(MECHANIC) || src.is(GUARD_BREAK)) return;
            ServerPlayer p = e.getPlayerPatch().getOriginal();
            if (e.isCanceled() && e.getResult() == AttackResult.ResultType.BLOCKED) BossGuardBreak.blocked(c, p, e.isParried());
            else if (!e.isCanceled()) BossGuardBreak.landed(p);
        }

        /** ef_stun_immune: no Epic Fight stun of any kind on a boss (its knockback and impact go with it). */
        static void onStun(EntityStunEvent e) {
            LivingEntity le = e.getStunnedEntityPatch().getOriginal();
            if (BossGuard.isBoss(le) && BossConfig.get(BossConfig.EF_STUN_IMMUNE)) e.setCanceled(true);
            else if (!e.isCanceled() && !le.level().isClientSide) ru.pohsmp.core.spell.CastLock.interrupt(le);   // a stunned player: the cast window ends
        }

        /** An Epic Fight hit on a boss, after Epic Fight scaled it: our protection again. */
        static void onHurt(LivingHurtEvent e) {
            BossCore c = BossGuard.core(e.getEntity());
            if (c == null || !(e.getSource() instanceof EpicFightDamageSource) || e.getEntity().level().isClientSide) return;
            float a = BossGuard.afterExternal(c, e.getAmount());
            if (a != e.getAmount()) e.setAmount(a);
        }
    }
}
