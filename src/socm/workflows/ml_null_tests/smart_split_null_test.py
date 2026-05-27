import warnings
from math import ceil
from pathlib import Path
from typing import Dict, List, Optional, Union

import numpy as np
from scipy.ndimage import uniform_filter
from sotodlib.core import Context

from socm.workflows.ml_null_tests import NullTestWorkflow

# Simons Observatory site (Atacama, Chile) — same as pixell.coordinates.default_site
_SO_LAT = -22.9585   # degrees North
_SO_LON = -67.7876   # degrees East
_SO_ALT = 5188.0     # metres above sea level

# Fields unique to this workflow that must be stripped before spawning child NullTestWorkflows
_SMART_FIELDS = frozenset({
    "nsplits", "block", "mode", "nopt", "opt_mode",
    "scanpat_tol", "constraint", "rad", "res", "weight", "prefix",
})


def _label_unique(patterns: np.ndarray, atol: float) -> np.ndarray:
    """Assign integer labels so rows within *atol* of an existing centroid share a label."""
    labels = np.full(len(patterns), -1, dtype=int)
    centroids: List[np.ndarray] = []
    for i, row in enumerate(patterns):
        for lid, cent in enumerate(centroids):
            if np.all(np.abs(row - cent) <= atol):
                labels[i] = lid
                break
        else:
            labels[i] = len(centroids)
            centroids.append(row.copy())
    return labels


class SmartSplitNullTestWorkflow(NullTestWorkflow):
    """
    A smart-split null-test workflow.

    Ports the algorithm from tenki/smartsplit.py for SO/sotodlib, replacing
    enlib/enact with astropy for sky-coordinate transforms and scipy for
    hitmap smoothing.  Observations are grouped into blocks, sorted largest-
    first, then assigned to splits with a greedy hitmap-score algorithm.  An
    optional sequence of relocate-based optimisation passes further improves
    balance.

    New parameters relative to the other null-test workflows
    ---------------------------------------------------------
    block : str
        Grouping mode.  ``"day"`` (default) or ``"tod"``, optionally with a
        colon-separated size multiplier, e.g. ``"day:2"`` for 2-day blocks.
    mode : str
        ``"plain"``, ``"crosslink"`` (default), or ``"scanpat"``.
        In crosslink mode rising and setting scans are balanced independently.
        In scanpat mode each unique (az, el, az_throw) scanning pattern is
        treated as a separate sub-population.
    nopt : int
        Number of block-relocate optimisation passes (default 2000).
    opt_mode : str
        ``"linear"`` (default) cycles through free blocks in order;
        ``"random"`` draws random block indices.
    scanpat_tol : float
        Tolerance in degrees for grouping scan patterns (only used when
        ``mode="scanpat"``).
    constraint : str or None
        Path to a directory that contains ``smart_split_N/query.txt`` files
        from a previous run.  Blocks whose observations appear in those files
        are pre-assigned and excluded from optimisation.
    rad : float
        Tophat smoothing radius in degrees applied to per-block hitmaps
        (default 0.7).
    res : float
        Sky-map pixel size in degrees (default 0.5).
    weight : str
        ``"plain"`` weights each scan by its duration; ``"det"`` weights by
        ``n_samples`` (proxy for detector count × duration).
    prefix : str or None
        Optional string prepended to virtual array names in the output.
    """

    nsplits: int = 4
    block: str = "day"
    mode: str = "crosslink"
    nopt: int = 2000
    opt_mode: str = "linear"
    scanpat_tol: float = 1.0
    constraint: Optional[str] = None
    rad: float = 0.7
    res: float = 0.5
    weight: str = "plain"
    prefix: Optional[str] = None
    name: str = "smart_split_null_test_workflow"

    # ------------------------------------------------------------------
    # Block construction
    # ------------------------------------------------------------------

    def _parse_block_params(self):
        """Return (block_mode, block_size) from the ``block`` field."""
        toks = self.block.split(":")
        return toks[0], float(toks[1]) if len(toks) > 1 else 1.0

    def _build_blocks(
        self, obs_info: Dict[str, Dict[str, Union[float, str]]]
    ) -> List[List[str]]:
        block_mode, block_size = self._parse_block_params()
        if block_mode == "tod":
            return [[oid] for oid in obs_info]
        elif block_mode == "day":
            groups: Dict[int, List[str]] = {}
            for oid, meta in obs_info.items():
                key = int(int(meta["start_time"]) // 86400 // block_size)
                groups.setdefault(key, []).append(oid)
            return [groups[k] for k in sorted(groups)]
        else:
            raise ValueError(f"Unknown block mode: {block_mode!r}. Expected 'day' or 'tod'.")

    # ------------------------------------------------------------------
    # Virtual array assignment
    # ------------------------------------------------------------------

    def _get_anames(
        self, obs_info: Dict[str, Dict[str, Union[float, str]]]
    ):
        """Return ``(aname_per_obs, unique_array_list, obs_to_array_index)``."""
        base = f"{self.prefix}_arr" if self.prefix else "arr"

        if self.mode == "crosslink":
            anames = {
                oid: base + ("r" if float(meta["az_center"]) % 360 < 180 else "s")
                for oid, meta in obs_info.items()
            }
        elif self.mode == "scanpat":
            obs_ids = list(obs_info.keys())
            patterns = np.array([
                [float(obs_info[oid]["az_center"]),
                 float(obs_info[oid]["el_center"]),
                 float(obs_info[oid]["az_throw"])]
                for oid in obs_ids
            ])
            pids = _label_unique(patterns, atol=self.scanpat_tol)
            anames = {oid: f"{base}p{pids[i]}" for i, oid in enumerate(obs_ids)}
        else:  # plain
            anames = {oid: base for oid in obs_info}

        arrays = sorted(set(anames.values()))
        ais = {oid: arrays.index(anames[oid]) for oid in obs_info}
        return anames, arrays, ais

    # ------------------------------------------------------------------
    # Hitmap construction
    # ------------------------------------------------------------------

    def _compute_scan_radec(
        self, obs_info: Dict[str, Dict[str, Union[float, str]]]
    ) -> Dict[str, tuple]:
        """Batch-convert all observation scan paths from AltAz to ICRS.

        Returns a dict mapping obs_id to ``(ra_deg_array, dec_deg_array)``.
        Requires an internet connection the first time (IERS table download);
        subsequent runs use the astropy cache.
        """
        import astropy.units as u
        from astropy.coordinates import AltAz, EarthLocation, SkyCoord
        from astropy.time import Time

        site = EarthLocation(
            lat=_SO_LAT * u.deg, lon=_SO_LON * u.deg, height=_SO_ALT * u.m
        )

        obs_ids: List[str] = list(obs_info.keys())
        all_az: List[np.ndarray] = []
        all_el: List[np.ndarray] = []
        all_t: List[np.ndarray] = []
        npts_per_obs: List[int] = []

        for oid in obs_ids:
            meta = obs_info[oid]
            az_c = float(meta["az_center"])
            el_c = float(meta["el_center"])
            az_throw = float(meta["az_throw"])
            dur = float(meta["duration"])
            t_mid = float(meta["start_time"]) + dur / 2.0
            n_az = max(2, int(abs(az_throw) / self.res + 1))
            azs = np.linspace(az_c - az_throw / 2.0, az_c + az_throw / 2.0, n_az)
            all_az.append(azs)
            all_el.append(np.full(n_az, el_c))
            all_t.append(np.full(n_az, t_mid))
            npts_per_obs.append(n_az)

        az_arr = np.concatenate(all_az)
        el_arr = np.concatenate(all_el)
        t_arr = np.concatenate(all_t)

        times = Time(t_arr, format="unix")
        frame = AltAz(obstime=times, location=site)
        coords = SkyCoord(az=az_arr * u.deg, alt=el_arr * u.deg, frame=frame)
        icrs = coords.icrs
        ras: np.ndarray = np.asarray(icrs.ra.deg)
        decs: np.ndarray = np.asarray(icrs.dec.deg)

        result: Dict[str, tuple] = {}
        i = 0
        for oid, npts in zip(obs_ids, npts_per_obs):
            result[oid] = (ras[i:i + npts], decs[i:i + npts])
            i += npts
        return result

    def _build_grid(self, scan_radec: Dict[str, tuple]):
        """Determine the RA/Dec grid parameters from all scan paths.

        Returns ``(ra_min, dec_min, ny, nx, ra_median)`` where
        ``ra_min`` / ``dec_min`` are the lower-left corners in degrees.
        """
        all_ras = np.concatenate([r for r, _ in scan_radec.values()])
        all_decs = np.concatenate([d for _, d in scan_radec.values()])

        # Unwrap RA around the median to handle the 0°/360° boundary.
        ra_med = float(np.median(all_ras))
        ra_uw = all_ras.copy()
        ra_uw[ra_uw < ra_med - 180.0] += 360.0
        ra_uw[ra_uw > ra_med + 180.0] -= 360.0

        pad = max(self.rad * 2.0, self.res)
        ra_min = float(np.min(ra_uw)) - pad
        ra_max = float(np.max(ra_uw)) + pad
        dec_min = float(np.min(all_decs)) - pad
        dec_max = float(np.max(all_decs)) + pad

        ny = max(1, int(ceil((dec_max - dec_min) / self.res)))
        nx = max(1, int(ceil((ra_max - ra_min) / self.res)))
        return ra_min, dec_min, ny, nx, ra_med

    def _obs_hitmap(
        self,
        oid: str,
        obs_info: Dict[str, Dict[str, Union[float, str]]],
        scan_radec: Dict[str, tuple],
        ra_min: float,
        dec_min: float,
        ny: int,
        nx: int,
        ra_med: float,
    ) -> np.ndarray:
        """Rasterise one observation onto a ``(ny, nx)`` hitmap."""
        ras, decs = scan_radec[oid]
        meta = obs_info[oid]
        dur = float(meta["duration"])
        n_samples = int(meta["n_samples"])

        ra_uw = ras.copy()
        ra_uw[ra_uw < ra_med - 180.0] += 360.0
        ra_uw[ra_uw > ra_med + 180.0] -= 360.0

        xi = np.round((ra_uw - ra_min) / self.res).astype(int)
        yi = np.round((decs - dec_min) / self.res).astype(int)
        valid = (xi >= 0) & (xi < nx) & (yi >= 0) & (yi < ny)
        xi, yi = xi[valid], yi[valid]

        w = (n_samples if self.weight == "det" else dur) / max(1, len(ras))

        hm = np.zeros((ny, nx), dtype=np.float64)
        np.add.at(hm, (yi, xi), w)
        return hm

    def _build_block_hits(
        self,
        blocks: List[List[str]],
        obs_info: Dict[str, Dict[str, Union[float, str]]],
        ais: Dict[str, int],
        narray: int,
        scan_radec: Dict[str, tuple],
        ra_min: float,
        dec_min: float,
        ny: int,
        nx: int,
        ra_med: float,
    ) -> np.ndarray:
        """Build per-block, per-array hitmaps ``hits[nblock, narray, ny, nx]``."""
        nblock = len(blocks)
        hits = np.zeros((nblock, narray, ny, nx), dtype=np.float64)
        smooth_size = 2 * max(1, int(self.rad / self.res)) + 1

        for bi, block in enumerate(blocks):
            raw = np.zeros((narray, ny, nx), dtype=np.float64)
            for oid in block:
                raw[ais[oid]] += self._obs_hitmap(
                    oid, obs_info, scan_radec, ra_min, dec_min, ny, nx, ra_med
                )
            for ai in range(narray):
                if raw[ai].any():
                    raw[ai] = uniform_filter(raw[ai], size=smooth_size, mode="constant")
            hits[bi] = raw

        return hits

    def _build_mask(self, hits: np.ndarray, narray: int) -> np.ndarray:
        """Build coverage mask ``[narray, ny, nx]`` for well-sampled pixels."""
        ny, nx = hits.shape[-2], hits.shape[-1]
        mask = np.zeros((narray, ny, nx), dtype=bool)
        for ai in range(narray):
            ahits = hits[:, ai]
            nonzero = ahits[ahits > 0]
            if not nonzero.size:
                continue
            ref = float(np.median(nonzero))
            nblock_per_pix = np.sum(ahits > ref * 0.2, axis=0)
            pos = nblock_per_pix[nblock_per_pix > 0]
            nbref = float(np.median(pos)) if pos.size else 1.0
            nblock_lim = min(2 * self.nsplits, nbref * 0.2)
            mask[ai] = nblock_per_pix > nblock_lim
        return mask

    @staticmethod
    def _delta_score(
        split_hits: np.ndarray, bhits: np.ndarray, mask: np.ndarray
    ) -> np.ndarray:
        """Score each split by its fractional coverage gain from adding *bhits*.

        ``split_hits`` is ``[nsplit, narray, ny, nx]``;
        ``bhits`` and ``mask`` are ``[narray, ny, nx]``.
        Returns ``[nsplit]``.
        """
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            ratio = bhits / split_hits   # broadcasts to [nsplit, narray, ny, nx]
        # Replace only NaN (0/0: no hits on either side → no contribution).
        # Inf (something/0: empty split) is left for the min-cap so that empty
        # splits receive the maximum possible score — matching the original.
        ratio = np.where(np.isnan(ratio), 0.0, ratio)
        ratio = np.minimum(ratio, 1000.0)
        flat_mask = mask.ravel()
        ratio_flat = ratio.reshape(split_hits.shape[0], -1)
        return np.sum(ratio_flat[:, flat_mask], axis=-1)

    # ------------------------------------------------------------------
    # Constraint loading
    # ------------------------------------------------------------------

    def _load_constraint(
        self, blocks: List[List[str]]
    ) -> np.ndarray:
        """Return block ownership array (``-1`` = free) from *constraint* dir."""
        block_ownership = np.full(len(blocks), -1, dtype=int)
        if not self.constraint:
            return block_ownership

        constraint_dir = Path(self.constraint)
        for split_idx in range(self.nsplits):
            qfile = constraint_dir / f"smart_split_{split_idx + 1}" / "query.txt"
            if not qfile.exists():
                continue
            with open(qfile) as fh:
                existing = {line.strip() for line in fh if line.strip()}
            for bi, block in enumerate(blocks):
                overlap = set(block) & existing
                if not overlap:
                    continue
                if block_ownership[bi] >= 0 and block_ownership[bi] != split_idx:
                    raise ValueError(
                        f"Block {bi} has conflicting ownership in constraint directory."
                    )
                block_ownership[bi] = split_idx

        return block_ownership

    # ------------------------------------------------------------------
    # Core split algorithm
    # ------------------------------------------------------------------

    def _get_splits(
        self, ctx: Context, obs_info: Dict[str, Dict[str, Union[float, str]]]
    ) -> List[List[str]]:
        """Assign observations to *nsplits* balanced groups.

        Algorithm
        ---------
        1. Group observations into blocks; sort blocks largest-first.
        2. Compute RA/Dec scan paths and build per-block hitmaps.
        3. Pre-assign blocks that appear in a constraint directory.
        4. Greedily assign free blocks to the split with the highest
           fractional coverage gain.
        5. Run *nopt* relocate-optimisation passes.
        """
        if len(obs_info) < self.nsplits:
            obs_list = list(obs_info.keys())
            splits: List[List[str]] = [[] for _ in range(self.nsplits)]
            for i, oid in enumerate(obs_list):
                splits[i % self.nsplits].append(oid)
            return splits

        blocks = sorted(self._build_blocks(obs_info), key=len, reverse=True)

        _, arrays, ais = self._get_anames(obs_info)
        narray = len(arrays)

        block_ownership = self._load_constraint(blocks)
        fixed_blocks = np.where(block_ownership >= 0)[0]
        free_blocks = np.where(block_ownership < 0)[0]
        nfree = len(free_blocks)

        scan_radec = self._compute_scan_radec(obs_info)
        ra_min, dec_min, ny, nx, ra_med = self._build_grid(scan_radec)
        hits = self._build_block_hits(
            blocks, obs_info, ais, narray, scan_radec, ra_min, dec_min, ny, nx, ra_med
        )
        mask = self._build_mask(hits, narray)

        split_hits = np.zeros((self.nsplits, narray, ny, nx), dtype=np.float64)
        block_assignments = block_ownership.copy()

        # Pre-assign fixed blocks.
        for bi in fixed_blocks:
            split_hits[int(block_assignments[bi])] += hits[bi]

        # Greedy initial assignment for free blocks.
        for bi in free_blocks:
            score = self._delta_score(split_hits, hits[bi], mask)
            best = int(np.argmax(score))
            block_assignments[bi] = best
            split_hits[best] += hits[bi]

        # Relocate-based optimisation.
        nopt_actual = self.nopt if self.nsplits > 1 else 0
        rng = np.random.default_rng(seed=0)
        if self.opt_mode == "linear":
            opt_order = np.arange(nopt_actual) % max(1, nfree)
        else:  # "random"
            opt_order = rng.integers(0, max(1, nfree), nopt_actual)

        for step in range(nopt_actual):
            if nfree == 0:
                break
            bi = int(free_blocks[opt_order[step]])
            scur = int(block_assignments[bi])
            bhits = hits[bi]

            split_hits[scur] = np.maximum(0.0, split_hits[scur] - bhits)
            score = self._delta_score(split_hits, bhits, mask)
            best = int(np.argmax(score))
            split_hits[best] += bhits
            block_assignments[bi] = best

        result: List[List[str]] = [[] for _ in range(self.nsplits)]
        for bi, block in enumerate(blocks):
            result[int(block_assignments[bi])].extend(block)

        return result

    # ------------------------------------------------------------------
    # Workflow factory
    # ------------------------------------------------------------------

    @classmethod
    def get_workflows(cls, desc: Optional[dict] = None) -> List[NullTestWorkflow]:
        """Create one NullTestWorkflow per non-empty smart-split group."""
        smart_workflow = cls(**(desc or {}))

        # Strip smartsplit-specific fields so child NullTestWorkflows do not
        # receive unknown keyword arguments or spurious command-line flags.
        base_desc = {
            k: v
            for k, v in smart_workflow.model_dump(exclude_unset=True).items()
            if k not in _SMART_FIELDS
        }

        workflows: List[NullTestWorkflow] = []
        for split in smart_workflow._splits:
            if not split:
                continue
            desc_copy = dict(base_desc)
            split_idx = len(workflows) + 1
            desc_copy["name"] = f"smart_split_{split_idx}_null_test_workflow"
            desc_copy["output_dir"] = f"{smart_workflow.output_dir}/smart_split_{split_idx}"
            desc_copy["datasize"] = 0
            query_file = Path(desc_copy["output_dir"]) / "query.txt"
            query_file.parent.mkdir(parents=True, exist_ok=True)
            with open(query_file, "w") as fh:
                for oid in split:
                    fh.write(f"{oid}\n")
            desc_copy["query"] = f"file://{query_file.absolute()!s}"
            desc_copy["chunk_nobs"] = 1
            workflows.append(NullTestWorkflow(**dict(desc_copy)))

        return workflows
