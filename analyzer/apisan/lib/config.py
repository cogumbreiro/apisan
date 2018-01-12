from collections import ChainMap
import pathlib
import os

_DEFAULTS = dict(
    # value for determining majority
    threshold = 0.8,
    max_score = 100,
    reference = 3,
    skip_cache = False,
    ignored_log_levels = ["debug"],
)

def parse_json(fp):
    import json
    return json.load(fp)

def parse_yaml(fp):
    import yaml
    return yaml.load(fp)

_PARSERS = {
    ".json": parse_json,
    ".yaml": parse_yaml,
}

def parse(filename, ext=None):
    if ext is None:
        ext = pathlib.Path(filename).suffix
    try:
        return _PARSERS[ext](open(filename))
    except KeyError:
        raise ValueError("Unsupported extension " + ext)


class Options:
    def __init__(self, data):
        self.data = data
    
    def __getattr__(self, key):
        if not key.startswith("_"):
            return self.data[key]
        else:
            raise AttributeError(key)
    
    def push(self, data):
        self.data = ChainMap(data, self.data)
    
    def get(self, key, v):
        return self.data.get(key, v)
    
    def __repr__(self):
        return repr(self.data)

def defaults(env_var="APISAN_CONF", ext=None):
    try:
        conf = parse(os.getenv(env_var, "apisan.yaml"))
        return Options(ChainMap(conf, _DEFAULTS))
    except IOError:
        return Options(ChainMap({}, _DEFAULTS))



