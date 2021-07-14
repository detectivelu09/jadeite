#!/bin/bash

CURR=`pwd`
WEKA_LIB="$CURR/deps/weka-3.6.7.jar"
JAD=/usr/bin/jad

if test $# -ne 1; then
    echo "Error: expected 1 parameter; $# provided"
    echo "Usage: $0 APPLET"
    exit 1
fi

DISASM_ANALYZER=$CURR/analyze.py
applet=$1

echo "Analyzing $applet" >> /tmp/appletanalysis.log
if [ "${applet##*.}" != "jar" ]; then
	END=.class
else
	END=.jar
fi

TMP_DIR=$CURR/`basename $applet $END`
mkdir -p $TMP_DIR
cd $TMP_DIR
cp $applet .

applet=$(basename -- "$applet")

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

	$DISASM_ANALYZER $TMP_DIR/$applet $CURR $TMP_DIR/disas > $TMP_DIR/out.arff
        output=`cat out.arff`
        if [[ $output == malicious* ]]; then
		echo $output
	else
		result=`java -cp $WEKA_LIB  weka.classifiers.trees.J48 -l $CURR/jarhead.model -T $TMP_DIR/out.arff | grep ^"Correctly" | sed 's/ \+ /\t/g' | awk '{print $4}'`
#	echo $result
		if [ "$result" = "1" ]; then
			echo malicious
		else
			echo benign
		fi
	fi

cd - >/dev/null

#cleanup
rm -rf $TMP_DIR
