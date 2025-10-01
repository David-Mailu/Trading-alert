from ctypes.wintypes import SMALL_RECT

from Logic import SRManager, Reversal


class uptrend:
    def __init__(self):
        self.sr=SRManager(self)
        self.reversal=Reversal()