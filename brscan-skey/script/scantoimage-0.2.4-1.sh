#! /bin/bash
set +o noclobber
#
#   $1 = scanner device
#   $2 = friendly name
#

#   
#       100,200,300,400,600
#
# query device with scanimage -h to get allowed resolutions

device=$1

# in color resolution more than 300 slows things down
resolution=200
# leave height and width uncommented to autodetect
#height=114
#width=160
compress_format="png"

# set color to full color or 24 bit. 
mode='"24Bit Color"'
#mode='"Black & White"'

# change to directory of script
# cd ${basedir}
# echo "basedir = $basedir" 

# ugly hack that makes environment variables set available
cfgfile="/opt/brother/scanner/brscan-skey/brscan-skey.config"
echo "cfgfile = $cfgfile"

if [[ -r "$cfgfile" ]]; then
    echo "Found cfgfile"
    source "$cfgfile"
    echo "environment after processing cfgfile"
    env
fi

# # SAVETO DIRECTORY
# if [[ -z "$SAVETO" ]];  then
#     SAVETO=${HOME}'/brscan/photos'
# else
#     SAVETO=${SAVETO}'/photos'
# fi

# SAVETO DIRECTORY

TMP_SAVETO=${HOME}'/brscan/photos'

SAVETO=${SAVETO}'/photos'


mkdir -p $SAVETO
mkdir -p $TMP_SAVETO

if [[ -z $LOGDIR ]]; then
    # if LOGDIR is not set, choose a default
    mkdir -p ${HOME}/brscan
    logfile=${HOME}"/brscan/$(date +%Y-%m-%d-%H-%M-%S)_photo_scan.log"
else
    mkdir -p $LOGDIR
    logfile=${LOGDIR}"/$(date +%Y-%m-%d-%H-%M-%S)_photo_scan.log"
fi
touch ${logfile}

# if SOURCE is not set
if [[ -z $SOURCE ]]; then
    SOURCE="Automatic Document Feeder(left aligned)"
fi
# for debugging purposes, output arguments
echo "options after processing." >> ${logfile}
echo "$*" >> ${logfile}
# export environment to logfile
set >> ${logfile}
echo $LOGDIR >> ${logfile}

# logfile="/home/arjun/brscan/brscan-skey.log"
# if [ -z "$1" ]; then
#     device='brother4:net1;dev0'
# else
#     device=$1
# fi

# in scantofile the widht and height are automatically set. Here, they're not.

# mkdir -p ~/brscan/photos
if [ "`which usleep  2>/dev/null `" != '' ];then
    usleep 100000
else
    sleep  0.1
fi
# output_file=$SAVETO + "/brscan_photo_" + `date +%Y-%m-%d-%H-%M-%S`".pnm
output_file="$TMP_SAVETO/brscan_photo_$(date +%Y-%m-%d-%H-%M-%S).pnm"

#echo "scan from $1($device) to $output_file"

# options
if [[ -z "$height" || -z "$width" ]]; then
    SCANOPTIONS="--mode $mode --device-name \"$device\" --resolution $resolution"
else
    SCANOPTIONS="--mode $mode --device-name \"$device\" --resolution $resolution -x $width -y $height"
fi

# echo the command to stdout. Then write it to logfile.
echo "scanimage $SCANOPTIONS > $output_file"
echo "scanimage $SCANOPTIONS > $output_file" >> $logfile 
echo "scanimage $SCANOPTIONS > $output_file" 2>> $logfile | bash

#scanimage --verbose $SCANOPTIONS > $output_file 2>/dev/null

# if the file is zero size, run again.
if [ ! -s $output_file ];then
  if [ "`which usleep  2>/dev/null `" != '' ];then
    usleep 1000000
  else
    sleep  1
  fi
  echo "Rerunning scanimage $SCANOPTIONS"
  scanimage $SCANOPTIONS > $output_file 2>/dev/null

fi
#echo gimp -n $output_file  2>/dev/null \;rm -f $output_file | sh & 

if [ -s $output_file ]; then
    echo  $output_file is created.
    # change ownership so arjun and szhao have access
    # chown arjun:szhao $output_file

    # Should convert to jpg and delete duplicates
    output_file_compressed=$(dirname $output_file)"/"$(basename $output_file .pnm)".$compress_format"
    echo convert -trim -bordercolor White -border 20x10 +repage -quality 95 -density "$resolution" $output_file "$output_file_compressed" 
    echo convert -trim -quality 95 -density "$resolution" $output_file "$output_file_compressed" >> $logfile
    echo convert -trim -quality 95 -density "$resolution" "$output_file" "$output_file_compressed" | bash
    mv $output_file_compressed $SAVETO
    rm $output_file
    curl \
        -u pi:m5QtrF8hY \
        -d "Single document scanned successfully!" \
        -H "Title: Scanning done!" \
        -H "Priority: low" \
        -H "Tags: scanner, pdf" \
        https://ntfy.danielvolz.org/scanner
    # chown arjun:szhao $output_file_compressed
fi
