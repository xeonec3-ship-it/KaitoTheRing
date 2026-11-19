package ru.pohsmp.core.spell;

import com.mojang.logging.LogUtils;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.util.List;
import net.minecraft.world.entity.Entity;
import org.slf4j.Logger;

/**
 * Calls a function of a CustomNPCs NPC script by name (without a compile dependency on CNPC): every script tab of the NPC that
 * has a function with that name gets one argument, a {@link Event}. Script side (README): <code>function coven_exit(e) { e.npc.say("...") }</code>.
 */
public final class CnpcHooks {
    private CnpcHooks() {}

    private static final Logger LOG = LogUtils.getLogger();

    /** What the script gets: the NPC (its CNPC wrapper), where it is, who cast, which stage. */
    public static final class Event {
        public final Object npc;
        public final String type, caster;
        public final double x, y, z;

        Event(Object npc, String type, String caster, double x, double y, double z) {
            this.npc = npc;
            this.type = type;
            this.caster = caster;
            this.x = x;
            this.y = y;
            this.z = z;
        }
    }

    public static boolean isNpc(Entity e) {
        for (Class<?> c = e.getClass(); c != null; c = c.getSuperclass())
            if (c.getName().equals("noppes.npcs.entity.EntityNPCInterface")) return true;
        return false;
    }

    /** Runs `function name(e)` in the NPC's scripts; false if it is not a CNPC NPC or something failed. */
    public static boolean call(Entity npc, String name, String caster) {
        return run(npc, name, wrapped -> new Event(wrapped, name, caster, npc.getX(), npc.getY(), npc.getZ()));
    }

    /** Same with an event object of the caller's (its public field `npc`, if any, gets the NPC's script wrapper). */
    public static boolean callWith(Entity npc, String name, Object event) {
        return run(npc, name, wrapped -> {
            try {
                event.getClass().getField("npc").set(event, wrapped);
            } catch (ReflectiveOperationException ignored) {
            }
            return event;
        });
    }

    private static boolean run(Entity npc, String name, java.util.function.Function<Object, Object> make) {
        if (!isNpc(npc)) return false;
        try {
            Field f = field(npc.getClass(), "script");
            Object data = f.get(npc);
            if (data == null) return false;
            Method en = data.getClass().getMethod("isEnabled");
            if (!(Boolean) en.invoke(data)) return false;
            List<?> scripts = (List<?>) data.getClass().getMethod("getScripts").invoke(data);
            Object own = field(npc.getClass(), "wrappedNPC").get(npc);
            for (Object sc : scripts) {
                // older CNPC builds keep the wrapper on the script container, newer ones (GBPort 1.20.1) only on the NPC
                Object wrapped = null;
                try {
                    wrapped = sc.getClass().getField("wrappedNPC").get(sc);
                } catch (NoSuchFieldException ignored) {
                }
                if (wrapped == null) wrapped = own;
                sc.getClass().getMethod("run", String.class, Object.class).invoke(sc, name, make.apply(wrapped));
            }
            return true;
        } catch (Throwable t) {
            LOG.warn("[pohsmp] CNPC script event {} failed: {}", name, t.toString());
            return false;
        }
    }

    /** CNPC model animation ({@code npc.getAi().setAnimation}: 0 normal, 3 arms forward, 11 bow ...); returns the previous one, -1 on failure. */
    public static int anim(Entity npc, int type) {
        if (!isNpc(npc)) return -1;
        try {
            Object w = field(npc.getClass(), "wrappedNPC").get(npc);
            Method ga = w.getClass().getMethod("getAi");
            ga.setAccessible(true);
            Object ai = ga.invoke(w);
            Method get = ai.getClass().getMethod("getAnimation"), set = ai.getClass().getMethod("setAnimation", int.class);
            get.setAccessible(true);
            set.setAccessible(true);
            int old = ((Number) get.invoke(ai)).intValue();
            set.invoke(ai, type);
            // DataAI.setAnimation only changes the server value: CNPC must resend the NPC data to the clients. Manager 19.11
            // («the NPC animations are gone again»): send it now (EntityNPCInterface.updateClient()), the flag only as a fallback
            boolean sent = false;
            try {
                npc.getClass().getMethod("updateClient").invoke(npc);
                sent = true;
            } catch (NoSuchMethodException ignored) {
            }
            if (!sent) try {
                field(npc.getClass(), "updateClient").setBoolean(npc, true);
                sent = true;
            } catch (NoSuchFieldException ignored) {
            }
            int now = ((Number) get.invoke(ai)).intValue();
            if (now != type || !sent) LOG.warn("[pohsmp] CNPC animation {} on {} did not take: now {}, sent to clients {}", type, npc.getUUID(), now, sent);
            else LOG.info("[pohsmp] CNPC animation {} -> {} on {}", old, type, npc.getUUID());
            return old;
        } catch (Throwable t) {
            LOG.warn("[pohsmp] CNPC animation {} failed: {}", type, t.toString());
            return -1;
        }
    }

    /**
     * Sets the NPC's home (DataAI start position) and returns the previous one (null if not a CNPC NPC or on failure). Owner 19.11
     * («the NPCs have no animations again»): CNPC's EntityAIAnimation shows the chosen model animation only while a returning NPC is
     * very near its home; carried off to the portal and the arena, it fell back to the normal pose every tick.
     */
    public static net.minecraft.core.BlockPos home(Entity npc, net.minecraft.core.BlockPos to) {
        if (!isNpc(npc)) return null;
        try {
            Object ais = field(npc.getClass(), "ais").get(npc);
            net.minecraft.core.BlockPos old = (net.minecraft.core.BlockPos) ais.getClass().getMethod("startPos").invoke(ais);
            if (!to.equals(old)) ais.getClass().getMethod("setStartPos", net.minecraft.core.BlockPos.class).invoke(ais, to);
            return old;
        } catch (Throwable t) {
            LOG.warn("[pohsmp] CNPC home for {} failed: {}", npc.getUUID(), t.toString());
            return null;
        }
    }

    /** For the log: whether e is a CNPC NPC, its model animation and whether its script is on (-1 / false when unknown). */
    public static String describe(Entity e) {
        if (!isNpc(e)) return "not a CNPC NPC";
        int anim = -1;
        boolean script = false;
        try {
            Object w = field(e.getClass(), "wrappedNPC").get(e);
            Object ai = w.getClass().getMethod("getAi").invoke(w);
            anim = ((Number) ai.getClass().getMethod("getAnimation").invoke(ai)).intValue();
            Object data = field(e.getClass(), "script").get(e);
            script = data != null && (Boolean) data.getClass().getMethod("isEnabled").invoke(data);
        } catch (Throwable t) {
            return "CNPC NPC, lookup failed: " + t;
        }
        return "CNPC NPC, animation " + anim + ", script " + (script ? "on" : "off");
    }

    /**
     * CNPC factions: is `npc` (a CNPC NPC) hostile to `other`? A player: the faction is aggressive to them. Another NPC: either faction
     * attacks the other. Unknown or failed lookups count as not hostile.
     */
    public static boolean hostileTo(Entity npc, Entity other) {
        if (!isNpc(npc)) return false;
        try {
            Object f = faction(npc);
            if (f == null) return false;
            if (other instanceof net.minecraft.world.entity.player.Player p) {
                Method m = f.getClass().getMethod("isAggressiveToPlayer", net.minecraft.world.entity.player.Player.class);
                return (Boolean) m.invoke(f, p);
            }
            if (!isNpc(other)) return false;
            Object g = faction(other);
            if (g == null) return false;
            int a = field(f.getClass(), "id").getInt(f), b = field(g.getClass(), "id").getInt(g);
            if (a == b) return false;
            java.util.Collection<?> fa = (java.util.Collection<?>) field(f.getClass(), "attackFactions").get(f);
            java.util.Collection<?> ga = (java.util.Collection<?>) field(g.getClass(), "attackFactions").get(g);
            return fa.contains(b) || ga.contains(a);
        } catch (Throwable t) {
            return false;
        }
    }

    private static Object faction(Entity npc) throws Exception {
        try {
            Method m = npc.getClass().getMethod("getFaction");
            return m.invoke(npc);
        } catch (NoSuchMethodException e) {
            return field(npc.getClass(), "faction").get(npc);
        }
    }

    private static Field field(Class<?> c, String name) throws NoSuchFieldException {
        for (Class<?> k = c; k != null; k = k.getSuperclass()) {
            try {
                Field f = k.getDeclaredField(name);
                f.setAccessible(true);
                return f;
            } catch (NoSuchFieldException ignored) {
            }
        }
        throw new NoSuchFieldException(name);
    }
}
