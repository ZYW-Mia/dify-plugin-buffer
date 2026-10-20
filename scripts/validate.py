"""Run from the project root to validate manifests, assets, and entrypoint classes."""

import re
from pathlib import Path

import yaml
from dify_plugin import DifyPluginEnv
from dify_plugin.core.plugin_registration import PluginRegistration


def validate_plugin_identity(root: Path) -> None:
    """Enforce the daemon's lowercase identity rules, which the Python SDK omits."""
    manifest = yaml.safe_load((root / "manifest.yaml").read_text())
    for field, maximum in (("author", 64), ("name", 128)):
        value = manifest.get(field)
        if not isinstance(value, str) or not re.fullmatch(rf"[a-z0-9_-]{{1,{maximum}}}", value):
            raise ValueError(
                f"manifest.yaml {field} must use 1–{maximum} lowercase letters, digits, "
                "underscores, or hyphens (Dify daemon identity requirement)."
            )


def main() -> None:
    validate_plugin_identity(Path.cwd())
    registration = PluginRegistration(DifyPluginEnv())
    for provider, (_, _, tools) in registration.tools_mapping.items():
        print(f"{provider}: {len(tools)} tools loaded: {', '.join(tools)}")


if __name__ == "__main__":
    main()
