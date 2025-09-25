from ._version import __version__

_lazy_map = {
    "GazeEstimator": ("src.gaze", "GazeEstimator"),
    "make_kalman": ("src.filters", "make_kalman"),
    "run_9_point_calibration": ("src.calibration", "run_9_point_calibration"),
    "run_5_point_calibration": ("src.calibration", "run_5_point_calibration"),
}


def __getattr__(name: str):
    try:
        module_name, symbol = _lazy_map[name]
    except KeyError:
        raise AttributeError(name) from None

    import importlib

    module = importlib.import_module(module_name)
    value = getattr(module, symbol)
    globals()[name] = value
    return value


def __dir__():
    std_attrs = set(globals()) | {"__getattr__", "__dir__"}
    return sorted(std_attrs | _lazy_map.keys())


__all__ = list(_lazy_map) + ["__version__"]
