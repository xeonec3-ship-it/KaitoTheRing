package ru.pohsmp.core.boss.cult;

import io.redspace.ironsspellbooks.entity.mobs.abstract_spell_casting_mob.AbstractSpellCastingMob;
import io.redspace.ironsspellbooks.entity.mobs.wizards.pyromancer.PyromancerEntity;
import java.util.UUID;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.util.RandomSource;
import net.minecraft.world.DifficultyInstance;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.damagesource.DamageSource;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.EquipmentSlot;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.Level;

/**
 * A fire cultist of phase 3 (2-4 summoned): an Iron's pyromancer in the cult's look (geo/entity/fire_cultist.geo.json), without the
 * pyromancer's armour (it would cover the robe), hostile to players, no trade, no loot; goes with the leader.
 */
public class FireCultistEntity extends PyromancerEntity {
    UUID leader;

    public FireCultistEntity(EntityType<? extends AbstractSpellCastingMob> type, Level level) {
        super(type, level);
        xpReward = 5;
    }

    @Override
    protected void populateDefaultEquipmentSlots(RandomSource r, DifficultyInstance d) {
        super.populateDefaultEquipmentSlots(r, d);
        for (EquipmentSlot s : new EquipmentSlot[] {EquipmentSlot.HEAD, EquipmentSlot.CHEST, EquipmentSlot.LEGS, EquipmentSlot.FEET})
            setItemSlot(s, ItemStack.EMPTY);
        for (EquipmentSlot s : EquipmentSlot.values()) setDropChance(s, 0);
    }

    /** Its leader, health (x the boss's player multiplier), armour, spell power ([cult_leader] cultist_*). */
    void setup(UUID leader, double hp, double armor, double power) {
        this.leader = leader;
        set(net.minecraft.world.entity.ai.attributes.Attributes.MAX_HEALTH, hp);
        set(net.minecraft.world.entity.ai.attributes.Attributes.ARMOR, armor);
        var sp = net.minecraftforge.registries.ForgeRegistries.ATTRIBUTES.getValue(new net.minecraft.resources.ResourceLocation("irons_spellbooks", "spell_power"));
        if (sp != null) set(sp, power);
        setHealth(getMaxHealth());
    }

    private void set(net.minecraft.world.entity.ai.attributes.Attribute a, double v) {
        var i = getAttribute(a);
        if (i != null) i.setBaseValue(v);
    }

    @Override
    public void tick() {
        super.tick();
        if (!(level() instanceof ServerLevel sl) || tickCount % 10 != 0) return;
        if (leader != null && !(sl.getEntity(leader) instanceof CultLeaderEntity l && l.isAlive())) {
            kill();
            return;
        }
        if (getTarget() == null || !getTarget().isAlive()) {
            Player p = sl.getNearestPlayer(this, 32);
            if (p != null && !p.isCreative() && !p.isSpectator()) {
                setTarget(p);
                setPersistentAngerTarget(p.getUUID());
                startPersistentAngerTimer();
            }
        }
    }

    @Override
    public boolean isAlliedTo(Entity e) {
        return e instanceof CultLeaderEntity || e instanceof FireCultistEntity || super.isAlliedTo(e);
    }

    @Override
    protected InteractionResult mobInteract(Player p, InteractionHand hand) {
        return InteractionResult.PASS;
    }

    @Override
    protected void dropCustomDeathLoot(DamageSource src, int looting, boolean byPlayer) {}

    @Override
    public boolean removeWhenFarAway(double d) {
        return false;
    }

    @Override
    public void addAdditionalSaveData(net.minecraft.nbt.CompoundTag tag) {
        super.addAdditionalSaveData(tag);
        if (leader != null) tag.putUUID("cult_leader", leader);
    }

    @Override
    public void readAdditionalSaveData(net.minecraft.nbt.CompoundTag tag) {
        super.readAdditionalSaveData(tag);
        if (tag.hasUUID("cult_leader")) leader = tag.getUUID("cult_leader");
    }
}
