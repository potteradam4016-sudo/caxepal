from datetime import date
import pytest
from pydantic import ValidationError
from sqlalchemy import select
from app.config import Settings
from app.models import AuditLog, User
from app.schemas import AnalysisData
from app.services import analysis as module
from app.services.analysis import extract_rules, validate_grounding
from app.services.recommendations import load_policy, score_notice
from tests.conftest import PASSWORD

def test_absent_benefits_not_fabricated():
    data,warnings=extract_rules("AI 교육","내용은 원문을 확인해주세요.")
    assert data.prize.status=="not_stated"
    assert data.mileages==[] and data.schedules==[]
    assert len(data.summary_lines)==3
    assert "RULE_BASED_ANALYSIS" in warnings

def test_explicit_no_prize_and_separate_mileage_systems():
    data,_=extract_rules("교육","상금: 없음\nNOVA 마일리지 10점 (참석 시)\n향림 마일리지 20점 (과제 완료 시)")
    assert data.prize.status=="none"
    assert [m.system for m in data.mileages]==["NOVA","향림"]
    assert [m.points_text for m in data.mileages]==["10점","20점"]

def test_ambiguous_eligibility_is_not_a_hard_filter():
    data,warnings=extract_rules("프로그램","대상: 컴퓨터공학과 등 3학년 재학생")
    assert data.eligibility_confirmed is False
    assert "AMBIGUOUS_ELIGIBILITY" in warnings

def test_ascii_keywords_do_not_match_inside_words():
    data,_=extract_rules("MAIL 안내","normal message")
    assert "ai_sw" not in data.field_ids

def test_no_fabricated_unstated_year_or_mixed_schedule():
    data,_=extract_rules("교육","신청 마감: 9.30 18:00\n신청 기간: 2026.09.01 ~ 행사 일정: 2026.10.01")
    assert not any(s.end_date for s in data.schedules)

def test_ai_fallback_is_explicit(settings,monkeypatch):
    settings.ai_provider="openai"
    def fail(*_): raise ValueError("bad output")
    monkeypatch.setattr(module,"openai_extract",fail)
    data,provider,status,warnings=module.analyze(settings,"교육","테스트")
    assert provider=="rules_fallback" and status=="failed"
    assert "AI_EXTRACTION_FAILED" in warnings

def test_ai_unfounded_date_rejected():
    text="신청 마감: 2026.09.30 18:00"
    data,_=extract_rules("교육",text)
    data.schedules[0].end_date=date(2026,10,1)
    with pytest.raises(ValueError,match="Date not explicit"):
        validate_grounding(data,"교육",text)

def test_ai_invented_benefit_rejected():
    data,_=extract_rules("교육","누구나 참여")
    data.prize.status="present"; data.prize.evidence="상금 100만원"
    with pytest.raises(ValueError,match="Ungrounded prize"):
        validate_grounding(data,"교육","누구나 참여")

def test_recommendation_score_independent_of_dates():
    a,_=extract_rules("AI 해커톤","대상: 컴퓨터공학과 2학년 재학생\n신청 마감: 2026.09.30")
    b,_=extract_rules("AI 해커톤","대상: 컴퓨터공학과 2학년 재학생\n신청 마감: 2070.09.30")
    profile={"department":"컴퓨터공학과","grade":2,"academic_status":"enrolled","interests":[
        {"id":"ai_sw","name":"AI·SW","type":"field"},{"id":"hackathon","name":"해커톤","type":"activity"}]}
    assert score_notice(a,profile,load_policy())==score_notice(b,profile,load_policy())

def test_unknown_eligibility_does_not_earn_match_points():
    data,_=extract_rules("AI 해커톤","프로그램에 참여해주세요.")
    profile={"department":"컴퓨터공학과","grade":2,"academic_status":"enrolled","interests":[
        {"id":"ai_sw","name":"AI·SW","type":"field"},{"id":"hackathon","name":"해커톤","type":"activity"}]}
    score=score_notice(data,profile,load_policy())
    assert score["score"]==50
    assert all(p["score"]==0 for p in score["breakdown"] if p["criterion"] in {"department","grade","academic_status"})

def test_admin_is_not_self_assignable(client,user_factory,app):
    headers,ident=user_factory()
    assert client.get("/api/admin/crawl-jobs",headers=headers).status_code == 403
    assert client.post("/api/auth/register",json={"email":"hack@example.com","password":PASSWORD,"is_admin":True}).status_code == 422
    with app.state.sessions() as db:
        db.get(User,ident).is_admin=True
        db.commit()
    assert client.get("/api/admin/crawl-jobs",headers=headers).status_code == 200
    assert client.post("/api/admin/crawl-jobs",headers=headers,json={}).status_code == 403

def test_manual_review_requires_current_hash(client,user_factory,notice_factory,app):
    headers,ident=user_factory()
    with app.state.sessions() as db:
        db.get(User,ident).is_admin=True; db.commit()
    notice_id=notice_factory()
    detail=client.get(f"/api/notices/{notice_id}",headers=headers).json()
    payload={"expected_content_hash":"0"*64,"analysis":detail["analysis"]["data"]}
    assert client.put(f"/api/admin/notices/{notice_id}/analysis",headers=headers,json=payload).status_code == 409
    payload["expected_content_hash"]=detail["content_hash"]
    r=client.put(f"/api/admin/notices/{notice_id}/analysis",headers=headers,json=payload)
    assert r.status_code == 200 and r.json()["analysis"]["provider"]=="manual"
    assert r.json()["needs_review"] is False

def test_cors_is_explicit(client):
    a=client.options("/api/notices",headers={"Origin":"http://localhost:5173","Access-Control-Request-Method":"GET"})
    b=client.options("/api/notices",headers={"Origin":"https://evil.example","Access-Control-Request-Method":"GET"})
    assert a.headers.get("access-control-allow-origin")=="http://localhost:5173"
    assert "access-control-allow-origin" not in b.headers

def test_security_headers(client):
    r=client.get("/api/notices")
    assert r.headers["x-content-type-options"]=="nosniff"
    assert r.headers["cache-control"]=="no-store"
    assert r.headers["referrer-policy"]=="no-referrer"
    assert r.headers["x-request-id"]

def test_request_size_limit(client,settings):
    r=client.post("/api/auth/register",content=b"x"*(settings.max_request_bytes+1),headers={"Content-Type":"application/json"})
    assert r.status_code == 413

def test_auth_throttle_persists_in_database(client,settings):
    settings.auth_limit_per_15_minutes=1
    body={"email":"unknown@example.com","password":"wrong"}
    assert client.post("/api/auth/login",json=body).status_code == 401
    r=client.post("/api/auth/login",json=body)
    assert r.status_code == 429 and int(r.headers["retry-after"]) > 0

def test_basic_auth_cannot_silently_be_anonymous(client):
    assert client.get("/api/notices",headers={"Authorization":"Basic abc"}).status_code == 401

def test_production_rejects_development_mail_and_sqlite():
    with pytest.raises(ValidationError):
        Settings(_env_file=None,secret_key="x"*40,app_env="production",mail_backend="file")
    with pytest.raises(ValidationError):
        Settings(_env_file=None,secret_key="x"*40,cors_origins="*")

def test_openapi_has_auth_and_calendar_contract(client):
    schema=client.get("/openapi.json").json()
    assert schema["components"]["securitySchemes"]["BearerAuth"]["scheme"]=="bearer"
    assert "/api/calendar" in schema["paths"]
    assert {} in schema["paths"]["/api/notices"]["get"]["security"]
    assert schema["paths"]["/api/profile"]["put"]["requestBody"]

@pytest.mark.parametrize("line", ["상금 미정", "상금 지급 여부는 추후 안내", "상금 관련 문의"])
def test_unknown_prize_not_marked_present(line):
    data, warnings = extract_rules("교육", line)
    assert data.prize.status == "not_stated"
    assert data.prize.description is None

def test_unnamed_mileage_does_not_invent_system_name():
    data, warnings = extract_rules("교육", "참가자에게 마일리지 10점 제공")
    assert data.mileages == []
    assert "MILEAGE_REQUIRES_REVIEW" in warnings

def test_ai_prize_cannot_contradict_negative_evidence():
    data, _ = extract_rules("교육", "상금: 없음")
    data.prize.status = "present"
    with pytest.raises(ValueError, match="contradicts"):
        validate_grounding(data, "교육", "상금: 없음")

def test_ai_summary_cannot_invent_freeform_benefit():
    body = "대상: 전 학과 재학생"
    data, _ = extract_rules("교육 안내", body)
    data.summary_lines[1] = "활동: 참가자 전원에게 상금 100만원 지급"
    checked = validate_grounding(data, "교육 안내", body)
    assert checked.summary_lines[1] == "활동: 교육 안내"

def test_mail_failure_keeps_generic_response_and_audit(client, app, monkeypatch):
    from app.services import mail
    def fail(*args, **kwargs):
        raise RuntimeError("private-provider-error")
    monkeypatch.setattr(mail, "send_action_mail", fail)
    response = client.post("/api/auth/register", json={"email":"delivery@example.com","password":PASSWORD})
    assert response.status_code == 202
    assert "private-provider-error" not in response.text
    with app.state.sessions() as db:
        records = db.scalars(select(AuditLog).where(AuditLog.action=="mail_delivery_failed")).all()
        assert len(records) == 1
        assert records[0].details["error_type"] == "RuntimeError"
        assert "private-provider-error" not in str(records[0].details)
