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
    A workflow for day/night null tests.

    This workflow splits observations based on whether they were taken during the day or night.
    It creates time-interleaved splits with nsplits=2 as specified.
    """

    chunk_nobs: Optional[int] = None
    chunk_duration: Optional[timedelta] = None
    nsplits: int = 2  # Fixed to 2 as specified in the issue
    name: str = "day_night_null_test_workflow"

    def _get_splits(
        self, ctx: Context, obs_info: Dict[str, Dict[str, Union[float, str]]]
    ) -> Dict[str, List[List[str]]]:
        """
        Split observations based on day/night.

        Groups observations by whether they were taken during the day or
        night and creates time-interleaved splits for each group.

        Parameters
        ----------
        ctx : Context
            The sotodlib Context object.
        obs_info : dict
            A mapping of observation IDs to their metadata.

        Returns
        -------
        dict
            A mapping of 'day' and 'night' to lists of observation splits.
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
        Create NullTestWorkflow instances for each day/night split.

        Parameters
        ----------
        desc : dict, optional
            The workflow configuration dictionary.

        Returns
        -------
        list of NullTestWorkflow
            One workflow per day/night-split combination, following the naming
            convention: {day,night}_split_{idx}_null_test_workflow.
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
