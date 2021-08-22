import contextvars
import types

request_global = contextvars.ContextVar("request_global",
                                        default=types.SimpleNamespace())


def g():
    return request_global.get()
