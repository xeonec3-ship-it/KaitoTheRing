package ru.pohsmp.core.spell;

import io.redspace.ironsspellbooks.api.config.DefaultConfig;
import io.redspace.ironsspellbooks.api.magic.MagicData;
import io.redspace.ironsspellbooks.api.spells.AbstractSpell;
import io.redspace.ironsspellbooks.api.spells.SpellRarity;
import io.redspace.ironsspellbooks.capabilities.magic.TargetEntityCastData;
import java.util.EnumSet;
import java.util.List;
import java.util.function.Predicate;
import net.minecraft.core.registries.Registries;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.damagesource.DamageSource;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.OwnableEntity;
import net.minecraft.world.entity.RelativeMovement;
import net.minecraft.world.entity.decoration.ArmorStand;
import net.minecraft.world.entity.monster.Enemy;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.Vec3;
import ru.pohsmp.core.PohCore;
import ru.pohsmp.core.Reg;
import ru.pohsmp.core.ServerConfig;
import ru.pohsmp.core.net.Net;

/** Higher school, level 1 only, Legendary in Iron's eyes (the tooltip shows "Higher"). No mana, no cooldown: scrolls are given by admins. */
public abstract class HigherSpell extends AbstractSpell {
    /** Owner 19.11: no scroll of our spells ever appears in a chest (see ru.pohsmp.core.NoLoot). */
    @Override public boolean allowLooting() { return false; }

    private final ResourceLocation id;
    private final DefaultConfig config = new DefaultConfig()
            .setMinRarity(SpellRarity.LEGENDARY)
            .setSchoolResource(Reg.HIGHER_ID)
            .setMaxLevel(1)
            .setCooldownSeconds(0)
            .setAllowCrafting(false)
            .build();

    protected HigherSpell(String path, int castTicks) {
        this.id = new ResourceLocation(PohCore.MODID, path);
        this.manaCostPerLevel = 0;
        this.baseSpellPower = 0;
        this.spellPowerPerLevel = 0;
        this.castTime = castTicks;
        this.baseManaCost = 0;
    }

    @Override public ResourceLocation getSpellResource() { return id; }
    @Override public DefaultConfig getDefaultConfig() { return config; }
    /** Black = invisible: Iron's target box is drawn additively, our spells have their own target visuals. */
    @Override public org.joml.Vector3f getTargetingColor() { return new org.joml.Vector3f(0, 0, 0); }

    protected net.minecraft.network.chat.MutableComponent ui(String key, Object... args) {
        return Component.translatable("ui.pohsmp_core." + id.getPath() + "." + key, args);
    }

    // ---- helpers shared by all Higher spells ----

    private static int KEY = 1;

    public static int key() {
        KEY = KEY >= 1_000_000_000 ? 1 : KEY + 1;
        return KEY;
    }

    public static float dmg(double base) {
        return (float) (base * ServerConfig.HIGHER_MULT.get());
    }

    public static String num(double d) {
        d *= ServerConfig.HIGHER_MULT.get();
        return d == Math.floor(d) ? String.valueOf((long) d) : String.format(java.util.Locale.ROOT, "%.1f", d);
    }

    public static DamageSource src(ServerLevel sl, LivingEntity caster) {
        return new DamageSource(sl.registryAccess().registryOrThrow(Registries.DAMAGE_TYPE).getHolderOrThrow(Reg.HIGHER_DAMAGE), caster);
    }

    public static boolean hurt(ServerLevel sl, LivingEntity caster, LivingEntity t, float amount) {
        if (!t.isAlive()) return false;
        t.invulnerableTime = 0;
        return t.hurt(src(sl, caster), amount);
    }

    /** Never hit by the caster's area spells: the caster, its team, its pets, armor stands, spectators. */
    public static boolean friendly(LivingEntity caster, Entity e) {
        if (e == caster || e instanceof ArmorStand || e.isSpectator()) return true;
        if (caster.isAlliedTo(e)) return true;
        return e instanceof OwnableEntity o && o.getOwnerUUID() != null && o.getOwnerUUID().equals(caster.getUUID());
    }

    /** Someone the caster is fighting: monsters, mobs targeting it, whoever it hit or was hit by. */
    public static boolean foe(LivingEntity caster, LivingEntity e) {
        if (!e.isAlive() || friendly(caster, e)) return false;
        if (e instanceof Enemy) return true;
        if (e instanceof Mob m && m.getTarget() == caster) return true;
        if (caster instanceof Mob cm && cm.getTarget() == e) return true;
        return caster.getLastHurtByMob() == e || caster.getLastHurtMob() == e;
    }

    public static List<LivingEntity> around(ServerLevel sl, Vec3 c, double r, Predicate<LivingEntity> p) {
        return sl.getEntitiesOfClass(LivingEntity.class, new AABB(c, c).inflate(r),
                e -> e.isAlive() && e.position().distanceToSqr(c) <= r * r && p.test(e));
    }

    protected static LivingEntity target(ServerLevel sl, MagicData md) {
        return md.getAdditionalCastData() instanceof TargetEntityCastData td ? td.getTarget(sl) : null;
    }

    /** Moves an entity to a point; players get a real teleport packet, view direction kept. */
    public static void place(LivingEntity t, double x, double y, double z) {
        if (t instanceof ServerPlayer p) p.connection.teleport(x, y, z, 0f, 0f, EnumSet.of(RelativeMovement.X_ROT, RelativeMovement.Y_ROT));
        else t.teleportTo(x, y, z);
    }

    /** Sets velocity and makes sure players receive it. */
    public static void push(Entity t, Vec3 v) {
        t.setDeltaMovement(v);
        t.hurtMarked = true;
    }

    public static void fx(ServerLevel sl, double x, double y, double z, Net.HFx m) {
        Net.sendNear(sl, x, y, z, x, y, z, m);
    }

    public static void stop(ServerLevel sl, double x, double y, double z, int key) {
        fx(sl, x, y, z, new Net.HFx(Net.HFx.STOP, key, -1, -1, 0, x, y, z, 0, 0));
    }

    public static void burst(ServerLevel sl, double x, double y, double z, double r, int rgb) {
        fx(sl, x, y, z, new Net.HFx(Net.HFx.BURST, key(), -1, -1, 30, x, y, z, r, rgb));
    }
}
