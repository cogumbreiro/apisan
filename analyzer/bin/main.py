#!/usr/bin/env python3
import argparse
import os
import subprocess
import sys

from apisan.check import CHECKERS
from apisan.parse.explorer import Explorer
from apisan.lib import dbg
from apisan.lib import config
from collections import ChainMap

TOP = os.path.join(os.path.dirname(os.path.realpath(__file__)), "../../")
SCAN_BUILD = os.path.join(TOP, "./llvm/tools/clang/tools/scan-build/scan-build")
CLANG_BIN = os.path.join(TOP, "./bin/llvm/bin/clang")
SYM_EXEC_EXTRACTOR = "alpha.unix.SymExecExtract"

DISABLED_CHECKERS = [
    "core.CallAndMessage",
    "core.DivideZero",
    "core.DynamicTypePropagation",
    "core.NonNullParamChecker",
    "core.NullDereference",
    "core.StackAddressEscape",
    "core.UndefinedBinaryOperatorResult",
    "core.VLASize",
    "core.builtin.BuiltinFunctions",
    "core.builtin.NoReturnFunctions",
    "core.uninitialized.ArraySubscript",
    "core.uninitialized.Assign",
    "core.uninitialized.Branch",
    "core.uninitialized.CapturedBlockVariable",
    "core.uninitialized.UndefReturn",
    "cplusplus.NewDelete",
    "deadcode.DeadStores",
    "security.insecureAPI.UncheckedReturn",
    "security.insecureAPI.getpw",
    "security.insecureAPI.gets",
    "security.insecureAPI.mkstemp",
    "security.insecureAPI.mktemp",
    "security.insecureAPI.vfork",
    "unix.API",
    "unix.Malloc",
    "unix.MallocSizeof",
    "unix.MismatchedDeallocator",
    "unix.cstring.BadSizeArg",
    "unix.cstring.NullArg"
]

CONFIGS = [
    "ipa=basic-inlining",
    # "ipa-always-inline-size=3",  # default: 3     # number of basic block
    # "max-inlinable-size=4",     # default: 4, 50 # number of basic block
    # "max-times-inline-large=32", # default: 32    # number of functions
]

def print_bugs(bugs):
    if bugs:
        print("=" * 30 + " POTENTIAL BUGS " + "=" * 30)
        for bug in bugs:
            print(bug)

def get_command():
    cmds = [SCAN_BUILD]
    for checker in DISABLED_CHECKERS:
        cmds += ["-disable-checker", checker]
    for config in CONFIGS:
        cmds += ["-analyzer-config", config]
    cmds += [
        "--use-analyzer", CLANG_BIN,
        "-enable-checker", SYM_EXEC_EXTRACTOR,
    ]
    return cmds

def add_build_command(subparsers, conf):
    parser = subparsers.add_parser("build", help="make a symbolic context database")
    parser.add_argument("cmds", nargs=argparse.REMAINDER)

def add_compile_command(subparsers, conf):
    parser = subparsers.add_parser("compile", help="make a symbolic context database")
    parser.add_argument("--compiler", default="gcc", help="set the compiler (default: gcc)")
    parser.add_argument("cmds", nargs=argparse.REMAINDER)
    
def add_check_command(subparsers, conf):
    parser = subparsers.add_parser("check", help="check a API misuse")
    parser.add_argument("checker", choices=CHECKERS.keys())
    parser.add_argument("--db", default=os.path.join(os.getcwd(), "as-out"))
    parser.add_argument("--filename", default=None, help="Check a single file (.as); ignores the database.")
    if conf.skip_cache:
        parser.add_argument("--cache", dest="skip_cache", action="store_false", default=True, help="Uses a cache for the results of the checker.")
    else:
        parser.add_argument("--skip-cache", action="store_true", default=False, help="Skips using any cached results of the checker.")

def parse_args():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="cmd")
    subparsers.required = True
    # Initialize the default configuration values
    conf = config.defaults()
    add_build_command(subparsers, conf)
    add_compile_command(subparsers, conf)
    add_check_command(subparsers, conf)
    # Extend the configuration object with the command-line args:
    # Conf objects expect dictionaries, so we conver a argparse.Namespace
    # into a dict using vars:
    conf.push(vars(parser.parse_args()))
    return conf

def handle_build(args):
    cmds = get_command()
    cmds += args.cmds
    sys.exit(subprocess.call(cmds))

def handle_compile(args):
    cmds = get_command()
    cmds += [args.compiler, "-c"]
    cmds += args.cmds
    sys.exit(subprocess.call(cmds))

def handle_check(args):
    chk = CHECKERS[args.checker](args)
    chk.name = args.checker
    exp = Explorer(chk)
    if args.skip_cache:
        exp.write_cache = False
        exp.read_cache = False
    if args.filename is not None:
        bugs = exp.explore_single_file(args.filename)
    else:
        bugs = exp.explore_parallel(args.db)
    print_bugs(bugs)

def main():
    args = parse_args()
    dbg.quiet(args.ignored_log_levels) # do not print debugging information
    globals()["handle_%s" % args.cmd](args)

if __name__ == "__main__":
    main()
