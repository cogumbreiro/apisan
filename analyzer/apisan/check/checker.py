#!/usr/bin/env python3
from ..parse.explorer import is_eop
from ..lib import config
from ..lib.store import Store

class BugReport():
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
                self.get_references(config.REFERENCE)
            )

class Context():
    def __init__(self):
        self.total_uses = Store(level=1)
        self.ctx_uses = Store(level=2)

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
                if score >= config.THRESHOLD and score != 1:
                    diff = total - codes
                    for bug in diff:
                        br = BugReport(score, bug, key, ctx)
                        added.add(bug)
                        bugs.append(br)
        return bugs

class Checker(object):
    def _initialize_process(self):
        # optional
        pass

    def _finalize_process(self):
        raise NotImplementedError

    def _process_path(self, path):
        raise NotImplementedError

    def process(self, tree):
        self._initialize_process()
        self._do_dfs(tree)
        return self._finalize_process()

    def _do_dfs(self, tree):
        count = 0
        iters = [iter(tree.root)]
        nodes = [tree.root]

        while nodes:
            node = nodes[-1]
            children = iters[-1]
            if is_eop(node):
                # delayed visiting for truncated paths
                self._process_path(nodes)
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


