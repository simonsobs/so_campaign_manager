PERFORMANCE_QUERY = """SELECT memory_function, memory_param,
                              time_function, time_param
                       FROM workflow_perf WHERE
                       workflow_name=:workflow_name AND
                       subcommand=:subcommand;"""
