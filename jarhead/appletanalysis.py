#!/usr/bin/python -tt
from __future__ import with_statement
import sys
import os
import re
import collections

def read_file(filename):
    with open(filename) as f:
        return f.readlines()

def collect_function_calls(lines, func_calls):
    pattern = re.compile("invoke.*?//.*?(Method|InterfaceMethod).*?(\S.*)$")
    for i in lines:
        match = pattern.search(i)
        if match:
            func_calls[match.group(2)] += 1

def collect_casts(lines, casts):
    pattern = re.compile("checkcast.*?// *class (\S.*)$")
    for i in lines:
        match = pattern.search(i)
        if match:
            casts[match.group(1)] += 1

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
    pattern = re.compile("new.*?//class (\S.*)$")
    for i in lines:
        match = pattern.search(i)
        if match:
            objects[match.group(1)] += 1

def collect_interfaces(lines, interfaces):
    #public class sunos.Globales extends java.lang.Object implements java.security.PrivilegedExceptionAction{
    pattern = re.compile("class.*?implements (\S.*?) *{$")
    for i in lines:
        match = pattern.search(i)
        if match:
            for j in match.group(1).split(","):
                interfaces[j] += 1

def collect_functions(lines, funcs):
    pattern = re.compile("(\S*? \S*?\(.*?\))")
    for i in lines:
        if (not ":" in i) and "(" in i:
                match = pattern.search(i)
                if match:
                        funcs[match.group(1)] += 1

def uses_reflection_to_create_objects(func_calls):
    if func_calls['java/lang/reflect/Constructor.newInstance:([Ljava/lang/Object;)Ljava/lang/Object;'] != 0:
        return True
    return False

def uses_reflection_to_call_methods(func_calls):
    if func_calls['java/lang/reflect/Method.invoke:(Ljava/lang/Object;[Ljava/lang/Object;)Ljava/lang/Object;'] != 0:
        return True
    return False

def uses_reflection_to_set_fields(func_calls):
    if func_calls['java/lang/reflect/Field.set:(Ljava/lang/Object;Ljava/lang/Object;)V'] != 0:
        return True
    return False

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

def main():
    found = ""
    found_cve = ""
    bin_features = ""
    func_calls = collections.defaultdict(int)
    instantiated_objects = collections.defaultdict(int)
    interfaces = collections.defaultdict(int)
    extends = collections.defaultdict(int)
    casts = collections.defaultdict(int)
    funcs = collections.defaultdict(int)
    for i in sys.argv[2:]:
        lines = read_file(i)
        collect_function_calls(lines, func_calls)
        collect_interfaces(lines, interfaces)
        collect_extends(lines, extends)
        collect_instantiated_objects(lines, instantiated_objects)
        collect_casts(lines, casts)
        collect_functions(lines, funcs)
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
        if os.path.exists("nocve"):
            print sys.argv[1] + "malicious" + found
        else:
            print "malicious " + found_cve
    else:
        bin_features +="0"
        print "benign"
    if uses_reflection_to_create_objects(func_calls) or uses_reflection_to_call_methods(func_calls) or uses_reflection_to_set_fields(func_calls):
        print "reflection"

    with open("bin_attr.csv", "a") as myfile:
        print (bin_features)
        myfile.write(bin_features)
        myfile.close()

if __name__ == '__main__':
    main()
