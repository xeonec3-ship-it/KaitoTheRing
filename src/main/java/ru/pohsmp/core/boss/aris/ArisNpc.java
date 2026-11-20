package ru.pohsmp.core.boss.aris;

import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.PathfinderMob;
import net.minecraft.world.level.Level;
import ru.pohsmp.core.boss.BossNpc;

/**
 * Aris after the surrender (owner 20.11): the framework's peaceful NPC (no dialogues, cannot be hurt) in her own pose — sitting on
 * the head of the fallen hammer (animation.aris.npc_sit; the bone hammer_ground is shown by the animation itself), texture aris_dim.
 */
public class ArisNpc extends BossNpc {
    public ArisNpc(EntityType<? extends PathfinderMob> type, Level level) {
        super(type, level, Aris.ID);
    }

    @Override
    public String idleAnimation() {
        return "animation.aris.npc_sit";
    }
}
