#! /bin/bash
set +o noclobber
#
#   $1 = scanner device
#   $2 = friendly name
#
# query device with scanimage -h to get allowed resolutions

if [ -n "$1" ]; then
    # if first argument is not empty
    device=$1
fi

# in color resolution more than 300 slows things down
resolution=300

# leave height and width uncommented to autodetect
height=297
width=210

compress_format="png"

# set color to full color or 24 bit. 
mode='"24Bit Color"'

# change to directory of script
# cd ${basedir}
# echo "basedir = $basedir" 

# LOGFILE
scriptname=$(basename "$0")

# ugly hack that makes environment variables set available
cfgfile="/opt/brother/scanner/brscan-skey/brscan-skey.config"
echo "cfgfile = $cfgfile"

if [[ -r "$cfgfile" ]]; then
    echo "Found cfgfile"
    source "$cfgfile"
    echo "environment after processing cfgfile"
    env
fi

# SAVETO DIRECTORY
TMP_SAVETO=${HOME}'/brscan/single'
mkdir -p "$TMP_SAVETO"

if [[ -z "$SAVETO" ]];  then
    SAVETO=${HOME}'/brscan/single'
else
    # SAVETO=${SAVETO}'/single'
    mkdir -p "$SAVETO"
fi

if [[ -z $LOGDIR ]]; then
    # if LOGDIR is not set, choose a default
    mkdir -p "${HOME}"/brscan
    logfile=${HOME}"/brscan/$scriptname.log"
else
    mkdir -p "$LOGDIR"
    logfile=${LOGDIR}"/$scriptname.log"
fi
touch "${logfile}"

# if SOURCE is not set
if [[ -z $SOURCE ]]; then
    SOURCE="Automatic Document Feeder(left aligned)"
fi

# for debugging purposes, output arguments
{
  echo "options after processing."
  echo "$*"
  set
  echo "$LOGDIR"
} >> "${logfile}"


if [ -z "$1" ]; then
    device='brother3:net1;dev0'
else
    device=$1
fi

# in scantofile the widht and height are automatically set. Here, they're not.
if [ "$(which usleep  2>/dev/null)" != '' ];then
    usleep 100000
else
    sleep  0.1
fi
output_file="$TMP_SAVETO/brscan_single_$(date +%d-%m-%Y:%H:%M:%S).pnm"

# options
if [[ -z "$height" || -z "$width" ]]; then
    SCANOPTIONS="--mode $mode --device-name \"$device\" --resolution $resolution"
else
    SCANOPTIONS="--mode $mode --device-name \"$device\" --resolution $resolution -x $width -y $height"
fi

# echo the command to stdout. Then write it to logfile.
echo "scanimage $SCANOPTIONS > $output_file"
echo "scanimage $SCANOPTIONS > $output_file" >> "$logfile" 
echo "scanimage $SCANOPTIONS > $output_file" 2>> "$logfile" | bash

# if the file is zero size, run again.
if [ ! -s "$output_file" ];then
  if [ "$(which usleep  2>/dev/null )" != '' ];then
    usleep 1000000
  else
    sleep  1
  fi
  echo "Rerunning scanimage $SCANOPTIONS"
  scanimage "$SCANOPTIONS" > "$output_file" 2>/dev/null

fi

if [ -s "$output_file" ]; then
    echo  "$output_file" is created.

    # Should convert to jpg and delete duplicates
    output_file_compressed=$(dirname "$output_file")"/$(basename "$output_file" .pnm).$compress_format"

    echo name output png = "$output_file_compressed"
    echo convert -trim -bordercolor White -border 20x10 +repage -quality 95 -density "$resolution" "$output_file" "$output_file_compressed" 
    echo convert -trim -quality 95 -density "$resolution" "$output_file" "$output_file_compressed" >> "$logfile"
    
    echo convert -trim -quality 95 -density "$resolution" "$output_file" "$output_file_compressed" | bash
    
    mv "$output_file_compressed" "$SAVETO"
    rm "$output_file"
    curl \
        -u pi:m5QtrF8hY \
        -d "Single document \"$output_file_compressed\" scanned successfully!" \
        -H "Title: Scanning done!" \
        -H "Priority: low" \
        -H "Tags: scanner, pdf" \
        https://ntfy.danielvolz.org/scanner
fi
