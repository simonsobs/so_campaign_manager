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
    A workflow for moonrise/moonset null tests.

    This workflow splits observations based on whether they were taken during the moonrise or moonset.
    It creates time-interleaved splits with nsplits=2 as specified.
    """

    chunk_nobs: Optional[int] = None
    chunk_duration: Optional[timedelta] = None
    nsplits: int = 2  # Fixed to 2 as specified in the issue
    name: str = "moonset_null_test_workflow"

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
        moon_sky_splits = {"insky": [], "outsky": []}
        for obs_id, obs_meta in obs_info.items():
            obs_time = datetime.fromtimestamp(
                timestamp=obs_meta["start_time"], tz=timezone.utc
            )  # Assuming time is in ISO format

            # Determine if it's day or night using the sun position
            city = LocationInfo(
                "San Pedro de Atacama", "Chile", "America/Santiago", -22.91, -68.2
            )
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

        final_splits = {}

        # For each direction, create time-interleaved splits
        for moon_sky, obs_infos in moon_sky_splits.items():
            if not obs_infos:
                continue

            # Sort by timestamp for time-based splitting
            sorted_ids = sorted(obs_infos, key=lambda k: obs_info[k]["start_time"])

            # Group in chunks based on chunk_nobs
            num_chunks = (
                len(sorted_ids) + self.chunk_nobs - 1
            ) // self.chunk_nobs  # Ceiling division
            obs_lists = np.array_split(sorted_ids, num_chunks)

            # Create nsplits (=2) time-interleaved splits
            splits = [[] for _ in range(self.nsplits)]
            for i, obs_list in enumerate(obs_lists):
                splits[i % self.nsplits] += obs_list.tolist()

            final_splits[moon_sky] = splits

        return final_splits

    @classmethod
    def get_workflows(cls, desc=None) -> List[NullTestWorkflow]:
        """
        Create a list of NullTestWorkflows instances from the provided descriptions.

        Creates separate workflows for each direction split following the naming
        convention: {setname} = direction_[rising,setting,middle]
        """
        moon_sky_workflow = cls(**desc)

        workflows = []
        for moon_sky, moon_sky_splits in moon_sky_workflow._splits.items():
            for split_idx, split in enumerate(moon_sky_splits):
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
