# DB-Rolling: secondary maintenance and election handoff

Preregistered before generation/execution. A constructed finite protocol inspired by the MongoDB 7.0 Community-to-Enterprise rolling procedure; not a MongoDB implementation or reproduction.

Primary sources verified 2026-09-29:
- https://www.mongodb.com/docs/v7.0/tutorial/upgrade-to-enterprise-replica-set/
- https://www.mongodb.com/docs/v7.0/reference/command/replsetstepdown/

The model separates primary stepdown and uncontrollable election completion. It allows a temporary absence of primary; it does not claim uninterrupted writes. Updates follow a secondary-only maintenance contract and return through a restarting state. Three ready replicas are used initially; the main interval bound is two, with three as a preregistered negative control. Restart and election termination are finite abstractions; replication lag, partitions, and data consistency are outside scope.

Final current result directory: `v2/`. Earlier inputs and results are retained as a modeling/validation correction history; see DAILY and v2 validation files.
