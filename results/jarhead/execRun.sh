#!/bin/bash

if [ $# -lt 1 ]
then 
    echo "USAGE: $0 <Folder with Jar files>"
    exit -1
fi


echo -n "" > bin_attr.csv
echo -n "file,midisoundbank,midisequencer,rmi,serialize,rhino,sms,atomic,jlist,colorconvertopfilter,sqldriver,storeimagearray,suntracing,mbeanserverintrospector,mbeaninstantiator,alphacomposite,findstaticsetter,lookupbytebi,alphacompositecompose,execute,det" >> bin_attr.csv
echo "" >> bin_attr.csv

echo -n "" > results.csv
echo -n "file" >> results.csv
echo -n "," >> results.csv
echo -n "m_b" >> results.csv
echo "" >> results.csv

currentPath=$(pwd)
#echo "Current Path : $currentPath"
#echo "PATH : $1"

files=$(cd "$1"; ls -l --color=none *.jar | awk -F " " '{print $NF}'; cd $currentPath)
for jarFile in $files
do
    echo "Processing: $jarFile"
    jarFile=$(echo $jarFile | awk -F "/" '{print $NF}')

    echo -n $jarFile >> bin_attr.csv
    echo -n "," >> bin_attr.csv

    ./run.sh "$1/$jarFile" 2>&1 | tee tmp_out.txt

    echo "" >> bin_attr.csv

    if grep -qs malicious tmp_out.txt
    then
        #cp $jarFile ${prob}No_Init
        echo -n "$jarFile" >> results.csv
        echo -n "," >> results.csv
        echo "1" >> results.csv
    elif grep -qs benign tmp_out.txt
    then
        echo -n "$jarFile" >> results.csv
        echo -n "," >> results.csv
        echo "0" >> results.csv
    else
    	exit 1
	fi

    rm -f tmp_out.txt
done