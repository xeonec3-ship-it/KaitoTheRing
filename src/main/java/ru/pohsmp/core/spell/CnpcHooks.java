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
            // DataAI.setAnimation only changes the server value: ask CNPC to resend the NPC data to the clients
            try {
                field(npc.getClass(), "updateClient").setBoolean(npc, true);
            } catch (NoSuchFieldException ignored) {
            }
            return old;
        } catch (Throwable t) {
            LOG.warn("[pohsmp] CNPC animation {} failed: {}", type, t.toString());
            return -1;
        }
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
