# ------------------------------------------------------------------------------
#  States
from enum import IntEnum


class States(IntEnum):
    """Workflow and campaign execution states."""

    NEW = 0  # New campaign is submitted
    PLANNING = 1  # Planning the execution of the campaign
    EXECUTING = 2  # At least one workflow is executing
    DONE = 3  # Campaign has finished successfully
    FAILED = 4  # Campaign execution has failed
    CANCELED = 5  # Campaign got canceled by the user.

# Final states for a campaign
CFINAL = [States.DONE, States.FAILED, States.CANCELED]
