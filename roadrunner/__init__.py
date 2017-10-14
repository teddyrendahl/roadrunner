from .block import BlockWatch
from .zmq   import ChipProgrammer

from ._version import get_versions
__version__ = get_versions()['version']
del get_versions
