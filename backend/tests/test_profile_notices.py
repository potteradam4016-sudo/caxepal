from datetime import date
from app.schemas import AnalysisData

def test_profile_requires_both_interest_types(client,user_factory):
    headers,_ = user_factory(with_profile=False)
    assert client.get("/api/notices/recommended",headers=headers).status_code == 409
    body={"department":"컴퓨터공학과","grade":2,"academic_status":"enrolled","interest_ids":["ai_sw"]}
    assert client.put("/api/profile",headers=headers,json=body).json()["onboarding_complete"] is False
    body["interest_ids"].append("hackathon")
    assert client.put("/api/profile",headers=headers,json=body).json()["onboarding_complete"] is True

def test_unknown_interest_rolls_back(client,user_factory):
    headers,_=user_factory()
    before=client.get("/api/profile",headers=headers).json()
    bad={"department":"의학과","grade":1,"academic_status":"on_leave","interest_ids":["not-a-choice"]}
    assert client.put("/api/profile",headers=headers,json=bad).status_code == 422
    assert client.get("/api/profile",headers=headers).json() == before

def test_profile_version_conflict(client,user_factory):
    headers,_=user_factory()
    body={"department":"컴퓨터공학과","grade":2,"academic_status":"enrolled",
          "interest_ids":["ai_sw","hackathon"],"expected_version":0}
    assert client.put("/api/profile",headers=headers,json=body).status_code == 409

def test_profile_ownership_not_accepted_in_payload(client,user_factory):
    headers, _ = user_factory()
    other, otherid = user_factory("bob")
    body={"department":"컴퓨터공학과","grade":3,"academic_status":"enrolled",
          "interest_ids":["ai_sw","hackathon"],"user_id":otherid}
    assert client.put("/api/profile",headers=headers,json=body).status_code == 422
    assert client.get("/api/profile",headers=other).json()["grade"] == 2

def test_recommendations_use_profile_and_exclude_expired(client,user_factory,notice_factory):
    headers,_ = user_factory()
    good = notice_factory()
    expired = notice_factory(body="대상: 컴퓨터공학과 2학년 재학생\n신청 마감: 2000.09.30 18:00")
    wrong = notice_factory(body="대상: 의학과 4학년 재학생")
    data=client.get("/api/notices/recommended",headers=headers).json()
    assert [n["id"] for n in data["items"]] == [good]
    score = data["items"][0]["recommendation"]
    assert score["score"] == 100
    assert sum(x["score"] for x in score["breakdown"]) == score["score"]
    assert len(score["reasons"]) > 0

def test_new_uses_original_date_not_insertion_order(client,notice_factory):
    first=notice_factory(posted=date(2026,9,18))
    second=notice_factory(posted=date(2026,1,1))
    assert [x["id"] for x in client.get("/api/notices/new").json()["items"]] == [first,second]

def test_literal_search_not_sql_or_wildcards(client,notice_factory):
    ident=notice_factory(title="100% AI 해커톤")
    assert client.get("/api/notices",params={"q":"%"}).json()["total"] == 1
    assert client.get("/api/notices",params={"q":"' OR 1=1 --"}).json()["total"] == 0
    assert client.get("/api/notices",params={"q":"100%"}).json()["items"][0]["id"] == ident

def test_static_route_and_pagination(client,notice_factory):
    for _ in range(5): notice_factory()
    data=client.get("/api/notices/new",params={"page":2,"page_size":2}).json()
    assert data["total"] == 5 and len(data["items"]) == 2
    assert client.get("/api/notices/new",params={"page":0}).status_code == 422
    assert client.get("/api/notices/999999").status_code == 404

def test_bookmark_idempotence_and_isolation(client,user_factory,notice_factory):
    alice,_ = user_factory()
    bob,_ = user_factory("bob")
    ident=notice_factory()
    assert client.post(f"/api/bookmarks/{ident}",headers=alice).status_code == 204
    assert client.post(f"/api/bookmarks/{ident}",headers=alice).status_code == 204
    assert client.get("/api/bookmarks",headers=alice).json()["total"] == 1
    assert client.get("/api/bookmarks",headers=bob).json()["total"] == 0
    assert client.delete(f"/api/bookmarks/{ident}",headers=bob).status_code == 204
    assert client.get("/api/bookmarks",headers=alice).json()["total"] == 1
    assert client.get(f"/api/notices/{ident}",headers=alice).json()["is_bookmarked"] is True
    assert client.get(f"/api/notices/{ident}",headers=bob).json()["is_bookmarked"] is False
    assert client.get(f"/api/notices/{ident}").json()["is_bookmarked"] is False

def test_interest_change_keeps_bookmarks_updates_recommendations(client,user_factory,notice_factory):
    headers,_=user_factory()
    ident=notice_factory(title="AI 해커톤",body="분야별 프로그램")
    client.post(f"/api/bookmarks/{ident}",headers=headers)
    before=client.get("/api/notices/recommended",headers=headers).json()
    assert before["total"] == 1
    client.put("/api/profile",headers=headers,json={"department":"컴퓨터공학과","grade":2,
        "academic_status":"enrolled","interest_ids":["arts","volunteer"]})
    after=client.get("/api/notices/recommended",headers=headers).json()
    assert after["total"] == 0
    assert after["profile_version"] > before["profile_version"]
    assert client.get("/api/bookmarks",headers=headers).json()["total"] == 1

def test_invalid_optional_token_does_not_become_anonymous(client):
    r=client.get("/api/notices",headers={"Authorization":"Bearer invalid"})
    assert r.status_code == 401

def test_only_three_source_codes_accepted(client):
    assert client.get("/api/notices?source=SCNU_GLOCAL").status_code == 422

