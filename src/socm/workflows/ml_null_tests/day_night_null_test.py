from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Union

import numpy as np
import pytz
from astral import LocationInfo
from astral.sun import sun
from sotodlib.core import Context

from socm.workflows.ml_null_tests import NullTestWorkflow


class DayNightNullTestWorkflow(NullTestWorkflow):
    """
    Null-test workflow that splits observations by time of day (day vs. night).

    Uses the `astral <https://astral.readthedocs.io/>`_ library and the
    geographic location of the SO site (San Pedro de Atacama, Chile) to
    determine whether each observation's start time falls between local sunrise
    and sunset. Observations are classified as ``"day"`` or ``"night"``, and
    within each group ``nsplits = 2`` time-interleaved splits are created to
    test for solar-related systematics. Child workflows follow the naming
    convention ``{day,night}_split_<N>_null_test_workflow``.

    Parameters
    ----------
    chunk_nobs : int or None, optional
        Number of observations per time chunk per day/night group. Defaults to
        ``None``.
    chunk_duration : timedelta or None, optional
        Duration per chunk (not yet implemented). Defaults to ``None``.
    nsplits : int, optional
        Number of time splits per day/night group. Fixed to ``2``. Defaults
        to ``2``.
    name : str, optional
        Human-readable workflow name. Defaults to
        ``"day_night_null_test_workflow"``.
    """

    chunk_nobs: Optional[int] = None
    chunk_duration: Optional[timedelta] = None
    nsplits: int = 2  # Fixed to 2 as specified in the issue
    name: str = "day_night_null_test_workflow"

    def _get_splits(
        self, ctx: Context, obs_info: Dict[str, Dict[str, Union[float, str]]]
    ) -> Dict[str, List[List[str]]]:
        """
        Split observations based on day/night classification.

        Groups observations by whether they were taken during daylight hours
        (between local sunrise and sunset at the SO site), then creates
        ``nsplits`` (= 2) time-interleaved splits within each group.

        Parameters
        ----------
        ctx : Context
            The sotodlib :class:`~sotodlib.core.Context` object (not used
            directly).
        obs_info : dict of str to dict
            Mapping of observation ID to metadata. The ``start_time`` key
            (Unix timestamp) is used for the day/night determination and
            chronological ordering.

        Returns
        -------
        dict of str to list of list of str
            Mapping of ``"day"`` and ``"night"`` to lists of ``nsplits``
            splits, each containing the observation IDs assigned to that
            group and split.

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
        day_night_splits = {"day": [], "night": []}
        for obs_id, obs_meta in obs_info.items():
            obs_time = datetime.fromtimestamp(
                timestamp=obs_meta["start_time"], tz=timezone.utc
            )  # Assuming time is in ISO format

            # Determine if it's day or night using the sun position
            city = LocationInfo(
                "San Pedro de Atacama", "Chile", "America/Santiago", -22.91, -68.2
            )
            s = sun(
                city.observer, date=obs_time.date(), tzinfo=pytz.timezone(city.timezone)
            )

            if s["sunrise"] <= obs_time <= s["sunset"]:
                day_night_splits["day"].append(obs_id)
            else:
                day_night_splits["night"].append(obs_id)

        final_splits = {}

        # For each direction, create time-interleaved splits
        for day_night, obs_infos in day_night_splits.items():
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

            final_splits[day_night] = splits

        return final_splits

    @classmethod
    def get_workflows(cls, desc=None) -> List[NullTestWorkflow]:
        """
        Create one :class:`~socm.workflows.ml_null_tests.base.NullTestWorkflow` per day/night-split pair.

        Instantiates the parent :class:`DayNightNullTestWorkflow` to compute
        the splits, then creates a child :class:`NullTestWorkflow` for each
        non-empty (day/night, time-split) combination. Query files are written
        to ``<output_dir>/{day,night}_split_<N>/query.txt``.

        Parameters
        ----------
        desc : dict, optional
            Workflow configuration dictionary.

        Returns
        -------
        list of NullTestWorkflow
            One workflow per non-empty day/night-split pair, named
            ``{day,night}_split_<N>_null_test_workflow``.
        """
        day_night_workflow = cls(**desc)

        workflows = []
        for day_night, day_night_splits in day_night_workflow._splits.items():
            for split_idx, split in enumerate(day_night_splits):
                if not split:
                    continue
                desc_copy = day_night_workflow.model_dump(exclude_unset=True)
                # Follow the naming convention: direction_[rising,setting,middle]
                desc_copy["output_dir"] = (
                    f"{day_night_workflow.output_dir}/{day_night}_split_{split_idx + 1}"
                )
                desc_copy["name"] = (
                    f"{day_night}_split_{split_idx + 1}_null_test_workflow"
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
