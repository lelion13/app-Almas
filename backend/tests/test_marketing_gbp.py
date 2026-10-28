from app.services.gbp_api_service import THANK_YOU_PHRASES, random_thank_you
from app.services.marketing_review_service import STAR_MAP, _normalize_review_payload


def test_thank_you_phrases_non_empty():
    assert len(THANK_YOU_PHRASES) >= 3
    assert random_thank_you() in THANK_YOU_PHRASES


def test_star_map_five():
    assert STAR_MAP["FIVE"] == 5
    assert STAR_MAP[5] == 5


def test_normalize_review_payload_five_empty():
    payload = {
        "type": "NEW_REVIEW",
        "review": {
            "name": "accounts/1/locations/2/reviews/abc",
            "reviewId": "abc",
            "starRating": "FIVE",
            "comment": "",
            "reviewer": {"displayName": "Ana"},
        },
    }
    norm = _normalize_review_payload(payload)
    assert norm["google_review_id"] == "abc"
    assert norm["star_rating"] == 5
    assert norm["comment"] is None
    assert norm["reviewer_name"] == "Ana"
