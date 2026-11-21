package ru.pohsmp.core.boss;

import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;

/**
 * Who is in a boss's vanilla boss-bar row (pure, no Minecraft types, so it is unit tested). The row is what makes the client fire
 * CustomizeGuiOverlayEvent.BossEventProgress for the boss's UUID — the only hook BossBarClient draws the phase bar in: no row, no bar
 * (the T34 bug: Aris, Irina, Ereb, Ereb Hand had no server boss event at all). A viewer joins on being seen (spawn, intro, a late
 * join — the client hides the row itself until BAR_VISIBLE), leaves on unseen; the finale / death closes it for good.
 */
public final class BossBarRow<P> {
    private final Set<P> members = new LinkedHashSet<>();
    private boolean closed;

    /** The viewer started seeing the boss: true = add it to the server boss event now. */
    public boolean seen(P p) {
        return !closed && members.add(p);
    }

    /** The viewer stopped seeing the boss: true = remove it from the server boss event. */
    public boolean unseen(P p) {
        return members.remove(p);
    }

    /** Finale or death: everyone out (returned), nobody joins again. */
    public List<P> close() {
        closed = true;
        List<P> out = new ArrayList<>(members);
        members.clear();
        return out;
    }

    public boolean has(P p) {
        return members.contains(p);
    }

    public boolean closed() {
        return closed;
    }

    /** The client draws the phase bar only when all four hold (BossBarClient.onBar). */
    public static boolean drawn(boolean inRow, boolean barMsgKnown, boolean visible, boolean camHidesBars) {
        return inRow && barMsgKnown && visible && !camHidesBars;
    }
}
