#!/bin/bash

if test $# -ne 3; then
    echo "Usage: $0 APPLET BASE_DIRECTORY OUTPUT"
    exit 1
fi

CURR=$2
TRACER_LIBS="$CURR/deps/asm-3.3.1.jar:$CURR/deps/asm-analysis-3.3.1.jar:$CURR/deps/asm-commons-3.3.1.jar:$CURR/deps/asm-tree-3.3.1.jar:$CURR/src/java/jarhead-tracer.jar"
CYVIS_LIBS="$CURR/deps/cyvis-0.9.jar"

applet=$1
if [ "${applet##*.}" == "jar" ]; then
        extension=.jar
elif  [ "${applet##*.}" == "class" ]; then
        extension=.class
else
    echo "--ERROR--" $applet
    extension=.jar
#    exit 2
fi
# if [[ $applet =~ \.jar$ ]]; then
#         extension=.jar
# elif [[ $applet =~ \.class$ ]]; then
#         extension=.class
# else
#     echo "--ERROR--" $applet
#     #extension = .jar
#     exit 2
# fi
output="$3"
mkdir temp
TMPDIR=`pwd`/temp
#echo "$TMPDIR" > ~/Desktop/wtf
# unzip the applet, if jar
cd $TMPDIR
cp $applet .
if [ "$extension" != ".class" ]; then
    (echo "A" | unzip $applet 2>&1 >> /dev/null)
fi
chmod -R 755 *
cd - > /dev/null

# analyze classes:
# - tracer
# - mime
# - executables
#echo "java -cp $TRACER_LIBS wepawetng.jarhead.tracer.Tracer" > ~/Desktop/wtf
(find $TMPDIR -name '*.class' | xargs java -cp $TRACER_LIBS wepawetng.jarhead.tracer.Tracer ) | grep -v ^fcall > $output
find $TMPDIR -type f -not -name '*.class' | grep -v '.jar$'| grep -v 'META-INF' | xargs file -b -i | cut -d';' -f 1 | while read mime; do echo MIME: $mime;done >> $output
find $TMPDIR -type f -not -name '*.class' | grep -v '.jar$'| grep -v 'META-INF' | xargs file | grep -i "executable"| while read mime; do echo EXECUTABLE;done >> $output
# analyze classes:
# - metrics
TMPFILE=`mktemp`
java -jar $CYVIS_LIBS -p $applet -t $TMPFILE
cat $TMPFILE.txt >> $output
cat $TMPFILE.txt | while read line; do 
    echo METRIC: $line
done >> $output

# cleanup
rm $TMPFILE $TMPFILE.txt
rm -rf $TMPDIR
