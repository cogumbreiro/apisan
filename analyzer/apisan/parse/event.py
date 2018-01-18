#!/usr/bin/env python3
from enum import Enum
from .symbol import CallSymbol
from .sparser import SParser
from ..lib import dbg
import ply.lex

gid = 0

class EventKind(Enum):
    Call = "@LOG_CALL"
    Return = "@LOG_RETURN"
    Location = "@LOG_LOCATION"
    EOP = "@LOG_EOP"
    Assume = "@LOG_ASSUME"

class LazyParse:
    def __init__(self, parse_fun, text):
        self.text = text
        self.parse_fun = parse_fun
    
    def __call__(self):
        if hasattr(self, 'result'):
            return self.result
        self.result = self.parse_fun(self.text)
        # no longer need text and parser
        del self.text
        del self.parse_fun
        return self.result

parser = SParser()

class Event(object):
    def __init__(self):
        global gid
        self.__dict__['id'] = gid
        gid += 1

    def __hash__(self):
        return self.id

    def _parse_symbol(self, string):
        try:
            sym = parser.parse(string)
            return sym
        except ply.lex.LexError as e:
            dbg.debug('Could not parse %r: %s', string, e)
        except Exception as e:
            import traceback
            traceback.print_exc()
            dbg.debug('Exception when parsing %r: %s', string, e)


    def __setattr__(self, name, value):
        raise TypeError("Event objects are immutable.")

def _call_name(txt):
    if txt is None: return None
    result = txt.split('(', 1)
    if len(result) < 2:
        return None
    return result[0]


class CallEvent(Event):
    def __init__(self, event, resolver):
        super().__init__()
        self.__dict__['kind'] = EventKind.Call

        for child in event:
            if child.tag == "KIND":
                assert child.text == self.kind.value
            elif child.tag == "CALL":
                self.__dict__['call_text'] = child.text
                self.__dict__['_call'] = LazyParse(self._parse_call, child.text)
                self.__dict__['_call_name'] = LazyParse(_call_name, child.text)

            elif child.tag == "CODE":
                self.__dict__['code'] = resolver(child.text)
            else:
                raise ValueError("Unknown tag for CallEvent")

    @property
    def call_name(self):
        return self._call_name()

    @property
    def call(self):
        return self._call()

    def _parse_call(self, text):
        sym = self._parse_symbol(text)
        if isinstance(sym, CallSymbol):
            return sym

class ReturnEvent(Event):
    def __init__(self, event, resolver):
        super().__init__()
        self.__dict__['kind'] = EventKind.Return

        for child in event:
            if child.tag == "KIND":
                assert child.text == self.kind.value
            elif child.tag == "RETURN":
                self.__dict__['call_text'] = child.text
                self.__dict__['_call'] = LazyParse(self._parse_call, child.text)
                self.__dict__['_call_name'] = LazyParse(_call_name, child.text)

            elif child.tag == "CODE":
                self.__dict__['code'] = resolver(child.text)
            else:
                raise ValueError("Unknown tag for CallEvent")

    @property
    def call_name(self):
        return self._call_name()

    @property
    def call(self):
        return self._call()

    def _parse_call(self, text):
        sym = self._parse_symbol(text)
        if isinstance(sym, CallSymbol):
            return sym

class LocationEvent(Event):
    def __init__(self, event, resolver):
        super().__init__()
        self.__dict__['kind'] = EventKind.Location

        for child in event:
            if child.tag == "KIND":
                assert child.text == self.kind.value
            elif child.tag == "LOC":
                self.__dict__['loc_text'] = child.text
                self.__dict__['_loc'] = LazyParse(self.parse_symbol, child.text)
            elif child.tag == "TYPE":
                self.__dict__['type'] = child.text
            elif child.tag == "CODE":
                self.__dict__['code'] = resolver(child.text)
            else:
                raise ValueError("Unknown tag for LocationEvent")

    @property
    def loc(self):
        return self._loc()

    def is_store(self):
        return self.type == "STORE"

class EOPEvent(Event):
    def __init__(self, event):
        super().__init__()
        self.__dict__['kind'] = EventKind.EOP

        for child in event:
            if child.tag == "KIND":
                assert child.text == self.kind.value
            else:
                raise ValueError("Unknown tag for EOPEvent")

class AssumeEvent(Event):
    def __init__(self, event):
        super().__init__()
        self.__dict__['kind'] = EventKind.Assume

        for child in event:
            if child.tag == "KIND":
                assert child.text == self.kind.value
            elif child.tag == "COND":
                self.__dict__['cond_text'] = child.text
                self.__dict__['_cond'] = LazyParse(self.parse_cond, child.text)
            else:
                raise ValueError("Unknown tag for AssumeEvent")

    @property
    def cond(self):
        return self._cond()

    def parse_cond(self, cond):
        # XXX: symbol can be UnknownSymbol when parsing failed
        sym = self._parse_symbol(cond)
        return sym
