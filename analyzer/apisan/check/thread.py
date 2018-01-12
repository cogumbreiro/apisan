#!/usr/bin/env python3
import copy
from .checker import Checker, Context, BugReport
from ..lib import rank_utils
from ..parse.explorer import is_call, is_lock, is_unlock, match_call, CallType
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
                if score >= self.config.threshold and ctx is not None and score != 1:
                    diff = diff - codes
                    for bug in diff:
                        scores[bug] = score

            if len(diff) != len(total):
                added = set()
                for bug in diff:
                    if bug in added:
                        continue
                    added.add(bug)
                    br = BugReport(scores[bug], bug, key, ctx, total - diff)
                    bugs.append(br)
        return bugs


class ThreadSafetyChecker(Checker):
    parse_constraints = False

    def _initialize_process(self):
        self.context = ThreadSafetyContext(self.config)

    def _process_path(self, path):
        mutex = False
        for node in path:
            m = match_call(node)
            if m is not None:
                call_name = node.event.call_name
                code = node.event.code
                if m == CallType.LOCK:
                    mutex = True
                elif m == CallType.UNLOCK:
                    mutex = False
                else: # normal call
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
