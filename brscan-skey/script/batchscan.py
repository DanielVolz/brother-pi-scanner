#!/usr/bin/python3

# Objectives: scan single sided files. convert to pdf.

import argparse
import datetime
import os
import re
import subprocess
import sys
import tempfile
import time
import traceback
from typing import List

import scanutils

# SETTINGS
PART = "part"
TIMEOFFSET = 5 * 60  # in seconds
AS_SCRIPT = False
DEBUG = True
WAITLIMIT = 300  # a limit for waiting to fix errors
scanutils.debug = DEBUG
default_logdir = os.path.join("/tmp", "brscan")
default_outdir = os.path.join("/tmp", "brscan")
today = datetime.date.today().isoformat()


def remove_files(folder_path):
    for file_name in os.listdir(folder_path):
        file_path = os.path.join(folder_path, file_name)
        if os.path.isfile(file_path):
            os.remove(file_path)


def send_ntfy_notification(
    username: str,
    password: str,
    message: str,
    title: str,
    priority: str,
    tags: List[str],
    url: str,
):
    # Prepare headers
    headers = [f"Title: {title}", f"Priority: {priority}", f'Tags: {", ".join(tags)}']

    # Prepare curl command
    cmd = ["curl", "-u", f"{username}:{password}", "-d", message, "-H", *headers, url]

    # Execute curl command
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    # Check result
    if result.returncode == 0:
        print("Notification sent successfully!")
    else:
        print(f"Failed to send notification, error: {result.stderr.decode()}")


def parse_arguments():
    global default_outdir, default_logdir

    # argument list
    parser = argparse.ArgumentParser(
        description="Process arguments for single and double sided scan"
    )
    # else take options from command line
    parser.add_argument(
        "--outputdir",
        nargs="?",
        action="store",
        default=default_outdir,
        const=default_outdir,
        help="tmp output directory for scanned files",
    )
    parser.add_argument(
        "--exportdir",
        nargs="?",
        action="store",
        default="/scans",
        const=default_outdir,
        help="docker mounted output directory for scanned files",
    )
    parser.add_argument(
        "--logdir",
        nargs="?",
        action="store",
        default=default_logdir,
        const=default_logdir,
        help="output directory for logfile",
    )
    parser.add_argument(
        "--prefix",
        nargs="?",
        action="store",
        default="brscan",
        const="brscan",
        help="prefix for scanned file name",
    )
    parser.add_argument(
        "--timenow",
        nargs="?",
        type=int,
        action="store",
        const=int(time.time()),
        default=int(time.time()),
        help="timestamp added to scanned output file, in secs from epoch",
    )
    parser.add_argument(
        "--device-name",
        nargs="?",
        action="store",
        const=None,
        default=None,
        help="scanned device name. Example: brother4:net1;dev1",
    )
    parser.add_argument(
        "--resolution",
        nargs="?",
        action="store",
        default="300",
        const="300",
        help="scanning resolution in dpi",
    )
    parser.add_argument(
        "--height",
        nargs="?",
        action="store",
        default="297",
        const="297",
        help="scanned page height. default letter paper height in mm",
    )
    parser.add_argument(
        "--width",
        nargs="?",
        action="store",
        default="210",
        const="210",
        help="scanned page width. similar to letter paper in mm",
    )

    parser.add_argument("--l", nargs="?", action="store", default="0", const="0")
    parser.add_argument("--t", nargs="?", action="store", default="0", const="0")
    parser.add_argument("--x", nargs="?", action="store", default="215", const="215")
    parser.add_argument("--y", nargs="?", action="store", default="287", const="287")

    parser.add_argument("--mode", nargs="?", action="store", default=None, const=None)
    # parser.add_argument('--mode',action='store',default = 'Black & White')
    parser.add_argument("--source", nargs="?", action="store", default=None, const=None)
    # by default, its not in double mode.
    parser.add_argument(
        "--duplex", nargs="?", action="store", default=None, const="manual"
    )
    # requires exactly one argument, but this not set by nargs
    # it's not a dry-run by default.
    parser.add_argument("--dry-run", action="store_true", default=False)

    # scanimage -l 0 -t 0 -x 215 -y 287 --resolution 300 --mode 'Black & White' > myimage.ppm

    args, unknown = parser.parse_known_args()

    # process options.
    if not args.device_name:
        if DEBUG:
            scanutils.logprint(
                "No device name set. Trying to automatically find default device"
            )
        args.device_name = scanutils.get_default_device()

    # check logdir and outputdir, and then normalize the paths
    if not os.path.exists(args.logdir):
        if DEBUG:
            scanutils.logprint(
                "Log directory ", args.logdir, " does not exist. Creating."
            )
        os.makedirs(args.logdir)
    # normalize name so that its easy to find
    args.logdir = os.path.normpath(args.logdir)

    if not os.path.exists(args.outputdir):
        if DEBUG:
            scanutils.logprint(
                "Output directory ", args.outputdir, " does not exist. Creating."
            )
        os.makedirs(args.outputdir)
    # normalize name so that its easy to find
    args.outputdir = os.path.normpath(args.outputdir)

    # if args.duplex is auto, then look for duplex source. If it's empty
    # choose something automatically by running `scanimage -A`. If it's set, use it.
    if args.duplex == "auto":
        if not args.source:
            args.source = scanutils.get_default_duplex_source()

    return args


# SCRIPT START
print("\n", today, " Starting ", sys.argv[0], " at", time.time())


# see if run as a script. as_script needed to parse arguments correctly.
# I dont think this is needed anymore.
if not re.match(r"/usr/bin/.*python.*", sys.argv[0]):
    AS_SCRIPT = True

# read arguments
args = parse_arguments()

# if debug, logprint parsed arguments
if DEBUG:
    # the logfile is not set yet
    print("parsed arguments:", args)


# Open logfile
logfile_name = args.logdir + "/batchscan.log"
logfile = None

try:
    logfile = open(logfile_name, "a")
    scanutils.logfile = logfile
    logfile.write("Opening logfile.\n")
except IOError as e:
    scanutils.logprint("Error opening or writing to logfile: " + str(e), logfile_name)

    try:
        logfile = tempfile.NamedTemporaryFile(dir="/tmp", delete=False)
        scanutils.logprint("Opened temporary logfile: " + logfile.name)
    except FileNotFoundError:
        scanutils.logprint("Failed to open a temporary file. You are so screwed.")

        # Set logfile to stdout
        logfile = sys.stdout

    if DEBUG:
        traceback.print_exc(file=sys.stdout)

# scanutils.logfile = logfile

if DEBUG:
    scanutils.logprint("The logfile is = " + str(logfile))

# set filename matchstring regular expressions
match_string_time = (
    args.outputdir + "/" + args.prefix + "-([0-9]+)-" + PART + r"-[0-9]+\..*"
)
match_string_part = (
    args.outputdir + "/" + args.prefix + "-[0-9]+-" + PART + r"-([0-9]+)\..*"
)

# list of odd files
odd_files_name = args.outputdir + "/" + "." + args.prefix + "-odd-filelist"

if DEBUG:
    scanutils.logprint(
        "Look for scanned files of the following form (regex): ", match_string_part
    )

if args.duplex == "manual":
    # then run complex double sided scanning routines.

    scanutils.logprint("Running duplex mode = ", args.duplex)

    # look for off files list
    if os.path.exists(odd_files_name):
        odd_files_list = eval(open(odd_files_name).read())
        scanutils.logprint("Found odd files list")
        if DEBUG:
            scanutils.logprint("They are:", odd_files_list)

        # can be overridden below if checks are failed.
        run_mode = "run_even"

        # look for file
        oddfiles = []
        for f in odd_files_list:
            if os.path.exists(f):
                oddfiles.append(f)
            else:
                # there is trouble; files missing. i won't do anything.
                scanutils.logprint(
                    "There are files missing in the odd files list. Missing file = ", f
                )
                # write filelist to logfile
                scanutils.logprint("Writing list of saved odd files to log.")
                scanutils.logprint(odd_files_list)
        if len(oddfiles) > 0:
            # the total number of files is of course twice the number of odd files
            maxpart = 2 * len(oddfiles)
        else:
            run_mode = "run_odd"
            scanutils.logprint("No files exist in odd files list.")
            os.remove(odd_files_name)

    else:
        # if no odd filelist found, run in odd mode
        run_mode = "run_odd"

    # run scanner command
    outputfile = (
        args.outputdir + "/" + args.prefix + "-" + str(args.timenow) + "-part-%03d.pnm"
    )
    if run_mode == "run_odd":
        scanutils.logprint("Scanning odd pages")

        [out, err, processhandle] = scanutils.run_scancommand(
            args.t,
            args.l,
            args.x,
            args.y,
            args.device_name,
            outputfile,
            width=args.width,
            height=args.height,
            logfile=logfile,
            debug=DEBUG,
            mode=args.mode,
            resolution=args.resolution,
            batch=True,
            batch_start="1",
            batch_increment="2",
            source=args.source,
            dry_run=args.dry_run,
        )
    else:  # run_mode == 'run_even'
        scanutils.logprint("Scanning even pages")

        [out, err, processhandle] = scanutils.run_scancommand(
            args.t,
            args.l,
            args.x,
            args.y,
            args.device_name,
            outputfile,
            width=args.width,
            height=args.height,
            logfile=logfile,
            debug=DEBUG,
            mode=args.mode,
            resolution=args.resolution,
            batch=True,
            batch_start=str(maxpart),
            batch_increment="-2",
            dry_run=args.dry_run,
        )

    # wait for run_scancommand to return
    processhandle.wait()

    # run conversion routines only if not dry_run.
    if not args.dry_run:
        # find list of scanned files.
        # this section can be abstracted since it appears in both single sided and duplex mode
        try:
            dirname = args.outputdir
            matchregex = args.prefix + "-" + str(args.timenow) + r"-part-.*\.pnm"
            scanned_files = scanutils.filelist(dirname, matchregex)

            if DEBUG:
                scanutils.logprint("Scanned files: ", scanned_files)
        except FileNotFoundError:
            scanutils.logprint(
                "Error finding scanned files; probably no scanned files found. Check"
                " permissions and/or pathname."
            )
            if DEBUG:
                traceback.print_exc(file=sys.stdout)

        # find number of scanned files
        # originally, I found the number of scanned files by looking at the maximum file part number. I don't see why I have to do that. In manual duplex scan mode, this also allows you to delete pages from the odd scanned pages list if necessary.
        number_scanned = len(scanned_files)

        if DEBUG:
            scanutils.logprint("number_scanned: " + str(number_scanned))

        if number_scanned > 0:
            # waiting is builtin to convert_to_pdf, but ideally you should pass the process handle back and you wait in the main script.
            err, converted_files = scanutils.convert_to_pdf(
                scanned_files, wait=0, debug=DEBUG, logfile=logfile
            )

            # delete original scanned files
            if not err and len(converted_files) == len(scanned_files):
                for f in scanned_files:
                    os.remove(f)
                    scanutils.logprint("removing original scanned file: " + f)

            # make a filelist and output filename for pdftk
            if run_mode == "run_odd":
                # compile the odd pages into a single pdf
                compiled_pdf_filename = (
                    args.outputdir
                    + "/"
                    + args.prefix
                    + "-"
                    + today
                    + "-"
                    + str(int(time.time()))
                    + "-odd.pdf"
                )
                filestopdftk = converted_files

                # write filelist to outputdir, used in odd/even mechanism.
                tempf = open(odd_files_name, "w")
                tempf.write(str(converted_files))
                tempf.close()
            elif run_mode == "run_even":
                # if scanned even parts, and hence max part number is bigger than 1
                # even files are automatically numbered in reverse by the scancommand.
                # new files have been ensured to be in sorted order.
                converted_files.sort()  # newfiles should be sorted already

                # interleave two lists, nested for loops
                if len(oddfiles) == len(converted_files):
                    allfiles = scanutils.interleave_lists(oddfiles, converted_files)
                else:
                    scanutils.logprint(
                        "Number of even files scanned not equal to odd files scanned."
                        " Compiling even files alone."
                    )
                    allfiles = converted_files

                if DEBUG:
                    scanutils.logprint("filelist: ", allfiles)

                timestamp = int(time.time())
                date_time = (
                    datetime.datetime.fromtimestamp(timestamp)
                    .strftime("%d.%m.%Y_%H:%M:%S")
                    .replace(".", "-")
                )
                filestopdftk = allfiles
                num_pages = len(filestopdftk)
                
                # args.outputdir = "/scans"
                # ensures that the filename for compiled pdf is unique
                compiled_pdf_filename = (
                    args.exportdir + "/" + args.prefix + "-" + date_time + "-" + str(num_pages) + ".pdf"
                )

                # finally delete even files list
                try:
                    os.remove(odd_files_name)
                except FileNotFoundError:
                    scanutils.logprint(
                        "Error deleting odd files list!!! Must manually delete"
                    )
                    if DEBUG:
                        traceback.print_exc(file=sys.stdout)

            if len(filestopdftk) > 0:
                scanutils.run_pdftk(
                    filestopdftk, compiled_pdf_filename, debug=DEBUG, logfile=logfile
                )
            else:
                scanutils.logprint("No files to compile")

            if run_mode == "run_even":
                
                num_pages = len(filestopdftk)
                send_ntfy_notification(
                    username="pi",
                    password="m5QtrF8hY",
                    message=(
                        f'PDF document "{compiled_pdf_filename}" with {num_pages} pages'
                        " created successfully!"
                    ),
                    title="Scanning done!",
                    priority="low",
                    tags="scanner, pdf",
                    url="https://ntfy.danielvolz.org/scanner",
                )

                remove_files(args.outputdir)

    # close logfile
    logfile.close()


else:  # if not (double sided and manual double scanning) simply run single sided scanning routine
    # in case we have args.duplex and args.duplextype = 'manual'
    # make outputfile

    scanutils.logprint('Running in single side mode or --duplex="auto"')

    # run scan command
    outputfile = (
        args.outputdir + "/" + args.prefix + "-" + str(args.timenow) + "-part-%03d.pnm"
    )
    [out, err, processhandle] = scanutils.run_scancommand(
        args.t,
        args.l,
        args.x,
        args.y,
        args.device_name,
        outputfile,
        width=args.width,
        height=args.height,
        logfile=logfile,
        debug=DEBUG,
        mode=args.mode,
        resolution=args.resolution,
        batch_start="1",
        batch_increment="1",
        source=args.source,
        dry_run=args.dry_run,
    )

    # wait for run_scancommand to return
    processhandle.wait()

    # run conversion routines only if not dry_run.
    if not args.dry_run:
        # find list of scanned files.
        try:
            dirname = args.outputdir
            matchregex = args.prefix + "-" + str(args.timenow) + r"-part-.*\.pnm"
            scanned_files = scanutils.filelist(dirname, matchregex)

            if DEBUG:
                scanutils.logprint("Scanned files:", scanned_files)
        except FileNotFoundError:
            scanutils.logprint(
                "Error finding scanned files; probably no scanned files found. Check"
                " permissions and/or pathname."
            )
            if DEBUG:
                traceback.print_exc(file=sys.stdout)

        # find number of scanned files
        # originally, I found the number of scanned files by looking at the maximum file part number. I don't see why I have to do that. In manual duplex scan mode, this also allows you to delete pages from the odd scanned pages list if necessary.
        number_scanned = len(scanned_files)

        if DEBUG:
            scanutils.logprint("number_scanned: " + str(number_scanned))

        if number_scanned > 0:
            # waiting is builtin to convert_to_pdf, but ideally you should pass the process handle back and you wait in the main script.
            err, converted_files = scanutils.convert_to_pdf(
                scanned_files, wait=0, debug=DEBUG, logfile=logfile
            )

            # delete original scanned files
            if not err and len(converted_files) == len(scanned_files):
                for f in scanned_files:
                    scanutils.logprint("scan file removed: " + str(f))
                    os.remove(f)

            # find newly converted files
            # convertedfiles = filelist('ls ' + args.outputdir + '/' + args.prefix + '-' + str(int(args.timenow)) + '-part-*.pdf')
            # args.outputdir = "/scans"

            timestamp = int(time.time())
            date_time = (
                datetime.datetime.fromtimestamp(timestamp)
                .strftime("%d.%m.%Y_%H:%M:%S")
                .replace(".", "-")
            )
            num_pages=len(converted_files)

            # make a filelist and output filename to pdftk
            compiled_pdf_filename = (
                args.exportdir + "/" + args.prefix + "-" + date_time + "-" + str(num_pages) + ".pdf"
            )
            scanutils.run_pdftk(
                converted_files, compiled_pdf_filename, debug=DEBUG, logfile=logfile
            )
            remove_files(args.outputdir)

            send_ntfy_notification(
                username="pi",
                password="m5QtrF8hY",
                message=(f'PDF document "{compiled_pdf_filename}" with {num_pages} pages'
                        " created successfully!"),
                title="Scanning done!",
                priority="low",
                tags="scanner, pdf",
                url="https://ntfy.danielvolz.org/scanner",
            )
        else:
            scanutils.logprint("No scanned files found")
