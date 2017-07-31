#!/usr/bin/env python3
import copy
from .checker import Checker, Context, BugReport
from ..lib import rank_utils, config
from ..parse.explorer import is_call, is_lock, is_unlock
from ..parse.symbol import IDSymbol

class ThreadSafetyContext(Context):
    def get_bugs(self):
        bugs = []
        for key, value in self.ctx_uses.items():
            total = self.total_uses[key]
            diff = copy.copy(total)
            scores = {}
            for ctx, codes in value.items():
                score = len(codes) / len(total)
                if score >= config.THRESHOLD and ctx and score != 1:
                    diff = diff - codes
                    for bug in diff:
                        scores[bug] = score

            if len(diff) != len(total):
                added = set()
                for bug in diff:
                    if bug in added:
                        continue
                    added.add(bug)
                    br = BugReport(scores[bug], bug, key, ctx)
                    bugs.append(br)
        return bugs


class ThreadSafetyChecker(Checker):
    def _initialize_process(self):
        self.context = ThreadSafetyContext()

    def _process_path(self, path):
        mutex = False
        for i, node in enumerate(path):
            if is_lock(node):
                mutex = True
                call_name = node.event.call_name
                code = node.event.code
            elif is_unlock(node):
                mutex = False
                call_name = node.event.call_name
                code = node.event.code
            elif is_call(node): # normal call
                call_name = node.event.call_name
                code = node.event.code
                self.context.add(call_name, mutex, code)
                

    def _finalize_process(self):
        return self.context

    def merge(self, ctxs):
        if not ctxs:
            return None
        ctx = ctxs[0]
        for i in range(1, len(ctxs)):
            ctx.merge(ctxs[i])
        return self.rank(ctx.get_bugs())

    def rank(self, reports):
        return sorted(reports, key=lambda k: k.score, reverse=True)
