#! /bin/sh

TMP=$(mktemp -d)
DSTDIR='/scans'
NAME=scan_$(date "+%d.%m.%Y-%H:%M:%S").tiff

scanimage -L
scanimage --device-name="brother4:net1;dev0" --resolution 200 --format=png --batch=$TMP"/out-%d.png" -x 210 -y 297

cd $TMP
convert out-*.png $NAME

mv $NAME $DSTDIR

rm -rf $TMP