package ru.pohsmp.core.test;

import com.mojang.authlib.GameProfile;
import io.netty.channel.embedded.EmbeddedChannel;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;
import net.minecraft.gametest.framework.GameTest;
import net.minecraft.gametest.framework.GameTestHelper;
import net.minecraft.network.Connection;
import net.minecraft.network.protocol.Packet;
import net.minecraft.network.protocol.PacketFlow;
import net.minecraft.network.protocol.game.ClientboundAddEntityPacket;
import net.minecraft.network.protocol.game.ClientboundBossEventPacket;
import net.minecraft.network.protocol.game.ClientboundBundlePacket;
import net.minecraft.network.protocol.game.ClientboundCustomPayloadPacket;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.level.GameType;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.event.RegisterGameTestsEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import net.minecraftforge.gametest.GameTestHolder;
import net.minecraftforge.gametest.PrefixGameTestTemplate;
import ru.pohsmp.core.PohCore;
import ru.pohsmp.core.boss.PohBoss;

/**
 * T34 bug (owner 21.11): no boss bar for Aris / Irina / Ereb, Ereb «just appears». For each of the six bosses, on a real server with a
 * player that has a (packet-capturing) connection: /pohsmp boss <id> → the client is sent the entity first, then the intro fx
 * (pohsmp_core:main) and the boss messages (pohsmp_core:boss), and a vanilla boss event row (ClientboundBossEventPacket, the entity's
 * UUID) — the only hook BossBarClient draws in; after the intro the fight has started. A second player who comes later gets the row too.
 * Run: gradlew runGameTestServer -PdevRun.
 */
@GameTestHolder(PohCore.MODID)
@PrefixGameTestTemplate(false)
@Mod.EventBusSubscriber(modid = PohCore.MODID, bus = Mod.EventBusSubscriber.Bus.MOD)
public final class BossSpawnGameTests {
    private BossSpawnGameTests() {}

    @SubscribeEvent
    public static void register(RegisterGameTestsEvent e) {
        e.register(BossSpawnGameTests.class);
    }

    private record Viewer(ServerPlayer p, EmbeddedChannel ch, List<Object> got) {
        void drain() {
            Object o;
            while ((o = ch.readOutbound()) != null) got.add(o);
        }
    }

    private static Viewer viewer(GameTestHelper h, String name, double x, double z) {
        ServerLevel lvl = h.getLevel();
        ServerPlayer p = new ServerPlayer(lvl.getServer(), lvl, new GameProfile(UUID.randomUUID(), name));
        Connection c = new Connection(PacketFlow.SERVERBOUND);
        EmbeddedChannel ch = new EmbeddedChannel(c);
        lvl.getServer().getPlayerList().placeNewPlayer(c, p);
        p.setGameMode(GameType.CREATIVE);
        Vec3 a = h.absoluteVec(new Vec3(x, 2, z));
        p.teleportTo(lvl, a.x, a.y, a.z, 0, 0);
        Viewer v = new Viewer(p, ch, new ArrayList<>());
        v.drain();
        v.got.clear();
        return v;
    }

    private static boolean addsEntity(Object o, int id) {
        if (o instanceof ClientboundAddEntityPacket a) return a.getId() == id;
        // Iron's FireBossEntity (the Cult Leader) spawns through Forge's own spawn packet: the first one in its pairing bundle
        if (o instanceof ClientboundBundlePacket b && b.subPackets().iterator().next() instanceof ClientboundCustomPayloadPacket) return true;
        if (o instanceof ClientboundBundlePacket b) for (Packet<?> q : b.subPackets()) if (addsEntity(q, id)) return true;
        return false;
    }

    private static int first(List<Object> got, java.util.function.Predicate<Object> p) {
        for (int i = 0; i < got.size(); i++) if (p.test(got.get(i))) return i;
        return -1;
    }

    private static boolean channel(Object o, String path) {
        return o instanceof ClientboundCustomPayloadPacket c && c.getIdentifier().getNamespace().equals(PohCore.MODID)
                && c.getIdentifier().getPath().equals(path);
    }

    private static int bossEvents(List<Object> got) {
        int n = 0;
        for (Object o : got) if (o instanceof ClientboundBossEventPacket) n++;
        return n;
    }

    private static void run(GameTestHelper h, String id, int introTicks) {
        Viewer a = viewer(h, id + "_a", 3, 3);
        Vec3 at = h.absoluteVec(new Vec3(8, 2, 8));
        h.runAfterDelay(5, () -> {
            a.drain();
            a.got.clear();
            var src = h.getLevel().getServer().createCommandSourceStack().withLevel(h.getLevel()).withPermission(4).withSuppressedOutput();
            h.getLevel().getServer().getCommands().performPrefixedCommand(src, "pohsmp boss " + id + " " + at.x + " " + at.y + " " + at.z);
            a.drain();
            List<Mob> found = h.getLevel().getEntitiesOfClass(Mob.class, new AABB(at, at).inflate(6), e -> e instanceof PohBoss);
            if (found.isEmpty()) h.fail(id + ": the boss was not spawned");
            Mob boss = found.get(0);
            int add = first(a.got, o -> addsEntity(o, boss.getId()));
            int fx = first(a.got, o -> channel(o, "main"));
            int msg = first(a.got, o -> channel(o, "boss"));
            PohCore.LOG.info("[boss_spawn] {}: packets in the spawn tick {}; add entity #{}, first fx #{}, first boss msg #{}, boss events {}", id,
                    a.got.size(), add, fx, msg, bossEvents(a.got));
            if (add < 0) PohCore.LOG.info("[boss_spawn] {}: packets {}", id, a.got.stream().map(o -> o instanceof ClientboundCustomPayloadPacket c
                    ? "payload " + c.getIdentifier() : o instanceof ClientboundBundlePacket b
                    ? "bundle " + java.util.stream.StreamSupport.stream(b.subPackets().spliterator(), false).map(q -> q.getClass().getSimpleName()).toList()
                    : o.getClass().getSimpleName()).toList());
            if (add < 0) h.fail(id + ": the spawning player was not sent the entity in the spawn tick");
            if (fx < 0) h.fail(id + ": no intro fx was sent in the spawn tick");
            if (fx < add) h.fail(id + ": the intro fx went before the entity (#" + fx + " < #" + add + ")");
            if (msg >= 0 && msg < add) h.fail(id + ": a boss message went before the entity (#" + msg + " < #" + add + ")");
            if (bossEvents(a.got) == 0) h.fail(id + ": no vanilla boss event row (BossBarClient has nothing to draw in)");

            h.runAfterDelay(introTicks, () -> {
                if (!((PohBoss) boss).bossCore().started()) h.fail(id + ": the fight did not start after the intro");
                Viewer b = viewer(h, id + "_b", 13, 13);   // a late viewer
                h.runAfterDelay(5, () -> {
                    b.drain();
                    if (first(b.got, o -> addsEntity(o, boss.getId())) < 0) h.fail(id + ": the late viewer was not sent the entity");
                    if (bossEvents(b.got) == 0) h.fail(id + ": the late viewer got no boss event row");
                    boss.discard();
                    a.p.discard();
                    b.p.discard();
                    h.succeed();
                });
            });
        });
    }

    @GameTest(template = "arena", batch = "boss_cult_leader", timeoutTicks = 600)
    public static void spawnCultLeader(GameTestHelper h) {
        run(h, "cult_leader", 260);
    }

    @GameTest(template = "arena", batch = "boss_irina", timeoutTicks = 600)
    public static void spawnIrina(GameTestHelper h) {
        run(h, "irina", 200);
    }

    @GameTest(template = "arena", batch = "boss_aris", timeoutTicks = 600)
    public static void spawnAris(GameTestHelper h) {
        run(h, "aris", 230);
    }

    @GameTest(template = "arena", batch = "boss_martin", timeoutTicks = 600)
    public static void spawnMartin(GameTestHelper h) {
        run(h, "martin", 180);
    }

    @GameTest(template = "arena", batch = "boss_ereb", timeoutTicks = 600)
    public static void spawnEreb(GameTestHelper h) {
        run(h, "ereb", 150);
    }

    @GameTest(template = "arena", batch = "boss_ereb_hand", timeoutTicks = 600)
    public static void spawnErebHand(GameTestHelper h) {
        run(h, "ereb_hand", 180);
    }
}
