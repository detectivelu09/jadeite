#!/bin/bash

CURR=`pwd`
WEKA_LIB="$CURR/deps/weka-3.6.7.jar"
JAD=/usr/bin/jad

if test $# -ne 3; then
    echo "Error: expected 3 parameters; $# provided"
    echo "Usage: $0 ANALYZER APPLET OUTPUT"
    exit 1
fi

DISASM_ANALYZER=$CURR/$1
applet=$2
OUTPUT=$CURR/$3

echo "Analyzing $applet" >> /tmp/appletanalysis.log
if [ "${applet##*.}" != "jar" ]; then
	END=.class
else
	END=.jar
fi

TMP_DIR=$CURR/`basename $applet $END`

mkdir -p $TMP_DIR
cd $TMP_DIR
cp ../$applet .

function findjars {
        ls | grep -e ".jar$" | grep -v $applet | xargs -I% sh -c "md5sum '%' | cut -f1 -d' ' | xargs -I{} mv '%' {}.jar;"
        ls | grep -e ".jar$" | grep -v $applet | while read j
                        do name=`basename $j .jar`; mkdir -p $name; cd $name; unzip ../$j 2>&1 >> /dev/null; cd ..;
        done
        ls -d */ | while read dir
                do cd $dir; ls | grep -e ".jar$" | grep -v $applet | xargs -I% sh -c "md5sum '%' | cut -f1 -d' ' | xargs -I{} mv '%' {}.jar;"; ls | grep -e ".jar$" | while read j
                        do name=`basename $j .jar`; mkdir -p $name; cd $name; unzip ../$j 2>&1 >> /dev/null; findjars; cd ..;
                done
                cd ..
        done
}

if [ "$END" != ".class" ]; then
	#jar xf $applet #unzip seems to work better
	/usr/bin/yes "A" | unzip $applet 2>&1 >> /dev/null
	chmod -R 755 *
	findjars
else
    #rename class
    class="$applet";
    	$JAD $class 2>&1 | grep Generating | cut -d ' ' -f 4 | while read i; do
        cp $class `basename $applet .jad`.class;
        rm *jad;
    done
fi

find . -name '*.class' | while read j;
    do k=`echo $j | sed -e 's/\//./g' | cut -d '.' -f 3-100`; echo $k; javap -c -private `basename $k .class`;
done > disas

if [ "$DISASM_ANALYZER" = "$CURR/appletanalysis.py" ]; then
	$DISASM_ANALYZER $TMP_DIR/$applet $TMP_DIR/disas > $OUTPUT
elif [ "$DISASM_ANALYZER" = "$CURR/jarhead.py" ]; then
	$DISASM_ANALYZER $TMP_DIR/$applet $CURR $TMP_DIR/disas > $TMP_DIR/out.arff
	result=`java -cp $WEKA_LIB  weka.classifiers.trees.J48 -l $CURR/jarhead.model -T $TMP_DIR/out.arff | grep ^"Correctly" | sed 's/ \+ /\t/g' | awk '{print $4}'`
#	echo $result
	if [ "$result" = "1" ]; then
		echo malicious > $OUTPUT
	else
		echo benign > $OUTPUT
	fi
else
	echo "INVALID ANALZYER PROVIDED" >> /tmp/appletanalysis.log
fi

cd - >/dev/null

#cleanup
rm -rf $TMP_DIR
