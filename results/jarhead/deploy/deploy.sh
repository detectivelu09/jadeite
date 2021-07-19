#!/bin/bash
# Deploy script for llweb.
#
# Note: requires apt-ftparchive
#
# Typical invocations:
# - staging:
#   ./deploy.sh -S -s cova@tllod.com
# - production:
#   ./deploy.sh -s cova@tllod.com
# - testing locally:
#   ./deploy.sh -p /var/www/ -s localhost

DEFAULT_SERVER="seclab.cs.ucsb.edu"
DEFAULT_PATH="/var/www"
DEFAULT_USER="seclab"

function usage ()
{
    cat <<EOF
Usage: $0 [OPTIONS] [PACKAGES]
  -b               build only (do not attempt to copy debs on server)
  -d               deploy only (do not rebuild the debs)
  -f               force build (re-builds all packages)
  -h               print this message and exit
  -l library       fakeroot support library (might be needed on Mac OS X)
  -p PATH          path on the server where deb packages are stored (default: $DEFAULT_PATH)
  -s SERVER        deb server to use (default: $DEFAULT_SERVER)
  -S               do "staging" deployment
  -U USER          user for deployment server (default: $DEFAULT_USER)
EOF
}

while getopts "bdfhp:s:SU:" opt; do
    case $opt in
        b)
            mode="BUILD"
            ;;
        d)
            mode="DEPLOY"
            ;;
        f)
            force_rebuild=1
            ;;
        h)
            usage
            exit 0
            ;;
        p)
            path="$OPTARG"
            ;;
        s) 
            server="$OPTARG"
            ;;
        l) 
            export FAKEROOTLIB="-l $OPTARG"
            ;;
        S)
            #path="/var/www"
            #server="tllod.com"
            dist="staging"
            conf="conf-staging"
            ;;
        U)
            user="$OPTARG"
            ;;
        ?) 
            echo "Invalid option."
            usage
            exit 1
            ;;
    esac
done

if test -z $mode; then
    mode="ALL"
fi
if test -z $server; then
    server="$DEFAULT_SERVER"
fi
if test -z "$path"; then
    path="$DEFAULT_PATH"
fi
if test -z "$dist"; then
    dist="lucid"
fi
if test -z "$conf"; then
    conf="conf"
fi
if test -z "$user"; then
    user="$DEFAULT_USER"
fi
if test -z "$force_rebuild"; then
    force_rebuild=0
fi

if test $force_rebuild -eq 1 -a $mode == "DEPLOY"; then
    echo "Cannot use options -f and -d together"
    exit 1
fi

# Reset the command line so that the remaining arguments are the (optional) list
# of packages to be built

shift $((OPTIND-1))

if test $# -eq 0; then
    components="`cut -f1 -d ':' versions`"
else
    components="$@"
fi

dpkgs=""
for c in $components; do

    # get the new package version
    version=`grep "^$c:" versions | cut -f 2 -d ':'`
    if ! [[ $version =~ [0-9]+\.[0-9]+\.[0-9] ]]; then
        echo "Cannot determine version for $c. Need to update versions file?"
        exit 2
    fi

    # get the version of the existing package, if any
    existing_deb=`test -f amd64/llweb-${c}_* && ls amd64/llweb-${c}_* | head -1 2> /dev/null`
    if [[ $existing_deb =~ .*_([0-9]+\.[0-9]+\.[0-9]+) ]]; then
        existing_version=${BASH_REMATCH[1]}
    else
        existing_version=""
    fi

    # build the package, unless:
    # - we are in deploy mode
    # - the new version is the same as the existing version and the user
    #   did not force the rebuild
    if [ $mode != "DEPLOY" ]; then
        if [ $force_rebuild -eq 0 -a "$existing_version" == "$version" ]; then
            echo "[+] $c already at version $version"
        else
            if [ $c = "plugin-appletanalysis" ]; then
                cd ../src/java/
                if test ! -f deps; then
                    echo "You must create the src/java/deps file from the template src/java/deps.tmpl"
                    exit 5
                fi
                make clean && make all
                if test $? -ne 0; then
                    echo "Failed building Java plugin"
                    exit 6
                fi
                cd -
            fi

            rm -f amd64/llweb-${c}_*.deb
            ./make_deb.sh $c $version amd64
            if test $? -ne 0; then
                echo "Cannot make package $c $version" >&2
                exit 2
            fi
            echo "[+] successfully built package $c $version"
        fi
    fi
    dpkgs="$dpkgs amd64/llweb-${c}_${version}.deb"
done

if [ $mode != "DEPLOY" ]; then
    if [ ! -d repo/wepawet-ng/binary-amd64 ]; then
        mkdir -p repo/wepawet-ng/binary-amd64
    fi

    rm -f repo/wepawet-ng/binary-amd64/Packages* Release*

    apt-ftparchive packages amd64 > repo/wepawet-ng/binary-amd64/Packages
    if test $? -ne 0; then
        echo "Cannot create Packages file"
        exit 3
    fi

    cat repo/wepawet-ng/binary-amd64/Packages | bzip2 > repo/wepawet-ng/binary-amd64/Packages.bz2
    if test $? -ne 0; then
        echo "Cannot create Packages.bz2 file"
        exit 3
    fi

    apt-ftparchive -c $conf release repo > Release
    if test $? -ne 0; then
        echo "Cannot create Release file"
        exit 3
    fi
    echo "[+] created meta files"

    gpg --local-user marco@tllod.com --detach-sign --armor --sign --output Release.gpg Release 
    if test $? -ne 0; then
        echo "Cannot sign packages"

        # if someone else wants to build the package, we must
        # be able to force this
        rm -f Release.gpg
        #exit 3
    fi
    echo "[+] signed Release file"
fi

echo $dpkgs
if [ $mode != "BUILD" ]; then
    rsync repo/wepawet-ng/binary-amd64/Packages repo/wepawet-ng/binary-amd64/Packages.bz2 Release $user@$server:/tmp/

    copied_dpkgs=""
    for dpkg in $dpkgs; do
        local_md5=`md5sum $dpkg | cut -c -32`
        remote_md5=`ssh $user@$server "test -f $path/wepawet-ng-repo/$dpkg && md5sum $path/wepawet-ng-repo/$dpkg | cut -c -32"`
        if test "$local_md5" == "$remote_md5"; then
            echo "[+] skip transfer of $dpkg (already present)"
        else
            rsync $dpkg $user@$server:/tmp/
            if test $? -ne 0; then
                echo "Cannot copy $dpkg to $server"
                exit 4
            fi
            copied_dpkgs="$copied_dpkgs `basename $dpkg`"
            echo "[+] copied $dpkg to $server"
        fi
    done

    if [ -e Release.gpg ]; then
        rsync Release.gpg $user@$server:/tmp/
        if test $? -ne 0; then
            echo "Cannot copy signature file to $server"
            exit 4
        fi
    fi

    ssh -t $user@$server "sudo mv /tmp/Packages /tmp/Packages.bz2 $path/wepawet-ng-repo/dists/$dist/wepawet-ng/binary-amd64/"
    if test $? -ne 0; then
        echo "Cannot move Packages.* to $path/wepawet-ng-repo/dists/$dist/wepawet-ng/binary-amd64/"
        exit 4
    fi

    ssh -t $user@$server "sudo mv /tmp/Release $path/wepawet-ng-repo/dists/$dist"
    if test $? -ne 0; then
        echo "Cannot move Release to $path/wepawet-ng-repo/dists/$dist/"
        exit 4
    fi

    if [ -e Release.gpg ]; then
        ssh -t $user@$server "sudo mv /tmp/Release.gpg $path/wepawet-ng-repo/dists/$dist"
        if test $? -ne 0; then
            echo "Cannot move Release.gpg to $path/wepawet-ng-repo/dists/$dist/"
            exit 4
        fi
    fi
    echo "[+] moved meta files into repository"

    if test ! -z "$copied_dpkgs"; then
        ssh -t $user@$server "cd /tmp && sudo mv $copied_dpkgs $path/wepawet-ng-repo/amd64/"
        if test $? -ne 0; then
            echo "Cannot move *.deb to $path/wepawet-ng-repo/amd64"
            exit 4
        fi
        echo "[+] moved packages into repository"
    fi
fi

