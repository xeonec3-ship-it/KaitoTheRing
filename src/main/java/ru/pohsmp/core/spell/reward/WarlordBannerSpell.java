package ru.pohsmp.core.spell.reward;

import io.redspace.ironsspellbooks.api.magic.MagicData;
import io.redspace.ironsspellbooks.api.spells.CastSource;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import net.minecraft.network.chat.MutableComponent;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.sounds.SoundEvent;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.effect.MobEffectInstance;
import net.minecraft.world.effect.MobEffects;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.MobSpawnType;
import net.minecraft.world.entity.decoration.ArmorStand;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.Vec3;
import ru.pohsmp.core.spell.PohSpell;
import ru.pohsmp.core.spell.Tasks;

/**
 * «Знамя Полководца» (reward of Martin): the banner is planted in front of the caster for 20 s: allies within r8 (the caster, its team,
 * its pets, its soldiers and players not fighting it) get Strength I and Resistance I; 2 ghost soldiers of Martin rise and fight for
 * the caster (BannerSoldierEntity), vanishing with the banner. One banner per caster: a new one takes the old one down. The banner
 * falls early if the caster dies or leaves the dimension. Fx: warlord_banner (the banner), warlord_banner_aura (the circle),
 * warlord_banner_soldier_spawn — fallback: Martin's martin_banner_plant / martin_banner_aura / martin_soldier_spawn.
 */
public class WarlordBannerSpell extends RewardSpell {
    private static final Map<UUID, Banner> UP = new HashMap<>();

    public WarlordBannerSpell() {
        super(RewardMath.WARLORD_BANNER, RewardMath.BAN_CAST, RewardMath.BAN_CD, RewardMath.BAN_MANA, RewardMath.BAN_MANA_LVL);
    }

    @Override public Optional<SoundEvent> getCastStartSound() { return Optional.of(SoundEvents.RAID_HORN.value()); }

    @Override
    public List<MutableComponent> getUniqueInfo(int level, LivingEntity caster) {
        return List.of(ui("duration", (int) lv(RewardMath.BAN_SECONDS, level)), ui("radius", (int) RewardMath.BAN_RADIUS),
                ui("soldiers", RewardMath.BAN_SOLDIERS, (int) lv(RewardMath.BAN_SOLDIER_HP, level), num(lv(RewardMath.BAN_SOLDIER_DAMAGE, level))));
    }

    @Override
    public void onCast(Level level, int spellLevel, LivingEntity caster, CastSource source, MagicData md) {
        if (level instanceof ServerLevel sl) {
            Banner old = UP.remove(caster.getUUID());
            if (old != null) old.end();
            Vec3 f = Vec3.directionFromRotation(0, caster.getYRot()).scale(1.2);
            Vec3 at = PohSpell.ground(sl, caster, caster.position().add(f.x, 0.5, f.z));
            Banner b = new Banner(sl, caster, at, spellLevel);
            UP.put(caster.getUUID(), b);
            Tasks.add(b);
        }
        super.onCast(level, spellLevel, caster, source, md);
    }

    private static final class Banner implements Tasks.Task {
        final ServerLevel sl;
        final LivingEntity caster;
        final Vec3 at;
        final int lvl, life;
        final long until;
        final int bannerFx, auraFx;
        final List<BannerSoldierEntity> soldiers = new ArrayList<>();
        int age;
        boolean ended;

        Banner(ServerLevel sl, LivingEntity caster, Vec3 at, int lvl) {
            this.sl = sl;
            this.caster = caster;
            this.at = at;
            this.lvl = lvl;
            this.life = RewardMath.ticks(lv(RewardMath.BAN_SECONDS, lvl));
            this.until = sl.getGameTime() + life;
            float yaw = caster.getYRot();
            bannerFx = play(sl, "warlord_banner", "martin_banner_plant", s -> s.at(at).yaw(yaw).caster(caster).duration(life));
            auraFx = play(sl, "warlord_banner_aura", "martin_banner_aura", s -> s.at(at).caster(caster).duration(life));
            sl.playSound(null, at.x, at.y, at.z, SoundEvents.ANVIL_PLACE, SoundSource.PLAYERS, 1f, 0.6f);
        }

        @Override
        public boolean tick() {
            if (ended) return false;
            age++;
            if (age >= life || !caster.isAlive() || caster.isRemoved() || caster.level() != sl) {
                end();
                return false;
            }
            if (age == RewardMath.BAN_SOLDIERS_AT) rise();
            if (age % 10 == 1) buff();
            return true;
        }

        boolean ally(LivingEntity e) {
            if (e == caster || e instanceof ArmorStand || e.isSpectator()) return e == caster;
            if (friendly(caster, e)) return true;
            return e instanceof Player && !foe(caster, e);
        }

        void buff() {
            for (LivingEntity e : around(sl, at, RewardMath.BAN_RADIUS, this::ally)) {
                e.addEffect(new MobEffectInstance(MobEffects.DAMAGE_BOOST, 30, 0, true, true, true), caster);
                e.addEffect(new MobEffectInstance(MobEffects.DAMAGE_RESISTANCE, 30, 0, true, true, true), caster);
            }
        }

        void rise() {
            if (Rewards.SOLDIER == null) return;
            float yaw = caster.getYRot();
            for (int i = 0; i < RewardMath.BAN_SOLDIERS; i++) {
                double side = (i - (RewardMath.BAN_SOLDIERS - 1) / 2.0) * 2.2;
                Vec3 r = Vec3.directionFromRotation(0, yaw + 90).scale(side);
                Vec3 p = PohSpell.ground(sl, caster, at.add(r.x, 1.0, r.z));
                BannerSoldierEntity s = Rewards.SOLDIER.get().create(sl);
                if (s == null) continue;
                s.moveTo(p.x, p.y, p.z, yaw, 0);
                s.setYHeadRot(yaw);
                s.setup(caster, until, lv(RewardMath.BAN_SOLDIER_HP, lvl), dmg(lv(RewardMath.BAN_SOLDIER_DAMAGE, lvl)));
                s.finalizeSpawn(sl, sl.getCurrentDifficultyAt(s.blockPosition()), MobSpawnType.MOB_SUMMONED, null, null);
                if (!sl.addFreshEntity(s)) continue;
                soldiers.add(s);
                s.serverTriggerAnimation("martin_soldier_spawn");
                play(sl, "warlord_banner_soldier_spawn", "martin_soldier_spawn", sp -> sp.at(p).yaw(yaw).caster(s));
            }
            sl.playSound(null, at.x, at.y, at.z, SoundEvents.SOUL_ESCAPE, SoundSource.PLAYERS, 1.2f, 0.6f);
        }

        void end() {
            if (ended) return;
            ended = true;
            UP.remove(caster.getUUID(), this);
            stopFx(sl, bannerFx);
            stopFx(sl, auraFx);
            for (BannerSoldierEntity s : soldiers) if (s.isAlive()) s.vanish(sl);
            soldiers.clear();
        }
    }
}
