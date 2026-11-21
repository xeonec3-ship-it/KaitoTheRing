import java.io.*;
import java.nio.file.*;
import java.util.*;
import java.util.zip.*;
import org.objectweb.asm.*;
import org.objectweb.asm.tree.*;
import org.objectweb.asm.tree.analysis.*;

/**
 * Client-only patch of a released pohsmp_core jar (no source rebuild, the server keeps its jar):
 *  1. adds ClientClock, AnimClock, MoveSmooth, FxGlide (compiled + reobfuscated from the repo);
 *  2. in the client visual classes every Level.getGameTime() (SRG m_46467_) becomes ClientClock.ticks(), and
 *     "time + partialTick" (long + float = float math) is done in double;
 *  3. ClientInit.init registers ClientClock on the Forge bus;
 *  4. FxClient.handle starts with "if (FxGlide.move(m)) return;", FxClient.onRender with "FxGlide.frame(e);".
 * Every patched method is checked by ASM's BasicVerifier. Usage: java PatchJar in.jar extraClassesDir out.jar
 */
public class PatchJar {
    static final String CLOCK = "ru/pohsmp/core/client/ClientClock", GLIDE = "ru/pohsmp/core/client/fx/FxGlide";
    static final Map<String, Integer> EXPECT = new LinkedHashMap<>();
    static {   // class -> getGameTime calls expected (as in the jar of 1.16.0 and in the repo)
        EXPECT.put("ru/pohsmp/core/client/DisintegrationFx", 2);
        EXPECT.put("ru/pohsmp/core/client/DownfallCut", 6);
        EXPECT.put("ru/pohsmp/core/client/EmberWhipClient", 8);
        EXPECT.put("ru/pohsmp/core/client/GateStaff", 1);
        EXPECT.put("ru/pohsmp/core/client/HiddenHands", 2);
        EXPECT.put("ru/pohsmp/core/client/HigherFx", 5);
        EXPECT.put("ru/pohsmp/core/client/JointFx", 2);
        EXPECT.put("ru/pohsmp/core/client/OutfitAnim", 2);
        EXPECT.put("ru/pohsmp/core/client/fx/FxClient", 2);
        EXPECT.put("ru/pohsmp/core/client/fx/gate/GateManaRender", 1);
        EXPECT.put("ru/pohsmp/core/client/illusion/Ghosts", 2);
    }
    static int floats;
    static final StringBuilder LOG = new StringBuilder();

    public static void main(String[] a) throws Exception {
        Path in = Path.of(a[0]), extra = Path.of(a[1]), out = Path.of(a[2]);
        Set<String> done = new HashSet<>();
        try (ZipInputStream zi = new ZipInputStream(Files.newInputStream(in));
             ZipOutputStream zo = new ZipOutputStream(Files.newOutputStream(out))) {
            ZipEntry e;
            while ((e = zi.getNextEntry()) != null) {
                byte[] b = zi.readAllBytes();
                String n = e.getName();
                if (n.endsWith(".class")) {
                    String cls = n.substring(0, n.length() - 6);
                    if (EXPECT.containsKey(cls) || cls.equals("ru/pohsmp/core/client/ClientInit")) {
                        b = patch(cls, b);
                        done.add(cls);
                    }
                }
                ZipEntry ne = new ZipEntry(n);
                ne.setTime(e.getTime());
                zo.putNextEntry(ne);
                zo.write(b);
                zo.closeEntry();
            }
            for (String c : List.of(CLOCK, "ru/pohsmp/core/fx/AnimClock", "ru/pohsmp/core/fx/MoveSmooth", GLIDE)) {
                zo.putNextEntry(new ZipEntry(c + ".class"));
                zo.write(Files.readAllBytes(extra.resolve(c + ".class")));
                zo.closeEntry();
                LOG.append("added ").append(c).append('\n');
            }
        }
        for (String c : EXPECT.keySet()) if (!done.contains(c)) throw new IllegalStateException("not in the jar: " + c);
        if (!done.contains("ru/pohsmp/core/client/ClientInit")) throw new IllegalStateException("no ClientInit");
        System.out.print(LOG);
        System.out.println("float time sums turned to double: " + floats);
    }

    static byte[] patch(String cls, byte[] b) throws Exception {
        ClassNode cn = new ClassNode();
        new ClassReader(b).accept(cn, ClassReader.EXPAND_FRAMES);
        int calls = 0;
        for (MethodNode m : cn.methods) {
            boolean changed = false;
            for (AbstractInsnNode i = m.instructions.getFirst(); i != null; i = i.getNext()) {
                if (i instanceof MethodInsnNode mi && mi.getOpcode() == Opcodes.INVOKEVIRTUAL && mi.name.equals("m_46467_") && mi.desc.equals("()J")) {
                    MethodInsnNode ticks = new MethodInsnNode(Opcodes.INVOKESTATIC, CLOCK, "ticks", "()J", false);
                    m.instructions.insertBefore(mi, new InsnNode(Opcodes.POP));
                    m.instructions.set(mi, ticks);
                    i = ticks;
                    calls++;
                    changed = true;
                    fixFloat(m, ticks, cls);
                }
            }
            if (cls.equals("ru/pohsmp/core/client/ClientInit") && m.name.equals("init")) {
                InsnList l = new InsnList();
                l.add(new FieldInsnNode(Opcodes.GETSTATIC, "net/minecraftforge/common/MinecraftForge", "EVENT_BUS", "Lnet/minecraftforge/eventbus/api/IEventBus;"));
                l.add(new LdcInsnNode(Type.getObjectType(CLOCK)));
                l.add(new MethodInsnNode(Opcodes.INVOKEINTERFACE, "net/minecraftforge/eventbus/api/IEventBus", "register", "(Ljava/lang/Object;)V", true));
                m.instructions.insert(l);
                changed = true;
                LOG.append("ClientInit.init: registers ClientClock\n");
            }
            if (cls.equals("ru/pohsmp/core/client/fx/FxClient") && m.name.equals("handle") && m.desc.equals("(Lru/pohsmp/core/net/FxMsg;)V")) {
                InsnList l = new InsnList();
                LabelNode go = new LabelNode();
                l.add(new VarInsnNode(Opcodes.ALOAD, 0));
                l.add(new MethodInsnNode(Opcodes.INVOKESTATIC, GLIDE, "move", "(Lru/pohsmp/core/net/FxMsg;)Z", false));
                l.add(new JumpInsnNode(Opcodes.IFEQ, go));
                l.add(new InsnNode(Opcodes.RETURN));
                l.add(go);
                l.add(new FrameNode(Opcodes.F_NEW, 1, new Object[]{"ru/pohsmp/core/net/FxMsg"}, 0, new Object[0]));
                m.instructions.insert(l);
                changed = true;
                LOG.append("FxClient.handle: MOVE -> FxGlide\n");
            }
            if (cls.equals("ru/pohsmp/core/client/fx/FxClient") && m.name.equals("onRender")
                    && m.desc.equals("(Lnet/minecraftforge/client/event/RenderLevelStageEvent;)V")) {
                InsnList l = new InsnList();
                l.add(new VarInsnNode(Opcodes.ALOAD, 0));
                l.add(new MethodInsnNode(Opcodes.INVOKESTATIC, GLIDE, "frame", "(Lnet/minecraftforge/client/event/RenderLevelStageEvent;)V", false));
                m.instructions.insert(l);
                changed = true;
                LOG.append("FxClient.onRender: FxGlide.frame first\n");
            }
            if (changed) new Analyzer<>(new BasicVerifier()).analyze(cn.name, m);
        }
        Integer want = EXPECT.get(cls);
        if (want != null && want != calls) throw new IllegalStateException(cls + ": " + calls + " getGameTime calls, expected " + want);
        if (want != null) LOG.append(cls).append(": ").append(calls).append(" getGameTime -> ClientClock.ticks\n");
        ClassWriter cw = new ClassWriter(ClassWriter.COMPUTE_MAXS);
        cn.accept(cw);
        return cw.toByteArray();
    }

    /** ticks(); L2F; <one float: FLOAD or a getter ()F>; FADD [F2D]  ->  ticks(); L2D; <float>; F2D; DADD [D2F]. */
    static void fixFloat(MethodNode m, AbstractInsnNode ticks, String cls) {
        AbstractInsnNode l2f = next(ticks);
        if (l2f == null || l2f.getOpcode() != Opcodes.L2F) return;
        AbstractInsnNode fadd = null, last = null;
        int n = 0;
        for (AbstractInsnNode i = next(l2f); i != null && n < 5; i = next(i), n++) {
            if (i.getOpcode() == Opcodes.FADD) { fadd = i; break; }
            last = i;
        }
        boolean oneFloat = last != null && (last.getOpcode() == Opcodes.FLOAD
                || last instanceof MethodInsnNode mi && mi.desc.endsWith(")F") && Type.getArgumentTypes(mi.desc).length == 0
                || last instanceof FieldInsnNode fi && fi.desc.equals("F"));
        if (fadd == null || !oneFloat) throw new IllegalStateException(cls + "." + m.name + ": time + float in an unknown form");
        m.instructions.set(l2f, new InsnNode(Opcodes.L2D));
        m.instructions.insert(last, new InsnNode(Opcodes.F2D));
        AbstractInsnNode dadd = new InsnNode(Opcodes.DADD);
        m.instructions.set(fadd, dadd);
        AbstractInsnNode after = next(dadd);
        if (after != null && after.getOpcode() == Opcodes.F2D) m.instructions.remove(after);
        else m.instructions.insert(dadd, new InsnNode(Opcodes.D2F));
        floats++;
    }

    static AbstractInsnNode next(AbstractInsnNode i) {
        AbstractInsnNode n = i.getNext();
        while (n != null && (n instanceof LineNumberNode || n instanceof LabelNode && !(n.getNext() instanceof FrameNode))) n = n.getNext();
        return n;
    }
}
