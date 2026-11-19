package ru.pohsmp.core.compat;

import de.maxhenkel.voicechat.api.ForgeVoicechatPlugin;
import de.maxhenkel.voicechat.api.VoicechatConnection;
import de.maxhenkel.voicechat.api.VoicechatPlugin;
import de.maxhenkel.voicechat.api.events.EntitySoundPacketEvent;
import de.maxhenkel.voicechat.api.events.EventRegistration;
import de.maxhenkel.voicechat.api.packets.EntitySoundPacket;
import java.util.UUID;
import net.minecraft.world.phys.Vec3;
import ru.pohsmp.core.illusion.Voices;

/**
 * T22, Simple Voice Chat: the voice of a caster under an illusion comes, for its victims only, from where the illusion says
 * (illusion/Voices): the copy («Отражения», «Ложный шаг»), a random point near the victim («Сон бабочки»). Everyone else hears it as
 * always. Per receiver: the voice chat asks for every listener separately; for a victim the packet bound to the player is dropped and the
 * same sound is sent from the place instead, at the same distance. Loaded by the voice chat itself only when it is installed.
 */
@ForgeVoicechatPlugin
public class VoiceIllusions implements VoicechatPlugin {
    @Override
    public String getPluginId() {
        return "pohsmp_core";
    }

    @Override
    public void registerEvents(EventRegistration r) {
        r.registerEvent(EntitySoundPacketEvent.class, VoiceIllusions::onEntitySound);
        r.registerEvent(de.maxhenkel.voicechat.api.events.MicrophonePacketEvent.class, VoiceIllusions::onMic);
    }

    /** T24: the erased are not heard - their microphone goes nowhere. */
    private static void onMic(de.maxhenkel.voicechat.api.events.MicrophonePacketEvent e) {
        VoicechatConnection from = e.getSenderConnection();
        if (from != null && from.getPlayer() != null && ru.pohsmp.core.erased.Erased.isErased(from.getPlayer().getUuid())) e.cancel();
    }

    private static void onEntitySound(EntitySoundPacketEvent e) {
        VoicechatConnection to = e.getReceiverConnection();
        if (to == null || to.getPlayer() == null) return;
        EntitySoundPacket p = e.getPacket();
        UUID speaker = p.getEntityUuid();
        Vec3 at = Voices.from(speaker, to.getPlayer().getUuid());
        if (at == null) return;
        e.cancel();
        var api = e.getVoicechat();
        api.sendLocationalSoundPacketTo(to, p.locationalSoundPacketBuilder()
                .position(api.createPosition(at.x, at.y, at.z))
                .distance(p.getDistance())
                .build());
    }
}
