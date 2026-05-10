import bgp_lg


def test_parse_bgp_summary_prefers_explicit_neighbor_count_line():
    output = """BGP router identifier 1.1.1.1, local AS number 64512
424 BGP AS-PATH entries
3 BGP neighbors, 2 up, 2 established
Neighbor        V    AS MsgRcvd MsgSent TblVer InQ OutQ Up/Down State/PfxRcd
192.0.2.1       4 64496    100    200      0   0   0 1d02h        10
198.51.100.1    4 64497    300    400      0   0   0 00:10:00     Idle
203.0.113.1     4 64498    500    600      0   0   0 2d01h        20
"""

    parsed = bgp_lg._parse_bgp_summary(output)

    assert parsed.parse_status == "success"
    assert parsed.neighbor_count == 3
    assert parsed.established_count == 2


def test_parse_bgp_summary_parses_ios_neighbors_slash_peers_summary_line():
    output = """BGP router identifier 1.1.1.1, local AS number 64512
10 BGP neighbors/peers, 1 up, 1 established
Neighbor        V    AS MsgRcvd MsgSent TblVer InQ OutQ Up/Down State/PfxRcd
192.0.2.1       4 64496    100    200      0   0   0 1d02h        10
198.51.100.1    4 64497    300    400      0   0   0 00:10:00     Idle
203.0.113.1     4 64498    500    600      0   0   0 2d01h        20
"""

    parsed = bgp_lg._parse_bgp_summary(output)

    assert parsed.parse_status == "success"
    assert parsed.neighbor_count == 10
    assert parsed.established_count == 1


def test_parse_bgp_summary_counts_neighbors_from_table_when_summary_absent():
    output = """BGP router identifier 1.1.1.1, local AS number 64512
Neighbor        V    AS MsgRcvd MsgSent TblVer InQ OutQ Up/Down State/PfxRcd
192.0.2.1       4 64496    100    200      0   0   0 1d02h        10
198.51.100.1    4 64497    300    400      0   0   0 00:10:00     Active
2001:db8::1     4 64498    500    600      0   0   0 2d01h        25
2001:db8::2     4 64499    700    800      0   0   0 00:00:10     Connect
"""

    parsed = bgp_lg._parse_bgp_summary(output)

    assert parsed.parse_status == "success"
    assert parsed.neighbor_count == 4
    assert parsed.established_count == 2
