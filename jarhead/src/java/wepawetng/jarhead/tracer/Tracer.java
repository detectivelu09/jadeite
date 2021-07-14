package wepawetng.jarhead.tracer;

import org.objectweb.asm.*;
import org.objectweb.asm.tree.analysis.*;
import org.objectweb.asm.commons.*;
import org.objectweb.asm.tree.*;
import java.io.*;
import java.util.*;

public class Tracer extends ClassNode {
	public Tracer(HashSet<String> called, HashSet<String> declared) {
		all_declared = declared;
		all_called = called;
	}
	private HashSet<String> all_declared;
	private HashSet<String> all_called;

	private static void dump_constant_pool(byte[] classfile) {
		DataInputStream stream = null;
		try {
			stream = new DataInputStream(new ByteArrayInputStream(classfile));
			Constant[] pool = Constant.extractConstantPool(stream);
			for (Constant c: pool) {
				System.out.println(c);
			}
		} catch (IOException e) {
			System.out.println(e);
		}
	}

	private double unused_variables() {
		int total_used, total;
		total = total_used = 0;
		for (Object o: methods) {
			int max = 0;
			Collection<Integer> stores = new HashSet<Integer>();
			Collection<Integer> loads = new HashSet<Integer>();
			MethodNode n = (MethodNode) o;
			InsnList ins = n.instructions;
			for (int i = 0; i < ins.size(); i++) {
				AbstractInsnNode a = ins.get(i);
				if (a.getType() == AbstractInsnNode.VAR_INSN) {
					VarInsnNode v = (VarInsnNode) a;
					int varidx = v.var;
					int opcode = v.getOpcode();
					switch (opcode) {
						case Opcodes.ILOAD:
						case Opcodes.LLOAD:
						case Opcodes.FLOAD:
						case Opcodes.DLOAD:
						case Opcodes.ALOAD:
							loads.add(varidx);
							break;
						case Opcodes.ISTORE:
						case Opcodes.LSTORE:
						case Opcodes.FSTORE:
						case Opcodes.DSTORE:
						case Opcodes.ASTORE:
							stores.add(varidx);
							break;
						case Opcodes.RET:
							break;
						default:
							assert(false);
					}
				}
			}
			Iterator<Integer> i = stores.iterator();
			while (i.hasNext()) {
				int tmp = i.next();
				if (tmp > max) {
					max = tmp;
				}
			}
			i = loads.iterator();
			while (i.hasNext()) {
				int tmp = i.next();
				if (tmp > max) {
					max = tmp;
				}
			}
			Set<Integer> intersection = new HashSet<Integer>(stores);
			intersection.retainAll(loads);
			total += max;
			total_used += intersection.size();
			//System.out.println("max: " + max + " not in both: " + (max - intersection.size()));
		}
		if (total != 0.0) {
			return ((double) (total - total_used) / (double) total) * 100.0;
		} else {
			return 0.0;
		}
	}

	private void collect_methods() {
		for (Object o: methods) {
			MethodNode n = (MethodNode) o;
			all_declared.add(n.name);
		}
		//System.out.println("Found " + methods.size() + " methods");
		for (Object o: methods) {
			MethodNode n = (MethodNode) o;
			InsnList ins = n.instructions;
			for (int i = 0; i < ins.size(); i++) {
				AbstractInsnNode a = ins.get(i);
				if (a.getType() == AbstractInsnNode.METHOD_INSN) {
					MethodInsnNode m = (MethodInsnNode) a;
					all_called.add(m.name);
					System.out.println("fcall:" + m.owner.replace('/', '.') + "." + m.name);
				}
			}
		}
	}

	public void visitEnd() {
		collect_methods();
		System.out.println("V: " + unused_variables());
	}

	private static double unused_methods(HashSet<String> all_called, HashSet<String> all_declared) {
		int total_unused, total;
		HashSet<String> declared_and_called = new HashSet<String>(all_called);
		declared_and_called.retainAll(all_declared);
		total = all_declared.size();
		total_unused = all_declared.size() - declared_and_called.size();
		if (total != 0.0) {
			return (((double) total_unused) / (double) total) * 100.0;
		} else {
			return 0.0;
		}
	}

	public static void main(String[] args) {
		HashSet<String> all_declared = new HashSet<String>();
		all_declared.add("<init>");
		all_declared.add("start");
		all_declared.add("main");
		all_declared.add("init");
		all_declared.add("<clinit>");
		HashSet<String> all_called = new HashSet<String>(all_declared);
		Tracer t = new Tracer(all_called, all_declared);
		ClassReader cr = null;
		for (String s: args) {
			//System.out.println(s);
			try {
				InputStream f = new FileInputStream(s);
				cr = new ClassReader(f);
				cr.accept(t, ClassReader.SKIP_DEBUG);
				//		dump_constant_pool(cr.b);
			} catch (Exception e) {
				e.printStackTrace();
			}
		}
		System.out.println("M: " + unused_methods(all_called, all_declared));
	}
}
