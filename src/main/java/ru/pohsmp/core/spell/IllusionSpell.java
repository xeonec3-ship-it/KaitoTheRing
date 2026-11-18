package ru.pohsmp.core.spell;

import io.redspace.ironsspellbooks.api.magic.MagicData;
import io.redspace.ironsspellbooks.api.registry.SchoolRegistry;
import io.redspace.ironsspellbooks.api.spells.CastSource;
import io.redspace.ironsspellbooks.api.spells.CastType;
import io.redspace.ironsspellbooks.api.spells.SpellRarity;
import java.util.List;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.chat.MutableComponent;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.effect.MobEffectInstance;
import net.minecraft.world.effect.MobEffects;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.EquipmentSlot;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.decoration.ArmorStand;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.event.entity.player.AttackEntityEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import ru.pohsmp.core.DivineEvents;

/**
 * Evocation: the caster leaves a double in its place and turns briefly invisible. Mobs hunting the caster go after the
 * double; it bursts when someone strikes or reaches it (or when it fades).
 */
public class IllusionSpell extends PohSpell {
    public static final String PATH = "illusion";

    public IllusionSpell() {
        super(PATH, SchoolRegistry.EVOCATION_RESOURCE, SpellRarity.UNCOMMON, 6, 20, 0, 40, 6);
    }

    @Override public CastType getCastType() { return CastType.INSTANT; }

    private int seconds(int l) { return (int) Math.round(lv(l, 6, 12)); }
    private double damage(int l, LivingEntity c) { return lv(l, 4, 12) * mult(c); }

    @Override
    public List<MutableComponent> getUniqueInfo(int level, LivingEntity caster) {
        return List.of(ui("time", seconds(level)), ui("damage", n(damage(level, caster))));
    }

    @Override
    public void onCast(Level level, int spellLevel, LivingEntity caster, CastSource source, MagicData md) {
        if (level instanceof ServerLevel sl) {
            ArmorStand body = EntityType.ARMOR_STAND.create(sl);
            if (body != null) {
                CompoundTag tag = new CompoundTag();
                body.saveWithoutId(tag);
                tag.putBoolean("ShowArms", true);
                tag.putBoolean("NoBasePlate", true);
                tag.putBoolean("Invulnerable", true);
                tag.putInt("DisabledSlots", 4144959);
                body.load(tag);
                Vec3 p = caster.position();
                body.moveTo(p.x, p.y, p.z, caster.getYRot(), 0);
                for (EquipmentSlot s : EquipmentSlot.values()) body.setItemSlot(s, caster.getItemBySlot(s).copy());
                if (caster instanceof Player pl && body.getItemBySlot(EquipmentSlot.HEAD).isEmpty()) {
                    ItemStack head = new ItemStack(Items.PLAYER_HEAD);
                    head.getOrCreateTag().putString("SkullOwner", pl.getGameProfile().getName());
                    body.setItemSlot(EquipmentSlot.HEAD, head);
                }
                body.setCustomName(caster.getDisplayName());
                body.setCustomNameVisible(caster instanceof Player);
                sl.addFreshEntity(body);
                Disp.track(body);
                Marks.Decoy d = new Marks.Decoy();
                d.spell = this;
                d.caster = caster;
                d.body = body;
                d.until = sl.getGameTime() + seconds(spellLevel) * 20L;
                d.dmg = (float) damage(spellLevel, caster);
                d.r = 3.5;
                Marks.DECOYS.add(d);
                caster.addEffect(new MobEffectInstance(MobEffects.INVISIBILITY, 60, 0, false, false, true));
                Vec3 side = caster.getLookAngle().multiply(1, 0, 1).normalize().yRot((float) Math.PI / 2).scale(2.5);
                HigherSpell.push(caster, side.add(0, 0.25, 0));
                sl.playSound(null, p.x, p.y, p.z, SoundEvents.ILLUSIONER_MIRROR_MOVE, SoundSource.PLAYERS, 1.5f, 1f);
                DivineEvents.particle(sl, ParticleTypes.WITCH, p.x, p.y + 1, p.z, 40, 0.5, 0.1);
            }
        }
        super.onCast(level, spellLevel, caster, source, md);
    }

    /** A player striking the double pops it. */
    public static final class Events {
        private Events() {}

        @SubscribeEvent
        public static void onPlayerAttack(AttackEntityEvent e) {
            if (Marks.DECOYS.isEmpty() || e.getEntity().level().isClientSide) return;
            for (Marks.Decoy d : new java.util.ArrayList<>(Marks.DECOYS))
                if (d.body == e.getTarget()) {
                    e.setCanceled(true);
                    Marks.boom((ServerLevel) d.body.level(), d);
                }
        }
    }
}
