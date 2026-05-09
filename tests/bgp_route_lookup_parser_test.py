import bgp_lg


def test_parse_bgp_route_lookup_includes_star_prefixed_routes():
    output = """BGP routing table entry for 203.0.113.0/24
Paths: (2 available, best #1)
  * 203.0.113.0/24 192.0.2.1 0 64500 i
"""

    parsed = bgp_lg._parse_bgp_route_lookup(output)

    assert parsed.parse_status == "success"
    assert [route.prefix for route in parsed.parsed_routes] == ["203.0.113.0/24"]


def test_parse_bgp_route_lookup_includes_star_best_marker_routes():
    output = """BGP routing table entry for 198.51.100.0/24
Paths: (1 available, best #1)
  *>198.51.100.0/24 0.0.0.0 0 64496 i
"""

    parsed = bgp_lg._parse_bgp_route_lookup(output)

    assert parsed.parse_status == "success"
    assert [route.prefix for route in parsed.parsed_routes] == ["198.51.100.0/24"]
