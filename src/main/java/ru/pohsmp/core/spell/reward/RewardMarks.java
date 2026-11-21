package ru.pohsmp.core.spell.reward;

import java.util.HashMap;
import java.util.Map;
import java.util.UUID;
import net.minecraft.world.damagesource.DamageSource;
import net.minecraft.world.damagesource.DamageTypes;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.LivingEntity;
import net.minecraftforge.event.entity.living.LivingHurtEvent;
import net.minecraftforge.event.server.ServerStoppingEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import ru.pohsmp.core.PohCore;
import ru.pohsmp.core.spell.HigherSpell;

/**
 * Damage bonuses of the T34 reward spells (short, not saved):
 * <ul>
 *   <li>«Метка ревности» (jealous_embrace): the marked target takes +EMB_MARK_BONUS from the player who marked it;</li>
 *   <li>«Закалка» (anvil_strike): the player's weapon hits (melee, player_attack) deal +ANV_TEMPER_BONUS;</li>
 *   <li>«Хватка Длани» (hand_of_lies): the held target takes +HAND_BONUS from the caster and its allies (team, pets, banner soldiers).</li>
 * </ul>
 */
@Mod.EventBusSubscriber(modid = PohCore.MODID)
public final class RewardMarks {
    private RewardMarks() {}

    private record Mark(UUID by, long until) {}

    private static final Map<UUID, Map<UUID, Long>> JEALOUS = new HashMap<>();
    private static final Map<UUID, Long> TEMPER = new HashMap<>();
    private static final Map<UUID, Mark> HAND = new HashMap<>();

    public static void jealous(LivingEntity target, LivingEntity by, int ticks) {
        JEALOUS.computeIfAbsent(target.getUUID(), k -> new HashMap<>()).put(by.getUUID(), target.level().getGameTime() + ticks);
    }

    public static void temper(LivingEntity player, int ticks) {
        TEMPER.put(player.getUUID(), player.level().getGameTime() + ticks);
    }

    public static boolean tempered(LivingEntity player) {
        Long u = TEMPER.get(player.getUUID());
        return u != null && player.level().getGameTime() < u;
    }

    public static void held(LivingEntity target, LivingEntity by, int ticks) {
        HAND.put(target.getUUID(), new Mark(by.getUUID(), target.level().getGameTime() + ticks));
    }

    /** The extra share of this hit (0 = none), all three bonuses multiplied. */
    static double bonus(LivingEntity victim, DamageSource src) {
        Entity att = src.getEntity();
        if (att == null || victim.level().isClientSide) return 0;
        long now = victim.level().getGameTime();
        double j = 0, t = 0, h = 0;
        Map<UUID, Long> jm = JEALOUS.get(victim.getUUID());
        if (jm != null) {
            Long u = jm.get(att.getUUID());
            if (u != null && now < u) j = RewardMath.EMB_MARK_BONUS;
            jm.values().removeIf(x -> x <= now);
            if (jm.isEmpty()) JEALOUS.remove(victim.getUUID());
        }
        if (att instanceof LivingEntity la && src.getDirectEntity() == att && src.is(DamageTypes.PLAYER_ATTACK) && tempered(la)) t = RewardMath.ANV_TEMPER_BONUS;
        Mark m = HAND.get(victim.getUUID());
        if (m != null) {
            if (now >= m.until()) HAND.remove(victim.getUUID());
            else if (att.getUUID().equals(m.by()) || ally(victim, m.by(), att)) h = RewardMath.HAND_BONUS;
        }
        return RewardMath.mult(j, t, h) - 1;
    }

    private static boolean ally(LivingEntity victim, UUID caster, Entity att) {
        if (!(victim.level() instanceof net.minecraft.server.level.ServerLevel sl)) return false;
        Entity c = sl.getEntity(caster);
        return c instanceof LivingEntity lc && HigherSpell.friendly(lc, att) && att != victim;
    }

    @SubscribeEvent
    public static void onHurt(LivingHurtEvent e) {
        if (JEALOUS.isEmpty() && TEMPER.isEmpty() && HAND.isEmpty()) return;
        double b = bonus(e.getEntity(), e.getSource());
        if (b > 0) e.setAmount((float) (e.getAmount() * (1 + b)));
    }

    @SubscribeEvent
    public static void onStopping(ServerStoppingEvent e) {
        JEALOUS.clear();
        TEMPER.clear();
        HAND.clear();
    }
}
