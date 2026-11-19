package ru.pohsmp.core.test;

import com.mojang.authlib.GameProfile;
import io.netty.channel.embedded.EmbeddedChannel;
import io.redspace.ironsspellbooks.api.magic.MagicData;
import io.redspace.ironsspellbooks.api.spells.AbstractSpell;
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
import net.minecraft.world.entity.animal.Wolf;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.GameType;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.event.RegisterGameTestsEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import net.minecraftforge.gametest.GameTestHolder;
import net.minecraftforge.gametest.PrefixGameTestTemplate;
import ru.pohsmp.core.PohCore;
import ru.pohsmp.core.Reg;
import ru.pohsmp.core.ServerConfig;
import ru.pohsmp.core.spell.Cutscene;
import ru.pohsmp.core.spell.silent.SilentGateSpell;

/**
 * "Gate" (T03) on a real server through Iron's own cast path (attemptInitiateCast from the Silent Witch staff):
 * the cast runs 50 s and is not interrupted, the watchers are held by the scene, rays and the main beam hit foes in the area
 * with the configured numbers (no main beam), players, peaceful animals and the caster's pet are spared, the scene ends at 65 s; a cancel stops everything; no staff - no cast.
 * Outfit: T19 items are not registered yet, so SilentWitch counts the set as worn (stub).
 */
@GameTestHolder(PohCore.MODID)
@PrefixGameTestTemplate(false)
@Mod.EventBusSubscriber(modid = PohCore.MODID, bus = Mod.EventBusSubscriber.Bus.MOD)
public final class SilentGateGameTests {
    private SilentGateGameTests() {}

    private static final String ARENA = "arena";
    private static final double HP = 1000;

    @SubscribeEvent
    public static void register(RegisterGameTestsEvent e) {
        e.register(SilentGateGameTests.class);
    }

    private static void check(boolean ok, String what) {
        if (!ok) throw new GameTestAssertException(what);
    }

    private static ServerPlayer mage(GameTestHelper h, String name, double x, double z) {
        ServerLevel lvl = h.getLevel();
        ServerPlayer p = new ServerPlayer(lvl.getServer(), lvl, new GameProfile(UUID.randomUUID(), name));
        Connection c = new Connection(PacketFlow.SERVERBOUND);
        new EmbeddedChannel(c);
        lvl.getServer().getPlayerList().placeNewPlayer(c, p);
        p.setGameMode(GameType.SURVIVAL);
        Vec3 a = top(h, h.absoluteVec(new Vec3(x, 1, z)));
        p.teleportTo(lvl, a.x, a.y, a.z, 0, 0);   // yaw 0: looks along +Z
        p.setYHeadRot(0);
        return p;
    }

    /** A husk (does not burn) with lots of health and no AI, at (x, z) relative to the mage's look (+Z). */
    /** The same x z on top of the ground. */
    private static Vec3 top(GameTestHelper h, Vec3 p) {
        int y = h.getLevel().getHeight(net.minecraft.world.level.levelgen.Heightmap.Types.MOTION_BLOCKING, (int) Math.floor(p.x), (int) Math.floor(p.z));
        return new Vec3(p.x, y, p.z);
    }

    private static Mob dummy(GameTestHelper h, Vec3 at) {
        at = top(h, at);
        Mob m = EntityType.HUSK.create(h.getLevel());
        m.moveTo(at.x, at.y, at.z, 180, 0);
        m.setNoAi(true);
        m.setPersistenceRequired();
        m.getAttribute(Attributes.MAX_HEALTH).setBaseValue(HP);
        m.setHealth((float) HP);
        h.getLevel().addFreshEntity(m);
        return m;
    }

    private static String src(Mob m) {
        var d = m.getLastDamageSource();
        return d == null ? "-" : d.getMsgId() + " at y " + String.format("%.1f", m.getY());
    }

    private static boolean cast(ServerPlayer p) {
        AbstractSpell gate = Reg.SILENT_GATE.get();
        ItemStack staff = p.getMainHandItem();
        return gate.attemptInitiateCast(staff, 1, p.level(), p, CastSource.SPELLBOOK, true, "mainhand");
    }

    @GameTest(template = ARENA, batch = "gate_full", timeoutTicks = 1500)
    public static void gateFullCast(GameTestHelper h) {
        ServerPlayer p = mage(h, "witch", 4, 2);
        p.setItemInHand(InteractionHand.MAIN_HAND, new ItemStack(Reg.SILENT_WITCH_STAFF.get()));
        Vec3 me = p.position();
        Mob aim = dummy(h, me.add(0, 0, 16)), other = dummy(h, me.add(9, 0, 22)), far = dummy(h, me.add(40, 0, 50));
        Wolf pet = EntityType.WOLF.create(h.getLevel());
        Vec3 pp = top(h, me.add(2, 0, 16));
        pet.moveTo(pp.x, pp.y, pp.z, 0, 0);
        pet.setNoAi(true);
        pet.tame(p);
        h.getLevel().addFreshEntity(pet);
        // owner's rule: players and peaceful creatures are never hit, even right next to a foe
        ServerPlayer bystander = mage(h, "bystander", 4 + 8, 2 + 22);
        Vec3 cp = top(h, me.add(-3, 0, 14));
        var cow = EntityType.COW.create(h.getLevel());
        cow.moveTo(cp.x, cp.y, cp.z, 0, 0);
        cow.setNoAi(true);
        h.getLevel().addFreshEntity(cow);
        double ray = ServerConfig.GATE_RAY_DAMAGE.get() * ServerConfig.GATE_SET_BONUS.get();
        float[] before = new float[1];
        h.runAfterDelay(2, () -> {
            Vec3 eye = p.getEyePosition(), t = aim.position().add(0, aim.getBbHeight() * 0.6, 0), d = t.subtract(eye);
            p.setYRot((float) Math.toDegrees(Math.atan2(-d.x, d.z)));
            p.setXRot((float) -Math.toDegrees(Math.atan2(d.y, Math.hypot(d.x, d.z))));
            p.setYHeadRot(p.getYRot());
            var hit = h.getLevel().clip(new net.minecraft.world.level.ClipContext(eye, t, net.minecraft.world.level.ClipContext.Block.COLLIDER,
                    net.minecraft.world.level.ClipContext.Fluid.NONE, p));
            check(hit.getType() == net.minecraft.world.phys.HitResult.Type.MISS, "no line of sight to the target: " + hit.getBlockPos() + " " + h.getLevel().getBlockState(hit.getBlockPos()));
            check(cast(p), "cast did not start");
            MagicData md = MagicData.getPlayerMagicData(p);
            check(md.isCasting(), "not casting");
            check(md.getCastDuration() == SilentGateSpell.CAST, "cast time " + md.getCastDuration());
            check(Cutscene.frozen().contains(p.getUUID()), "the caster must watch the scene");
        });
        h.runAfterDelay(400, () -> {   // 20 s: still casting, nothing hit yet
            check(MagicData.getPlayerMagicData(p).isCasting(), "cast stopped early");
            check(aim.getHealth() == HP && other.getHealth() == HP, "hit before 50 s: " + aim.getHealth() + " " + src(aim) + " / " + other.getHealth() + " " + src(other));
        });
        h.runAfterDelay(1000 + 2 + 2, () -> {   // just after 50 s: the spell is cast, first rays fell (aimed ones too)
            check(!MagicData.getPlayerMagicData(p).isCasting(), "still casting after 50 s");
            check(HP - other.getHealth() >= ray - 0.5, "no aimed ray on the foe in the area: " + other.getHealth());
            before[0] = aim.getHealth();
        });
        h.runAfterDelay(1040 + 2 + 4, () -> {   // 52 s: no main beam (owner) - only rays: at most 12 per 2 s on one creature
            double got = before[0] - aim.getHealth();
            check(got <= 6 * ray + 1, "the aimed creature took " + got + " in 2 s - a main beam?");
        });
        h.runAfterDelay(SilentGateSpell.END + 2 + 5, () -> {
            check(pet.getHealth() == pet.getMaxHealth(), "the caster's pet was hit");
            check(bystander.getHealth() == bystander.getMaxHealth(), "a player was hit: " + bystander.getHealth());
            check(cow.getHealth() == cow.getMaxHealth(), "a peaceful animal was hit");
            check(far.getHealth() == HP, "a creature outside the area was hit");
            double otherLost = HP - other.getHealth();
            check(otherLost >= 20 * ray && otherLost <= 40 * ray, "foe in the area lost " + otherLost);
            check(!Cutscene.frozen().contains(p.getUUID()), "scene did not end");
            check(MagicData.getPlayerMagicData(p).getPlayerCooldowns().isOnCooldown(Reg.SILENT_GATE.get()), "no Silence cooldown");
            p.server.getPlayerList().remove(p);
            bystander.server.getPlayerList().remove(bystander);
            h.succeed();
        });
    }

    @GameTest(template = ARENA, batch = "gate_cancel", timeoutTicks = 1500)
    public static void gateCancelled(GameTestHelper h) {
        ServerPlayer p = mage(h, "witch_cancel", 4, 2);
        p.setItemInHand(InteractionHand.MAIN_HAND, new ItemStack(Reg.SILENT_WITCH_STAFF.get()));
        Mob aim = dummy(h, p.position().add(0, 0, 16));
        h.runAfterDelay(2, () -> check(cast(p), "cast did not start"));
        h.runAfterDelay(200, () -> {
            Utils.serverSideCancelCast(p);
            check(!MagicData.getPlayerMagicData(p).isCasting(), "cancel did not stop the cast");
        });
        h.runAfterDelay(205, () -> check(!Cutscene.frozen().contains(p.getUUID()), "scene not ended on cancel"));
        h.runAfterDelay(SilentGateSpell.END + 20, () -> {
            check(aim.getHealth() == HP, "hit after a cancelled cast: " + aim.getHealth() + " " + src(aim));
            p.server.getPlayerList().remove(p);
            h.succeed();
        });
    }

    @GameTest(template = ARENA, batch = "gate_no_staff", timeoutTicks = 60)
    public static void gateNeedsStaff(GameTestHelper h) {
        ServerPlayer p = mage(h, "witch_bare", 4, 2);
        p.setItemInHand(InteractionHand.MAIN_HAND, ItemStack.EMPTY);
        h.runAfterDelay(2, () -> {
            cast(p);
            check(!MagicData.getPlayerMagicData(p).isCasting(), "Gate started without the staff");
            check(!Cutscene.frozen().contains(p.getUUID()), "scene started without the staff");
            p.server.getPlayerList().remove(p);
            h.succeed();
        });
    }
}
