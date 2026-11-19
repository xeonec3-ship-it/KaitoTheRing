package ru.pohsmp.core.spell.illusion;

import io.redspace.ironsspellbooks.api.magic.MagicData;
import io.redspace.ironsspellbooks.api.spells.CastSource;
import io.redspace.ironsspellbooks.api.spells.CastType;
import io.redspace.ironsspellbooks.api.spells.SpellRarity;
import io.redspace.ironsspellbooks.api.util.AnimationHolder;
import java.util.List;
import net.minecraft.network.chat.MutableComponent;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.network.PacketDistributor;
import ru.pohsmp.core.ServerConfig;
import ru.pohsmp.core.fx.Fx;
import ru.pohsmp.core.illusion.Copies;
import ru.pohsmp.core.illusion.Illusions;
import ru.pohsmp.core.net.HideMsg;
import ru.pohsmp.core.net.Net;
import ru.pohsmp.core.spell.CastAnims;
import ru.pohsmp.core.spell.HigherSpell;

/**
 * T22 «Ложный шаг»: for [false_step] seconds the caster is gone for the enemies around (model, armour, shadow, name - not drawn on their
 * clients), while a copy runs on along its course at its speed and swings once; the caster itself dashes up to `dash` blocks the way it
 * looks. Only the caster and its allies see the ghost trail (fx/illusion_false_step); the enemies see nothing but the runner.
 */
public class FalseStepSpell extends IllusionBase {
    public static final String PATH = "false_step";

    public FalseStepSpell() {
        super(PATH, SpellRarity.UNCOMMON, 5, 0, ServerConfig.FS_MANA, ServerConfig.FS_COOLDOWN);
    }

    @Override public CastType getCastType() { return CastType.INSTANT; }
    @Override public AnimationHolder getCastStartAnimation() { return CastAnims.of("illusion_false_step_cast"); }

    private double dash(int level) {
        return d(ServerConfig.FS_DASH) * lv(level, 0.75, 1.25);
    }

    @Override
    public List<MutableComponent> getUniqueInfo(int level, LivingEntity caster) {
        return List.of(ui("dash", n(Math.round(dash(level) * 10) / 10.0)), ui("time", n(d(ServerConfig.FS_SECONDS))));
    }

    @Override
    public void onCast(Level level, int spellLevel, LivingEntity caster, CastSource source, MagicData md) {
        if (level instanceof ServerLevel sl) {
            int ticks = Math.max(2, ticks(ServerConfig.FS_SECONDS));
            List<ServerPlayer> victims = Illusions.victims(sl, caster, 64);
            Vec3 start = caster.position();
            Vec3 run = caster.getDeltaMovement().multiply(1, 0, 1);
            Vec3 look = caster.getLookAngle().multiply(1, 0, 1);
            if (look.lengthSqr() < 1e-4) look = Vec3.directionFromRotation(0, caster.getYRot());
            look = look.normalize();
            double speed = Math.max(caster.isSprinting() ? 0.28 : 0.2, run.length());
            Vec3 course = run.lengthSqr() > 1e-3 ? run.normalize() : look;
            // the runner: on along the course, one swing on the way
            Copies.spawn(caster, Copies.Mode.RUNNER, start, course.scale(speed), ticks, 1, 0, victims);
            for (ServerPlayer v : victims) {
                int left = Illusions.duration(v, ticks);
                Net.CH.send(PacketDistributor.PLAYER.with(() -> v), new HideMsg(caster.getId(), left));
            }
            Vec3 to = dashTo(sl, caster, look, dash(spellLevel));
            HigherSpell.place(caster, to.x, to.y, to.z);
            caster.fallDistance = 0;
            for (ServerPlayer p : sl.players())   // the trail only for the caster and its allies
                if (p.distanceToSqr(caster) < 64 * 64 && Illusions.ally(caster, p))
                    fx(sl, Fx.fx("illusion_false_step").at(start).caster(caster).attach(caster).point("to", to).only(p), "illusion_false_step");
            if (caster instanceof ServerPlayer sp)
                sp.connection.send(new net.minecraft.network.protocol.game.ClientboundSoundPacket(
                        net.minecraft.core.Holder.direct(SoundEvents.AMETHYST_BLOCK_CHIME), SoundSource.PLAYERS, to.x, to.y + 1, to.z, 0.8f, 1.5f, 0));
        }
        super.onCast(level, spellLevel, caster, source, md);
    }

    /** As far along the look as the caster's body fits (stops at walls; steps up half a block). */
    private static Vec3 dashTo(ServerLevel sl, LivingEntity c, Vec3 dir, double len) {
        Vec3 at = c.position();
        AABB box = c.getBoundingBox();
        for (double s = 0.25; s <= len; s += 0.25) {
            Vec3 p = c.position().add(dir.scale(s));
            Vec3 d = p.subtract(c.position());
            if (sl.noCollision(c, box.move(d))) at = p;
            else if (sl.noCollision(c, box.move(d.add(0, 0.6, 0)))) at = p.add(0, 0.6, 0);
            else break;
        }
        return at;
    }
}
