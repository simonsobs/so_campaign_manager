from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Union

import astropy.units as u
import numpy as np
from astral import LocationInfo
from astropy.coordinates import AltAz, EarthLocation, SkyCoord, get_sun
from astropy.time import Time
from pydantic import PrivateAttr
from sotodlib.core import Context

from socm.workflows.ml_null_tests import NullTestWorkflow


class SunCloseFarNullTestWorkflow(NullTestWorkflow):
    """
    A workflow for day/night null tests.

    This workflow splits observations based on whether they were taken during the day or night.
    A workflow for sun proximity-based null tests.

    This workflow splits observations based on whether they are "close" or "far" from the Sun,
    using a configurable sun distance threshold (in degrees). It creates time-interleaved splits
    with nsplits=2 as specified.
    """

    chunk_nobs: Optional[int] = None
    chunk_duration: Optional[timedelta] = None
    nsplits: int = 2  # Fixed to 2 as specified in the issue
    name: str = "sun_close_far_null_test_workflow"
    sun_distance_threshold: float = (
        10.0  # in degrees, threshold for close/far from the Sun
    )

    _field_view_radius_per_telescope: Dict[str, float] = PrivateAttr(
        {"sat": 1.0, "act": 1.0, "lat": 1.0}
    )

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
        Distribute the observations across splits based on proximity to the sun.

        Groups observations by whether they are 'close' or 'far' from the sun, according to
        the sun_distance_threshold, and then creates time-interleaved splits for each group
        with nsplits=2.

        Args:
            ctx: Context object
            obs_info: Dictionary mapping obs_id to observation metadata

        Returns:
            Dict mapping 'close' and 'far' to list of splits, where each split is a list
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
        sun_position_splits = {"close": [], "far": []}
        for obs_id, obs_meta in obs_info.items():
            obs_time = datetime.fromtimestamp(
                timestamp=obs_meta["start_time"], tz=timezone.utc
            )  # Assuming time is in ISO format
            obs_time = Time(obs_meta["start_time"], format="unix", scale="utc")

            city = LocationInfo(
                "San Pedro de Atacama", "Chile", "America/Santiago", -22.91, -68.2
            )
            alt = 5190  # Altitude in meters
            location = EarthLocation(
                lat=city.latitude * u.deg, lon=city.longitude * u.deg, height=alt * u.m
            )
            altaz = AltAz(obstime=obs_time, location=location)
            altaz_coord = SkyCoord(
                az=obs_meta["az_center"] * u.deg,
                alt=obs_meta["el_center"] * u.deg,
                frame=altaz,
            )
            radec = altaz_coord.transform_to("icrs")

            # Get Sun's position
            sun = get_sun(obs_time)

            # Compute angular separation
            separation = radec.separation(sun)

            if separation.deg <= (
                self.sun_distance_threshold
                + self._field_view_radius_per_telescope[self.site]
            ):
                sun_position_splits["close"].append(obs_id)
            else:
                sun_position_splits["far"].append(obs_id)

        final_splits = {}

        # For each direction, create time-interleaved splits
        for sun_position, obs_infos in sun_position_splits.items():
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

            final_splits[sun_position] = splits

        return final_splits

    @classmethod
    def get_workflows(cls, desc=None) -> List[NullTestWorkflow]:
        """
        Create a list of NullTestWorkflows instances from the provided descriptions.

        Creates separate workflows for each direction split following the naming
        convention: {setname} = direction_[rising,setting,middle]
        """
        sun_position_workflow = cls(**desc)

        workflows = []
        for sun_position, sun_position_splits in sun_position_workflow._splits.items():
            for split_idx, split in enumerate(sun_position_splits):
                if not split:
                    continue
                desc_copy = sun_position_workflow.model_dump(exclude_unset=True)
                desc_copy["name"] = (
                    f"sun_{sun_position}_split_{split_idx + 1}_null_test_workflow"
                )

                # Follow the naming convention: direction_[rising,setting,middle]
                desc_copy["output_dir"] = (
                    f"{sun_position_workflow.output_dir}/sun_{sun_position}_split_{split_idx + 1}"
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
