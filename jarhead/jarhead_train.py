#!/usr/bin/python -tt
from __future__ import with_statement
import sys
import os
import subprocess
import re
import collections
import string
import tempfile

def read_file(filename):
	with open(filename) as f:
		return f.readlines()

def collect_classes(lines, classes):
	pattern = re.compile("^(public final class|private final class|protected final class|final class|public class|private class|protected class|class) (\S.*)?(extends|implements|{)")
	for i in lines:
		match = pattern.search(i)
		if match:
			classes.append(match.group(2).strip())

def collect_strings(lines, strings):
	pattern = re.compile("ldc.*?// *String (.*)$")
	for i in lines:
		match = pattern.search(i)
		if match:
			strings.append(match.group(1))

def collect_instructions(lines, instructions):
	pattern = re.compile("^   \d+:\t(\S.*)")
	for i in lines:
		match = pattern.search(i)
		if match:
			instructions.append(match.group(1))

def count_functions(lines):
	cnt = 0
	pattern = re.compile("^  Code:$")
	for i in lines:
		match = pattern.search(i)
		if match:
			cnt += 1
	return cnt

def collect_function_calls(lines, func_calls):
	pattern = re.compile("invoke.*?//.*?(Method|InterfaceMethod).*?(\S.*)$")
	for i in lines:
		match = pattern.search(i)
		if match:
			func_calls[match.group(2)] += 1

def collect_extends(lines, extends):
	#public class main extends javax.microedition.midlet.MIDlet implements javax.microedition.lcdui.CommandListener{
	pattern = re.compile("class.*?extends ([A-Za-z._$0-9,]*)")
	for i in lines:
		match = pattern.search(i)
		if match:
			for j in match.group(1).split(","):
				extends[j] += 1

def collect_instantiated_objects(lines, objects):
	#new     #262; //class java/lang/RuntimeException
	pattern = re.compile("new.*?// *class (\S.*)$")
	for i in lines:
		match = pattern.search(i)
		if match:
			objects[match.group(1)] += 1

def collect_instantiated_object_arrays(lines, objects):
	# anewarray       #9; //class java/lang/Class
	pattern = re.compile("anewarray.*?// *class (\S.*)$")
	for i in lines:
		match = pattern.search(i)
		if match:
			objects[match.group(1)] += 1

def collect_interfaces(lines, interfaces):
	#public class sunos.Globales extends java.lang.Object implements java.security.PrivilegedExceptionAction{
	pattern = re.compile("class.*?implements (\S.*)? *{$")
	for i in lines:
		match = pattern.search(i)
		if match:
			for j in match.group(1).split(","):
				interfaces[j] += 1

def check_script_engine_eval(func_calls):
	if func_calls['javax/script/ScriptEngine.eval:(Ljava/lang/String;)Ljava/lang/Object;'] != 0:
		return True
	if func_calls['javax/script/ScriptEngine.eval:(Ljava/io/Reader;)Ljava/lang/Object;'] != 0:
		return True
	if func_calls['javax/script/ScriptEngine.eval:(Ljava/io/Reader;Ljavax/script/Bindings;)Ljava/lang/Object;'] != 0:
		return True
	if func_calls['javax/script/ScriptEngine.eval:(Ljava/io/Reader;Ljavax/script/ScriptContext;)Ljava/lang/Object;'] != 0:
		return True
	if func_calls['javax/script/ScriptEngine.eval:(Ljava/lang/String;Ljavax/script/Bindings;)Ljava/lang/Object;'] != 0:
		return True
	if func_calls['javax/script/ScriptEngine.eval:(Ljava/lang/String;Ljavax/script/ScriptContext;)Ljava/lang/Object;'] != 0:
		return True
	return False

def check_script_engine_get_put(func_calls):
	if func_calls['javax/script/ScriptEngine.get:(Ljava/lang/String;)Ljava/lang/Object;'] != 0:
		return True
	if func_calls['javax/script/ScriptEngine.put:(Ljava/lang/String;Ljava/lang/Object;)V'] != 0:
		return True
	return False

def calls_vulnerable_draw_function(func_calls):#if we make this a vulnerable function it messes everything up
	if func_calls['java/awt/Graphics.drawImage:(Ljava/awt/Image;IILjava/awt/image/ImageObserver;)Z'] != 0:
		return True
	return False

def implements_vulnerable_mbeanserver(interfaces):
	if interfaces['javax.management.MBeanServer'] != 0:
		return True
	return False

def check_implements_serializable(interfaces):
	if interfaces['java.io.Serializable'] != 0:
		return True
	return False

def check_sms_send(func_calls):
	if func_calls['javax/wireless/messaging/MessageConnection.send:(Ljavax/wireless/messaging/Message;)V'] != 0:
		return True
	return False

def check_execute(func_calls):

	exec_arg_options = ( "Ljava/lang/String;", "[Ljava/lang/String;", "[Ljava/lang/String;[Ljava/lang/String;", "[Ljava/lang/String;[Ljava/lang/String;Ljava/io/File;", "Ljava/lang/String;[Ljava/lang/String;", "Ljava/lang/String;[Ljava/lang/String;Ljava/io/File;")
	if func_calls['java/lang/ProcessBuilder.start:()Ljava/lang/Process;'] != 0 or func_calls['java/awt/Desktop.open:(Ljava/io/File;)V'] != 0:
		return True
	for i in exec_arg_options:
		if func_calls['java/lang/Runtime.exec:('+i+')Ljava/lang/Process;'] != 0:
			return True
	return False

def uses_reflection_to_create_objects(func_calls):
	return func_calls['java/lang/reflect/Constructor.newInstance:([Ljava/lang/Object;)Ljava/lang/Object;']

def uses_reflection_to_call_methods(func_calls):
	return func_calls['java/lang/reflect/Method.invoke:(Ljava/lang/Object;[Ljava/lang/Object;)Ljava/lang/Object;']

def uses_reflection_to_set_fields(func_calls):
        return func_calls['java/lang/reflect/Field.set:(Ljava/lang/Object;Ljava/lang/Object;)V']

def uses_expression(func_calls):
	return func_calls['java/beans/Expression.execute:()V']

def uses_statement(func_calls):
	return func_calls['java/beans/Statement.execute:()V']

def uses_method_lookup(func_calls):
	return func_calls['java/lang/invoke/MethodHandles$Lookup.findVirtual:(Ljava/lang/Class;Ljava/lang/String;Ljava/lang/invoke/MethodType;)Ljava/lang/invoke/MethodHandle;'] + func_calls['java/lang/invoke/MethodHandles$Lookup.findStatic:(Ljava/lang/Class;Ljava/lang/String;Ljava/lang/invoke/MethodType;)Ljava/lang/invoke/MethodHandle;'] + func_calls['java/lang/Class.getMethod:(Ljava/lang/String;[Ljava/lang/Class;)Ljava/lang/reflect/Method;']

def uses_class_finder(func_calls):
	return func_calls['java/lang/Class.forName:(Ljava/lang/String;)Ljava/lang/Class;']

def instantiates_protection_domain(instantiated_objects):
	if instantiated_objects['java/security/ProtectionDomain'] != 0:
		return True
	return False

def instantiates_certificate(instantiated_objects):
	if instantiated_objects['java/security/cert/Certificate'] != 0:
		return True
	return False

def uses_do_privileged(func_calls):
	if func_calls['java/security/AccessController.doPrivileged:(Ljava/security/PrivilegedExceptionAction;)Ljava/lang/Object;'] != 0:
		return True
	return False

def appends_strings(func_calls):
	return func_calls['java/lang/StringBuilder.append:(Ljava/lang/String;)Ljava/lang/StringBuilder;']

def get_byte_size(path):
	return os.path.getsize(path)

def uses_sockets(instantiated_objects, func_calls):
	if instantiated_objects['java/net/Socket'] != 0:
		return True
	if instantiated_objects['java/net/SSLSocket'] != 0:
		return True
	if instantiated_objects['java/net/ServerSocket'] != 0:
		return True
	if instantiated_objects['javax/microedition/io/Connector'] != 0:
		return True
	if func_calls['javax/microedition/io/Connector.open:(Ljava/lang/String;)Ljavax/microedition/io/Connection;'] != 0:
		return True
	if  func_calls['javax/microedition/io/Connector.open:(Ljava/lang/String;I)Ljavax/microedition/io/Connection;'] != 0:
		return True
	if func_calls['javax/microedition/io/Connector.open:(Ljava/lang/String;IZ)Ljavax/microedition/io/Connection;'] != 0:
		return True
	return False

def uses_files(instantiated_objects):
	if instantiated_objects['java/io/File'] != 0:
		return True
	return False

def get_external_results(path):
	result_file, result_filename = tempfile.mkstemp()
	subprocess.call([sys.argv[2]+"/tracer_run.sh", path, sys.argv[2], result_filename], 
        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	with open(result_filename) as f:
		output = f.readlines()
	os.remove(result_filename)
	total = 0.0
	cnt = 0
	methods = 0.0
	mimes = collections.defaultdict(int)
	executables = 0
	mccabe = []
	func_sizes = []
	pattern = re.compile("(\d+),(\d+)")
	for i in output:
		if (i.startswith("V:")):
			total += float(i.split(':')[1])
			cnt += 1
		elif (i.startswith("M:")):
			methods = float(i.split(':')[1])
		elif (i.startswith("MIME:")):
			mimes[i.split(":")[1]] += 1
		elif (i.startswith("EXECUTABLE")):
			executables += 1
		elif (i.startswith("METRIC:")):
			for match in re.finditer(pattern, i):
				mccabe.append(int(match.group(1)))
				func_sizes.append(int(match.group(2)))
	if cnt != 0:
		return (mccabe, func_sizes, mimes, str(methods) + "," + str(total / float(cnt)), executables)
	else:
		return (mccabe, func_sizes, mimes, str(methods) + "," + str(0.0), executables)

def instantiates_url(objects):
	if objects['java/net/URL'] != 0:
		return True
	return False

def touch_system_security_manager(func_calls):
	if func_calls['java/lang/System.getSecurityManager:()Ljava/lang/SecurityManager;'] != 0:
		return True
	if func_calls['java/lang/System.setSecurityManager:(Ljava/lang/SecurityManager;)V'] != 0:
		return True
	return False

def touch_system_property(func_calls):
	if func_calls['java/lang/System.getProperties:()Ljava/util/Properties;'] != 0:
		return True
	if func_calls['java/lang/System.getProperty:(Ljava/lang/String;)Ljava/lang/String;'] != 0:
		return True
	if func_calls['java/lang/System.getProperty:(Ljava/lang/String;Ljava/lang.String;)Ljava/lang/String;'] != 0:
		return True
	if func_calls['java/lang/System.setProperty:(Ljava/lang/String;Ljava/lang.String;)Ljava/lang/String;'] != 0:
		return True
	if func_calls['java/lang/System.setProperties:(Ljava/util/Properties;)V'] != 0:
		return True
	return False

def uses_file_outputstream(instantiated_objects):
	if instantiated_objects['java/io/FileOutputStream'] != 0:
		return True
	return False

def count_mimes(mimes):
	if len(mimes.values()) != 0:
		return reduce(lambda x, y: x + y, mimes.values())
	else:
		return 0

def mccabe_per_length_avg(mccabe, length):
	vals = map(lambda x, y: y != 0 and x / float(y) or 0.0, mccabe, length)
	if len(mccabe) != 0:
		return reduce(lambda x, y: x + y, vals) / float(len(mccabe))
	else:
		return 0.0

def calls_vulnerable_get_soundbank(func_calls):
	if func_calls['javax/sound/midi/MidiSystem.getSoundbank:(Ljava/net/URL;)Ljavax/sound/midi/Soundbank;'] != 0:
		return True
	return False

def calls_vulnerable_rmiconnectionimpl(func_calls):
	if func_calls['javax/management/remote/rmi/RMIConnectionImpl."<init>":(Ljavax/management/remote/rmi/RMIServerImpl;Ljava/lang/String;Ljava/lang/ClassLoader;Ljavax/security/auth/Subject;Ljava/util/Map;)V'] != 0:
		return True
	return False

def calls_vulnerable_getsequencer(func_calls):
	if func_calls['javax/sound/midi/MidiSystem.getSequencer:()Ljavax/sound/midi/Sequencer;'] != 0:
		return True
	if func_calls['javax/sound/midi/Sequencer.addControllerEventListener:(Ljavax/sound/midi/ControllerEventListener;[I)[I'] != 0:
		return True
	return False

def extends_class_loader(extends):
	if extends['java.lang.ClassLoader'] != 0:
		return True
	if extends['java.security.SecureClassLoader'] != 0:
		return True
	return False

def implements_class_loader_repo(implements):
	if implements['javax.management.loading.ClassLoaderRepository'] != 0:
		return True
	return False

def extends_security_policy(extends):
	if extends['java.security.Policy'] != 0:
		return True
	return False

def get_longest_string_len(strings):
	m = 0
	for i in strings:
		if len(i) > m:
			m = len(i)
	return m

def get_shortest_string_len(strings):
	if (len(strings) == 0):
		return 0
	m = 10000000
	for i in strings:
		if len(i) < m:
			m = len(i)
	return m

def get_average_string_len(strings):
	if len(strings) == 0:
		return 0.0
	return float(reduce(lambda x, y: x + y, map(len, strings))) / float(len(strings))

def frac_non_printable_strings(strings):
	if len(strings) == 0:
		return 0.0
	non_printable = 0
	for i in strings:
		if not all(c in string.printable for c in i):
			non_printable += 1
	return float(non_printable) / float(len(strings))

def implements_privileged_action(implements):
	if implements['java.security.PrivilegedAction'] != 0:
		return True
	if implements['java.security.PrivilegedExceptionAction'] != 0:
		return True
	return False

def get_parameters(func_calls):
	if func_calls['java/applet/Applet.getParameter:(Ljava/lang/String;)Ljava/lang/String;'] != 0:
		return True
	return False

def get_runtime(func_calls):
	if func_calls['java/lang/Runtime.getRuntime:()Ljava/lang/Runtime;'] != 0:
		return True
	return False

def uses_system_load(functions):
	if functions['java/lang/System.load:(Ljava/lang/String;)V']:
		return True
	if functions['java/lang/System.loadLibrary:(Ljava/lang/String;)V']:
		return True
	if functions['java/lang/System.mapLibraryName:(Ljava/lang/String;)Ljava/lang/String;']:
		return True
	return False

def instantiate_bare_class(arrs, instantiated_objects):
	if arrs['java/lang/Class'] != 0:
		return True
	if instantiated_objects['java/lang/Class'] != 0:
		return True
	return False

def instantiate_bare_object(arrs, instantiated_objects):
	if arrs['java/lang/Object'] != 0:
		return True
	if instantiated_objects['java/lang/Object'] != 0:
		return True
	return False

def print_attrs():
	print("@attribute bytesize integer")
	print("@attribute lines_of_disassembly integer")
	print("@attribute number_of_classes integer")
	print("@attribute execute {True, False}")
	print("@attribute instantiates_bare_class {True, False}")
	print("@attribute instantiates_bare_object {True, False}")
	print("@attribute uses_system_load {True, False}")
	print("@attribute vulnerable_get_soundbank {True, False}")
	print("@attribute vulnerable_rmiconnectionimpl {True, False}")
	print("@attribute vulnerable_getsequencer {True, False}")
	print("@attribute reflect_new integer")
	print("@attribute reflect_call integer")
	print("@attribute reflect_set integer")
	print("@attribute expression integer")
	print("@attribute statement integer")
	print("@attribute method_lookup integer")
	print("@attribute class_finder integer")
	print("@attribute script_language_eval {True, False}")
	print("@attribute script_language_get_put {True, False}")
	print("@attribute sms_send {True, False}")
	print("@attribute implements_serializable {True, False}")
	print("@attribute unused_methods real")
	print("@attribute unused_variables real")
	print("@attribute instantiates_url {True, False}")
	print("@attribute number_of_functions_per_class real")
	print("@attribute has_executables {True, False}")
	print("@attribute uses_socket {True, False}")
	print("@attribute uses_files {True, False}")
	print("@attribute uses_file_outputstream {True, False}")
	print("@attribute touch_system_security_manager {True, False}")
	print("@attribute touch_system_property {True, False}")
	print("@attribute implements_class_loader_repo {True, False}")
	print("@attribute extends_class_loader {True, False}")
	print("@attribute extends_security_policy {True, False}")
	print("@attribute implements_privileged_action {True, False}")
	print("@attribute implements_vulnerable_mbeanserver {True, False}")
	print("@attribute instantiates_protection_domain {True, False}")
	print("@attribute instantiates_certificate {True, False}")
	print("@attribute uses_do_privileged {True, False}")
	print("@attribute number_of_mimes integer")
	print("@attribute mccabe_complexity_per_instruction_avg real")
	print("@attribute longest_string integer")
	print("@attribute shortest_string integer")
	print("@attribute avg_string real")
	print("@attribute non_printable_strings_frac real")
	print("@attribute no_of_strings integer")
	#print("@attribute no_of_appends integer")
	print("@attribute no_of_instructions integer")
	print("@attribute gets_parameters {True, False}")
	print("@attribute gets_runtime {True, False}")
	print("@attribute result {malicious, benign}")

def contains_applet(extends):
	if extends['java.applet.Applet'] != 0:
		return True
	if extends['javax.swing.JApplet'] != 0:
		return True
	if extends['javax.microedition.midlet.MIDlet'] != 0:
		return True
	return False

def main():
	name = sys.argv[1]
	func_calls = collections.defaultdict(int)
	instantiated_objects = collections.defaultdict(int)
	interfaces = collections.defaultdict(int)
	extends = collections.defaultdict(int)
	instantiated_object_arrays = collections.defaultdict(int)
	classes = []
	strings = []
	instructions = []
	n_functions = 0
	line_cnt = 0
	for i in sys.argv[3:]:
		lines = read_file(i)
		line_cnt += len(lines)
		collect_function_calls(lines, func_calls)
		collect_interfaces(lines, interfaces)
		collect_extends(lines, extends)
		collect_instantiated_objects(lines, instantiated_objects)
		collect_classes(lines, classes)
		collect_instantiated_object_arrays(lines, instantiated_object_arrays)
		collect_strings(lines, strings)
		collect_instructions(lines, instructions)
		n_functions += count_functions(lines)
	if len(classes) == 0:
		#print("ERROR:" + name + " did not contain classes")
		return
	if not contains_applet(extends):
		#print("ERROR:" + name + " did not contain an applet")
		return
	arff_line = ""
	arff_line += str(get_byte_size(name))
	#FIXME print all other attributes here in order
	arff_line += "," + str(line_cnt)
	arff_line += "," + str(len(classes))
	arff_line += "," + str(check_execute(func_calls))
	arff_line += "," + str(instantiate_bare_class(instantiated_object_arrays, instantiated_objects))
	arff_line += "," + str(instantiate_bare_object(instantiated_object_arrays, instantiated_objects))
	arff_line += "," + str(uses_system_load(func_calls))
	arff_line += "," + str(calls_vulnerable_get_soundbank(func_calls))
	arff_line += "," + str(calls_vulnerable_rmiconnectionimpl(func_calls))
	arff_line += "," + str(calls_vulnerable_getsequencer(func_calls))
	arff_line += "," + str(uses_reflection_to_create_objects(func_calls))
	arff_line += "," + str(uses_reflection_to_call_methods(func_calls))
	arff_line += "," + str(uses_reflection_to_set_fields(func_calls))
	arff_line += "," + str(uses_expression(func_calls))
	arff_line += "," + str(uses_statement(func_calls))
	arff_line += "," + str(uses_method_lookup(func_calls))
	arff_line += "," + str(uses_class_finder(func_calls))
	arff_line += "," + str(check_script_engine_eval(func_calls))
	arff_line += "," + str(check_script_engine_get_put(func_calls))
	arff_line += "," + str(check_sms_send(func_calls))
	arff_line += "," + str(check_implements_serializable(interfaces))
	(mccabe, funcsizes, mimes, unused_v_f, executables) = get_external_results(name)
	arff_line += "," + unused_v_f
	arff_line += "," + str(instantiates_url(instantiated_objects))
	if len(classes) != 0:
		arff_line += "," + str(float(n_functions) / float(len(classes)))
	else:
		arff_line += "," + str(float(n_functions))
	if executables > 0:
		arff_line += "," + str(True)
	else:
		arff_line += "," + str(False)
	arff_line += "," + str(uses_sockets(instantiated_objects, func_calls))
	arff_line += "," + str(uses_files(instantiated_objects))
	arff_line += "," + str(uses_file_outputstream(instantiated_objects))
	arff_line += "," + str(touch_system_security_manager(func_calls))
	arff_line += "," + str(touch_system_property(func_calls))
	arff_line += "," + str(implements_class_loader_repo(interfaces))
	arff_line += "," + str(extends_class_loader(extends))
	arff_line += "," + str(extends_security_policy(interfaces))
	arff_line += "," + str(implements_privileged_action(interfaces))
	arff_line += "," + str(implements_vulnerable_mbeanserver(interfaces))
	arff_line += "," + str(instantiates_protection_domain(instantiated_objects))
	arff_line += "," + str(instantiates_certificate(instantiated_objects))
	arff_line += "," + str(uses_do_privileged(func_calls))
	arff_line += "," + str(count_mimes(mimes))
	arff_line += "," + str(mccabe_per_length_avg(mccabe, funcsizes))
	arff_line += "," + str(get_longest_string_len(strings))
	arff_line += "," + str(get_shortest_string_len(strings))
	arff_line += "," + str(get_average_string_len(strings))
	arff_line += "," + str(frac_non_printable_strings(strings))
	arff_line += "," + str(len(strings))
	#arff_line += "," + str(appends_strings(func_calls))
	arff_line += "," + str(len(instructions))
	arff_line += "," + str(get_parameters(func_calls))
	arff_line += "," + str(get_runtime(func_calls))
	arff_line += ",benign"
	#print("@relation xxx")
	#print_attrs()
	#print("@data")
	print(arff_line)

if __name__ == '__main__':
	main()
