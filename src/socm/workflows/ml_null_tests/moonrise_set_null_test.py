from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Union

import numpy as np
from astral import LocationInfo
from astral.moon import moonrise, moonset
from sotodlib.core import Context

from socm.workflows.ml_null_tests import NullTestWorkflow


class MoonRiseSetNullTestWorkflow(NullTestWorkflow):
    """
    Null-test workflow that splits observations by whether the Moon is in the sky.

    Uses the `astral <https://astral.readthedocs.io/>`_ library and the SO
    site coordinates (San Pedro de Atacama, Chile) to determine the moonrise and
    moonset times for each observation's date. Observations taken while the Moon
    is above the horizon are classified as ``"insky"``; the remainder are
    classified as ``"outsky"``. Within each group ``nsplits = 2``
    time-interleaved splits are created. Child workflows follow the naming
    convention ``moon_{insky,outsky}_split_<N>_null_test_workflow``.

    Parameters
    ----------
    chunk_nobs : int or None, optional
        Number of observations per time chunk per moon-sky group. Defaults to
        ``None``.
    chunk_duration : timedelta or None, optional
        Duration per chunk (not yet implemented). Defaults to ``None``.
    nsplits : int, optional
        Number of time splits per group. Fixed to ``2``. Defaults to ``2``.
    name : str, optional
        Human-readable workflow name. Defaults to
        ``"moonset_null_test_workflow"``.
    """

    chunk_nobs: Optional[int] = None
    chunk_duration: Optional[timedelta] = None
    nsplits: int = 2  # Fixed to 2 as specified in the issue
    name: str = "moonset_null_test_workflow"

    def _get_splits(
        self, ctx: Context, obs_info: Dict[str, Dict[str, Union[float, str]]]
    ) -> Dict[str, List[List[str]]]:
        """
        Split observations based on whether the Moon is above the horizon.

        Computes moonrise/moonset times for the SO site on each observation
        date and classifies observations as ``"insky"`` (moon above horizon)
        or ``"outsky"`` (moon below horizon). Within each group, observations
        are sorted chronologically, chunked by ``chunk_nobs``, and distributed
        round-robin across ``nsplits`` (= 2) splits. Observations for which
        moonrise/moonset cannot be computed (``ValueError``) are silently
        skipped.

        Parameters
        ----------
        ctx : Context
            The sotodlib :class:`~sotodlib.core.Context` object (not used
            directly).
        obs_info : dict of str to dict
            Mapping of observation ID to metadata. The ``start_time`` key
            (Unix timestamp) is used.

        Returns
        -------
        dict of str to list of list of str
            Mapping of ``"insky"`` and ``"outsky"`` to lists of ``nsplits``
            splits, each containing the observation IDs for that group and
            split.

        Raises
        ------
        ValueError
            If neither ``chunk_nobs`` nor ``chunk_duration`` is set, or if
            both are set.
        NotImplementedError
            If ``chunk_duration`` is set (not yet implemented).
        """
        if self.chunk_nobs is None and self.chunk_duration is None:
            raise ValueError("Either chunk_nobs or duration must be set.")
        elif self.chunk_nobs is not None and self.chunk_duration is not None:
            raise ValueError("Only one of chunk_nobs or duration can be set.")
        elif self.chunk_nobs is None:
            # Decide the chunk size based on the duration
            raise NotImplementedError(
                "Splitting by duration is not implemented yet. Please set chunk_nobs."
            )

        # Group observations by day/night
        moon_sky_splits = {"insky": [], "outsky": []}
        for obs_id, obs_meta in obs_info.items():
            obs_time = datetime.fromtimestamp(
                timestamp=obs_meta["start_time"], tz=timezone.utc
            )  # Assuming time is in ISO format

            # Determine if it's day or night using the sun position
            city = LocationInfo(
                "San Pedro de Atacama", "Chile", "America/Santiago", -22.91, -68.2
            )

            try:
                moon_rise = moonrise(city.observer, obs_time, timezone.utc)
                moon_set = moonset(city.observer, obs_time, timezone.utc)

                moon_times = []
                if moon_set.hour < moon_rise.hour:
                    # Moon sets on a different day
                    start_of_day = obs_time.replace(
                        hour=0, minute=0, second=0, microsecond=0
                    )
                    end_of_day = obs_time.replace(
                        hour=23, minute=59, second=59, microsecond=999999
                    )
                    moon_times = [
                        {"start_time": start_of_day, "end_time": moon_set},
                        {"start_time": moon_rise, "end_time": end_of_day},
                    ]
                else:
                    # Moon sets on the same day
                    moon_times = [{"start_time": moon_rise, "end_time": moon_set}]
                moon_in_sky = False
                for mt in moon_times:
                    if mt["start_time"] <= obs_time <= mt["end_time"]:
                        moon_in_sky = True
                        break
                if moon_in_sky:
                    moon_sky_splits["insky"].append(obs_id)
                else:
                    moon_sky_splits["outsky"].append(obs_id)
            except ValueError:
                continue

        final_splits = {}

        # For each direction, create time-interleaved splits
        for moon_sky, obs_infos in moon_sky_splits.items():
            if not obs_infos:
                continue

            # Sort by timestamp for time-based splitting
            sorted_ids = sorted(obs_infos, key=lambda k: obs_info[k]["start_time"])

            # Group in chunks based on chunk_nobs
            num_chunks = self._get_num_chunks(len(sorted_ids))
            obs_lists = np.array_split(sorted_ids, num_chunks) if num_chunks > 0 else []

            # Create nsplits (=2) time-interleaved splits
            splits = [[] for _ in range(self.nsplits)]
            for i, obs_list in enumerate(obs_lists):
                splits[i % self.nsplits] += obs_list.tolist()

            final_splits[moon_sky] = splits

        return final_splits

    @classmethod
    def get_workflows(cls, desc=None) -> List[NullTestWorkflow]:
        """
        Create one :class:`~socm.workflows.ml_null_tests.base.NullTestWorkflow` per moon-sky-split pair.

        Instantiates the parent :class:`MoonRiseSetNullTestWorkflow` to compute
        the splits, then creates a child :class:`NullTestWorkflow` for each
        non-empty (moon sky status, time-split) combination. Query files are
        written to ``<output_dir>/moon_{insky,outsky}_split_<N>/query.txt``.

        Parameters
        ----------
        desc : dict, optional
            Workflow configuration dictionary.

        Returns
        -------
        list of NullTestWorkflow
            One workflow per non-empty moon-sky-split pair, named
            ``moon_{insky,outsky}_split_<N>_null_test_workflow``.
        """
        moon_sky_workflow = cls(**desc)

        workflows = []
        for moon_sky, moon_sky_splits in moon_sky_workflow._splits.items():
            for split_idx, split in enumerate(moon_sky_splits):
                if not split:
                    continue
                desc_copy = moon_sky_workflow.model_dump(exclude_unset=True)
                desc_copy["name"] = (
                    f"moon_{moon_sky}_split_{split_idx + 1}_null_test_workflow"
                )

                # Follow the naming convention: direction_[rising,setting,middle]
                desc_copy["output_dir"] = (
                    f"{moon_sky_workflow.output_dir}/moon_{moon_sky}_split_{split_idx + 1}"
                )
                desc_copy["datasize"] = 0
                query_file = Path(desc_copy["output_dir"]) / "query.txt"
                query_file.parent.mkdir(parents=True, exist_ok=True)
                with open(query_file, "w") as f:
                    for oid in split:
                        f.write(f"{oid}\n")
                desc_copy["query"] = f"file://{str(query_file.absolute())}"
                desc_copy["chunk_nobs"] = 1
                workflow = NullTestWorkflow(**desc_copy)
                workflows.append(workflow)

        return workflows
