from datetime import date, datetime, time
from app.schemas import Schedule
from app.services.dates import SEOUL, dates_in_text, deadline_badge, deadline_values

def test_date_only_deadline_end_of_seoul_day():
    s=Schedule(kind="application",label="신청",start_date=None,end_date=date(2026,9,21),
               start_time=None,end_time=None,evidence="2026.09.21")
    d,ts=deadline_values([s])
    assert datetime.fromtimestamp(ts,tz=SEOUL).time() == time(23,59,59)
    assert deadline_badge(d,ts,ts)[2] is False
    assert deadline_badge(d,ts,ts+1)[2] is True

def test_exact_deadline_can_expire_on_dday():
    deadline=int(datetime(2026,9,21,18,0,tzinfo=SEOUL).timestamp())
    d,label,closed=deadline_badge(date(2026,9,21),deadline,deadline+1)
    assert d == 0 and closed and label == "마감"

def test_event_does_not_become_application_deadline():
    s=Schedule(kind="event",label="행사",start_date=date(2026,10,1),end_date=date(2026,10,3),
               start_time=None,end_time=None,evidence="event")
    assert deadline_values([s]) == (None,None)

def test_unknown_additional_application_window_prevents_false_closure():
    a=Schedule(kind="application",label="1차",start_date=None,end_date=date(2026,9,1),
               start_time=None,end_time=None,evidence="1차")
    b=Schedule(kind="application",label="추가",start_date=None,end_date=None,
               start_time=None,end_time=None,evidence="미정")
    assert deadline_values([a,b]) == (None,None)

def test_no_year_guess():
    assert dates_in_text("신청 마감: 9.30 18:00") == []
    assert dates_in_text("2026.02.30") == []
    assert dates_in_text("2026년 9월 30일 18시")[0] == (date(2026,9,30),time(18))

def test_calendar_overlap_labels_and_expired_application(client,user_factory,notice_factory):
    headers,_=user_factory()
    ident=notice_factory(body="신청 기간: 2020.08.25 ~ 2020.09.05\n행사 기간: 2020.09.29 ~ 2020.10.03")
    client.post(f"/api/bookmarks/{ident}",headers=headers)
    data=client.get("/api/calendar?month=2020-09",headers=headers).json()
    assert len(data["events"]) == 2
    assert {e["kind"] for e in data["events"]} == {"application","event"}
    event=next(e for e in data["events"] if e["kind"]=="event")
    assert event["display_end"]=="2020-09-30" and event["continues_after_month"]
    october=client.get("/api/calendar?month=2020-10",headers=headers).json()
    assert len(october["events"]) == 1
    assert october["events"][0]["display_start"]=="2020-10-01"
    assert october["events"][0]["start_date"]=="2020-09-29"

def test_calendar_no_dates_and_ownership(client,user_factory,notice_factory):
    alice,_=user_factory()
    bob,_=user_factory("bob")
    ident=notice_factory(body="일정은 추후 안내합니다.")
    client.post(f"/api/bookmarks/{ident}",headers=alice)
    assert client.get("/api/calendar?month=2026-09",headers=alice).json()["undated"][0]["notice_id"] == ident
    assert client.get("/api/calendar?month=2026-09",headers=bob).json()["undated"] == []
    assert client.get("/api/calendar?month=2026-13",headers=alice).status_code == 422

def test_calendar_lone_end_is_point_with_null_start(client,user_factory,notice_factory):
    headers,_=user_factory()
    ident=notice_factory(body="신청 마감: 2070.09.30 18:00")
    client.post(f"/api/bookmarks/{ident}",headers=headers)
    e=client.get("/api/calendar?month=2070-09",headers=headers).json()["events"][0]
    assert e["start_date"] is None and e["is_partial"]
    assert e["display_start"]==e["display_end"]=="2070-09-30"

