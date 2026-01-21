# DirectionNullTestWorkflow Implementation

This document describes the implementation of the `DirectionNullTestWorkflow` class that addresses issue #21, providing direction-based scan splitting with time-interleaved splits.

## Overview

The `DirectionNullTestWorkflow` extends the existing null test framework to handle observations based on their scan direction (rising, setting, middle). It creates `nsplits=2` time-interleaved splits for each direction, following the naming convention specified in the issue.

## Key Features

### 1. Direction-Based Splitting
- Groups observations by scan direction: `rising`, `setting`, `middle`
- Uses a hash-based assignment method (placeholder for actual direction metadata)
- Each direction group is processed independently

### 2. Time-Interleaved Splits
- Fixed `nsplits=2` as specified in the issue
- Observations within each direction are sorted by timestamp
- Creates time-interleaved splits to ensure balanced temporal coverage

### 3. Naming Convention
- Output directories follow the pattern: `direction_{direction}_split_{N}`
- Examples:
  - `direction_rising_split_1`
  - `direction_rising_split_2`
  - `direction_setting_split_1`
  - `direction_setting_split_2`
  - `direction_middle_split_1`
  - `direction_middle_split_2`

## Usage

### Configuration

The workflow is registered as `"ml-null-tests.direction-tests"` and can be configured in TOML files:

```toml
[campaign.ml-null-tests.direction-tests]
context = "context.yaml"
area = "so_geometry_v20250306_lat_f090.fits"
output_dir = "output/direction_null_tests"
query = "obs_id IN ('obs1', 'obs2', 'obs3', 'obs4', 'obs5', 'obs6')"

# Basic mapmaking parameters
bands = "f090"
wafer = "ws0"
comps = "TQU"
maxiter = 10
tiled = 1
site = "act"

# Direction test specific parameters
chunk_nobs = 3      # Number of chunks to create per direction
nsplits = 2         # Fixed to 2 as specified in the issue

[campaign.ml-null-tests.direction-tests.resources]
ranks = 4
threads = 8
memory = "80000"
runtime = "80000"
```

### Programmatic Usage

```python
from socm.workflows.ml_null_tests import DirectionNullTestWorkflow

# Create workflow configuration
config = {
    "context": "context.yaml",
    "area": "area.fits",
    "output_dir": "output/direction_tests",
    "chunk_nobs": 3,
    "query": "obs_id IN ('obs1', 'obs2', 'obs3')",
    # ... other parameters
}

# Generate workflows for all direction splits
workflows = DirectionNullTestWorkflow.get_workflows(config)

# Each workflow in the list represents one direction split
for workflow in workflows:
    print(f"Output: {workflow.output_dir}")
    print(f"Query: {workflow.query}")
```

## Implementation Details

### Core Methods

#### `_get_scan_direction(obs_info)`
Determines the scan direction for a given observation. Currently uses a hash-based assignment as a placeholder. In production, this should extract actual scan direction from observation metadata.

#### `_get_splits(ctx, obs_info)`
Groups observations by direction and creates time-interleaved splits:
1. Groups observations by scan direction
2. Sorts each group by timestamp
3. Creates chunks based on `chunk_nobs`
4. Distributes chunks across `nsplits=2` in round-robin fashion

#### `get_workflows(desc)`
Class method that creates individual workflow instances for each direction split:
1. Instantiates the main workflow to compute splits
2. Creates separate workflow instances for each split
3. Sets appropriate output directories and queries

### File Structure

```
src/socm/workflows/ml_null_tests/
├── __init__.py                 # Updated to export DirectionNullTestWorkflow
├── direction_null_test.py      # New implementation
├── base.py                     # Base NullTestWorkflow class
├── time_null_test.py          # Time-based null tests
└── wafer_null_test.py         # Wafer-based null tests

src/socm/workflows/
└── __init__.py                # Updated registered_workflows and subcampaign_map

tests/workflows/
└── test_direction_null_tests.py  # Comprehensive test suite

examples/
└── direction_null_test_config.toml  # Example configuration
```

## Testing

The implementation includes comprehensive tests covering:
- Workflow initialization and configuration
- Direction-based splitting logic
- Output directory naming conventions
- Query construction for splits
- Error handling for invalid configurations
- Argument exclusion in command generation

## Future Enhancements

### Scan Direction Detection
The current implementation uses a placeholder hash-based method for direction assignment. This should be replaced with actual scan direction extraction from observation metadata when the metadata structure is defined.

Possible implementations:
- Extract from observation database fields
- Compute from azimuth/elevation patterns
- Use pre-computed direction labels

### Additional Validation
- Validate that all directions have sufficient observations
- Handle cases where some directions have no observations
- Add warnings for unbalanced direction distributions

## Compliance

The implementation follows the project's coding standards:
- Line length limit of 90 characters
- PEP8 compliance
- Consistent with existing null test workflow patterns
- Proper inheritance from `NullTestWorkflow`
- Integration with existing workflow registry system
