import os
import tomllib

from socm.bookkeeper.bookkeeper import (
    SLURMISE_DIR_ENV,
    resolve_slurmise_dir,
    write_slurmise_toml,
)


def test_resolve_slurmise_dir_env_wins(monkeypatch, tmp_path):
    monkeypatch.setenv(SLURMISE_DIR_ENV, str(tmp_path / "shared"))
    assert resolve_slurmise_dir("/some/base") == str(tmp_path / "shared")


def test_resolve_slurmise_dir_expands_user(monkeypatch):
    monkeypatch.setenv(SLURMISE_DIR_ENV, "~/slurmise")
    assert resolve_slurmise_dir() == os.path.expanduser("~/slurmise")


def test_resolve_slurmise_dir_base_path(monkeypatch):
    monkeypatch.delenv(SLURMISE_DIR_ENV, raising=False)
    assert resolve_slurmise_dir("/some/base") == "/some/base/slurmise_dir"


def test_resolve_slurmise_dir_cwd(monkeypatch, tmp_path):
    monkeypatch.delenv(SLURMISE_DIR_ENV, raising=False)
    monkeypatch.chdir(tmp_path)
    assert resolve_slurmise_dir(None) == str(tmp_path / "slurmise_dir")


def test_resolve_slurmise_dir_empty_env_ignored(monkeypatch, tmp_path):
    monkeypatch.setenv(SLURMISE_DIR_ENV, "")
    assert resolve_slurmise_dir(str(tmp_path)) == str(tmp_path / "slurmise_dir")


def test_write_slurmise_toml(tmp_path):
    dest = write_slurmise_toml("/data/slurmise", tmp_path / "session" / "slurmise.toml")

    assert dest.exists()
    with open(dest, "rb") as f:
        config = tomllib.load(f)
    assert config["slurmise"]["base_dir"] == "/data/slurmise"
