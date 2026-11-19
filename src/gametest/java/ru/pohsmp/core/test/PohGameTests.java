package ru.pohsmp.core.test;

import com.mojang.authlib.GameProfile;
import io.netty.channel.embedded.EmbeddedChannel;
import io.redspace.ironsspellbooks.api.events.SpellOnCastEvent;
import io.redspace.ironsspellbooks.api.magic.MagicData;
import io.redspace.ironsspellbooks.api.spells.ISpellContainer;
import io.redspace.ironsspellbooks.api.spells.SpellData;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;
import net.minecraft.gametest.framework.GameTest;
import net.minecraft.gametest.framework.GameTestAssertException;
import net.minecraft.gametest.framework.GameTestHelper;
import net.minecraft.network.Connection;
import net.minecraft.network.chat.Component;
import net.minecraft.network.protocol.PacketFlow;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.GameType;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.common.MinecraftForge;
import net.minecraftforge.event.RegisterGameTestsEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import net.minecraftforge.gametest.GameTestHolder;
import net.minecraftforge.gametest.PrefixGameTestTemplate;
import ru.pohsmp.core.Charges;
import ru.pohsmp.core.PohCore;
import ru.pohsmp.core.Scrolls;
import ru.pohsmp.core.ServerConfig;
import ru.pohsmp.core.spell.JointCast;

/**
 * In-game checks on a real server with Iron's Spells: scroll charges (T16) and the joint cast (T15).
 * Run: gradlew runGameTestServer -PdevRun (the server exits with the number of failed tests).
 * Mages are survival players without a client (their packets go nowhere); casting goes through Iron's own Scroll.use.
 */
@GameTestHolder(PohCore.MODID)
@PrefixGameTestTemplate(false)
@Mod.EventBusSubscriber(modid = PohCore.MODID, bus = Mod.EventBusSubscriber.Bus.MOD)
public final class PohGameTests {
    private PohGameTests() {}

    private static final String ARENA = "arena";
    private static final ResourceLocation HEAL = new ResourceLocation("irons_spellbooks", "heal");
    private static final ResourceLocation FORTIFY = new ResourceLocation("irons_spellbooks", "fortify");

    @SubscribeEvent
    public static void register(RegisterGameTestsEvent e) {
        e.register(PohGameTests.class);
        MinecraftForge.EVENT_BUS.addListener(PohGameTests::onCast);
    }

    // ---- what took effect ----

    private record Cast(String spell, String who, long tick) {}

    private static final List<Cast> CASTS = new ArrayList<>();

    private static void onCast(SpellOnCastEvent e) {
        CASTS.add(new Cast(e.getSpellId(), e.getEntity().getGameProfile().getName(), e.getEntity().level().getGameTime()));
    }

    private static List<Cast> casts(String spell) {
        return CASTS.stream().filter(c -> c.spell.equals(spell)).toList();
    }

    // ---- helpers ----

    private static ServerPlayer mage(GameTestHelper h, String name, double x, double z, boolean creative) {
        ServerLevel lvl = h.getLevel();
        ServerPlayer p = new ServerPlayer(lvl.getServer(), lvl, new GameProfile(UUID.randomUUID(), name));
        Connection c = new Connection(PacketFlow.SERVERBOUND);
        new EmbeddedChannel(c);
        lvl.getServer().getPlayerList().placeNewPlayer(c, p);
        p.setGameMode(creative ? GameType.CREATIVE : GameType.SURVIVAL);
        Vec3 a = h.absoluteVec(new Vec3(x, 1, z));
        p.teleportTo(lvl, a.x, a.y, a.z, 0, 0);
        return p;
    }

    private static void leave(ServerPlayer... ps) {
        for (ServerPlayer p : ps) p.server.getPlayerList().remove(p);
    }

    private static ItemStack scroll(ResourceLocation spell, int charges) {
        ItemStack st = Scrolls.make(spell, 1, null);
        if (charges > 0) st.getOrCreateTag().putInt(Charges.NBT, charges);   // the way /give writes it: no max yet
        return st;
    }

    private static void use(ServerPlayer p) {
        p.getMainHandItem().use(p.level(), p, InteractionHand.MAIN_HAND);
    }

    private static void check(boolean ok, String what) {
        if (!ok) throw new GameTestAssertException(what);
    }

    private static String tip(ItemStack st) {
        Component c = Charges.tooltip(st);
        return c == null ? "-" : c.getString();
    }

    private static void scrollWith(ItemStack st, ResourceLocation spell, int charges, String tip, String where) {
        check(st.getItem() instanceof io.redspace.ironsspellbooks.item.Scroll, where + ": no scroll, got " + st);
        check(Charges.get(st) == charges, where + ": charges " + Charges.get(st) + " != " + charges);
        check(tip(st).equals(tip), where + ": tooltip '" + tip(st) + "' != '" + tip + "'");
        SpellData sd = ISpellContainer.get(st).getSpellAtIndex(0);
        check(sd.getSpell().getSpellResource().equals(spell) && sd.getLevel() == 1, where + ": spell changed: " + sd.getSpell().getSpellId());
        check(sd.isLocked(), where + ": Iron's 'locked' flag lost");
    }

    // ---- T16: scroll charges ----

    /** 3 charges: two casts leave 2/3 and 1/3, the third one takes the scroll; the spell and 'locked' stay. */
    @GameTest(template = ARENA, batch = "charges_spend", timeoutTicks = 200)
    public static void chargesSpendOneEach(GameTestHelper h) {
        ServerPlayer p = mage(h, "mage_a", 6, 6, false);
        p.setItemInHand(InteractionHand.MAIN_HAND, scroll(HEAL, 3));
        h.runAfterDelay(2, () -> {
            scrollWith(p.getMainHandItem(), HEAL, 3, "Charges: 3/3", "start");
            use(p);
        });
        h.runAfterDelay(12, () -> {
            scrollWith(p.getMainHandItem(), HEAL, 2, "Charges: 2/3", "after cast 1");
            check(casts(HEAL.toString()).size() == 1, "cast 1 did not take effect");
            use(p);
        });
        h.runAfterDelay(22, () -> {
            scrollWith(p.getMainHandItem(), HEAL, 1, "Charges: 1/3", "after cast 2");
            use(p);
        });
        h.runAfterDelay(32, () -> {
            check(p.getMainHandItem().isEmpty(), "the last charge must take the scroll, hand: " + p.getMainHandItem());
            check(casts(HEAL.toString()).size() == 3, "3 casts expected, got " + casts(HEAL.toString()).size());
            CASTS.clear();
            leave(p);
            h.succeed();
        });
    }

    /** A stack of two charged scrolls: one cast leaves the other one whole and gives back one scroll with a charge less. */
    @GameTest(template = ARENA, batch = "charges_stack", timeoutTicks = 100)
    public static void chargesStackOfTwo(GameTestHelper h) {
        ServerPlayer p = mage(h, "mage_b", 6, 6, false);
        ItemStack two = scroll(HEAL, 2);
        two.setCount(2);
        p.setItemInHand(InteractionHand.MAIN_HAND, two);
        h.runAfterDelay(2, () -> use(p));
        h.runAfterDelay(12, () -> {
            ItemStack hand = p.getMainHandItem();
            check(hand.getCount() == 1, "one whole scroll must stay in hand, count " + hand.getCount());
            scrollWith(hand, HEAL, 2, "Charges: 2/2", "hand");
            ItemStack back = ItemStack.EMPTY;
            for (int i = 0; i < p.getInventory().getContainerSize(); i++) {
                ItemStack s = p.getInventory().getItem(i);
                if (s != hand && Charges.get(s) > 0) back = s;
            }
            scrollWith(back, HEAL, 1, "Charges: 1/2", "given back");
            CASTS.clear();
            leave(p);
            h.succeed();
        });
    }

    /** Creative: Iron's does not take scrolls, the charge stays too. A scroll without the tag is spent as usual. */
    @GameTest(template = ARENA, batch = "charges_creative", timeoutTicks = 100)
    public static void chargesCreativeAndPlain(GameTestHelper h) {
        ServerPlayer c = mage(h, "mage_c", 3, 6, true);
        ServerPlayer s = mage(h, "mage_d", 9, 6, false);
        c.setItemInHand(InteractionHand.MAIN_HAND, scroll(HEAL, 3));
        s.setItemInHand(InteractionHand.MAIN_HAND, scroll(HEAL, 0));
        h.runAfterDelay(2, () -> {
            check(tip(s.getMainHandItem()).equals("-"), "plain scroll must have no charges line");
            use(c);
            use(s);
        });
        h.runAfterDelay(12, () -> {
            scrollWith(c.getMainHandItem(), HEAL, 3, "Charges: 3/3", "creative");
            check(s.getMainHandItem().isEmpty(), "plain scroll must be spent");
            CASTS.clear();
            leave(c, s);
            h.succeed();
        });
    }

    // ---- T15: joint cast ----

    private static List<? extends String> jointWith(String spell) {
        ServerConfig.JOINT_SPELLS.set(spell == null ? List.of() : List.of(spell));
        return ServerConfig.JOINT_SPELLS.getDefault();   // put back afterwards
    }

    /**
     * Fortify (long cast, 60 ticks) from two scrolls 4 blocks apart, the second 10 ticks later: merged, both end at 0.7 x 60 = 42 ticks
     * after the first start, the spell takes effect once (first mage), both scrolls are spent (the second loses a charge).
     */
    @GameTest(template = ARENA, batch = "joint_merge", timeoutTicks = 200)
    public static void jointCastMerges(GameTestHelper h) {
        List<? extends String> old = jointWith(FORTIFY.toString());
        CASTS.clear();
        ServerPlayer a = mage(h, "mage_lead", 4, 6, false), b = mage(h, "mage_second", 8, 6, false);
        a.setItemInHand(InteractionHand.MAIN_HAND, scroll(FORTIFY, 0));
        b.setItemInHand(InteractionHand.MAIN_HAND, scroll(FORTIFY, 2));
        long[] start = new long[2];
        h.runAfterDelay(2, () -> {
            use(a);
            start[0] = h.getLevel().getGameTime();
            check(MagicData.getPlayerMagicData(a).isCasting(), "first mage did not start");
            check(MagicData.getPlayerMagicData(a).getCastDuration() == 60, "cast time " + MagicData.getPlayerMagicData(a).getCastDuration());
        });
        h.runAfterDelay(12, () -> {
            use(b);
            start[1] = h.getLevel().getGameTime();
            check(MagicData.getPlayerMagicData(b).isCasting(), "second mage did not start");
        });
        h.runAfterDelay(16, () -> {
            check(JointCast.isJoint(a) && JointCast.isJoint(b), "casts did not merge");
            MagicData ma = MagicData.getPlayerMagicData(a), mb = MagicData.getPlayerMagicData(b);
            long now = h.getLevel().getGameTime();
            long endA = now + ma.getCastDurationRemaining(), endB = now + mb.getCastDurationRemaining();
            check(Math.abs(endA - (start[0] + 42)) <= 1, "first mage ends at +" + (endA - start[0]) + ", expected +42");
            check(endB == endA + 1, "second mage ends at " + endB + ", first at " + endA);
            check(ma.getCastDuration() == 42, "first cast bar total " + ma.getCastDuration());
        });
        h.runAfterDelay(70, () -> {
            List<Cast> cs = casts(FORTIFY.toString()).stream().filter(c -> c.who.startsWith("mage_")).toList();
            check(cs.size() == 1, "the spell must take effect once, got " + cs);
            check(cs.get(0).who.equals("mage_lead"), "the first mage casts, got " + cs.get(0).who);
            check(Math.abs(cs.get(0).tick - (start[0] + 42)) <= 1, "took effect at +" + (cs.get(0).tick - start[0]) + ", expected +42");
            check(!MagicData.getPlayerMagicData(a).isCasting() && !MagicData.getPlayerMagicData(b).isCasting(), "someone still casts");
            check(a.getMainHandItem().isEmpty(), "first scroll must be spent");
            scrollWith(b.getMainHandItem(), FORTIFY, 1, "Charges: 1/2", "second mage scroll");
            check(!JointCast.isJoint(a) && !JointCast.isJoint(b), "pair not cleared");
            ServerConfig.JOINT_SPELLS.set(old);
            CASTS.clear();
            leave(a, b);
            h.succeed();
        });
    }

    /** No merge: too far (10 blocks), not in the list, or the second starts after the window (2 s). Each cast goes on its own. */
    @GameTest(template = ARENA, batch = "joint_far", timeoutTicks = 200)
    public static void jointCastTooFar(GameTestHelper h) {
        separate(h, "far", FORTIFY.toString(), 1, 11, 10);
    }

    @GameTest(template = ARENA, batch = "joint_unlisted", timeoutTicks = 200)
    public static void jointCastNotListed(GameTestHelper h) {
        separate(h, "unlisted", null, 4, 8, 10);
    }

    @GameTest(template = ARENA, batch = "joint_late", timeoutTicks = 200)
    public static void jointCastLate(GameTestHelper h) {
        separate(h, "late", FORTIFY.toString(), 4, 8, 45);
    }

    private static void separate(GameTestHelper h, String tag, String listed, double xa, double xb, int delay) {
        List<? extends String> old = jointWith(listed);
        CASTS.clear();
        ServerPlayer a = mage(h, tag + "_one", xa, 6, false), b = mage(h, tag + "_two", xb, 6, false);
        a.setItemInHand(InteractionHand.MAIN_HAND, scroll(FORTIFY, 0));
        b.setItemInHand(InteractionHand.MAIN_HAND, scroll(FORTIFY, 0));
        long[] start = new long[2];
        h.runAfterDelay(2, () -> {
            use(a);
            start[0] = h.getLevel().getGameTime();
        });
        h.runAfterDelay(2 + delay, () -> {
            use(b);
            start[1] = h.getLevel().getGameTime();
            check(!JointCast.isJoint(a) && !JointCast.isJoint(b), "must not merge");
        });
        h.runAfterDelay(2 + delay + 4, () -> check(!JointCast.isJoint(a) && !JointCast.isJoint(b), "must not merge"));
        h.runAfterDelay(2 + delay + 70, () -> {
            List<Cast> cs = casts(FORTIFY.toString()).stream().filter(c -> c.who.startsWith(tag + "_")).toList();
            check(cs.size() == 2, "each mage casts on his own, got " + cs);
            for (Cast c : cs) {
                long s = c.who.equals(tag + "_one") ? start[0] : start[1];
                check(Math.abs(c.tick - (s + 60)) <= 1, c.who + " took effect at +" + (c.tick - s) + ", expected the full +60");
            }
            ServerConfig.JOINT_SPELLS.set(old);
            CASTS.clear();
            leave(a, b);
            h.succeed();
        });
    }
}
