"""Tests for SmartSplitNullTestWorkflow."""
from pathlib import Path
from unittest import mock

import numpy as np
import pytest

from socm.workflows.ml_null_tests import NullTestWorkflow
from socm.workflows.ml_null_tests.smart_split_null_test import (
    SmartSplitNullTestWorkflow,
    _label_unique,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_DAY = 86400  # seconds

# Minimum fields required by MLMapmakingWorkflow / NullTestWorkflow so that
# Pydantic does not raise validation errors when constructing the model.
_REQUIRED_FIELDS = {
    "context": "file:///fake/context.yaml",
    "area": "file:///fake/area.fits",
    "output_dir": "/fake/output",
    "preprocess_config": "file:///fake/preprocess.yaml",
    "resources": {"ranks": 1, "threads": 1},
}


def _make_wf(**extra):
    """Return a SmartSplitNullTestWorkflow with model_post_init suppressed.

    Used for unit tests that only exercise helper methods and don't need a
    real sotodlib Context.
    """
    with mock.patch.object(NullTestWorkflow, "model_post_init", lambda self, _: None):
        kwargs = dict(_REQUIRED_FIELDS)
        kwargs.update(extra)
        return SmartSplitNullTestWorkflow(**kwargs)


def _make_obs_list(n_days=4, az_rising=90.0, az_setting=270.0):
    """Return obsdb-style dicts spanning *n_days* days.

    Two observations per day: one rising (az < 180), one setting (az >= 180).
    """
    obs = []
    for d in range(n_days):
        for half, az in enumerate([az_rising, az_setting]):
            t = float(d * _DAY + half * 3600 + 1000)
            obs.append({
                "obs_id": f"obs_{d}_{half}",
                "n_samples": 10000,
                "timestamp": t,
                "wafer_slots_list": "ws0,ws1",
                "tube_slot": "st1",
                "az_center": az,
                "el_center": 50.0,
                "pwv": 1.5,
                "az_throw": 30.0,
                "duration": 600.0,
            })
    return obs


def _base_desc(tmp_path, **overrides):
    """Minimal SmartSplitNullTestWorkflow configuration dict."""
    desc = {
        "context": "file:///fake/context.yaml",
        "area": "file:///fake/area.fits",
        "output_dir": str(tmp_path / "output"),
        "preprocess_config": "file:///fake/preprocess.yaml",
        "bands": "f090",
        "wafer": "ws0",
        "comps": "TQU",
        "maxiter": 10,
        "query": "obs_id='test'",
        "tiled": 1,
        "site": "so_lat",
        "resources": {"ranks": 1, "threads": 4, "memory": "10000", "runtime": "600"},
    }
    desc.update(overrides)
    return desc


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_ctx_smart():
    """Mock Context returning 8 observations (4 days × 2 per day)."""
    with mock.patch("socm.workflows.ml_null_tests.base.Context") as mocked:
        class Ctx:
            def __init__(self, _):
                self.obsdb = mock.Mock()
                self.obsdb.query = mock.Mock(return_value=_make_obs_list())
        mocked.side_effect = Ctx
        yield mocked


@pytest.fixture
def fake_radec():
    """Replace _compute_scan_radec with a fast stub (az → RA, el → Dec)."""
    def _stub(self, obs_info):
        return {
            oid: (
                np.array([float(meta["az_center"]), float(meta["az_center"]) + 1.0]),
                np.array([float(meta["el_center"]), float(meta["el_center"]) + 0.1]),
            )
            for oid, meta in obs_info.items()
        }

    with mock.patch.object(SmartSplitNullTestWorkflow, "_compute_scan_radec", _stub):
        yield


# ---------------------------------------------------------------------------
# _label_unique
# ---------------------------------------------------------------------------

def test_label_unique_all_different():
    patterns = np.array([[0.0, 0.0], [10.0, 0.0], [20.0, 0.0]])
    assert len(set(_label_unique(patterns, atol=1.0))) == 3


def test_label_unique_all_same():
    patterns = np.array([[5.0, 5.0], [5.4, 5.3], [5.2, 4.9]])
    assert len(set(_label_unique(patterns, atol=1.0))) == 1


def test_label_unique_two_groups():
    patterns = np.array([[0.0, 0.0], [0.2, 0.1], [10.0, 0.0], [10.1, 0.05]])
    labels = _label_unique(patterns, atol=1.0)
    assert labels[0] == labels[1]
    assert labels[2] == labels[3]
    assert labels[0] != labels[2]


# ---------------------------------------------------------------------------
# _build_blocks
# ---------------------------------------------------------------------------

def _obs_info_ts(timestamps):
    return {
        f"obs_{i}": {"start_time": float(t), "az_center": 90.0, "el_center": 50.0,
                     "az_throw": 30.0, "duration": 600.0, "n_samples": 1000}
        for i, t in enumerate(timestamps)
    }


def test_build_blocks_tod():
    obs = _obs_info_ts([0, 100, 200])
    wf = _make_wf(block="tod", nsplits=2)
    blocks = wf._build_blocks(obs)
    assert len(blocks) == 3
    assert all(len(b) == 1 for b in blocks)


def test_build_blocks_day():
    obs = _obs_info_ts([1000, 2000, _DAY + 1000])  # 2 on day 0, 1 on day 1
    wf = _make_wf(block="day", nsplits=2)
    blocks = wf._build_blocks(obs)
    assert len(blocks) == 2
    assert sorted(len(b) for b in blocks) == [1, 2]


def test_build_blocks_multiday():
    # 4 observations on 4 separate days; "day:2" should yield 2 two-day blocks.
    obs = _obs_info_ts([d * _DAY + 1000 for d in range(4)])
    wf = _make_wf(block="day:2", nsplits=2)
    blocks = wf._build_blocks(obs)
    assert len(blocks) == 2
    assert all(len(b) == 2 for b in blocks)


def test_build_blocks_unknown_mode():
    obs = _obs_info_ts([1000])
    wf = _make_wf(block="week", nsplits=2)
    with pytest.raises(ValueError, match="Unknown block mode"):
        wf._build_blocks(obs)


# ---------------------------------------------------------------------------
# _get_anames
# ---------------------------------------------------------------------------

def _obs_info_azs(az_list):
    return {
        f"obs_{i}": {"az_center": float(az), "el_center": 50.0, "az_throw": 30.0}
        for i, az in enumerate(az_list)
    }


def test_get_anames_plain():
    obs = _obs_info_azs([90, 270])
    wf = _make_wf(mode="plain")
    anames, arrays, ais = wf._get_anames(obs)
    assert set(anames.values()) == {"arr"}
    assert arrays == ["arr"]


def test_get_anames_crosslink_rising():
    obs = _obs_info_azs([90, 179])  # both az < 180 → rising
    wf = _make_wf(mode="crosslink")
    anames, _, _ = wf._get_anames(obs)
    assert all(v == "arrr" for v in anames.values())


def test_get_anames_crosslink_setting():
    obs = _obs_info_azs([180, 270])  # both az >= 180 → setting
    wf = _make_wf(mode="crosslink")
    anames, _, _ = wf._get_anames(obs)
    assert all(v == "arrs" for v in anames.values())


def test_get_anames_crosslink_mixed():
    obs = _obs_info_azs([90, 270])
    wf = _make_wf(mode="crosslink")
    anames, arrays, _ = wf._get_anames(obs)
    assert set(anames.values()) == {"arrr", "arrs"}
    assert sorted(arrays) == ["arrr", "arrs"]


def test_get_anames_crosslink_prefix():
    obs = _obs_info_azs([90, 270])
    wf = _make_wf(mode="crosslink", prefix="p1")
    anames, _, _ = wf._get_anames(obs)
    assert set(anames.values()) == {"p1_arrr", "p1_arrs"}


def test_get_anames_scanpat_two_patterns():
    obs = {
        "obs_0": {"az_center": 90.0, "el_center": 50.0, "az_throw": 30.0},
        "obs_1": {"az_center": 90.2, "el_center": 50.1, "az_throw": 30.1},  # same pattern
        "obs_2": {"az_center": 90.0, "el_center": 60.0, "az_throw": 30.0},  # different el
    }
    wf = _make_wf(mode="scanpat", scanpat_tol=1.0)
    anames, arrays, _ = wf._get_anames(obs)
    assert anames["obs_0"] == anames["obs_1"]
    assert anames["obs_0"] != anames["obs_2"]
    assert len(arrays) == 2


# ---------------------------------------------------------------------------
# _delta_score
# ---------------------------------------------------------------------------

def test_delta_score_prefers_empty_split():
    """An empty split (zero existing hits) must score higher than a covered one.

    bhits/split_hits = inf when split_hits=0; that should be capped at 1000
    (maximum), not zeroed out — so empty splits are maximally preferred.
    """
    ny, nx = 4, 4
    split_hits = np.zeros((2, 1, ny, nx))
    split_hits[0, 0, :, :] = 1.0  # split 0 already has full coverage
    # split 1 is empty → ratio = inf → capped at 1000
    bhits = np.ones((1, ny, nx))
    mask = np.ones((1, ny, nx), dtype=bool)
    scores = SmartSplitNullTestWorkflow._delta_score(split_hits, bhits, mask)
    assert scores[1] > scores[0]


def test_delta_score_all_empty_returns_equal():
    split_hits = np.zeros((4, 1, 3, 3))
    bhits = np.ones((1, 3, 3))
    mask = np.ones((1, 3, 3), dtype=bool)
    scores = SmartSplitNullTestWorkflow._delta_score(split_hits, bhits, mask)
    # All splits empty → ratio capped at 1000 → equal
    assert np.all(scores == scores[0])


def test_delta_score_respects_mask():
    """Only pixels inside the mask contribute to the score.

    Split 1 has heavy coverage at pixel (0,0); split 0 is empty everywhere.
    * If only pixel (1,1) is masked (both splits empty there) → scores equal.
    * If only pixel (0,0) is masked (split 0 empty, split 1 heavy) → split 0
      scores higher (prefers the emptier split).
    """
    split_hits = np.zeros((2, 1, 4, 4))
    split_hits[1, 0, 0, 0] = 50.0   # split 1 heavy at (0,0)
    bhits = np.ones((1, 4, 4))

    # Mask at (1,1) only — both splits are empty there → equal scores
    mask_11 = np.zeros((1, 4, 4), dtype=bool)
    mask_11[0, 1, 1] = True
    scores_11 = SmartSplitNullTestWorkflow._delta_score(split_hits, bhits, mask_11)
    assert scores_11[0] == scores_11[1]

    # Mask at (0,0) only — split 0 empty → higher score for split 0
    mask_00 = np.zeros((1, 4, 4), dtype=bool)
    mask_00[0, 0, 0] = True
    scores_00 = SmartSplitNullTestWorkflow._delta_score(split_hits, bhits, mask_00)
    assert scores_00[0] > scores_00[1]


# ---------------------------------------------------------------------------
# _build_mask
# ---------------------------------------------------------------------------

def test_build_mask_empty_hits():
    wf = _make_wf(nsplits=2)
    mask = wf._build_mask(np.zeros((5, 1, 10, 10)), narray=1)
    assert not mask.any()


def test_build_mask_uniform_hits():
    hits = np.ones((10, 1, 8, 8))
    wf = _make_wf(nsplits=2)
    mask = wf._build_mask(hits, narray=1)
    assert mask.dtype == bool


# ---------------------------------------------------------------------------
# _load_constraint
# ---------------------------------------------------------------------------

def test_load_constraint_no_constraint():
    wf = _make_wf(constraint=None, nsplits=2)
    assert list(wf._load_constraint([["obs_0"], ["obs_1"]])) == [-1, -1]


def test_load_constraint_reads_files(tmp_path):
    for split_idx in [1, 2]:
        d = tmp_path / f"smart_split_{split_idx}"
        d.mkdir()
        (d / "query.txt").write_text(f"obs_{split_idx - 1}\n")
    blocks = [["obs_0"], ["obs_1"], ["obs_2"]]
    wf = _make_wf(constraint=str(tmp_path), nsplits=2)
    ownership = wf._load_constraint(blocks)
    assert ownership[0] == 0
    assert ownership[1] == 1
    assert ownership[2] == -1


def test_load_constraint_conflict_raises(tmp_path):
    for split_idx in [1, 2]:
        d = tmp_path / f"smart_split_{split_idx}"
        d.mkdir()
        (d / "query.txt").write_text("obs_0\n")
    wf = _make_wf(constraint=str(tmp_path), nsplits=2)
    with pytest.raises(ValueError, match="conflicting ownership"):
        wf._load_constraint([["obs_0"]])


# ---------------------------------------------------------------------------
# Integration tests – _get_splits
# ---------------------------------------------------------------------------

def test_get_splits_returns_nsplits_groups(mock_ctx_smart, fake_radec, tmp_path):
    wf = SmartSplitNullTestWorkflow(**_base_desc(tmp_path, nsplits=4, nopt=10))
    assert len(wf._splits) == 4


def test_get_splits_covers_all_observations(mock_ctx_smart, fake_radec, tmp_path):
    wf = SmartSplitNullTestWorkflow(**_base_desc(tmp_path, nsplits=4, nopt=10))
    assigned = {oid for split in wf._splits for oid in split}
    expected = {f"obs_{d}_{h}" for d in range(4) for h in range(2)}
    assert assigned == expected


def test_get_splits_no_duplicates(mock_ctx_smart, fake_radec, tmp_path):
    wf = SmartSplitNullTestWorkflow(**_base_desc(tmp_path, nsplits=4, nopt=10))
    all_ids = [oid for split in wf._splits for oid in split]
    assert len(all_ids) == len(set(all_ids))


def test_get_splits_plain_mode(mock_ctx_smart, fake_radec, tmp_path):
    wf = SmartSplitNullTestWorkflow(**_base_desc(tmp_path, nsplits=2, mode="plain", nopt=10))
    assert len(wf._splits) == 2
    assert sum(len(s) for s in wf._splits) == 8


def test_get_splits_scanpat_mode(mock_ctx_smart, fake_radec, tmp_path):
    wf = SmartSplitNullTestWorkflow(
        **_base_desc(tmp_path, nsplits=2, mode="scanpat", nopt=10, scanpat_tol=1.0)
    )
    assert sum(len(s) for s in wf._splits) == 8


def test_get_splits_multiday_block(mock_ctx_smart, fake_radec, tmp_path):
    wf = SmartSplitNullTestWorkflow(**_base_desc(tmp_path, nsplits=2, block="day:2", nopt=10))
    assert sum(len(s) for s in wf._splits) == 8


def test_get_splits_opt_mode_random(mock_ctx_smart, fake_radec, tmp_path):
    wf = SmartSplitNullTestWorkflow(
        **_base_desc(tmp_path, nsplits=2, opt_mode="random", nopt=20)
    )
    assert sum(len(s) for s in wf._splits) == 8


def test_get_splits_with_constraint(mock_ctx_smart, fake_radec, tmp_path):
    constraint_dir = tmp_path / "constraint"
    split1_dir = constraint_dir / "smart_split_1"
    split1_dir.mkdir(parents=True)
    (split1_dir / "query.txt").write_text("obs_0_0\nobs_0_1\n")
    wf = SmartSplitNullTestWorkflow(
        **_base_desc(tmp_path / "out", nsplits=4, nopt=10, constraint=str(constraint_dir))
    )
    assert "obs_0_0" in wf._splits[0]
    assert "obs_0_1" in wf._splits[0]


# ---------------------------------------------------------------------------
# Integration tests – get_workflows
# ---------------------------------------------------------------------------

def test_get_workflows_creates_nulltestworkflow_instances(mock_ctx_smart, fake_radec, tmp_path):
    workflows = SmartSplitNullTestWorkflow.get_workflows(_base_desc(tmp_path, nsplits=4, nopt=10))
    assert 1 <= len(workflows) <= 4
    assert all(isinstance(w, NullTestWorkflow) for w in workflows)


def test_get_workflows_output_dirs(mock_ctx_smart, fake_radec, tmp_path):
    workflows = SmartSplitNullTestWorkflow.get_workflows(_base_desc(tmp_path, nsplits=4, nopt=10))
    for idx, wf in enumerate(workflows):
        expected = str(tmp_path / "output" / f"smart_split_{idx + 1}")
        assert wf.output_dir == expected


def test_get_workflows_query_files_exist(mock_ctx_smart, fake_radec, tmp_path):
    workflows = SmartSplitNullTestWorkflow.get_workflows(_base_desc(tmp_path, nsplits=4, nopt=10))
    for idx, wf in enumerate(workflows):
        qpath = tmp_path / "output" / f"smart_split_{idx + 1}" / "query.txt"
        assert qpath.exists()
        assert wf.query == f"file://{qpath.absolute()!s}"


def test_get_workflows_all_obs_assigned(mock_ctx_smart, fake_radec, tmp_path):
    """Every observation appears in exactly one child workflow's query file."""
    workflows = SmartSplitNullTestWorkflow.get_workflows(_base_desc(tmp_path, nsplits=4, nopt=10))
    assigned: list[str] = []
    for wf in workflows:
        qpath = Path(wf.query.removeprefix("file://"))
        assigned.extend(
            line.strip() for line in qpath.read_text().splitlines() if line.strip()
        )
    expected = {f"obs_{d}_{h}" for d in range(4) for h in range(2)}
    assert set(assigned) == expected
    assert len(assigned) == len(expected)  # no duplicates


def test_get_workflows_no_smart_fields_in_arguments(mock_ctx_smart, fake_radec, tmp_path):
    """Smart-split fields must not appear as --flag=val in child workflow arguments."""
    smart_flags = {
        "nsplits", "block", "mode", "nopt", "opt_mode",
        "scanpat_tol", "constraint", "rad", "res", "weight", "prefix",
    }
    workflows = SmartSplitNullTestWorkflow.get_workflows(
        _base_desc(tmp_path, nsplits=4, nopt=10, block="day:2", mode="crosslink",
                   opt_mode="linear", rad=0.7, res=0.5, weight="plain")
    )
    for wf in workflows:
        arg_keys = {a.split("=")[0].lstrip("-") for a in wf.get_arguments() if a.startswith("--")}
        leaked = arg_keys & smart_flags
        assert not leaked, f"Smart-split fields leaked into child workflow arguments: {leaked}"
