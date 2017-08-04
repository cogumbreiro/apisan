#!/usr/bin/env python3
import copy
import multiprocessing as mp
import os
import xml.etree.ElementTree as ET
import re
import pickle
from enum import Enum

from functools import wraps

from ..lib import dbg
from ..lib import utils
from .event import EventKind, EOPEvent, CallEvent, LocationEvent, AssumeEvent
from .symbol import SymbolKind

ROOT = os.path.dirname(__file__)
SIG = "@SYM_EXEC_EXTRACTOR"

def is_too_big(body):
    # > 1GB
    return len(body) / (2 ** 30) > 1

def sig_begin():
    return SIG + "_BEGIN"

def sig_end():
    return SIG + "_END"

def get_all_files(in_d):
    files = []
    for fn in utils.get_files(in_d):
        files.append(fn)
    return files

class ConstraintMgr(object):
    def __init__(self, constraints=None):
        if constraints is None:
            constraints = dict()
        self.constraints = constraints

    def feed(self, node):
        # return newly allocated ConstraintMgr if changed
        # otherwise return null
        event = node.event
        if event.kind == EventKind.Assume:
            cond = event.cond
            if cond and cond.kind == SymbolKind.Constraint:
                # XXX : latest gives false positives
                if not cond.symbol in self.constraints:
                    new = ConstraintMgr(self.constraints.copy())
                    new.constraints[cond.symbol] = cond.constraints
                    return new

    def __repr__(self):
        return "CM(%s)" % repr(self.constraints)

    def get(self, sym, immutable=False):
        if sym in self.constraints:
            cstr = self.constraints[sym]
            if immutable:
                return tuple(cstr)
            else:
                return cstr
        return None

def is_eop(node):
    return (node.event is not None
            and isinstance(node.event, EOPEvent))

class CallType(Enum):
    LOCK = 1
    UNLOCK = 2
    OTHER = 3

def match_call(node):
    if is_call(node):
        call_name = node.event.call_name
        if call_name == "pthread_mutex_lock":
            return CallType.LOCK
        elif call_name == "pthread_mutex_unlock":
            return CallType.UNLOCK
        return CallType.OTHER
    return None

def is_call(node):
    return (node.event is not None
            and isinstance(node.event, CallEvent)
            and node.event.call_text is not None)

LOCK_RE = re.compile(r"pthread_mutex_lock.*")
def is_lock(node):
    if is_call(node):
        call_name = node.event.call_name
        return call_name is not None and \
            re.match(LOCK_RE, call_name) is not None
    else:
        return False

UNLOCK_RE = re.compile(r"pthread_mutex_unlock.*")
def is_unlock(node):
    if is_call(node):
        call_name = node.event.call_name
        return call_name is not None and \
            re.match(UNLOCK_RE, call_name) is not None
    else:
        return False


class ExecNode(object):
    def __init__(self, node, children):
        assert node.tag == "NODE"
        self._set_children(children)
        self.parent = None
        self.visited = False
        self.event = None

        for child in node:
            if child.tag == "EVENT":
                assert self.event is None
                self.event = self._parse_event(child)
            elif child.tag == "NODE":
                continue
            else:
                raise ValueError("Unknown tag")

    def _parse_event(self, node):
        kind = node[0]
        assert kind.tag == "KIND"

        if kind.text == "@LOG_CALL":
            return CallEvent(node)
        elif kind.text == "@LOG_LOCATION":
            return LocationEvent(node)
        elif kind.text == "@LOG_EOP":
            return EOPEvent(node)
        elif kind.text == "@LOG_ASSUME":
            return AssumeEvent(node)
        else:
            raise ValueError("Unknown kind")

    def _set_children(self, children):
        # set parent-child relation
        self.children = children
        for child in children:
            child.parent = self

    # debugging function
    def __str__(self, i=0):
        result = (" " * i + repr(self) + "\n")
        for child in self.children:
            result += child.__str__(i + 1)
        return result

class ExecTree(object):
    def __init__(self, xml):
        self.xml = xml

    def parse(self, parse_constraints):
        self.root = self._parse()
        if parse_constraints:
            self._set_cmgr()

    def _set_cmgr(self):
        stack = []
        stack.append((self.root, 0))
        self.root.cmgr = ConstraintMgr()

        while stack:
            node, idx = stack.pop()
            if idx == len(node.children):
                # base case : all childrens are visited
                continue
            else:
                child = node.children[idx]
                cmgr = node.cmgr.feed(node)
                if cmgr:
                    child.cmgr = cmgr
                else:
                    child.cmgr = node.cmgr

                stack.append((node, idx + 1))
                stack.append((child, 0))

    def _parse(self):
        stack = []
        stack.append((self.xml, 0, []))

        while True:
            xml_node, idx, children = stack.pop()
            # + 1 because of event
            if len(xml_node) == idx + 1:
                node = ExecNode(xml_node, children)
                if not stack:
                    return node
                else:
                    # children
                    stack[-1][2].append(node)
            else:
                # increase stack & create new stack frame
                stack.append((xml_node, idx + 1, children))
                stack.append((xml_node[idx + 1], 0, []))

def cached(filename_gen):
    def gen(func):
        @wraps(func)
        def try_cached(self, filename):
            if self.read_cache:
                cached_fn = filename_gen(self, filename)
                # Try to load a memoized result
                try:
                    with open(cached_fn, 'rb') as f:
                        result = pickle.load(f)
                        dbg.info("Loaded cached result: %s" % cached_fn)
                        return result
                except:
                    pass
            result = func(self, filename)
            if self.write_cache:
                # Try to cache the result
                try:
                    with open(cached_fn, 'wb') as f:
                        pickle.dump(result, f)
                    dbg.info("Cached checker result: %s" % cached_fn)
                except:
                    pass
            return result
        return try_cached
    return gen

class Explorer(object):
    def __init__(self, checker):
        self.checker = checker
        self.load_cache = True
        self.write_cache = True

    def explore(self, in_d):
        result = []
        for fn in utils.get_files(in_d):
            result += self._explore_file(fn)
        return self.checker.merge(result)

    @cached(lambda self, fn: fn + "." + self.checker.name)
    def _explore_file(self, fn):
        result = []
        parse_constraints = getattr(self.checker, "parse_constraints", True)
        for tree in self._parse_file(fn, parse_constraints):
            result.append(self.checker.process(tree))
        dbg.debug("Explored: %s" % fn)
        return result

    def explore_parallel(self, in_d):
        pool = mp.Pool(processes=mp.cpu_count(),)
        files = utils.get_all_files(in_d)
        results = pool.map(self._explore_file, files)
        pool.close()
        pool.join()
        result = []
        for r in results:
            result += r
        return self.checker.merge(result)

    def explore_single_file(self, filename):
        # This is only useful to cache the analysis
        self._explore_file(filename)
        return []

    def _parse_file(self, fn, parse_constraints):
        forest = []
        with open(fn, 'r') as f:
            start = False
            body = ""

            for line in f:
                if line.startswith(sig_begin()):
                    start = True
                    body = ""
                elif start:
                    if line.startswith(sig_end()):
                        start = False

                        # XXX: tooo large file cannot be handled
                        if is_too_big(body):
                            dbg.info("Ignore too large file : %s" % fn)
                            continue
                        try:
                            xml = ET.fromstring(body)
                        except Exception as e:
                            dbg.info("ERROR : %s when parsing %s" % (repr(e), fn))
                            return []

                        for root in xml:
                            tree = ExecTree(root)
                            tree.parse(parse_constraints)
                            forest.append(tree)
                    else:
                        body += line
        return forest
