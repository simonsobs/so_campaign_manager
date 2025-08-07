from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Union

import astropy.units as u
import numpy as np
from astral import LocationInfo
from astropy.coordinates import AltAz, EarthLocation, SkyCoord, get_body
from astropy.time import Time
from pydantic import PrivateAttr
from sotodlib.core import Context

from socm.workflows.ml_null_tests import NullTestWorkflow


class MoonCloseFarNullTestWorkflow(NullTestWorkflow):
    """
    A workflow for day/night null tests.

    A workflow for moon proximity-based null tests.

    This workflow splits observations based on whether they were taken close to or far from the moon.
    It creates time-interleaved splits with nsplits=2 as specified.
    """

    chunk_nobs: Optional[int] = None
    chunk_duration: Optional[timedelta] = None
    nsplits: int = 2  # Fixed to 2 as specified in the issue
    name: str = "moon_close_far_null_test_workflow"
    sun_distance_threshold: float = (
        10.0  # in degrees, threshold for close/far from the Moon
    )

    _field_view_radius_per_telescope: Dict[str, float] = PrivateAttr(
        {"sat": 1.0, "act": 1.0, "lat": 1.0}
    )

    def _get_splits(
        self, ctx: Context, obs_info: Dict[str, Dict[str, Union[float, str]]]
    ) -> Dict[str, List[List[str]]]:
        """
        Distribute the observations across splits based on day/night.

        Distribute the observations across splits based on proximity to the moon (close/far).

        Groups observations by whether they were taken close to or far from the moon and then
        creates time-interleaved splits for each with nsplits=2.

        Args:
            ctx: Context object
            obs_info: Dictionary mapping obs_id to observation metadata

        Returns:
            Dict mapping 'day' and 'night' to list of splits, where each split is a list
            Dict mapping 'close' and 'far' to list of splits, where each split is a list
            of obs_ids.
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
        moon_position_splits = {"close": [], "far": []}
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

            # Get Moon's position
            moon = get_body("moon", obs_time, location=location)

            # Compute angular separation
            separation = radec.separation(moon)

            if separation.deg <= (
                self.sun_distance_threshold
                + self._field_view_radius_per_telescope[self.site]
            ):
                moon_position_splits["close"].append(obs_id)
            else:
                moon_position_splits["far"].append(obs_id)

        final_splits = {}

        # For each direction, create time-interleaved splits
        for moon_position, obs_infos in moon_position_splits.items():
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

            final_splits[moon_position] = splits

        return final_splits

    @classmethod
    def get_workflows(cls, desc=None) -> List[NullTestWorkflow]:
        """
        Create a list of NullTestWorkflows instances from the provided descriptions.

        Creates separate workflows for each direction split following the naming
        convention: {setname} = direction_[rising,setting,middle]
        """
        moon_position_workflow = cls(**desc)

        workflows = []
        for (
            moon_position,
            moon_position_splits,
        ) in moon_position_workflow._splits.items():
            for split_idx, split in enumerate(moon_position_splits):
                desc_copy = moon_position_workflow.model_dump(exclude_unset=True)
                desc_copy["name"] = (
                    f"moon_{moon_position}_split_{split_idx + 1}_null_test_workflow"
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
                    f"{moon_position_workflow.output_dir}/moon_{moon_position}_split_{split_idx + 1}"
                )

                workflow = NullTestWorkflow(**desc_copy)
                workflows.append(workflow)

        return workflows
