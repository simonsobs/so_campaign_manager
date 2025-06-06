import toml
from socm.workflows import MLMapmakingWorkflow
test = toml.load("examples/campaign.toml")
t = test["campaign"]["ml-mapmaking"]
t["name"] = "ml_mapmaking_workflow_test"
t["executable"] = "so-site-pipeline"
t["context"] = t["context"]
t["subcommand"] = "make-ml-map"
t["something_extra"] = "test_value"  # Example of adding an extra field
a = MLMapmakingWorkflow(**t)
print(a)
print("\n\n\n\n")
print(a.get_command(ranks=1))

