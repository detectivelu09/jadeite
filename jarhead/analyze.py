#!/usr/bin/python -tt
from __future__ import with_statement
import sys
import os
import subprocess
import re
import collections
import string
import tempfile
import cPickle

def read_file(filename):
    with open(filename) as f:
        return f.readlines()

def collect_instructions(line, instructions, pattern):
    match = pattern.search(line)
    if match:
        instructions.append(match.group(1))
            
def collect_functions(line, funcs, pattern):
    pattern = re.compile("(\S*? \S*?\(.*?\))")
    if (not ":" in line) and "(" in line:
            match = pattern.search(line)
            if match:
                funcs[match.group(1)] += 1
                return True
    return False
                        
def collect_classes(line, classes, pattern):
    pattern = re.compile("^(public final class|private final class|protected final class|final class|public class|private class|protected class|class) (\S.*)?(extends|implements|{)")
    match = pattern.search(line)
    if match:
        classes.append(match.group(2).strip())
        return True
    return False

def collect_strings(line, strings, pattern):
    pattern = re.compile("ldc.*?// *String (.*)$")
    match = pattern.search(line)
    if match:
        strings.append(match.group(1))
        return True
    return False
            
def collect_function_calls(line, func_calls, pattern):
    pattern = re.compile("invoke.*?//.*?(Method|InterfaceMethod).*?(\S.*)$")
    match = pattern.search(line)
    if match:
        func_calls[match.group(2)] += 1
        return True
    return False

def collect_extends(line, extends, pattern):
    #public class main extends javax.microedition.midlet.MIDlet implements javax.microedition.lcdui.CommandListener{
    pattern = re.compile("class.*?extends ([A-Za-z._$0-9,]*)")
    match = pattern.search(line)
    if match:
        for j in match.group(1).split(","):
            extends[j] += 1
        return True
    return False

def collect_instantiated_objects(line, objects, pattern):
    #new     #262; //class java/lang/RuntimeException
    pattern = re.compile("new.*?// *class (\S.*)$")
    match = pattern.search(line)
    if match:
        objects[match.group(1)] += 1
        return True
    return False

def collect_instantiated_object_arrays(line, objects, pattern):
    # anewarray       #9; //class java/lang/Class
    pattern = re.compile("anewarray.*?// *class (\S.*)$")
    match = pattern.search(line)
    if match:
        objects[match.group(1)] += 1
        return True
    return False

def collect_interfaces(line, interfaces, pattern):
    #public class sunos.Globales extends java.lang.Object implements java.security.PrivilegedExceptionAction{
    pattern = re.compile("class.*?implements (\S.*)? *{$")
    match = pattern.search(line)
    if match:
        for j in match.group(1).split(","):
            interfaces[j] += 1
        return True
    return False

def collect_casts(line, casts, pattern):
    pattern = re.compile("checkcast.*?// *class (\S.*)$")
    match = pattern.search(line)
    if match:
        casts[match.group(1)] += 1
        return True
    return False    

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
                                 
def uses_reflection_to_create_objects(func_calls):
    return func_calls['java/lang/reflect/Constructor.newInstance:([Ljava/lang/Object;)Ljava/lang/Object;']

def uses_reflection_to_call_methods(func_calls):
    return func_calls['java/lang/reflect/Method.invoke:(Ljava/lang/Object;[Ljava/lang/Object;)Ljava/lang/Object;']

def uses_reflection_to_set_fields(func_calls):
        return func_calls['java/lang/reflect/Field.set:(Ljava/lang/Object;Ljava/lang/Object;)V']

def check_midisoundbank(func_calls):
    if func_calls['javax/sound/midi/MidiSystem.getSoundbank:(Ljava/net/URL;)Ljavax/sound/midi/Soundbank;'] != 0:
        return True
    return False

def check_midisequencer(func_calls, implements):
    if implements['javax.sound.midi.ControllerEventListener'] != 0:
        if func_calls['javax/sound/midi/Sequencer.open:()V'] != 0:
            if func_calls['javax/sound/midi/Sequencer.setSequence:(Ljava/io/InputStream;)V'] != 0:
                if func_calls['javax/sound/midi/Sequencer.addControllerEventListener:(Ljavax/sound/midi/ControllerEventListener;[I)[I'] != 0:
                    return True
    return False

def check_rmi(func_calls):
    if func_calls['javax/management/remote/rmi/RMIConnectionImpl."<init>":(Ljavax/management/remote/rmi/RMIServerImpl;Ljava/lang/String;Ljava/lang/ClassLoader;Ljavax/security/auth/Subject;Ljava/util/Map;)V'] != 0:
        return True
    return False

def check_rhino(func_calls):
    if func_calls['javax/script/ScriptEngine.eval:(Ljava/lang/String;)Ljava/lang/Object;'] != 0:
        if func_calls['javax/script/ScriptEngine.get:(Ljava/lang/String;)Ljava/lang/Object;'] != 0:
            if func_calls['javax/swing/JList."<init>":([Ljava/lang/Object;)V'] != 0:
                if func_calls['add:(Ljava/awt/Component;)Ljava/awt/Component;'] != 0:
                    return True
    return False

def check_serialize(interfaces, extends):
    if interfaces['java.io.Serializable'] != 0:
        if interfaces['java.security.PrivilegedExceptionAction'] != 0:
            if extends['java.lang.ClassLoader'] != 0 or extends['java.security.SecureClassLoader'] != 0:
                return True
    return False

def check_execute(func_calls, instantiated_objects):
    exec_arg_options = ( "Ljava/lang/String;", "[Ljava/lang/String;", "[Ljava/lang/String;[Ljava/lang/String;", "[Ljava/lang/String;[Ljava/lang/String;Ljava/io/File;", "Ljava/lang/String;[Ljava/lang/String;", "Ljava/lang/String;[Ljava/lang/String;Ljava/io/File;")
    if uses_reflection_to_call_methods(func_calls):
        if func_calls['java/lang/Runtime.getRuntime:()Ljava/lang/Runtime;'] != 0 or func_calls['java/awt/Desktop.getDesktop:()Ljava/awt/Desktop;'] != 0:
            if instantiated_objects['java/net/URL'] != 0 or uses_reflection_to_create_objects(func_calls):
                return True
    if func_calls['java/net/URL.openConnection:()Ljava/net/URLConnection;'] != 0 or func_calls['java/net/URL.openStream:()Ljava/io/InputStream;'] != 0:
        for i in exec_arg_options:
            if func_calls['java/lang/Runtime.exec:('+i+')Ljava/lang/Process;'] != 0 or func_calls['java/lang/ProcessBuilder.start:()Ljava/lang/Process;'] != 0 or func_calls['java/awt/Desktop.open:(Ljava/io/File;)V'] != 0:
                return True
    return False

def check_sms(func_calls, extends, interfaces, instantiated_objects):
    if extends['javax.microedition.midlet.MIDlet'] != 0:
        if func_calls['javax/microedition/io/Connector.open:(Ljava/lang/String;)Ljavax/microedition/io/Connection;'] != 0:
            if func_calls['javax/wireless/messaging/MessageConnection.send:(Ljavax/wireless/messaging/Message;)V'] != 0:
        #        if interfaces['javax.microedition.lcdui.CommandListener'] != 0:
                    #if instantiated_objects['javax/microedition/lcdui/CommandListener'] != 0:
                        return True
    return False

def check_setdifficm(func_calls):
    if func_calls['java/awt/Graphics.drawImage:(Ljava/awt/Image;IILjava/awt/image/ImageObserver;)Z'] != 0:
        return True
    return False

def check_jlist(func_calls, extends, instantiated_objects):
    if extends['java.beans.Expression'] != 0:
        if instantiated_objects['java/util/HashSet'] != 0:
            if extends['java.util.HashMap'] != 0:
                if instantiated_objects['javax/swing/JList'] != 0:
                    return True
    return False

def check_atomic(extends, casts):
    if extends['java.lang.ClassLoader'] != 0 or extends['java.security.SecureClassLoader'] != 0:
        if casts['java/util/concurrent/atomic/AtomicReferenceArray'] != 0:
            return True
    return False

def check_findclass(func_calls):
    if func_calls['java/lang/Class.forName:(Ljava/lang/String;)Ljava/lang/Class;'] != 0:
        return True
    return False

def check_colorconvertopfilter(func_calls):
    if func_calls['java/awt/image/ColorConvertOp.filter:(Ljava/awt/image/BufferedImage;Ljava/awt/image/BufferedImage;)Ljava/awt/image/BufferedImage;'] != 0:
        return True
    return False
def check_sqldriver(interfaces, extends):
    if interfaces['java.sql.Driver'] != 0:
        for x in extends:
            pattern = re.compile("java\.util\..*?(Set|List)")
            if pattern.search(x):
                return True
    return False

def check_storeimagearray(func_calls, extends):
    if extends['java.awt.image.ColorModel'] != 0 or extends['java.awt.image.ComponentColorModel'] != 0:
        if func_calls['java/awt/image/AffineTransformOp.filter:(Ljava/awt/image/BufferedImage;Ljava/awt/image/BufferedImage;)Ljava/awt/image/BufferedImage;'] != 0:
            return True
    return False

def check_suntracing(casts, func_calls):
    if func_calls['com/sun/tracing/ProviderFactory.createProvider:(Ljava/lang/Class;)Lcom/sun/tracing/Provider;'] != 0:
        if casts['java/lang/invoke/MethodHandles$Lookup'] != 0 or func_calls['java/lang/invoke/MethodHandles$Lookup.findVirtual:(Ljava/lang/Class;Ljava/lang/String;Ljava/lang/invoke/MethodType;)Ljava/lang/invoke/MethodHandle;'] or func_calls['java/lang/invoke/MethodHandles$Lookup.findStatic:(Ljava/lang/Class;Ljava/lang/String;Ljava/lang/invoke/MethodType;)Ljava/lang/invoke/MethodHandle;']:
            return True
    return False

def check_mbeanserverintrospector(func_calls):
    if func_calls['com/sun/jmx/mbeanserver/Introspector.elementFromComplex:(Ljava/lang/Object;Ljava/lang/String;)Ljava/lang/Object;'] != 0:
        return True
    return False

def check_mbeaninstantiator(func_calls):
    if func_calls['com/sun/jmx/mbeanserver/MBeanInstantiator.findClass:(Ljava/lang/String;Ljava/lang/ClassLoader;)Ljava/lang/Class;'] != 0:
        return True
    return False

def check_alphacomposite(instantiated_objects, extends, funcs):
    if funcs['int getNumDataElements()'] != 0:
        if extends['java.awt.image.SampleModel'] != 0 or extends['java.awt.image.ComponentSampleModel'] != 0 or extends['java.awt.image.MultiPixelPackedSampleModel'] != 0 or extends['java.awt.image.SinglePixelPackedSampleModel'] != 0 or instantiated_objects['java/awt/AlphaComposite'] != 0:
            return True
    return False

def check_findstaticsetter(func_calls):
    if func_calls['java/lang/invoke/MethodHandles$Lookup.findStaticSetter:(Ljava/lang/Class;Ljava/lang/String;Ljava/lang/Class;)Ljava/lang/invoke/MethodHandle;'] != 0:
        return True
    return False

def check_lookupbytebi(extends, funcs):
    if extends['java.awt.image.BufferedImage'] != 0:
        if funcs['int getWidth()'] != 0 or funcs['int getHeight()'] != 0:
            return True
    return False

def check_alphacompositecompose(func_calls):
    if func_calls['java/awt/AlphaComposite.createContext:(Ljava/awt/image/ColorModel;Ljava/awt/image/ColorModel;Ljava/awt/RenderingHints;)Ljava/awt/CompositeContext;'] != 0:
        return True
    return False

def check_command_execute(func_calls):
    exec_arg_options = ( "Ljava/lang/String;", "[Ljava/lang/String;", "[Ljava/lang/String;[Ljava/lang/String;", "[Ljava/lang/String;[Ljava/lang/String;Ljava/io/File;", "Ljava/lang/String;[Ljava/lang/String;", "Ljava/lang/String;[Ljava/lang/String;Ljava/io/File;")
    if func_calls['java/lang/ProcessBuilder.start:()Ljava/lang/Process;'] != 0 or func_calls['java/awt/Desktop.open:(Ljava/io/File;)V'] != 0:
        return True
    for i in exec_arg_options:
        if func_calls['java/lang/Runtime.exec:('+i+')Ljava/lang/Process;'] != 0:
            return True
    return False    
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

def appletanalysis(func_calls, instantiated_objects, interfaces, extends, casts, funcs):
    found = ""
    found_cve = ""
    bin_features = ""
    if check_midisoundbank(func_calls):
        found += "MIDISOUNDBANK "
        found_cve = "CVE-2009-3867 "
        bin_features +="1,"
    else:
        bin_features  +="0,"
    if check_midisequencer(func_calls, interfaces):
        found += "MIDISEQUENCER "
        found_cve = "CVE-2010-0842 "
        bin_features +="1,"
    else:
        bin_features  +="0,"
    if check_rmi(func_calls):
        found += "RMI "
        found_cve += "CVE-2010-0094 "
        bin_features +="1,"
    else:
        bin_features  +="0,"
    if check_serialize(interfaces, extends):
        found += "SERIALIZE "
        found_cve += "CVE-2008-5353 "
        bin_features +="1,"
    else:
        bin_features  +="0,"
    if check_rhino(func_calls):
        found += "RHINO "
        found_cve += "CVE-2011-3544 "
        bin_features +="1,"
    else:
        bin_features  +="0,"
    if check_sms(func_calls, extends, interfaces, instantiated_objects):
        found += "SMS "
        found_cve += "CVE-2004-2626 "
        bin_features +="1,"
    else:
        bin_features  +="0,"
    if check_atomic(extends, casts):
        found += "ATOMIC "
        found_cve += "CVE-2012-0507 "
        bin_features +="1,"
    else:
        bin_features  +="0,"
    if check_jlist(func_calls, extends, instantiated_objects):
        found += "JLIST "
        found_cve += "CVE-2010-0840 "
        bin_features +="1,"
    else:
        bin_features  +="0,"
#    if check_findclass(func_calls):
#        found += "FINDCLASS "
#        found_cve += "CVE-2012-4681"
    if check_colorconvertopfilter(func_calls):
        found += "COLORCONVERTOPFILTER "
        found_cve += "CVE-2013-1493 "
        bin_features +="1,"
    else:
        bin_features  +="0,"
    if check_sqldriver(interfaces, extends):
        found += "SQLDRIVER "
        found_cve += "CVE-2013-1488 "
        bin_features +="1,"
    else:
        bin_features  +="0,"
    if check_storeimagearray(func_calls, extends):
        found += "STOREIMAGEARRAY "
        found_cve += "CVE-2013-2465 "
        bin_features +="1,"
    else:
        bin_features  +="0,"
    if check_suntracing(casts, func_calls):
        found += "SUNTRACING "
        found_cve += "CVE-2013-2460 "
        bin_features +="1,"
    else:
        bin_features  +="0,"
    if check_mbeanserverintrospector(func_calls):
        found += "MBEANSERVERINTROSPECTOR "
        found_cve += "CVE-2013-0431 "
        bin_features +="1,"
    else:
        bin_features  +="0,"
    if check_mbeaninstantiator(func_calls):
        found += "MBEANINSTANTIATOR "
        found_cve += "CVE-2013-0422 "
        bin_features +="1,"
    else:
        bin_features  +="0,"
    if check_alphacomposite(instantiated_objects, extends, funcs):
        found += "ALPHACOMPOSITE "
        found_cve += "CVE-2013-2471 "
        bin_features +="1,"
    else:
        bin_features  +="0,"
    if check_findstaticsetter(func_calls):
        found += "FINDSTATICSETTER "
        found_cve += "CVE-2013-2423 "
        bin_features +="1,"
    else:
        bin_features  +="0,"
    if check_lookupbytebi(extends, funcs):
        found += "LOOKUPBYTEBI "
        found_cve += "CVE-2013-2470 "
        bin_features +="1,"
    else:
        bin_features  +="0,"
    if check_alphacompositecompose(func_calls):
        found += "ALPHACOMPOSITECOMPOSE "
        found_cve += "CVE-2013-2463"
        bin_features +="1,"
    else:
        bin_features  +="0,"
    #if check_setdifficm(func_calls):
    #    found += "AWTDIM "
    if check_execute(func_calls, instantiated_objects):
        found += "EXECUTE "
        found_cve += "EXECUTE "
        bin_features +="1,"
    else:
        bin_features  +="0,"

    if found:
        bin_features +="1"

        z= open("/home/iobaidat/jarhead/bin_attr.csv","a")
        z.write(bin_features)
        z.close()

        if os.path.exists("nocve"):
            return "malicious" + found
        else:
            return "malicious " + found_cve
    else:
        bin_features +="0"

        z= open("/home/iobaidat/jarhead/bin_attr.csv","a")
        z.write(bin_features)
        z.close()

        return False

def jarhead(func_calls, instantiated_objects, interfaces, extends, instantiated_object_arrays, classes, strings, instructions, n_functions, line_cnt):
    name = sys.argv[1]
    #if not contains_applet(extends):
        #print("ERROR:" + name + " did not contain an applet")
        #return
    arff_line = ""
    arff_line += str(get_byte_size(name))
    #FIXME print all other attributes here in order
    arff_line += "," + str(line_cnt)
    arff_line += "," + str(len(classes))
    arff_line += "," + str(check_command_execute(func_calls))
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
    arff_line += "," + str(len(instructions))
    arff_line += "," + str(get_parameters(func_calls))
    arff_line += "," + str(get_runtime(func_calls))
    arff_line += ",malicious"
    print("@relation xxx")
    print_attrs()
    print("@data")
    print(arff_line)


def main():
    name = sys.argv[1]
    func_calls = collections.defaultdict(int)
    instantiated_objects = collections.defaultdict(int)
    interfaces = collections.defaultdict(int)
    extends = collections.defaultdict(int)
    instantiated_object_arrays = collections.defaultdict(int)
    casts = collections.defaultdict(int)
    funcs = collections.defaultdict(int)
    classes = []
    strings = []
    instructions = []
    n_functions = 0
    line_cnt = 0
    instructions_pattern = re.compile("^ *\d+:\t(\S.*)")
    functions_pattern = re.compile("(\S*? \S*?\(.*?\))")
    classes_pattern = re.compile("^(public final class|private final class|protected final class|final class|public class|private class|protected class|class) (\S.*)?(extends|implements|{)")
    strings_pattern = re.compile("ldc.*?// *String (.*)$")
    function_calls_pattern = re.compile("invoke.*?//.*?(Method|InterfaceMethod).*?(\S.*)$")
    extends_pattern = re.compile("class.*?extends ([A-Za-z._$0-9,]*)")
    instantiated_objects_pattern = re.compile("new.*?// *class (\S.*)$")
    instantiated_object_arrays_pattern = re.compile("anewarray.*?// *class (\S.*)$")
    interfaces_pattern = re.compile("class.*?implements (\S.*)? *{$")
    casts_pattern = re.compile("checkcast.*?// *class (\S.*)$")

    for i in sys.argv[3:]:
        lines = read_file(i)
        line_cnt += len(lines)
        for line in lines:
            collect_instructions(line, instructions, instructions_pattern)
            if collect_function_calls(line, func_calls, function_calls_pattern):
                continue
            if collect_classes(line, classes, classes_pattern):
                collect_extends(line, extends, extends_pattern)
                collect_interfaces(line, interfaces, interfaces_pattern)
                continue
            if collect_instantiated_objects(line, instantiated_objects, instantiated_objects_pattern):
                continue
            if collect_instantiated_object_arrays(line, instantiated_object_arrays, instantiated_object_arrays_pattern):
                continue
            if collect_strings(line, strings, strings_pattern):
                continue
            if collect_casts(line, casts, casts_pattern):
                continue
            if collect_functions(line, funcs, functions_pattern):
                n_functions += 1

    f = open("../func_calls.pik", "wb")
    cPickle.dump(func_calls, f)
    f.close()
    f = open("../instantiated_objects.pik", "wb")
    cPickle.dump(instantiated_objects, f)
    f.close()
    f = open("../interfaces.pik", "wb")
    cPickle.dump(interfaces, f)
    f.close()
    f = open("../extends.pik", "wb")
    cPickle.dump(extends, f)
    f.close()
    f = open("../casts.pik", "wb")
    cPickle.dump(casts, f)
    f.close()
    f = open("../funcs.pik", "wb")
    cPickle.dump(funcs, f)
    f.close()

    if len(classes) == 0:
        print("ERROR:" + name + " did not contain classes")
        return

    result = appletanalysis(func_calls, instantiated_objects, interfaces, extends, casts, funcs)
    if result:
        print(result)
    else:
        #print("benign")
        jarhead(func_calls, instantiated_objects, interfaces, extends, instantiated_object_arrays, classes, strings, instructions, n_functions, line_cnt)
        
if __name__ == '__main__':
    main()