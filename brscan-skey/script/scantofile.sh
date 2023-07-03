#!/bin/bash
# $1 = scanner device
# $2 = friendly name

#override environment, as brscan is screwing it up:
export $(grep -v '^#' /opt/brother/scanner/env.txt | xargs)

# Resolution (dpi):
# 100,200,300,400,600
resolution=150
device=$1
date=$(date +%Y-%m-%d-%H-%M-%S)

mkdir "/scans/$date"
cd "/scans/$date"
filename_base=/scans/$date/$date"-front-page"
output_file=$filename_base"%04d.pnm"
echo "filename: "$output_file

if [ "`which usleep  2>/dev/null `" != '' ];then
    usleep 100000
else
    sleep  0.1
fi
scanimage -l 0 -t 0 -x 215 -y 297 --device-name "$device" --source "Automatic Document Feeder(centrally aligned)" --resolution $resolution --batch=$output_file
if [ ! -s $filename_base"0001.pnm" ];then
  if [ "`which usleep  2>/dev/null `" != '' ];then
    usleep 1000000
  else
    sleep  1
  fi
  scanimage -l 0 -t 0 -x 215 -y 297 --device-name "$device" --source "Automatic Document Feeder(centrally aligned)" --resolution $resolution --batch=$output_file
fi

#only convert when no back pages are being scanned:
(
	if [ "`which usleep  2>/dev/null `" != '' ];then
		usleep 120000000
	else
		sleep  120
	fi
	
	(
		echo "converting to PDF for $date..."
		gm convert -define magick:format=application/pdf -page A4+0+0 $filename_base*.pnm /scans/$date.pdf
		curl \
		    -u pi:m5QtrF8hY \
			-d "PDF $date created successfully!" \
			-H "Title: Scanning done!" \
			-H "Priority: low" \
			-H "Tags: scanner, pdf" \
		    https://ntfy.danielvolz.org/scanner
	
		echo "cleaning up for $date..."
		cd /scans
		rm -rf $date
	

	) &
) &
echo $! > scan_pid
echo "conversion process for $date is running in PID: "$(cat scan_pid)