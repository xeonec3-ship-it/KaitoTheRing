package ru.pohsmp.core.spell;

import io.redspace.ironsspellbooks.api.config.DefaultConfig;
import io.redspace.ironsspellbooks.api.spells.AbstractSpell;
import io.redspace.ironsspellbooks.api.spells.SpellRarity;
import io.redspace.ironsspellbooks.damage.DamageSources;
import net.minecraft.network.chat.Component;
import net.minecraft.network.chat.MutableComponent;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.level.ClipContext;
import net.minecraft.world.phys.BlockHitResult;
import net.minecraft.world.phys.HitResult;
import net.minecraft.world.phys.Vec3;
import ru.pohsmp.core.PohCore;

/** Base of the ordinary-school spells of this mod (Iron's schools, levels 1..max, mana and cooldown as usual). */
public abstract class PohSpell extends AbstractSpell {
    private final ResourceLocation id;
    private final DefaultConfig config;

    protected PohSpell(String path, ResourceLocation school, SpellRarity minRarity, int maxLevel, double cooldownSec,
                       int castTicks, int baseMana, int manaPerLevel) {
        this.id = new ResourceLocation(PohCore.MODID, path);
        this.config = new DefaultConfig()
                .setMinRarity(minRarity)
                .setSchoolResource(school)
                .setMaxLevel(maxLevel)
                .setCooldownSeconds(cooldownSec)
                .setAllowCrafting(true)
                .build();
        this.castTime = castTicks;
        this.baseManaCost = baseMana;
        this.manaCostPerLevel = manaPerLevel;
        this.baseSpellPower = 1;
        this.spellPowerPerLevel = 0;
    }

    /** Iron's schools with a drawn sign: effect fx/school_&lt;school&gt;.json (sigil sigils/school_&lt;school&gt;.json, style fx/styles/&lt;school&gt;.json). */
    private static final java.util.Set<String> SIGIL_SCHOOLS =
            java.util.Set.of("fire", "ice", "lightning", "nature", "holy", "blood", "ender", "evocation", "eldritch", "wind");

    /** The same schools in HFx.SIGIL order (b) and their colors: the joint cast (T15) still draws its double outline through HFx. */
    private static final String[] SIGIL_ORDER = {"fire", "ice", "lightning", "nature", "holy", "blood", "ender", "evocation", "eldritch", "wind"};
    private static final int[] SIGIL_COLORS = {0xFF7A2A, 0x9FE0FF, 0x6BE6FF, 0x7EE04A, 0xFFE38A, 0xE0242C, 0xC060FF, 0xDDE6F0, 0x3FD6B8, 0xBFF2E8};

    /** Index of the drawn sigil of an Iron's school (by path), -1 if it has none. */
    public static int sigilIndex(String school) {
        for (int i = 0; i < SIGIL_ORDER.length; i++) if (SIGIL_ORDER[i].equals(school)) return i;
        return -1;
    }

    public static int sigilColor(int index) {
        return SIGIL_COLORS[index];
    }

    /** Every cast of an ordinary-school spell draws the sign of its school under the caster (the spell's own visuals stay as they are). */
    @Override
    public void onCast(net.minecraft.world.level.Level level, int spellLevel, LivingEntity caster, io.redspace.ironsspellbooks.api.spells.CastSource source,
                       io.redspace.ironsspellbooks.api.magic.MagicData md) {
        if (level instanceof ServerLevel sl && caster != null) {
            String school = getSchoolType() == null ? "" : getSchoolType().getId().getPath();
            if (SIGIL_SCHOOLS.contains(school) && !ru.pohsmp.core.SchoolSeals.shown(caster))   // T06: a tier seal is up — no second sign
                ru.pohsmp.core.fx.Fx.play(sl, ru.pohsmp.core.fx.Fx.fx("school_" + school).at(caster.position()).caster(caster));
        }
        super.onCast(level, spellLevel, caster, source, md);
    }

    @Override public ResourceLocation getSpellResource() { return id; }

    /** Silent-school spells also take the Silent cast time reduction (the Silent Witch robe). */
    @Override
    public int getEffectiveCastTime(int spellLevel, @org.jetbrains.annotations.Nullable LivingEntity entity) {
        if (getSchoolType() == ru.pohsmp.core.Reg.SILENT.get()) return ru.pohsmp.core.silent.SilentWitch.castTime(this, spellLevel, entity);
        return super.getEffectiveCastTime(spellLevel, entity);
    }
    @Override public DefaultConfig getDefaultConfig() { return config; }
    /** Black = invisible: Iron's target box is drawn additively. */
    @Override public org.joml.Vector3f getTargetingColor() { return new org.joml.Vector3f(0, 0, 0); }

    protected MutableComponent ui(String key, Object... args) {
        return Component.translatable("ui.pohsmp_core." + id.getPath() + "." + key, args);
    }

    /** Value growing linearly from a (level 1) to b (max level). */
    protected double lv(int level, double a, double b) {
        int max = Math.max(2, getMaxLevel());
        return a + (b - a) * (Math.max(1, Math.min(level, max)) - 1) / (double) (max - 1);
    }

    /** Spell power multiplier of the caster for this school (1.0 = no bonus). */
    protected float mult(LivingEntity caster) {
        return caster == null ? 1f : getEntityPowerMultiplier(caster);
    }

    /** School damage through Iron's (resistances, spell events). */
    public boolean hit(LivingEntity caster, LivingEntity t, float amount) {
        if (!t.isAlive()) return false;
        t.invulnerableTime = 0;
        return DamageSources.applyDamage(t, amount, getDamageSource(caster));
    }

    public static String n(double d) {
        return d == Math.floor(d) ? String.valueOf((long) d) : String.format(java.util.Locale.ROOT, "%.1f", d);
    }

    /** Point where the caster looks: the first creature on the line (its feet), else the first block, else the end of the range. */
    public static Vec3 lookPoint(ServerLevel sl, LivingEntity caster, double range) {
        Vec3 eye = caster.getEyePosition();
        Vec3 end = eye.add(caster.getLookAngle().scale(range));
        BlockHitResult hr = sl.clip(new ClipContext(eye, end, ClipContext.Block.COLLIDER, ClipContext.Fluid.NONE, caster));
        if (hr.getType() != HitResult.Type.MISS) end = hr.getLocation();
        net.minecraft.world.phys.EntityHitResult eh = net.minecraft.world.entity.projectile.ProjectileUtil.getEntityHitResult(sl, caster, eye, end,
                new net.minecraft.world.phys.AABB(eye, end).inflate(1),
                e -> e instanceof LivingEntity && e != caster && !e.isSpectator() && e.isPickable() && !(e instanceof net.minecraft.world.entity.decoration.ArmorStand));
        return eh != null ? eh.getEntity().position() : end;
    }

    /** Ground under a point (down to 24 blocks). */
    public static Vec3 ground(ServerLevel sl, Entity e, Vec3 p) {
        BlockHitResult hr = sl.clip(new ClipContext(p.add(0, 0.5, 0), p.add(0, -24, 0), ClipContext.Block.COLLIDER, ClipContext.Fluid.NONE, e));
        return hr.getType() == HitResult.Type.MISS ? p : hr.getLocation();
    }

    public static double hdist(Entity e, Vec3 c) {
        double dx = e.getX() - c.x, dz = e.getZ() - c.z;
        return Math.sqrt(dx * dx + dz * dz);
    }
}
