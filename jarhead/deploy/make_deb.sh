#!/bin/bash
###############
# Script to create the deb packages for llweb 
#
# Note: this script has to be run on a Linux distro because it needs fakeroot (not available on Mac OS X)

project="llweb"

known_package_names="plugin-appletanalysis"

# a regexp to verify the provided version string
known_package_version="^[0-9]+\.[0-9]+\.[0-9]+$"

known_package_architectures="i386 amd64"

# a control file template
default_control_file="default_control"

#
# check input parameters
#

if [ $# -eq 3 ]; then
    package_name=$1
    package_version=$2
    package_architecture=$3
else
    echo "Usage $0: <package> <version> <architecture>"
    f=`echo $known_package_names | sed -e "s/ /, /g"`
    echo "  where    package is in [$f]"
    echo "           version is of form major.minor.release (e.g., 1.2.3)"
    f=`echo $known_package_architectures | sed -e "s/ /, /g"`
    echo "           architecture is in [$f]"
    exit 1
fi

# verify that we have a correct version number
valid_version=`echo $package_version | egrep $known_package_version >/dev/null 2>/dev/null; echo $?`
if [ $valid_version -ne 0 ]; then
    echo "Invalid version string $package_version"
    exit 1
fi

# verify that the package name is one of the known packages
valid_name=0
for name in ${known_package_names}
do
    if [ $name == $package_name ]; then
        valid_name=1
        break
    fi
done

if [ $valid_name -eq 0 ]; then
    echo "Invalid package name $package_name"
    exit 1
fi

# verify that the architecture is one of the known architectures
valid_architecture=0
for name in ${known_package_architectures}
do
    if [ $name == $package_architecture ]; then
        valid_architecture=1
        break
    fi
done

if [ $valid_architecture -eq 0 ]; then
    echo "Invalid package architecture $package_architecture"
    exit 1
fi

# create the directory with the name of the architecture
mkdir -p $package_architecture;
full_package_name=`echo "${package_architecture}/${project}-${package_name}_${package_version}"`

#
# create the actual package
#
# mainly based on
#  - http://tldp.org/HOWTO/html_single/Debian-Binary-Package-Building-HOWTO/
#  - http://www.linuxfordevices.com/c/a/Linux-For-Devices-Articles/How-to-make-deb-packages/
#
# these are also useful resources:
# - http://www.iniy.org/?p=88

# Creates a temporary dir
temp_dir=`mktemp -d tmp.XXXXXXXXXX`

package_dir=`echo $temp_dir/$full_package_name`
mkdir -p $package_dir
mkdir $package_dir/DEBIAN
# this is necessary on Debian Woody, don't ask me why
for x in `find $package_dir -type d`; do chmod 755 $x; done

# copy in the control file
if [ -e ${package_name}_control ]
then
    `cp ${package_name}_control $package_dir/DEBIAN/control`
else
    `cp $default_control_file $package_dir/DEBIAN/control`
fi

# Updates the control file with the package's attributes
sed -i -e "s/<@package_name@>/${project}-$package_name/g" $package_dir/DEBIAN/control
sed -i -e "s/<@version@>/$package_version/g" $package_dir/DEBIAN/control
sed -i -e "s/<@architecture@>/$package_architecture/g" $package_dir/DEBIAN/control

# If there are dependencies creares a comma-separated list of dependencies and
# add put it in the control file

package_dependencies=""
if [ -e ${package_name}_dependencies ]
then
    for x in `cat ${package_name}_dependencies | grep -v '^#'`; 
    do
        package_dependencies=`echo $x, "${package_dependencies}"`
    done
else
    echo "no dependency file found for $package_name"
fi
# remove the last comma
package_dependencies=`echo ${package_dependencies} | sed -e "s/,\s*$//"`
# update the control file
sed -i -e "s/<@dependencies@>/$package_dependencies/g" $package_dir/DEBIAN/control

# if there are no dependencies, we must eliminate the line
sed -i -e "/^Depends: $/d" $package_dir/DEBIAN/control

# copy in the post-install/pre-uninstall scripts if present
err=`cp ${package_name}_postinstall $package_dir/DEBIAN/postinst 2>&1`
if [ $? -ne 0 ]; then
    echo "no post-install file found for $package_name"
else
    chmod 0755 $package_dir/DEBIAN/postinst
fi
err=`cp ${package_name}_preuninstall $package_dir/DEBIAN/prerm 2>&1`
if [ $? -ne 0 ]; then
    echo "no pre-uninstall file found for $package_name"
else
    chmod 0755 $package_dir/DEBIAN/prerm
fi

# copy in all files as specified by the _files file
OIFS=$IFS
IFS=$'\n'
for fns in `egrep -v "^\s*#" ${package_name}_files`
do
    src=`echo $fns | awk '{ print $1 }'`
    dest=`echo $fns | awk '{ print $2 }'`

    # if we are instructed to copy all files,
    # if it ends in '/', the destination is a
    # directory
    echo "copying '$src' to '$dest'"
    err=`echo $dest | grep "/$" 2>&1`
    if [ $? -eq 0 ]; then
        mkdir -p $package_dir/$dest
    else
        mkdir -p $package_dir/`dirname $dest`
    fi
    # use rsync instead of copy to
    # 1) copy links as such
    # 2) correctly ignore directories
    err=`rsync --links $src $package_dir$dest 2>&1`
    if [ $? -ne 0 ]; then
        echo "failed: $err"
        echo "aborting."
        rm -rf $temp_dir
        exit 1
    fi
done
IFS=$OIFS

# Now create the debian package Note: fakeroot on Mac OS X is broken. 
# Therefore it is necessary to run this script as root on Mac OS X

if [[ $EUID -ne 0 ]]; then
    fakeroot dpkg-deb --build $package_dir ./$full_package_name.deb
else
    dpkg-deb --build $package_dir ./$full_package_name.deb
fi
dpkg-deb --info $full_package_name.deb

#
# clean up
#

rm -rf $temp_dir

echo "Done"

