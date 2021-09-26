# PyMixin

PyMixin is a python library designed to help inject code in a compatible way.
It is heavily inspired by the SpongePowered Mixin project.

## Features

### Redirect function calls

```python
>>> from mixin import *
>>> from math import log, log10
>>> 
>>> def test_function(n: int) -> int:
...     return log(n)
... 
>>> @redirect(method=test_function, at=At(value=AtValue.INVOKE, target=log))
... def real_input(n: int) -> int:
...     # Call log10 instead of log
...     return log10(n)
... 
>>> test_function(10)
1.0
```

### Change constants

```python
>>> from mixin import *
>>> from random import randint
>>> 
>>> def percent(n: int) -> float:
...     return n / 100
... 
>>> @modify_const(method=percent, at=At(value=AtValue.LOAD, target=100))
... def random_denominator():
...     return randint(0, 100)
... 
>>> percent(10)
0.2777777777777778
>>> percent(10)
0.35714285714285715
```

### Inject callbacks

```python
>>> from mixin import *
>>> 
>>> def internal_message_handler(data: bytes):
...     return  # Dummy implementation
... 
>>> @inject(method=internal_message_handler, at=At(value=AtValue.HEAD))
... def log_message(data: bytes, callback_info: CallbackInfo):
...     print("Received data:", data)
... 
>>> internal_message_handler(b"Hello world")
Received data: b'Hello world'
```

### Cancel functions

```python
>>> from mixin import *
>>> 
>>> def process(body: str):
...     if body == "Hello":
...         print("World")
...     else:
...         print("Invalid body")
... 
>>> @inject(method=process, at=At(value=AtValue.HEAD), cancellable=True)
... def cancel_if_bad(body: str, callback_info: CallbackInfo):
...     if body != "Hello":
...         callback_info.cancel()
... 
>>> process("Hello")
World
>>> process("World")
>>> 
```

### Modify returned value

```python
>>> from mixin import *
>>> 
>>> def return_n_squared(n):
...     return n * n
... 
>>> @inject(method=return_n_squared, at=At(value=AtValue.RETURN), cancellable=True)  # Warning: injects at EVERY return by default
... def return_n_cubed_instead(callback_info: CallbackInfo):
...     n = (callback_info.return_value**0.5)
...     callback_info.set_return(n**3)
... 
>>> return_n_squared(10)
1000.0
```

### Overwrite functions

```python
>>> from mixin import *
>>> 
>>> def spam_a():
...     while True:
...         print("a")
... 
>>> @overwrite(method=spam_a)
... def replacement():
...     print("b")
... 
>>> spam_a()
b
```

### A note on decorators

Often in python, a function is wrapped with a decorator. This means the value of a function is no longer the same.
To resolve this, we added `mixin.unwrap`, to get the original function back (assuming `functools.wraps`) was used.

```python
>>> from mixin import *
>>> from functools import wraps
>>> 
>>> def with_print(func):
...     @wraps(func)
...     def inner(*args, **kwargs):
...         print("args", args, kwargs)
...         return func(*args, **kwargs)
...     return inner
... 
>>> @with_print
... def test(n):
...     return n*2
... 
>>> @inject(method=unwrap(test), at=At(value=AtValue.HEAD))
... def log_n(n, callback_info):
...     print("N:", n)
... 
>>> test(10)
args (10,) {}
N: 10
20

```

## Installing

To install PyMixin, you can just use pip:

```shell
pip install pymixin
```

## License

PyMixin is licensed under MIT.
