package ru.pohsmp.core;

import io.redspace.ironsspellbooks.api.registry.AttributeRegistry;
import io.redspace.ironsspellbooks.api.registry.SchoolRegistry;
import io.redspace.ironsspellbooks.api.registry.SpellRegistry;
import io.redspace.ironsspellbooks.api.spells.AbstractSpell;
import io.redspace.ironsspellbooks.api.spells.SchoolType;
import net.minecraft.core.registries.Registries;
import net.minecraft.network.chat.Component;
import net.minecraft.network.chat.Style;
import net.minecraft.resources.ResourceKey;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.tags.ItemTags;
import net.minecraft.tags.TagKey;
import net.minecraft.world.damagesource.DamageType;
import net.minecraft.world.effect.MobEffect;
import net.minecraft.world.entity.ai.attributes.Attribute;
import net.minecraft.world.entity.ai.attributes.RangedAttribute;
import net.minecraft.world.item.CreativeModeTab;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraftforge.eventbus.api.IEventBus;
import net.minecraftforge.registries.DeferredRegister;
import net.minecraftforge.registries.ForgeRegistries;
import net.minecraftforge.registries.RegistryObject;
import java.util.List;
import net.minecraft.world.effect.MobEffectCategory;
import net.minecraft.world.entity.ai.attributes.AttributeModifier;
import net.minecraft.world.entity.ai.attributes.Attributes;
import ru.pohsmp.core.spell.AscensionSpell;
import ru.pohsmp.core.spell.AshlessSpell;
import ru.pohsmp.core.spell.CradleSpell;
import ru.pohsmp.core.spell.DisintegrationSpell;
import ru.pohsmp.core.spell.FateStarSpell;
import ru.pohsmp.core.spell.SealSpell;
import ru.pohsmp.core.spell.SingularitySpell;

public final class Reg {
    private Reg() {}

    public static final int DIVINE_COLOR = 0xFFD34D;

    public static final DeferredRegister<Attribute> ATTRS = DeferredRegister.create(ForgeRegistries.ATTRIBUTES, PohCore.MODID);
    public static final RegistryObject<Attribute> DIVINE_POWER = ATTRS.register("divine_spell_power",
            () -> new RangedAttribute("attribute.pohsmp_core.divine_spell_power", 1.0, 0.0, 10.0).setSyncable(true));
    public static final RegistryObject<Attribute> DIVINE_RESIST = ATTRS.register("divine_magic_resist",
            () -> new RangedAttribute("attribute.pohsmp_core.divine_magic_resist", 1.0, -100.0, 100.0).setSyncable(true));

    public static final DeferredRegister<MobEffect> EFFECTS = DeferredRegister.create(ForgeRegistries.MOB_EFFECTS, PohCore.MODID);
    public static final RegistryObject<MobEffect> BACKLASH = EFFECTS.register("divine_backlash", BacklashEffect::new);
    public static final RegistryObject<MobEffect> NIGHTMARE = EFFECTS.register("nightmare_sleep", () -> new PohEffect(MobEffectCategory.HARMFUL, 0x4A2A7A)
            .addAttributeModifier(Attributes.MOVEMENT_SPEED, "6f1c6f5e-2b1a-4c51-9a41-0b8f3c5e7a01", -1.0, AttributeModifier.Operation.MULTIPLY_TOTAL)
            .addAttributeModifier(Attributes.ATTACK_DAMAGE, "6f1c6f5e-2b1a-4c51-9a41-0b8f3c5e7a02", -1.0, AttributeModifier.Operation.MULTIPLY_TOTAL));
    public static final RegistryObject<MobEffect> DREAD = EFFECTS.register("dread", () -> new PohEffect(MobEffectCategory.HARMFUL, 0x2B1B3D)
            .addAttributeModifier(Attributes.MOVEMENT_SPEED, "6f1c6f5e-2b1a-4c51-9a41-0b8f3c5e7a03", -0.35, AttributeModifier.Operation.MULTIPLY_TOTAL)
            .addAttributeModifier(Attributes.ATTACK_DAMAGE, "6f1c6f5e-2b1a-4c51-9a41-0b8f3c5e7a04", -0.4, AttributeModifier.Operation.MULTIPLY_TOTAL));
    public static final RegistryObject<MobEffect> SEAL = EFFECTS.register("forbidding_seal", () -> new PohEffect(MobEffectCategory.HARMFUL, 0xFF3B3B));
    public static final RegistryObject<MobEffect> HEAVY = EFFECTS.register("gravity_crush", () -> new PohEffect(MobEffectCategory.HARMFUL, 0x5B2A86));
    public static final RegistryObject<MobEffect> ASCENSION = EFFECTS.register("ascension", () -> new PohEffect(MobEffectCategory.BENEFICIAL, 0xFFF2B0));
    public static final RegistryObject<MobEffect> PARALYSIS = EFFECTS.register("paralysis", () -> new PohEffect(MobEffectCategory.HARMFUL, 0xF2E85A)
            .addAttributeModifier(Attributes.MOVEMENT_SPEED, "6f1c6f5e-2b1a-4c51-9a41-0b8f3c5e7a05", -1.0, AttributeModifier.Operation.MULTIPLY_TOTAL)
            .addAttributeModifier(Attributes.ATTACK_DAMAGE, "6f1c6f5e-2b1a-4c51-9a41-0b8f3c5e7a06", -1.0, AttributeModifier.Operation.MULTIPLY_TOTAL));
    public static final RegistryObject<MobEffect> TOSS = EFFECTS.register("wind_mark", () -> new PohEffect(MobEffectCategory.HARMFUL, 0xBFEFFF));
    public static final RegistryObject<MobEffect> LIVING_SHIELD = EFFECTS.register("living_shield", () -> new PohEffect(MobEffectCategory.BENEFICIAL, 0xFFE38A));
    public static final RegistryObject<MobEffect> EIGHT_SHIELDS = EFFECTS.register("eight_shields", () -> new PohEffect(MobEffectCategory.BENEFICIAL, 0x9FB7D6));
    public static final RegistryObject<MobEffect> SPENT = EFFECTS.register("spent", () -> new PohEffect(MobEffectCategory.HARMFUL, 0x5A3A2A)
            .addAttributeModifier(Attributes.MOVEMENT_SPEED, "6f1c6f5e-2b1a-4c51-9a41-0b8f3c5e7a07", -1.0, AttributeModifier.Operation.MULTIPLY_TOTAL)
            .addAttributeModifier(Attributes.ATTACK_DAMAGE, "6f1c6f5e-2b1a-4c51-9a41-0b8f3c5e7a08", -1.0, AttributeModifier.Operation.MULTIPLY_TOTAL));
    public static final RegistryObject<MobEffect> MADNESS = EFFECTS.register("magic_madness", () -> new PohEffect(MobEffectCategory.NEUTRAL, 0xB0101E));
    public static final RegistryObject<MobEffect> BLOOD_MARK = EFFECTS.register("blood_mark", () -> new PohEffect(MobEffectCategory.HARMFUL, 0x9A0A1A));
    public static final RegistryObject<MobEffect> HEMORRHAGE = EFFECTS.register("hemorrhage", () -> new PohEffect(MobEffectCategory.HARMFUL, 0x6E0010));
    public static final RegistryObject<MobEffect> OVERLOAD = EFFECTS.register("overload", () -> new PohEffect(MobEffectCategory.HARMFUL, 0x8FD8FF));
    public static final RegistryObject<MobEffect> SPORES = EFFECTS.register("spores", () -> new PohEffect(MobEffectCategory.HARMFUL, 0x8CB43A));

    public static final ResourceKey<DamageType> SHIELD_DAMAGE = ResourceKey.create(Registries.DAMAGE_TYPE, new ResourceLocation(PohCore.MODID, "living_shield"));
    public static final ResourceKey<DamageType> SOUL_DAMAGE = ResourceKey.create(Registries.DAMAGE_TYPE, new ResourceLocation(PohCore.MODID, "soul_devour"));

    public static final ResourceKey<DamageType> DIVINE_DAMAGE = ResourceKey.create(Registries.DAMAGE_TYPE, new ResourceLocation(PohCore.MODID, "divine_magic"));
    public static final TagKey<Item> DIVINE_FOCUS = ItemTags.create(new ResourceLocation(PohCore.MODID, "divine_focus"));

    public static final ResourceLocation DIVINE_ID = new ResourceLocation(PohCore.MODID, "divine");
    public static final DeferredRegister<SchoolType> SCHOOLS = DeferredRegister.create(SchoolRegistry.SCHOOL_REGISTRY_KEY, PohCore.MODID);
    public static final RegistryObject<SchoolType> DIVINE = SCHOOLS.register("divine", () -> new SchoolType(DIVINE_ID, DIVINE_FOCUS,
            Component.translatable("school.pohsmp_core.divine").withStyle(Style.EMPTY.withColor(DIVINE_COLOR)),
            DIVINE_POWER, DIVINE_RESIST, () -> SoundEvents.BEACON_ACTIVATE, DIVINE_DAMAGE, false, false));

    public static final int HIGHER_COLOR = 0xFF3B3B;
    public static final RegistryObject<Attribute> HIGHER_POWER = ATTRS.register("higher_spell_power",
            () -> new RangedAttribute("attribute.pohsmp_core.higher_spell_power", 1.0, 0.0, 10.0).setSyncable(true));
    public static final RegistryObject<Attribute> HIGHER_RESIST = ATTRS.register("higher_magic_resist",
            () -> new RangedAttribute("attribute.pohsmp_core.higher_magic_resist", 1.0, -100.0, 100.0).setSyncable(true));
    public static final ResourceKey<DamageType> HIGHER_DAMAGE = ResourceKey.create(Registries.DAMAGE_TYPE, new ResourceLocation(PohCore.MODID, "higher_magic"));
    public static final TagKey<Item> HIGHER_FOCUS = ItemTags.create(new ResourceLocation(PohCore.MODID, "higher_focus"));
    public static final ResourceLocation HIGHER_ID = new ResourceLocation(PohCore.MODID, "higher");
    public static final RegistryObject<SchoolType> HIGHER = SCHOOLS.register("higher", () -> new SchoolType(HIGHER_ID, HIGHER_FOCUS,
            Component.translatable("school.pohsmp_core.higher").withStyle(Style.EMPTY.withColor(HIGHER_COLOR)),
            HIGHER_POWER, HIGHER_RESIST, () -> SoundEvents.AMETHYST_BLOCK_RESONATE, HIGHER_DAMAGE, false, false));

    public static final int FORBIDDEN_COLOR = 0xD4A017;
    public static final RegistryObject<Attribute> FORBIDDEN_POWER = ATTRS.register("forbidden_spell_power",
            () -> new RangedAttribute("attribute.pohsmp_core.forbidden_spell_power", 1.0, 0.0, 10.0).setSyncable(true));
    public static final RegistryObject<Attribute> FORBIDDEN_RESIST = ATTRS.register("forbidden_magic_resist",
            () -> new RangedAttribute("attribute.pohsmp_core.forbidden_magic_resist", 1.0, -100.0, 100.0).setSyncable(true));
    public static final ResourceKey<DamageType> FORBIDDEN_DAMAGE = ResourceKey.create(Registries.DAMAGE_TYPE, new ResourceLocation(PohCore.MODID, "forbidden_magic"));
    public static final TagKey<Item> FORBIDDEN_FOCUS = ItemTags.create(new ResourceLocation(PohCore.MODID, "forbidden_focus"));
    public static final ResourceLocation FORBIDDEN_ID = new ResourceLocation(PohCore.MODID, "forbidden");
    public static final RegistryObject<SchoolType> FORBIDDEN = SCHOOLS.register("forbidden", () -> new SchoolType(FORBIDDEN_ID, FORBIDDEN_FOCUS,
            Component.translatable("school.pohsmp_core.forbidden").withStyle(Style.EMPTY.withColor(FORBIDDEN_COLOR)),
            FORBIDDEN_POWER, FORBIDDEN_RESIST, () -> SoundEvents.END_PORTAL_SPAWN, FORBIDDEN_DAMAGE, false, false));
    /** Price of "Downfall": max health -50%, slow, weak; mana does not grow and no spells while it lasts (HigherEvents, DivineEvents). */
    public static final RegistryObject<MobEffect> CREATION_BACKLASH = EFFECTS.register("creation_backlash", () -> new PohEffect(MobEffectCategory.HARMFUL, FORBIDDEN_COLOR)
            .addAttributeModifier(Attributes.MAX_HEALTH, "6f1c6f5e-2b1a-4c51-9a41-0b8f3c5e7a09", -0.5, AttributeModifier.Operation.MULTIPLY_TOTAL)
            .addAttributeModifier(Attributes.MOVEMENT_SPEED, "6f1c6f5e-2b1a-4c51-9a41-0b8f3c5e7a0a", -0.35, AttributeModifier.Operation.MULTIPLY_TOTAL)
            .addAttributeModifier(Attributes.ATTACK_DAMAGE, "6f1c6f5e-2b1a-4c51-9a41-0b8f3c5e7a0b", -0.5, AttributeModifier.Operation.MULTIPLY_TOTAL));

    /** "Silent" school (T18): the Silent Witch's magic, cast without words. Damage goes through armor. */
    public static final int SILENT_COLOR = 0x7FFFD0;
    public static final RegistryObject<Attribute> SILENT_POWER = ATTRS.register("silent_spell_power",
            () -> new RangedAttribute("attribute.pohsmp_core.silent_spell_power", 1.0, 0.0, 10.0).setSyncable(true));
    public static final RegistryObject<Attribute> SILENT_RESIST = ATTRS.register("silent_magic_resist",
            () -> new RangedAttribute("attribute.pohsmp_core.silent_magic_resist", 1.0, -100.0, 100.0).setSyncable(true));
    public static final ResourceKey<DamageType> SILENT_DAMAGE = ResourceKey.create(Registries.DAMAGE_TYPE, new ResourceLocation(PohCore.MODID, "silent_magic"));
    public static final TagKey<Item> SILENT_FOCUS = ItemTags.create(new ResourceLocation(PohCore.MODID, "silent_focus"));
    public static final ResourceLocation SILENT_ID = new ResourceLocation(PohCore.MODID, "silent");
    public static final RegistryObject<SchoolType> SILENT = SCHOOLS.register("silent", () -> new SchoolType(SILENT_ID, SILENT_FOCUS,
            Component.translatable("school.pohsmp_core.silent").withStyle(Style.EMPTY.withColor(SILENT_COLOR)),
            SILENT_POWER, SILENT_RESIST, () -> SoundEvents.AMETHYST_BLOCK_CHIME, SILENT_DAMAGE, false, false));
    /** Black flame of Worgan: 1.5 damage a second, water does not put it out, milk does not cure it. */
    public static final RegistryObject<MobEffect> BLACK_FLAME = EFFECTS.register("black_flame", ru.pohsmp.core.spell.silent.WorganFlameSpell.BlackFlame::new);

    public static final DeferredRegister<AbstractSpell> SPELLS = DeferredRegister.create(SpellRegistry.SPELL_REGISTRY_KEY, PohCore.MODID);
    public static final RegistryObject<AbstractSpell> DISINTEGRATION = SPELLS.register("disintegration", DisintegrationSpell::new);
    public static final RegistryObject<AbstractSpell> CRADLE = SPELLS.register(CradleSpell.PATH, CradleSpell::new);
    public static final RegistryObject<AbstractSpell> FATE_STAR = SPELLS.register(FateStarSpell.PATH, FateStarSpell::new);
    public static final RegistryObject<AbstractSpell> SINGULARITY = SPELLS.register(SingularitySpell.PATH, SingularitySpell::new);
    public static final RegistryObject<AbstractSpell> SEAL_SPELL = SPELLS.register(SealSpell.PATH, SealSpell::new);
    public static final RegistryObject<AbstractSpell> ASCENSION_SPELL = SPELLS.register(AscensionSpell.PATH, AscensionSpell::new);
    public static final RegistryObject<AbstractSpell> ASHLESS = SPELLS.register(AshlessSpell.PATH, AshlessSpell::new);

    /** Ordinary spells (levels 1-6) in tab order; wind spells only when Wind Spellbooks is installed. */
    public static final List<String> COMMON_SPELLS = new java.util.ArrayList<>();
    private static void spell(String path, java.util.function.Supplier<AbstractSpell> s) {
        SPELLS.register(path, s);
        COMMON_SPELLS.add(path);
    }
    static {
        spell(ru.pohsmp.core.spell.BloodGiftSpell.PATH, ru.pohsmp.core.spell.BloodGiftSpell::new);
        spell(ru.pohsmp.core.spell.LivingShieldSpell.PATH, ru.pohsmp.core.spell.LivingShieldSpell::new);
        spell(ru.pohsmp.core.spell.GlacialTombsSpell.PATH, ru.pohsmp.core.spell.GlacialTombsSpell::new);
        spell(ru.pohsmp.core.spell.FrostSpikeWallSpell.PATH, ru.pohsmp.core.spell.FrostSpikeWallSpell::new);
        spell(ru.pohsmp.core.spell.FallingSunSpell.PATH, ru.pohsmp.core.spell.FallingSunSpell::new);
        spell(ru.pohsmp.core.spell.GroundShockSpell.PATH, ru.pohsmp.core.spell.GroundShockSpell::new);
        spell(ru.pohsmp.core.spell.GraspingGardenSpell.PATH, ru.pohsmp.core.spell.GraspingGardenSpell::new);
        spell(ru.pohsmp.core.spell.BanishmentSpell.PATH, ru.pohsmp.core.spell.BanishmentSpell::new);
        spell(ru.pohsmp.core.spell.EightShieldsSpell.PATH, ru.pohsmp.core.spell.EightShieldsSpell::new);
        spell(ru.pohsmp.core.spell.MadnessSpell.PATH, ru.pohsmp.core.spell.MadnessSpell::new);
        spell(ru.pohsmp.core.spell.FireWhipSpell.PATH, ru.pohsmp.core.spell.FireWhipSpell::new);
        spell(ru.pohsmp.core.spell.LightningRodSpell.PATH, ru.pohsmp.core.spell.LightningRodSpell::new);
        spell(ru.pohsmp.core.spell.OverloadSpell.PATH, ru.pohsmp.core.spell.OverloadSpell::new);
        spell(ru.pohsmp.core.spell.SanctuarySpell.PATH, ru.pohsmp.core.spell.SanctuarySpell::new);
        spell(ru.pohsmp.core.spell.JudgementSpell.PATH, ru.pohsmp.core.spell.JudgementSpell::new);
        spell(ru.pohsmp.core.spell.SwapSpell.PATH, ru.pohsmp.core.spell.SwapSpell::new);
        spell(ru.pohsmp.core.spell.BloodMarkSpell.PATH, ru.pohsmp.core.spell.BloodMarkSpell::new);
        spell(ru.pohsmp.core.spell.HemorrhageSpell.PATH, ru.pohsmp.core.spell.HemorrhageSpell::new);
        spell(ru.pohsmp.core.spell.PhantomTrapSpell.PATH, ru.pohsmp.core.spell.PhantomTrapSpell::new);
        spell(ru.pohsmp.core.spell.IllusionSpell.PATH, ru.pohsmp.core.spell.IllusionSpell::new);
        spell(ru.pohsmp.core.spell.SporeCloudSpell.PATH, ru.pohsmp.core.spell.SporeCloudSpell::new);
        if (net.minecraftforge.fml.ModList.get().isLoaded("wind_spellbooks")) {
            spell(ru.pohsmp.core.spell.GaleWardSpell.PATH, ru.pohsmp.core.spell.GaleWardSpell::new);
            spell(ru.pohsmp.core.spell.WindMarkSpell.PATH, ru.pohsmp.core.spell.WindMarkSpell::new);
        }
    }

    /** Built-in Divine and Mythic tier spells (besides Disintegration). */
    public static final List<String> DIVINE_SPELLS = List.of(ru.pohsmp.core.spell.TabooSpell.PATH, ru.pohsmp.core.spell.SoulDevourSpell.PATH,
            ru.pohsmp.core.spell.ArkSpell.PATH);
    public static final List<String> MYTHIC_SPELLS = List.of(ru.pohsmp.core.spell.ExplosionSpell.PATH,
            ru.pohsmp.core.spell.HeavenFallSpell.PATH, ru.pohsmp.core.spell.FrozenHourSpell.PATH, ru.pohsmp.core.spell.SpaceClosureSpell.PATH,
            ru.pohsmp.core.spell.CovenArrivalSpell.PATH, ru.pohsmp.core.spell.StarFallSpell.PATH);
    public static final RegistryObject<AbstractSpell> COVEN_ARRIVAL = SPELLS.register(ru.pohsmp.core.spell.CovenArrivalSpell.PATH,
            ru.pohsmp.core.spell.CovenArrivalSpell::new);
    static {
        SPELLS.register(ru.pohsmp.core.spell.SpaceClosureSpell.PATH, ru.pohsmp.core.spell.SpaceClosureSpell::new);
        SPELLS.register(ru.pohsmp.core.spell.HeavenFallSpell.PATH, ru.pohsmp.core.spell.HeavenFallSpell::new);
        SPELLS.register(ru.pohsmp.core.spell.FrozenHourSpell.PATH, ru.pohsmp.core.spell.FrozenHourSpell::new);
        SPELLS.register(ru.pohsmp.core.spell.TabooSpell.PATH, ru.pohsmp.core.spell.TabooSpell::new);
        SPELLS.register(ru.pohsmp.core.spell.SoulDevourSpell.PATH, ru.pohsmp.core.spell.SoulDevourSpell::new);
        SPELLS.register(ru.pohsmp.core.spell.ArkSpell.PATH, ru.pohsmp.core.spell.ArkSpell::new);
        SPELLS.register(ru.pohsmp.core.spell.ExplosionSpell.PATH, ru.pohsmp.core.spell.ExplosionSpell::new);
        SPELLS.register(ru.pohsmp.core.spell.StarFallSpell.PATH, ru.pohsmp.core.spell.StarFallSpell::new);
    }

    /** "Creation" tier: only through its staff. */
    public static final List<String> CREATION_SPELLS = List.of(ru.pohsmp.core.spell.DownfallSpell.PATH);
    public static final RegistryObject<AbstractSpell> DOWNFALL = SPELLS.register(ru.pohsmp.core.spell.DownfallSpell.PATH, ru.pohsmp.core.spell.DownfallSpell::new);

    /** "Unknown" tier: only through the Silent Witch staff, in its slot order (T18; spells - T03 Gate, T20 the other four). */
    public static final List<String> UNKNOWN_SPELLS = List.of(ru.pohsmp.core.spell.silent.SilentGateSpell.PATH,
            ru.pohsmp.core.spell.silent.WindSpearsSpell.PATH, ru.pohsmp.core.spell.silent.SilentVolleySpell.PATH,
            ru.pohsmp.core.spell.silent.SageBarrierSpell.PATH, ru.pohsmp.core.spell.silent.WorganFlameSpell.PATH);
    public static final RegistryObject<AbstractSpell> SILENT_GATE = SPELLS.register(ru.pohsmp.core.spell.silent.SilentGateSpell.PATH,
            ru.pohsmp.core.spell.silent.SilentGateSpell::new);
    public static final RegistryObject<AbstractSpell> WIND_SPEARS = SPELLS.register(ru.pohsmp.core.spell.silent.WindSpearsSpell.PATH,
            ru.pohsmp.core.spell.silent.WindSpearsSpell::new);
    public static final RegistryObject<AbstractSpell> SILENT_VOLLEY = SPELLS.register(ru.pohsmp.core.spell.silent.SilentVolleySpell.PATH,
            ru.pohsmp.core.spell.silent.SilentVolleySpell::new);
    public static final RegistryObject<AbstractSpell> SAGE_BARRIER = SPELLS.register(ru.pohsmp.core.spell.silent.SageBarrierSpell.PATH,
            ru.pohsmp.core.spell.silent.SageBarrierSpell::new);
    public static final RegistryObject<AbstractSpell> WORGAN_FLAME = SPELLS.register(ru.pohsmp.core.spell.silent.WorganFlameSpell.PATH,
            ru.pohsmp.core.spell.silent.WorganFlameSpell::new);
    /** Spells of the Silent Witch staff, slot by slot (same order as {@link #UNKNOWN_SPELLS}). */
    public static final List<RegistryObject<AbstractSpell>> SILENT_STAFF_SPELLS = List.of(SILENT_GATE, WIND_SPEARS, SILENT_VOLLEY, SAGE_BARRIER, WORGAN_FLAME);

    /** Spells with the built-in Higher tier, in tab order. */
    public static final List<String> HIGHER_SPELLS = List.of(CradleSpell.PATH, FateStarSpell.PATH, SingularitySpell.PATH,
            SealSpell.PATH, AscensionSpell.PATH, AshlessSpell.PATH, ru.pohsmp.core.spell.BloodMoonSpell.PATH,
            ru.pohsmp.core.spell.OblivionBladesSpell.PATH, ru.pohsmp.core.spell.WorldRiftSpell.PATH, ru.pohsmp.core.spell.MirrorPrisonSpell.PATH,
            ru.pohsmp.core.spell.MilkyWaySpell.PATH, ru.pohsmp.core.spell.EternalBlizzardSpell.PATH,
            ru.pohsmp.core.spell.DisintegrationReplicaSpell.PATH, ru.pohsmp.core.spell.CountdownSpell.PATH,
            ru.pohsmp.core.spell.ScarletCutSpell.PATH);
    static {
        SPELLS.register(ru.pohsmp.core.spell.ScarletCutSpell.PATH, ru.pohsmp.core.spell.ScarletCutSpell::new);
        SPELLS.register(ru.pohsmp.core.spell.CountdownSpell.PATH, ru.pohsmp.core.spell.CountdownSpell::new);
        SPELLS.register(ru.pohsmp.core.spell.DisintegrationReplicaSpell.PATH, ru.pohsmp.core.spell.DisintegrationReplicaSpell::new);
        SPELLS.register(ru.pohsmp.core.spell.MilkyWaySpell.PATH, ru.pohsmp.core.spell.MilkyWaySpell::new);
        SPELLS.register(ru.pohsmp.core.spell.EternalBlizzardSpell.PATH, ru.pohsmp.core.spell.EternalBlizzardSpell::new);
        SPELLS.register(ru.pohsmp.core.spell.BloodMoonSpell.PATH, ru.pohsmp.core.spell.BloodMoonSpell::new);
        SPELLS.register(ru.pohsmp.core.spell.OblivionBladesSpell.PATH, ru.pohsmp.core.spell.OblivionBladesSpell::new);
        SPELLS.register(ru.pohsmp.core.spell.WorldRiftSpell.PATH, ru.pohsmp.core.spell.WorldRiftSpell::new);
        SPELLS.register(ru.pohsmp.core.spell.MirrorPrisonSpell.PATH, ru.pohsmp.core.spell.MirrorPrisonSpell::new);
    }

    /** School staffs: +15% school spell power, +5% spell power, +25% mana regen; Mythic: +20% spell power, +25% mana regen. */
    public static final DeferredRegister<Item> ITEMS = DeferredRegister.create(ForgeRegistries.ITEMS, PohCore.MODID);
    public static final double STAFF_SCHOOL = 0.15, STAFF_POWER = 0.05, STAFF_REGEN = 0.25;
    private static RegistryObject<Item> staff(String name, java.util.function.Supplier<Attribute> school) {
        return ITEMS.register(name + "_staff", () -> new AnimatedStaff(name + "_staff", school, STAFF_SCHOOL, STAFF_POWER, STAFF_REGEN));
    }
    public static final List<RegistryObject<Item>> STAFFS = List.of(
            staff("fire", AttributeRegistry.FIRE_SPELL_POWER),
            staff("blood", AttributeRegistry.BLOOD_SPELL_POWER),
            staff("eldritch", AttributeRegistry.ELDRITCH_SPELL_POWER),
            staff("ender", AttributeRegistry.ENDER_SPELL_POWER),
            staff("evocation", AttributeRegistry.EVOCATION_SPELL_POWER),
            staff("holy", AttributeRegistry.HOLY_SPELL_POWER),
            staff("lightning", AttributeRegistry.LIGHTNING_SPELL_POWER),
            staff("nature", AttributeRegistry.NATURE_SPELL_POWER),
            staff("higher", HIGHER_POWER),
            staff("divine", DIVINE_POWER),
            ITEMS.register("mythic_staff", () -> new AnimatedStaff("mythic_staff", null, 0, STAFF_SCHOOL + STAFF_POWER, STAFF_REGEN)));
    public static final RegistryObject<Item> DOWNFALL_STAFF = ITEMS.register("downfall_staff", DownfallStaff::new);
    public static final RegistryObject<Item> SILENT_WITCH_STAFF = ITEMS.register(SilentWitchStaff.NAME, SilentWitchStaff::new);

    public static final DeferredRegister<CreativeModeTab> TABS = DeferredRegister.create(Registries.CREATIVE_MODE_TAB, PohCore.MODID);
    public static final RegistryObject<CreativeModeTab> TAB = TABS.register("main", () -> CreativeModeTab.builder()
            .title(Component.translatable("itemGroup.pohsmp_core"))
            .icon(() -> {
                Item crown = ForgeRegistries.ITEMS.getValue(new ResourceLocation("irons_spellbooks", "gold_crown"));
                return new ItemStack(crown == null || crown == Items.AIR ? Items.NETHER_STAR : crown);
            })
            .displayItems((params, out) -> {
                for (String p : COMMON_SPELLS) out.accept(Scrolls.make(new ResourceLocation(PohCore.MODID, p), 1, null));
                for (String p : HIGHER_SPELLS) out.accept(Scrolls.make(new ResourceLocation(PohCore.MODID, p), 1, null));
                out.accept(Scrolls.make(DisintegrationSpell.ID, 1, null));
                for (String p : MYTHIC_SPELLS) out.accept(Scrolls.make(new ResourceLocation(PohCore.MODID, p), 1, null));
                for (String p : DIVINE_SPELLS) out.accept(Scrolls.make(new ResourceLocation(PohCore.MODID, p), 1, null));
                for (RegistryObject<Item> s : STAFFS) out.accept(s.get());
                out.accept(DOWNFALL_STAFF.get());
                out.accept(SILENT_WITCH_STAFF.get());
            })
            .build());

    public static void register(IEventBus modBus) {
        ATTRS.register(modBus);
        EFFECTS.register(modBus);
        SCHOOLS.register(modBus);
        SPELLS.register(modBus);
        ITEMS.register(modBus);
        TABS.register(modBus);
    }
}
