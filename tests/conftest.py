# The SDK applies gevent patching at import time; load it before HTTP libraries.
import dify_plugin  # noqa: F401
