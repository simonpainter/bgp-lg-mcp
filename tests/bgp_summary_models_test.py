import pytest

from models import BGPNeighbor, BGPSummaryResponse


def test_bgp_summary_neighbors_are_validated_as_models():
    parsed = BGPSummaryResponse(
        raw_output="sample",
        neighbors=[
            {
                "peer_ip": "192.0.2.1",
                "asn": 64496,
                "state": "Established",
                "uptime": "1d02h",
                "prefixes_received": 123,
            }
        ],
    )

    assert len(parsed.neighbors) == 1
    assert isinstance(parsed.neighbors[0], BGPNeighbor)
    assert parsed.neighbors[0].peer_ip == "192.0.2.1"


def test_bgp_summary_neighbors_reject_invalid_neighbor_type():
    with pytest.raises(ValueError, match="neighbors.0"):
        BGPSummaryResponse(raw_output="sample", neighbors=["not-a-neighbor-object"])
