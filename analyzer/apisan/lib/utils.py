#!/usr/bin/env python2
import os
import sys
import pdb
import glob
import bz2
import lzma
import gzip
import os.path

from operator import itemgetter
from collections import OrderedDict

# when break, call pdb
def install_pdb():
    def info(type, value, tb):
        if hasattr(sys, 'ps1') or not sys.stderr.isatty():
            # You are in interactive mode or don't have a tty-like
            # device, so call the default hook
            sys.__execthook__(type, value, tb)
        else:
            import traceback
            # You are not in interactive mode; print the exception
            traceback.print_exception(type, value, tb)
            print()
            # ... then star the debugger in post-mortem mode
            pdb.pm()

    sys.excepthook = info

# get the latest file from pn
def get_latest_file(pn):
    rtn = []
    for f in glob.glob(pn):
        rtn.append([f, os.stat(f).st_mtime])
    if len(rtn) == 0:
        return None
    return max(rtn, key=itemgetter(1))[0]

# iter down to zero
def to_zero(start):
    return range(start-1, -1, -1)

# clean split
def split(line, tok):
    (lhs, rhs) = line.rsplit(tok, 1)
    return (lhs.strip(), rhs.strip())

# get content
def read_file(pn):
    data = ""
    with open(pn) as fd:
        data = fd.read()
    return data

LOADERS = OrderedDict([
    (".xz", lzma.open),
    (".lzma", lzma.open),
    (".bz2", bz2.open),
    (".gz", gzip.open),
    (".gzip", gzip.open),
])

def get_supported_extensions(ext=".as"):
    """
    Returns the supported extensions.
    """
    result = list(ext + x for x in LOADERS.keys())
    result.append(ext)
    return result

def smart_open(filename, *args, **kwargs):
    """
    Uses the file name's extension to transparently decompress files.
    """
    return LOADERS.get(os.path.splitext(filename)[1], open)(filename, *args, **kwargs)

def get_files(out_d):
    for root, dirs, files in os.walk(out_d):
        for name in files:
            pn = os.path.join(root, name)
            if any(map(pn.endswith, get_supported_extensions())):
                yield pn

def get_all_files(in_d):
    if os.path.isdir(in_d):
        files = []
        for fn in get_files(in_d):
            files.append(fn)
        return files
    else:
        with open(in_d) as f:
            result = []
            for line in f.readlines():
                line = line.strip()
                if line.startswith("#"):
                    continue
                result.append(line)
            return result

def is_debug():
    return "DEBUG" in os.environ
