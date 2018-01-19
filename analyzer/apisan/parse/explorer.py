#!/usr/bin/env python3
import copy
import multiprocessing as mp
import os
import xml.etree.ElementTree as ET
import re
import pickle
import weakref

from io import StringIO
from enum import Enum
from functools import wraps
from collections import namedtuple

from ..lib import dbg
from ..lib import utils
from .event import EventKind, EOPEvent, CallEvent, ReturnEvent, LocationEvent, AssumeEvent
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

    def copy(self):
        return ConstraintMgr(self.constraints.copy())

def is_eop(node):
    return isinstance(node.event, EOPEvent)

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

def is_return(node):
    return (node.event is not None
            and isinstance(node.event, ReturnEvent)
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
    def __init__(self, node, resolver, cmgr=None):
        assert node.tag == "NODE"
        self.resolver = resolver
        self.node = node
        self.event = self._parse_event(self.node.find("EVENT"))
        self._cmgr = cmgr

    def init_constraint_mgr(self):
        self._cmgr = ConstraintMgr()

    @property
    def cmgr(self):
        return self._cmgr

    def _get_child(self, xml):
        # Create the child constraint manager
        cmgr = self.cmgr
        if cmgr is not None:
            # set a newly allocated ConstraintMgr if changed
            # otherwise use as is
            event = self.event
            if event.kind == EventKind.Assume:
                cond = event.cond
                if cond and cond.kind == SymbolKind.Constraint:
                    # XXX : latest gives false positives
                    if not cond.symbol in cmgr.constraints:
                        cmgr = cmgr.copy()
                        cmgr.constraints[cond.symbol] = cond.constraints
        return ExecNode(xml, resolver=self.resolver, cmgr=cmgr)

    def __iter__(self):
        for x in self.node.findall("NODE"):
            yield self._get_child(x)

    def _parse_event(self, node):
        kind = node[0]
        assert kind.tag == "KIND"

        if kind.text == "@LOG_CALL":
            return CallEvent(node, self.resolver)
        elif kind.text == "@LOG_RETURN":
            return ReturnEvent(node, self.resolver)
        elif kind.text == "@LOG_LOCATION":
            return LocationEvent(node, self.resolver)
        elif kind.text == "@LOG_EOP":
            return EOPEvent(node)
        elif kind.text == "@LOG_ASSUME":
            return AssumeEvent(node)
        else:
            raise ValueError("Unknown kind")

    # debugging function
    def __str__(self, i=0):
        result = (" " * i + repr(self) + "\n")
        for child in self:
            result += child.__str__(i + 1)
        return result

class ExecTree:
    __slots__ = ['root']
    
    def __init__(self, root):
        self.root = root

    def __iter__(self):
        """
        Given a tree, yields every path going from root to a leaf.
        DFS navigation.
        """
        count = 0
        iters = [iter(self.root)]
        nodes = [self.root]

        while nodes:
            node = nodes[-1]
            children = iters[-1]
            if is_eop(node):
                # delayed visiting for truncated paths
                yield nodes
                count += 1
                # clean up
                nodes.pop()
                iters.pop()
            else:
                try:
                    child = next(children)
                    nodes.append(child)
                    iters.append(iter(child))
                except StopIteration:
                    nodes.pop()
                    iters.pop()
    
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

def no_resolver(x): return x

class FilenameResolver:
    def __init__(self, prefix=os.path.join(os.getcwd(), "as-out")):
        self.prefix = prefix
    
    def __call__(self, filename):
        if filename.startswith(self.prefix):
            filename = filename[len(self.prefix) + 1:] # remove the common prefix
            # Guess the original filename
            fname, ext = os.path.splitext(filename)
            while ext != ".as" and ext != "":
                fname, ext = os.path.splitext(fname)
            if ext == ".as":
                return ContainedResolver(fname)
            else:
                # Couldn't find it, just return the original filename
                return ContainedResolver(filename)
        else:
            return no_resolver

class ContainedResolver:
    def __init__(self, container, sep=":"):
        self.container = container + sep
    
    def __call__(self, filename):
        return self.container + filename

def parse_file(fn, parse_constraints=False, resolver=FilenameResolver()):
    """
    A file consists of a collection of tree-objects. Parsing it returns
    an iterator over the collection of trees
    """
    resolver = resolver(fn)
    with utils.smart_open(fn, 'rt') as f:
        start = False
        body = StringIO()

        for line in f:
            if line.startswith(sig_begin()):
                start = True
                body = StringIO()
            elif start:
                if line.startswith(sig_end()):
                    start = False

                    try:
                        xml = ET.fromstring(body.getvalue())
                    except Exception as e:
                        dbg.info("ERROR : %s when parsing %s" % (repr(e), fn))
                        return []

                    for root in xml:
                        tree = ExecTree(ExecNode(root, resolver=resolver))
                        if parse_constraints:
                            tree.root.init_constraint_mgr()
                        yield tree
                        del tree
                        
                else:
                    body.write(line)


class Explorer(object):
    def __init__(self, checker):
        self.checker = checker
        self.read_cache = True
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
        for tree in parse_file(fn, parse_constraints):
            result.append(self.checker.process(tree))
        dbg.info("Explored: %s" % fn)
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


