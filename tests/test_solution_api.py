from solution_api import build_solution_graph


def test_solution_schema_is_consistent():
    for solution_id in [1, 2, 3, 4]:
        payload = build_solution_graph(
            solution_id,
            "A 56-year-old woman presented with abdominal pain. CT scan showed a pancreatic cyst. Labs: 6 cm mass and CA 19-9 12,476.5 ng/mL.",
        )
        assert set(payload.keys()) == {"nodes", "edges", "summary"}
        assert isinstance(payload["nodes"], list)
        assert isinstance(payload["edges"], list)
        assert payload["summary"]["solution_id"] == solution_id
        assert payload["summary"]["node_count"] >= 1
        assert payload["summary"]["edge_count"] >= 0
