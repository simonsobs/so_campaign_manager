# ------------------------------------------------------------------------------
#  States
from enum import Enum, auto


class States(Enum):
    """Workflow and campaign execution states."""

    NEW = auto()  # New campaign is submitted
    PLANNING = auto()  # Planning the execution of the campaign
    EXECUTING = auto()  # At least one workflow is executing
    DONE = auto()  # Campaign has finished successfully
    FAILED = auto()  # Campaign execution has failed
    CANCELED = auto()  # Campaign got canceled by the user.

# Final states for a campaign
CFINAL = [States.DONE, States.FAILED, States.CANCELED]
