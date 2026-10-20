"""Build an unsigned .difypkg with the layout used by Dify's ZIP packager.

Reference: langgenius/dify-plugin-daemon 0.6.11,
pkg/plugin_packager/packager/packager.go (ordinary ZIP entries at the project root).
"""

import hashlib
import os
import zipfile
from pathlib import Path

from dify_plugin import DifyPluginEnv
from dify_plugin.core.plugin_registration import PluginRegistration

from scripts.validate import validate_plugin_identity

ROOT = Path(__file__).resolve().parents[1]
ROOT_FILES = ("manifest.yaml", "main.py", "requirements.txt", "README.md", "PRIVACY.md", "LICENSE")
SOURCE_DIRS = ("common", "provider", "tools", "_assets", "readme", "docs")
EXTENSIONS = {".py", ".yaml", ".svg", ".png", ".jpg", ".jpeg", ".webp", ".md"}


def package_files(root: Path) -> list[Path]:
    files = [root / name for name in ROOT_FILES]
    for folder in SOURCE_DIRS:
        files.extend(
            source
            for source in (root / folder).rglob("*")
            if source.is_file() and source.suffix in EXTENSIONS
        )
    for source in files:
        if source.is_symlink() or not source.resolve().is_relative_to(root.resolve()):
            raise ValueError(f"Refusing to package a symlink or external file: {source.name}")
        if not source.is_file():
            raise ValueError(f"Required package file missing: {source.name}")
    return sorted(files)


def build(root: Path = ROOT) -> Path:
    root = root.resolve()
    original_cwd = Path.cwd()
    try:
        os.chdir(root)
        validate_plugin_identity(root)
        registration = PluginRegistration(DifyPluginEnv())
        version = registration.configuration.version
        files = package_files(root)
        size = sum(source.stat().st_size for source in files)
        if size > 10 * 1024 * 1024:
            raise ValueError("Plugin sources exceed the 10 MiB package limit.")
        destination = root / "dist" / f"buffer-{version}.difypkg"
        destination.parent.mkdir(exist_ok=True)
        with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for source in files:
                entry = zipfile.ZipInfo(source.relative_to(root).as_posix())
                entry.date_time = (2026, 10, 16, 0, 0, 0)
                entry.compress_type = zipfile.ZIP_DEFLATED
                entry.external_attr = 0o100644 << 16
                archive.writestr(entry, source.read_bytes())
        digest = hashlib.sha256(destination.read_bytes()).hexdigest()
        destination.with_suffix(".difypkg.sha256").write_text(f"{digest}  {destination.name}\n")
        print(f"Built {destination}: {len(files)} files, {destination.stat().st_size} bytes")
        print(f"SHA256 {digest}")
        return destination
    finally:
        os.chdir(original_cwd)


if __name__ == "__main__":
    build()
