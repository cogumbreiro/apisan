#!/usr/bin/env python3
from ..lib import config
from ..lib.store import Store
import os.path
import re

CONSTANTS = {
    -128: "INT8_MIN",
    128: "INT8_MAX",
    255: "UINT8_MAX",
    -32768: "INT16_MIN",
    32767: "INT16_MAX",
    65535: "UINT16_MAX",
    -2147483648: "INT32_MIN",
    2147483647: "INT32_MAX",
    4294967295: "UINT32_MAX",
    -9223372036854775808: "INT64_MIN",
    9223372036854775807: "INT64_MAX",
}

def parse_constant_type(k):
    left, _ = k.split("_")
    return left

def humanize_num(n):
    return CONSTANTS.get(n, str(n))

def humanize_ival(p):
    if p[0] == p[1]:
        return humanize_num(p[0])
    else:
        return "[%s,%s]" % (humanize_num(p[0]), humanize_num(p[1]))

def humanize_range(r):
    if len(r) == 1:
        return "== " + humanize_ival(r[0])
    if len(r) == 2:
        ((lo1, hi1), (lo2, hi2)) = r
        if hi1 + 2 == lo2 and lo1 in CONSTANTS and hi2 in CONSTANTS:
            if parse_constant_type(CONSTANTS[lo1]) == parse_constant_type(CONSTANTS[hi2]):
              return "!= " + str(hi1 + 1)
            
    return "in {" + ", ".join(humanize_ival(p) for p in r) + "}"

def print_line(enc_filename):
    try:
        orig_fname, fname, lineno = enc_filename.split(":")
        lineno = int(lineno)
    except ValueError:
        return
    if not os.path.exists(orig_fname):
        return
    expr = re.compile('# ([0-9]+) "([^"]+)".*')
    with open(orig_fname) as fp:
        counter = 1
        curr_line = 1
        curr_fname = os.path.basename(orig_fname)
        for line in fp:
            res = expr.match(line)
            if res is not None:
                curr_fname = res.group(2)
                curr_line = int(res.group(1))
                counter += 1
                continue

            if curr_fname == fname and lineno == curr_line:
                return f"{orig_fname}:{counter}: {line}"

            curr_line += 1
            counter += 1
    return

class BugReport:
    def __init__(self, score, code, key, ctx, references=None):
        self.key = key
        self.ctx = ctx
        self.score = score
        self.code = code
        self.references = references

    def get_references(self, size):
        if len(self.references) == 1 or size == 1:
            refs = "{" + self.references.pop() + "}"
        else:
            i = 0
            refs = "{"
            for x in self.references:
                if i >= size:
                    break
                elif i == len(self.references) - 1 or i == size - 1:
                    refs += x
                else:
                    refs = refs + x + ", "
                i += 1
            refs += "}"
        return refs

    def __repr__(self):
        if self.references is None:
            return "BugReport(score=%.02f, code=%s, key=%s, ctx=%s)" % (
                self.score, self.code, self.key, self.ctx
            )
        else:
            return "BugReport(score=%.02f, code=%s, key=%s, ctx=%s, reference=%s)" % (
                self.score, self.code, self.key, self.ctx,
                self.get_references(self.ctx.config.reference)
            )


    def __str__(self):
        refs = self.get_references(self.ctx.config.reference) if self.references is not None else ""
        ctx = humanize_range(self.ctx)
        line = print_line(self.code)
        line = "\n" + line if line is not None else ""
        return f"{self.score:.2%} {self.code} '{self.key}' {ctx} {refs}{line}"

class Context:
    def __init__(self, config):
        self.total_uses = Store(level=1)
        self.ctx_uses = Store(level=2)
        self.config = config

    def add(self, key, value, code):
        if value is not None:
            self.ctx_uses[key][value].add(code)
        self.total_uses[key].add(code)

    def merge(self, other):
        self.total_uses.merge(other.total_uses)
        self.ctx_uses.merge(other.ctx_uses)

    def get_bugs(self):
        added = set()
        bugs = []
        for key, value in self.ctx_uses.items():
            total = self.total_uses[key]
            for ctx, codes in value.items():
                score = len(codes) / len(total)
                if score >= self.config.threshold and score != 1:
                    diff = total - codes
                    for bug in diff:
                        br = BugReport(score, bug, key, ctx)
                        added.add(bug)
                        bugs.append(br)
        return bugs

class Checker:
    def __init__(self, config):
        self.config = config
        
    def _initialize_process(self):
        # optional
        pass

    def _finalize_process(self):
        raise NotImplementedError

    def _process_path(self, path):
        raise NotImplementedError

    def process(self, tree):
        self._initialize_process()
        for path in tree:
            self._process_path(path)
        return self._finalize_process()



