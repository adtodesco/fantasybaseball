from datetime import datetime
import pandas as pd
import os
import yaml

from .exceptions import FileDoesNotExist
from .model import ProjectionType, StatType

_PROJECTIONS_EXT = ".csv"
_METADATA_SUFFIX = "-metadata"
_METADATA_EXT = ".yaml"


def read_projections(projections_dir, projection_types=None, stat_types=None, ros=None):
    """

    Args:
        projections_dir:
        projection_types:
        stat_types:
        ros:

    Returns:

    """
    projections = list()
    for file in os.listdir(projections_dir):
        if os.path.isfile(os.path.join(projections_dir, file)) and _METADATA_SUFFIX + _METADATA_EXT in file:
            with open(os.path.join(projections_dir, file)) as f:
                metadata = yaml.safe_load(f)
            if projection_types and ProjectionType(metadata["projection_type"]) not in projection_types:
                continue
            if stat_types and StatType(metadata["stat_type"]) not in stat_types:
                continue
            if ros is not None and ros != metadata["ros"]:
                continue
            projections_filename = file.replace(_METADATA_SUFFIX + _METADATA_EXT, _PROJECTIONS_EXT)
            projections_file = os.path.join(projections_dir, projections_filename)
            if os.path.isfile(projections_file):
                projections.append((metadata, pd.read_csv(projections_file)))
            else:
                raise FileDoesNotExist(f"No projection file found for metadata file '{file}'.")

    return projections


def write_projections(projections, projections_dir, projection_type, stat_type, ros=False):
    """

    Args:
        projections:
        projections_dir:
        projection_type:
        stat_type:
        ros:

    Returns:

    """
    ros_string = "-ROS" if ros else ""
    basename = f"{projection_type.name}{ros_string}-{stat_type.name}"
    metadata_file = os.path.join(projections_dir, basename + _METADATA_SUFFIX + _METADATA_EXT)
    projections_file = os.path.join(projections_dir, basename + _PROJECTIONS_EXT)
    metadata = {
        "projection_type": projection_type.value,
        "stat_type": stat_type.value,
        "ros": ros,
        "last_updated": datetime.utcnow(),
    }
    with open(metadata_file, 'w') as m:
        yaml.safe_dump(metadata, m)
    projections.to_csv(projections_file, index=False)
