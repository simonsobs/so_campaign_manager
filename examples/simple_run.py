from socm.core import Workflow, Resource, Campaign

from socm.bookkeeper import Bookkeeper

if __name__ == "__main__":

    # Create a list of workflows along with their config and context file
    # Each workflow needs to have its own unique id. This id can be used later
    # for reference.
    # Executable denotes the executable command of the workflow
    # subcommand: the subcommand of the executable
    ws = []
    for i in range(1, 3):
        w = Workflow(
            id=i,
            name=f"test.{i}",
            executable="so-site-pipeline",
            subcommand="make-filterbin-map",
            context_file="$SCRATCH/so/untracked/metadata/satp3/contexts/use_this_local.yaml",
            config=f"config{i}.yaml",
        )
        ws.append(w)

    # A campaign is a set of workflows to execute. It has its own id and it
    # takes as input the workflows, and a policy
    # Currently the only policy that is supported is "time". This tells the
    # scheduler to try and minimize the total time to completion
    c = Campaign(id=1, workflows=ws, campaign_policy="time")

    # A resource is where the campaign will run.
    r = Resource(
        name="tiger2",
        nodes=1,
        cores_per_node=40,
        memory_per_node=180000,
        default_queue="tiger-test",
        maximum_walltime=3600000,
    )

    # This main class to execute the campaign to a resource.
    b = Bookkeeper(
        campaign=c, resources={"tiger2": r}, policy="time", target_resource="tiger2"
    )

    b.run()
