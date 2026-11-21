package ru.pohsmp.core.test;

import com.mojang.authlib.GameProfile;
import io.netty.channel.embedded.EmbeddedChannel;
import io.redspace.ironsspellbooks.api.magic.MagicData;
import io.redspace.ironsspellbooks.api.spells.CastSource;
import io.redspace.ironsspellbooks.api.util.Utils;
import java.util.UUID;
import net.minecraft.gametest.framework.GameTest;
import net.minecraft.gametest.framework.GameTestAssertException;
import net.minecraft.gametest.framework.GameTestHelper;
import net.minecraft.network.Connection;
import net.minecraft.network.protocol.PacketFlow;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.ai.attributes.Attributes;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.GameType;
import net.minecraft.world.level.levelgen.Heightmap;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.event.RegisterGameTestsEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import net.minecraftforge.gametest.GameTestHolder;
import net.minecraftforge.gametest.PrefixGameTestTemplate;
import ru.pohsmp.core.PohCore;
import ru.pohsmp.core.Reg;
import ru.pohsmp.core.spell.CastLock;

/**
 * Owner 21.11: an animated spell («Безмолвные врата», cast 50 s with a scene) cannot be cut by another animated one («Копья ветра»)
 * through any of Iron's paths, and while it runs the player does nothing (attack, hotbar slot, walking speed). Ends on a real cancel.
 */
@GameTestHolder(PohCore.MODID)
@PrefixGameTestTemplate(false)
@Mod.EventBusSubscriber(modid = PohCore.MODID, bus = Mod.EventBusSubscriber.Bus.MOD)
public final class CastLockGameTests {
    private CastLockGameTests() {}

    @SubscribeEvent
    public static void register(RegisterGameTestsEvent e) {
        e.register(CastLockGameTests.class);
    }

    private static void check(boolean ok, String what) {
        if (!ok) throw new GameTestAssertException(what);
    }

    private static Vec3 top(GameTestHelper h, Vec3 p) {
        int y = h.getLevel().getHeight(Heightmap.Types.MOTION_BLOCKING, (int) Math.floor(p.x), (int) Math.floor(p.z));
        return new Vec3(p.x, y, p.z);
    }

    private static ServerPlayer mage(GameTestHelper h, String name) {
        ServerLevel lvl = h.getLevel();
        ServerPlayer p = new ServerPlayer(lvl.getServer(), lvl, new GameProfile(UUID.randomUUID(), name));
        Connection c = new Connection(PacketFlow.SERVERBOUND);
        new EmbeddedChannel(c);
        lvl.getServer().getPlayerList().placeNewPlayer(c, p);
        p.setGameMode(GameType.SURVIVAL);
        Vec3 a = top(h, h.absoluteVec(new Vec3(4, 1, 2)));
        p.teleportTo(lvl, a.x, a.y, a.z, 0, 0);
        return p;
    }

    private static boolean gate(ServerPlayer p) {
        return Reg.SILENT_GATE.get().attemptInitiateCast(p.getMainHandItem(), 1, p.level(), p, CastSource.SPELLBOOK, true, "mainhand");
    }

    private static boolean spears(ServerPlayer p) {
        return Reg.WIND_SPEARS.get().attemptInitiateCast(p.getMainHandItem(), 1, p.level(), p, CastSource.SPELLBOOK, true, "mainhand");
    }

    private static boolean castingGate(ServerPlayer p) {
        MagicData md = MagicData.getPlayerMagicData(p);
        return md.isCasting() && Reg.SILENT_GATE.get().getSpellId().equals(md.getCastingSpellId());
    }

    @GameTest(template = "arena", batch = "cast_lock", timeoutTicks = 400)
    public static void animatedCannotBeCut(GameTestHelper h) {
        ServerPlayer p = mage(h, "lock_witch");
        p.getInventory().selected = 0;
        p.setItemInHand(InteractionHand.MAIN_HAND, new ItemStack(Reg.SILENT_WITCH_STAFF.get()));
        MagicData.getPlayerMagicData(p).setMana(100000);
        Mob dummy = EntityType.HUSK.create(h.getLevel());
        Vec3 d = top(h, p.position().add(0, 0, 2));
        dummy.moveTo(d.x, d.y, d.z, 180, 0);
        dummy.setNoAi(true);
        h.getLevel().addFreshEntity(dummy);
        float hp = dummy.getHealth();
        double walk = p.getAttributeBaseValue(Attributes.MOVEMENT_SPEED);
        h.runAfterDelay(2, () -> check(gate(p) && castingGate(p), "the Gate did not start"));
        h.runAfterDelay(20, () -> {
            check(CastLock.busy(p), "no window while the Gate casts");
            float mana = MagicData.getPlayerMagicData(p).getMana();
            // another animated spell: refused, the Gate goes on, no mana spent
            check(!spears(p), "Wind Spears started during the Gate");
            check(castingGate(p), "the Gate was cut by Wind Spears");
            check(MagicData.getPlayerMagicData(p).getMana() == mana, "mana spent on a refused cast");
            // the book key / quick cast path: Iron's cancelled before attemptInitiateCast
            Utils.serverSideInitiateCast(p);
            Utils.serverSideInitiateQuickCast(p, 0);
            check(castingGate(p), "the Gate was cut by the cast key path");
            // letting go of the use button with the staff
            Utils.releaseUsingHelper(p, p.getMainHandItem(), 0);
            check(castingGate(p), "the Gate was cut by releasing the use button");
            // attack: cancelled
            p.attack(dummy);
            check(dummy.getHealth() == hp, "the player hit something during the Gate");
            // hotbar: the slot comes back
            p.getInventory().selected = 4;
        });
        h.runAfterDelay(23, () -> {
            check(p.getInventory().selected == 0, "the hotbar slot changed during the Gate: " + p.getInventory().selected);
            check(castingGate(p), "the Gate was cut by the slot change");
            check(p.getAttributeValue(Attributes.MOVEMENT_SPEED) < 1e-6, "the player can walk during the Gate");
            Utils.serverSideCancelCast(p);   // a real interruption (stun, script) still stops it
        });
        h.runAfterDelay(26, () -> {
            check(!CastLock.busy(p), "the window stayed after the cancel");
            check(Math.abs(p.getAttributeValue(Attributes.MOVEMENT_SPEED) - walk) < 1e-6, "walking speed not given back");
            check(spears(p), "Wind Spears refused after the window ended");
            p.server.getPlayerList().remove(p);
            h.succeed();
        });
    }
}
