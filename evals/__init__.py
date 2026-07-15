import importlib
import pkgutil
from typing import Callable, Iterable

PairSource = Callable[[int], Iterable[tuple[str, str]]]


def discover() -> dict[str, PairSource]:
    """Each module in this package is an eval: its name is the eval name,
    and it must define pairs(n) yielding up to n (option, option) tuples.
    """
    found = {}
    for info in pkgutil.iter_modules(__path__):
        module = importlib.import_module(f"{__name__}.{info.name}")
        found[info.name] = module.pairs
    return found
