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
        if (!isNpc(npc)) return false;
        try {
            Field f = field(npc.getClass(), "script");
            Object data = f.get(npc);
            if (data == null) return false;
            Method en = data.getClass().getMethod("isEnabled");
            if (!(Boolean) en.invoke(data)) return false;
            List<?> scripts = (List<?>) data.getClass().getMethod("getScripts").invoke(data);
            for (Object sc : scripts) {
                Object wrapped = sc.getClass().getField("wrappedNPC").get(sc);
                if (wrapped == null) wrapped = field(npc.getClass(), "wrappedNPC").get(npc);
                Event ev = new Event(wrapped, name, caster, npc.getX(), npc.getY(), npc.getZ());
                sc.getClass().getMethod("run", String.class, Object.class).invoke(sc, name, ev);
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
