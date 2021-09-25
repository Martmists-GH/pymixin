from dataclasses import dataclass
from typing import Any


class CancellationException(RuntimeError):
    def __init__(self):
        super().__init__("Mixin not marked as cancellable!")


@dataclass(eq=False)
class CallbackInfo:
    cancellable: bool = False
    return_value: Any = None

    _cancelled: bool = False

    def __call__(self, ret: Any = None):
        self.return_value = ret

    def cancel(self):
        if not self.cancellable:
            raise CancellationException()
        self._cancelled = True

    def set_return(self, val: Any):
        self.cancel()
        self.return_value = val
