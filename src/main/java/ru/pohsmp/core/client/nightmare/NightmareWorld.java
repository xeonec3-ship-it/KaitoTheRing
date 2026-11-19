package ru.pohsmp.core.client.nightmare;

import net.minecraft.client.Minecraft;
import net.minecraft.client.renderer.BiomeColors;
import net.minecraft.world.level.FoliageColor;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.client.event.RegisterColorHandlersEvent;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;

/**
 * T25, the world of stage 3 on the victim's own client (the blocks are not changed; visual letter 19.11, colours from it):
 * grass rots (#4A3E36), leaves wither (#3A2E2C), water turns to ink (#0A0610), the sky blood-black (#1A0408), clouds #3A0A16.
 * Block tints only change with a chunk rebuild, so the world is rebuilt once when it turns and once when it turns back.
 */
public final class NightmareWorld {
    private NightmareWorld() {}

    private static boolean on, drawn;
    /** 0..1 for the sky and clouds (smooth) */
    private static float sky;

    /** True while this client is in the nightmare world (stage 3, or the Mythic holds it). */
    public static boolean on() {
        return on;
    }

    @SubscribeEvent
    public static void onTick(TickEvent.ClientTickEvent e) {
        if (e.phase != TickEvent.Phase.END) return;
        Minecraft mc = Minecraft.getInstance();
        if (mc.level == null) {
            if (NightmareBlocks.applied()) NightmareBlocks.set(false);   // left the world in the nightmare: the atlas back
            on = drawn = false;
            sky = 0;
            return;
        }
        on = NightmareClient.stage() >= 3;
        sky = on ? Math.min(1, sky + 0.03f) : Math.max(0, sky - 0.03f);
        if (on != drawn) {   // the tints are baked into the chunk meshes
            drawn = on;
            NightmareBlocks.set(on);
            mc.levelRenderer.allChanged();
        } else if (on && mc.level.getGameTime() % 100 == 0) NightmareBlocks.set(true);   // a resource reload puts the vanilla atlas back
    }

    public static Vec3 sky(Vec3 c) {
        return sky <= 0 ? c : c.lerp(new Vec3(0x1A / 255.0, 0x04 / 255.0, 0x08 / 255.0), sky);
    }

    private static final net.minecraft.resources.ResourceLocation MOON = new net.minecraft.resources.ResourceLocation("minecraft", "textures/environment/moon_phases.png"),
            RED_MOON = new net.minecraft.resources.ResourceLocation(ru.pohsmp.core.PohCore.MODID, "textures/environment/nightmare_moon_phases.png");

    /** LevelRendererMixin: the red moon (same layout as the vanilla phases) at stage 3 and in «Ночь без рассвета». */
    public static net.minecraft.resources.ResourceLocation moon(net.minecraft.resources.ResourceLocation tex) {
        return (on || NightmareClient.night() > 0) && MOON.equals(tex) ? RED_MOON : tex;
    }

    public static Vec3 clouds(Vec3 c) {
        return sky <= 0 ? c : c.lerp(new Vec3(0x3A / 255.0, 0x0A / 255.0, 0x16 / 255.0), sky);
    }

    /**
     * ClientLevelMixin, getBlockTint: the biome tints (grass, foliage, water - also the water fluid and every mod block that asks the biome)
     * turn to the nightmare's; null = the vanilla colour.
     */
    public static Integer tint(net.minecraft.world.level.ColorResolver r) {
        if (!drawn) return null;
        boolean painted = NightmareBlocks.applied();   // the rotten sprites carry their own colour: no tint over them
        if (r == BiomeColors.GRASS_COLOR_RESOLVER) return painted ? 0x8A7E70 : 0x4A3E36;
        if (r == BiomeColors.FOLIAGE_COLOR_RESOLVER) return painted ? 0xFFFFFF : 0x3A2E2C;
        if (r == BiomeColors.WATER_COLOR_RESOLVER) return 0x0A0610;
        return null;
    }

    /** Mod bus: spruce and birch leaves have fixed colours (no biome): wither them too. */
    public static void colors(RegisterColorHandlersEvent.Block e) {
        e.register((s, l, p, i) -> drawn ? (NightmareBlocks.applied() ? 0xFFFFFF : 0x3A2E2C) : FoliageColor.getEvergreenColor(), Blocks.SPRUCE_LEAVES);
        e.register((s, l, p, i) -> drawn ? (NightmareBlocks.applied() ? 0xFFFFFF : 0x3A2E2C) : FoliageColor.getBirchColor(), Blocks.BIRCH_LEAVES);
    }
}
