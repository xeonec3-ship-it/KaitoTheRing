package ru.pohsmp.core.spell;

import java.util.List;
import net.minecraft.ChatFormatting;
import net.minecraft.core.registries.Registries;
import net.minecraft.network.chat.Component;
import net.minecraft.network.chat.MutableComponent;
import net.minecraft.resources.ResourceKey;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.damagesource.DamageSource;
import net.minecraft.world.damagesource.DamageType;
import net.minecraft.world.entity.LivingEntity;
import net.minecraftforge.event.entity.living.LivingDamageEvent;
import net.minecraftforge.eventbus.api.EventPriority;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import ru.pohsmp.core.PohCore;
import ru.pohsmp.core.Reg;
import ru.pohsmp.core.ServerConfig;

/**
 * «Дезинтеграция: Реплика» — Higher school, level 1. Same hold and cast as {@link DisintegrationSpell} (10 s, target frozen
 * and lifted, cast not interrupted), scarlet visuals (fx/disintegration_replica.json), a spoken chant, and a hit of
 * {@code replica.damagePercent} (0.9) of max HP through armor that can never kill: the target is left with at least 1 HP.
 */
public class DisintegrationReplicaSpell extends DisintegrationSpell {
    public static final String PATH = "disintegration_replica";
    public static final ResourceLocation RID = new ResourceLocation(PohCore.MODID, PATH);
    public static final ResourceKey<DamageType> DAMAGE = ResourceKey.create(Registries.DAMAGE_TYPE, new ResourceLocation(PohCore.MODID, "replica_magic"));

    /** Chant: line and the hold tick it is spoken at (cast is 200 ticks; the screen flash of the effect is at 192). */
    private static final String[] CHANT = {
            "Я желаю и жажду силы святых духов.",
            "Услышь мою мольбу и исполни её.",
            "Пусть всё сущее обратится в прах!",
            "Дезинтеграция!!"};
    private static final int[] CHANT_AT = {10, 70, 130, 192};

    public DisintegrationReplicaSpell() {
        super(RID, Reg.HIGHER_ID, 1);
    }

    @Override
    public List<MutableComponent> getUniqueInfo(int spellLevel, LivingEntity caster) {
        int pct = (int) Math.round(ServerConfig.REPLICA_PERCENT.get() * 100);
        return List.of(Component.translatable("ui.pohsmp_core.disintegration_replica.damage", pct + "%"),
                Component.translatable("ui.pohsmp_core.disintegration_replica.nonlethal"));
    }

    @Override
    protected void chant(ServerLevel sl, LivingEntity caster, int age) {
        for (int i = 0; i < CHANT.length; i++) if (CHANT_AT[i] == age) say(sl, caster, CHANT[i], i == CHANT.length - 1);
    }

    private static void say(ServerLevel sl, LivingEntity caster, String text, boolean last) {
        MutableComponent line = Component.literal("«" + text + "»").withStyle(ChatFormatting.RED, ChatFormatting.ITALIC);
        if (last) line.withStyle(ChatFormatting.BOLD);
        Component msg = Component.literal("").append(caster.getDisplayName()).append(Component.literal(": ").withStyle(ChatFormatting.GRAY)).append(line);
        for (ServerPlayer p : sl.players()) if (p.distanceToSqr(caster) < 64 * 64) p.sendSystemMessage(msg);
    }

    @Override
    protected void strike(ServerLevel sl, LivingEntity caster, LivingEntity t) {
        if (t.getHealth() <= 1) return;
        float dmg = (float) (t.getMaxHealth() * ServerConfig.REPLICA_PERCENT.get());
        DamageSource src = new DamageSource(sl.registryAccess().registryOrThrow(Registries.DAMAGE_TYPE).getHolderOrThrow(DAMAGE), caster);
        t.invulnerableTime = 0;
        t.hurt(src, dmg);
    }

    /** Never lethal: runs last, after armor, resistances, absorption and other mods' changes. */
    public static final class ReplicaEvents {
        private ReplicaEvents() {}

        @SubscribeEvent(priority = EventPriority.LOWEST)
        public static void onDamage(LivingDamageEvent e) {
            if (!e.getSource().is(DAMAGE)) return;
            float keep = e.getEntity().getHealth() - 1;
            if (keep <= 0) e.setCanceled(true);
            else if (e.getAmount() > keep) e.setAmount(keep);
        }
    }
}
