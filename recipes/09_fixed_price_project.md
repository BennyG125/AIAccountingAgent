# Fixed-Price Project (Tier 2)
1. Follow Create Project recipe → capture project_id
2. GET /project/{project_id} → capture version
3. PUT /project/{project_id} {id: project_id, version: V, isFixedPrice: true, fixedprice: AMOUNT}
The fixedprice is set via PUT on the project, not a separate endpoint.
