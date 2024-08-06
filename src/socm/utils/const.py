PERFORMANCE_QUERY = """SELECT memory_function, memory_params,
                              time_function, time_params
                       FROM workflow_perf WHERE
                       workflow_name=:workflow_name AND
                       subcommand=:subcommad;"""
