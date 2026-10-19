import zipfile
from pathlib import Path

from scripts.package import ROOT, build, package_files


def test_package_allowlist_excludes_credentials_environments_and_tests():
    names = [p.relative_to(ROOT).as_posix() for p in package_files(ROOT)]
    assert "manifest.yaml" in names
    assert "provider/buffer.py" in names
    assert "tools/schedule_post.yaml" in names
    assert not any(name.startswith((".venv/", "tests/", "scripts/", "dist/")) for name in names)
    assert ".env" not in names
    assert not any("__pycache__" in name for name in names)


def test_package_is_a_valid_root_level_zip():
    result = build()
    with zipfile.ZipFile(result) as archive:
        assert archive.testzip() is None
        assert "manifest.yaml" in archive.namelist()
        assert "_assets/icon.png" in archive.namelist()
        assert all(
            not Path(name).is_absolute() and ".." not in Path(name).parts
            for name in archive.namelist()
        )
