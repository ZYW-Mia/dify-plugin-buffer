"""Run from the project root to validate manifests, assets, and entrypoint classes."""

from dify_plugin import DifyPluginEnv
from dify_plugin.core.plugin_registration import PluginRegistration

registration = PluginRegistration(DifyPluginEnv())
for provider, (_, _, tools) in registration.tools_mapping.items():
    print(f"{provider}: {len(tools)} tools loaded: {', '.join(tools)}")
