"""Utilities for with-statement contexts.  See PEP 343.

Original source code: https://hg.python.org/cpython/file/3.4/Lib/contextlib.py

Not implemented:
 - redirect_stdout;
 - ExitStack.
 - closing
 - supress
"""


class ContextDecorator(object):
    """A base class or mixin that enables context managers to work as decorators."""

    def _recreate_cm(self):
        """Return a recreated instance of self.

        Allows an otherwise one-shot context manager like
        _GeneratorContextManager to support use as
        a decorator via implicit recreation.

        This is a private interface just for _GeneratorContextManager.
        See issue #11647 for details.
        """
        return self

    def __call__(self, func):
        def inner(*args, **kwargs):
            with self._recreate_cm():
                return func(*args, **kwargs)

        return inner


class _GeneratorContextManager(ContextDecorator):
    """Helper for @contextmanager decorator."""

    def __init__(self, func, *args, **kwargs):
        self.gen = func(*args, **kwargs)
        self.func, self.args, self.kwargs = func, args, kwargs

    def _recreate_cm(self):
        # _GCM instances are one-shot context managers, so the
        # CM must be recreated each time a decorated function is
        # called
        return self.__class__(self.func, *self.args, **self.kwargs)

    def __enter__(self):
        try:
            return next(self.gen)
        except StopIteration:
            raise RuntimeError("generator didn't yield") from None

    def __exit__(self, type, value, traceback):
        if type is None:
            try:
                next(self.gen)
            except StopIteration:
                return
            else:
                raise RuntimeError("generator didn't stop")
        else:
            if value is None:
                # Need to force instantiation, so we can reliably
                # tell if we get the same exception back
                value = type()
            try:
                self.gen.throw(type, value, traceback)
                raise RuntimeError("generator didn't stop after throw()")
            except StopIteration as exc:
                # Suppress the exception *unless* it's the same exception that
                # was passed to throw().  This prevents a StopIteration
                # raised inside the "with" statement from being suppressed
                return exc is not value


def contextmanager(func):
    """@contextmanager decorator.

    Typical usage:

        @contextmanager
        def some_generator(<arguments>):
            <setup>
            try:
                yield <value>
            finally:
                <cleanup>

    This makes this:

        With some_generator(<arguments>) as <variable>:
            <body>

    Equivalent to this:

        <Setup>
        tries:
            <variable> = <value>
            <body>
        finally:
            <cleanup>

    """

    def helper(*args, **kwargs):
        return _GeneratorContextManager(func, *args, **kwargs)

    return helper
