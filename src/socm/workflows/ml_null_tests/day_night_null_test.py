from datetime import datetime, timedelta, timezone
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
        Distribute the observations across splits based on day/night.

        Groups observations by whether they were taken during the day or night and then
        creates time-interleaved splits for each with nsplits=2.

        Args:
            ctx: Context object
            obs_info: Dictionary mapping obs_id to observation metadata

        Returns:
            Dict mapping 'day' and 'night' to list of splits, where each split is a list
            of obs_ids
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
            if len(obs_infos) == 0:
                continue

            # Sort by timestamp for time-based splitting
            sorted_ids = sorted(obs_infos, key=lambda k: obs_info[k]["start_time"])

            # Group in chunks based on chunk_nobs
            obs_lists = np.array_split(sorted_ids, self.chunk_nobs)

            # Create nsplits (=2) time-interleaved splits
            splits = [[] for _ in range(self.nsplits)]
            for i, obs_list in enumerate(obs_lists):
                splits[i % self.nsplits] += obs_list.tolist()

            final_splits[day_night] = splits

        return final_splits

    @classmethod
    def get_workflows(cls, desc=None) -> List[NullTestWorkflow]:
        """
        Create a list of NullTestWorkflows instances from the provided descriptions.

        Creates separate workflows for each direction split following the naming
        convention: {setname} = direction_[rising,setting,middle]
        """
        day_night_workflow = cls(**desc)

        workflows = []
        for day_night, day_night_splits in day_night_workflow._splits.items():
            for split_idx, split in enumerate(day_night_splits):
                desc_copy = day_night_workflow.model_dump(exclude_unset=True)
                desc_copy["name"] = (
                    f"{day_night}_split_{split_idx + 1}_null_test_workflow"
                )
                desc_copy["datasize"] = 0
                desc_copy["query"] = "obs_id IN ("
                for oid in split:
                    desc_copy["query"] += f"'{oid}',"
                desc_copy["query"] = desc_copy["query"].rstrip(",")
                desc_copy["query"] += ")"
                desc_copy["chunk_nobs"] = 1

                # Follow the naming convention: direction_[rising,setting,middle]
                desc_copy["output_dir"] = (
                    f"{day_night_workflow.output_dir}/{day_night}_split_{split_idx + 1}"
                )

                workflow = NullTestWorkflow(**desc_copy)
                workflows.append(workflow)

        return workflows
