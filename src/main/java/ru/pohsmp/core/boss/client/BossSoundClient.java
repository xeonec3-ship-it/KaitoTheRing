package ru.pohsmp.core.boss.client;

import java.util.Collections;
import java.util.HashMap;
import java.util.Map;
import java.util.Set;
import java.util.WeakHashMap;
import net.minecraft.client.Minecraft;
import net.minecraft.client.resources.sounds.AbstractTickableSoundInstance;
import net.minecraft.client.resources.sounds.SoundInstance;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.sounds.SoundSource;
import net.minecraft.util.RandomSource;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.LivingEntity;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.registries.ForgeRegistries;
import ru.pohsmp.core.PohCore;
import ru.pohsmp.core.boss.BossCore;
import ru.pohsmp.core.boss.PohBoss;
import software.bernie.geckolib.animatable.GeoEntity;
import software.bernie.geckolib.core.animation.AnimationController;

/**
 * Boss sounds on the client (owner 21.11: «боссам нужно больше звуков»).
 * <ul>
 * <li>GeckoLib {@code sound_effects} of the boss animations: every controller of every mod GeoEntity nearby gets a handler once
 * (Iron's and our controllers set none). Effect string: {@code pohsmp_core:martin.swing} or {@code martin.swing|volume|pitch};
 * the pitch varies by ±4% so repeated steps / swings never sound identical.</li>
 * <li>A quiet aura loop ({@code <boss>.aura}) follows each living boss (fades in / out with the distance, stops on death).</li>
 * </ul>
 */
public final class BossSoundClient {
    private BossSoundClient() {}

    /** Entity type path -> aura sound id and its volume (the loop files are already quiet; volume sets the range: 1 = 16 blocks). */
    private static final Map<String, Float> AURA = new HashMap<>();
    static {
        AURA.put("cult_leader", 1.4f);
        AURA.put("irina", 1.2f);
        AURA.put("aris", 1.4f);
        AURA.put("martin", 1.4f);
        AURA.put("ereb", 1.2f);
        AURA.put("ereb_hand", 1.6f);
    }

    private static final Set<AnimationController<?>> HOOKED = Collections.newSetFromMap(new WeakHashMap<>());
    private static final Map<Entity, Aura> AURAS = new WeakHashMap<>();
    private static int scan;

    @SubscribeEvent
    public static void onTick(TickEvent.ClientTickEvent e) {
        if (e.phase != TickEvent.Phase.END) return;
        Minecraft mc = Minecraft.getInstance();
        if (mc.level == null || mc.player == null || mc.isPaused()) return;
        if (++scan % 5 != 0) return;
        for (Entity en : mc.level.entitiesForRendering()) {
            if (!(en instanceof GeoEntity geo)) continue;
            ResourceLocation key = ForgeRegistries.ENTITY_TYPES.getKey(en.getType());
            if (key == null || !PohCore.MODID.equals(key.getNamespace())) continue;
            if (en.distanceToSqr(mc.player) > 64 * 64) continue;
            hook(geo, en);
            Float vol = AURA.get(key.getPath());
            if (vol != null && en instanceof PohBoss && en.isAlive()) {
                Aura a = AURAS.get(en);
                if (a == null || a.isStopped()) {
                    a = new Aura(en, BossCore.sound(key.getPath() + ".aura"), vol);
                    AURAS.put(en, a);
                    mc.getSoundManager().play(a);
                }
            }
        }
    }

    @SuppressWarnings({"unchecked", "rawtypes"})
    private static void hook(GeoEntity geo, Entity en) {
        var manager = geo.getAnimatableInstanceCache().getManagerForId(en.getId());
        if (manager == null) return;
        for (AnimationController c : manager.getAnimationControllers().values()) {
            if (!HOOKED.add(c)) continue;
            c.setSoundKeyframeHandler(ev -> play(en, ((software.bernie.geckolib.core.keyframe.event.SoundKeyframeEvent<?>) ev).getKeyframeData().getSound()));
        }
    }

    /** {@code id[|volume[|pitch]]}, played at the entity (positional, hostile channel). */
    public static void play(Entity en, String effect) {
        if (effect == null || effect.isEmpty() || en.level() == null || !en.level().isClientSide) return;
        String[] p = effect.split("\\|");
        float vol = p.length > 1 ? parse(p[1], 1) : 1;
        float pitch = p.length > 2 ? parse(p[2], 1) : 1;
        RandomSource r = en.level().random;
        pitch *= 0.96f + r.nextFloat() * 0.08f;
        en.level().playLocalSound(en.getX(), en.getY() + en.getBbHeight() * 0.5, en.getZ(), BossCore.sound(p[0].trim()),
                SoundSource.HOSTILE, vol, pitch, false);
    }

    private static float parse(String s, float def) {
        try {
            return Float.parseFloat(s.trim());
        } catch (NumberFormatException ex) {
            return def;
        }
    }

    public static void clear() {
        AURAS.clear();
        HOOKED.clear();
    }

    /** The aura loop: follows the boss, fades with distance, fades out and stops when it dies or is gone. */
    private static final class Aura extends AbstractTickableSoundInstance {
        private final Entity boss;
        private final float max;
        private float fade;

        Aura(Entity boss, net.minecraft.sounds.SoundEvent ev, float max) {
            super(ev, SoundSource.HOSTILE, SoundInstance.createUnseededRandom());
            this.boss = boss;
            this.max = max;
            this.looping = true;
            this.delay = 0;
            this.volume = 0.01f;
            this.attenuation = SoundInstance.Attenuation.LINEAR;
            this.x = boss.getX();
            this.y = boss.getY() + 1;
            this.z = boss.getZ();
        }

        @Override
        public void tick() {
            boolean alive = boss.isAlive() && !boss.isRemoved() && (!(boss instanceof LivingEntity l) || l.getHealth() > 0);
            fade = alive ? Math.min(1, fade + 0.03f) : fade - 0.05f;
            if (fade <= 0 && !alive) {
                stop();
                return;
            }
            x = boss.getX();
            y = boss.getY() + 1;
            z = boss.getZ();
            volume = Math.max(0.001f, max * fade);
        }

        @Override
        public boolean canStartSilent() {
            return true;
        }
    }
}
