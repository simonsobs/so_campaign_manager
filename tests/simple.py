import toml
from socm.workflows.null_tests import TimeNullTestWorkflow
from socm.utils.time_utils import parse_timedelta
test = toml.load("examples/campaign.toml")
t = test["campaign"]["lat-null-test"]
t["chunk_duration"] = t["mission"]["chunk_duration"]
t["nsplits"] = t["mission"]["nsplits"]
t["name"] = "mission_null_test"
t["executable"] = "python"
t["context_file"] = t["context"]
t["subcommand"] = "make_ml_mapmaker"
t["chunk_duration"] = '3d'
a = TimeNullTestWorkflow(**t)
print(a)
