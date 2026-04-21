"""Tests for booking.py — venue query, filtering, and booking."""

import json
from unittest.mock import MagicMock, patch

import pytest
import responses

from booking import Venue, BookingClient, API_BASE


# ─── Venue Model ───────────────────────────────────────


class TestVenue:
    """Venue dataclass properties."""

    def test_time_slot(self, sample_venue):
        assert sample_venue.time_slot == "18:00-19:00"

    def test_display(self, sample_venue):
        assert "运动广场东馆" in sample_venue.display
        assert "羽毛球1号" in sample_venue.display
        assert "18:00-19:00" in sample_venue.display

    def test_different_hours(self):
        v = Venue(
            wid="x", name="场地", venue_name="馆",
            date="2026-04-08", begin_hour="20", end_hour="21",
            sport_code="001", campus_code="1",
        )
        assert v.time_slot == "20:00-21:00"


# ─── Query Venues ──────────────────────────────────────

QUERY_URL = f"{API_BASE}/modules/sportVenue/getOpeningRoom.do"
BOOK_URL = f"{API_BASE}/sportVenue/insertVenueBookingInfo.do"


def make_query_response(rows):
    return {"datas": {"getOpeningRoom": {"rows": rows}}}


class TestQueryVenues:
    """BookingClient.query_venues() parsing."""

    @responses.activate
    def test_returns_available_venues(self):
        responses.post(QUERY_URL, json=make_query_response([
            {"WID": "w1", "CDMC": "羽毛球1号", "CGMC": "东馆", "disabled": False},
            {"WID": "w2", "CDMC": "羽毛球2号", "CGMC": "东馆", "disabled": False},
            {"WID": "w3", "CDMC": "羽毛球3号", "CGMC": "东馆", "disabled": True},
        ]))

        client = BookingClient(session=_mock_session(), username="u")
        venues = client.query_venues("2026-04-08", "18", "19")

        assert len(venues) == 2
        assert venues[0].wid == "w1"
        assert venues[0].name == "羽毛球1号"
        assert venues[0].venue_name == "东馆"

    @responses.activate
    def test_all_disabled_returns_empty(self):
        responses.post(QUERY_URL, json=make_query_response([
            {"WID": "w1", "CDMC": "场地1", "disabled": True},
        ]))

        client = BookingClient(session=_mock_session())
        venues = client.query_venues("2026-04-08", "18", "19")
        assert venues == []

    @responses.activate
    def test_empty_rows(self):
        responses.post(QUERY_URL, json=make_query_response([]))

        client = BookingClient(session=_mock_session())
        venues = client.query_venues("2026-04-08", "18", "19")
        assert venues == []

    @responses.activate
    def test_malformed_response_returns_empty(self):
        responses.post(QUERY_URL, json={"unexpected": "structure"})

        client = BookingClient(session=_mock_session())
        venues = client.query_venues("2026-04-08", "18", "19")
        assert venues == []

    @responses.activate
    def test_network_error_returns_empty(self):
        import requests as req
        responses.post(QUERY_URL, body=req.exceptions.ConnectionError("timeout"))

        client = BookingClient(session=_mock_session())
        venues = client.query_venues("2026-04-08", "18", "19")
        assert venues == []

    @responses.activate
    def test_non_json_response_returns_empty(self):
        responses.post(QUERY_URL, body="<html>error</html>", status=200)

        client = BookingClient(session=_mock_session())
        venues = client.query_venues("2026-04-08", "18", "19")
        assert venues == []


class TestQueryAllHours:
    """BookingClient.query_all_hours() multi-slot query."""

    @responses.activate
    def test_queries_multiple_hours(self):
        for _ in range(2):
            responses.post(QUERY_URL, json=make_query_response([
                {"WID": "w1", "CDMC": "场地1", "CGMC": "馆", "disabled": False},
            ]))

        client = BookingClient(session=_mock_session())
        venues = client.query_all_hours("2026-04-08", ["18-19", "19-20"])
        assert len(venues) == 2

    @responses.activate
    def test_invalid_hour_format_skipped(self):
        responses.post(QUERY_URL, json=make_query_response([
            {"WID": "w1", "CDMC": "场地1", "CGMC": "馆", "disabled": False},
        ]))

        client = BookingClient(session=_mock_session())
        venues = client.query_all_hours("2026-04-08", ["bad_format", "18-19"])
        assert len(venues) == 1


# ─── Filter by Venue Names ─────────────────────────────


class TestFilterByVenueNames:
    """Static method for venue name filtering."""

    def test_empty_preferred_returns_all(self):
        venues = [_make_venue("w1", "A馆"), _make_venue("w2", "B馆")]
        result = BookingClient.filter_by_venue_names(venues, [])
        assert len(result) == 2

    def test_preferred_sorted_first(self):
        venues = [
            _make_venue("w1", "C馆"),
            _make_venue("w2", "A馆"),
            _make_venue("w3", "B馆"),
        ]
        result = BookingClient.filter_by_venue_names(venues, ["B馆", "A馆"])
        assert result[0].venue_name == "B馆"
        assert result[1].venue_name == "A馆"
        assert result[2].venue_name == "C馆"

    def test_no_match_preserves_order(self):
        venues = [_make_venue("w1", "X馆"), _make_venue("w2", "Y馆")]
        result = BookingClient.filter_by_venue_names(venues, ["不存在的馆"])
        assert len(result) == 2

    def test_partial_name_match(self):
        venues = [
            _make_venue("w1", "至快体育馆羽毛球"),
            _make_venue("w2", "至畅体育馆"),
        ]
        result = BookingClient.filter_by_venue_names(venues, ["至快体育馆"])
        assert result[0].venue_name == "至快体育馆羽毛球"


# ─── Book One ──────────────────────────────────────────


class TestBookOne:
    """BookingClient.book_one() single venue booking."""

    @responses.activate
    def test_success(self, sample_venue):
        responses.post(BOOK_URL, json={"code": "0", "msg": "成功"})

        client = BookingClient(
            session=_mock_session(), username="2023001",
            real_name="Test", phone="13800000000",
        )
        assert client.book_one(sample_venue, max_retries=1) is True

    @responses.activate
    def test_already_booked_no_retry(self, sample_venue):
        responses.post(BOOK_URL, json={"code": "1", "msg": "该场地已被预约"})

        client = BookingClient(session=_mock_session(), username="u")
        assert client.book_one(sample_venue, max_retries=3) is False
        assert len(responses.calls) == 1  # no retry

    @responses.activate
    def test_full_no_retry(self, sample_venue):
        responses.post(BOOK_URL, json={"code": "1", "msg": "已满"})

        client = BookingClient(session=_mock_session(), username="u")
        assert client.book_one(sample_venue, max_retries=3) is False

    @responses.activate
    def test_retryable_error_retries(self, sample_venue):
        responses.post(BOOK_URL, json={"code": "1", "msg": "系统繁忙"})
        responses.post(BOOK_URL, json={"code": "1", "msg": "系统繁忙"})
        responses.post(BOOK_URL, json={"code": "0", "msg": "成功"})

        client = BookingClient(session=_mock_session(), username="u")
        assert client.book_one(sample_venue, max_retries=3) is True
        assert len(responses.calls) == 3

    @responses.activate
    def test_all_retries_exhausted(self, sample_venue):
        for _ in range(3):
            responses.post(BOOK_URL, json={"code": "1", "msg": "系统繁忙"})

        client = BookingClient(session=_mock_session(), username="u")
        assert client.book_one(sample_venue, max_retries=3) is False

    @responses.activate
    def test_network_error_retries(self, sample_venue):
        import requests as req
        responses.post(BOOK_URL, body=req.exceptions.ConnectionError("timeout"))
        responses.post(BOOK_URL, json={"code": "0", "msg": "成功"})

        client = BookingClient(session=_mock_session(), username="u")
        assert client.book_one(sample_venue, max_retries=2) is True


# ─── Book Concurrent ───────────────────────────────────


class TestBookConcurrent:
    """BookingClient.book_concurrent() parallel booking."""

    def test_empty_venues_returns_none(self):
        client = BookingClient(session=_mock_session(), username="u")
        assert client.book_concurrent([], max_workers=2) is None

    @responses.activate
    def test_first_success_wins(self):
        responses.post(BOOK_URL, json={"code": "0", "msg": "成功"})

        client = BookingClient(session=_mock_session(), username="u")
        venues = [_make_venue(f"w{i}") for i in range(3)]
        result = client.book_concurrent(venues, max_workers=3, max_retries=1)
        assert result is not None


# ─── Validate Session ──────────────────────────────────


class TestValidateSession:
    """BookingClient.validate_session()."""

    @responses.activate
    def test_valid_session(self):
        responses.post(
            f"{API_BASE}/modules/sportVenue/getOpeningRoom.do",
            json={"datas": {"getOpeningRoom": {"rows": []}}},
        )

        client = BookingClient(session=_mock_session())
        assert client.validate_session() is True

    @responses.activate
    def test_invalid_response(self):
        responses.post(
            f"{API_BASE}/modules/sportVenue/getOpeningRoom.do",
            json={"error": "unauthorized"},
        )

        client = BookingClient(session=_mock_session())
        assert client.validate_session() is False

    @responses.activate
    def test_network_error(self):
        responses.post(
            f"{API_BASE}/modules/sportVenue/getOpeningRoom.do",
            body=ConnectionError("timeout"),
        )

        client = BookingClient(session=_mock_session())
        assert client.validate_session() is False


# ─── Helpers ───────────────────────────────────────────


def _mock_session():
    """Create a real requests.Session for use with responses library."""
    import requests
    s = requests.Session()
    s.headers.update({
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "X-Requested-With": "XMLHttpRequest",
    })
    return s


def _make_venue(wid="w1", venue_name="测试馆", name="场地1"):
    return Venue(
        wid=wid, name=name, venue_name=venue_name,
        date="2026-04-08", begin_hour="18", end_hour="19",
        sport_code="001", campus_code="1",
    )
