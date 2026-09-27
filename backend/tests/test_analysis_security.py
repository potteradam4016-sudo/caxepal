import json
import copy
from datetime import date
import httpx
import pytest
import sys
from pydantic import ValidationError
from sqlalchemy import select
from app.config import Settings
from app.models import AuditLog, Notice, User
from app.schemas import AnalysisData
from app.services import analysis as module
from app.services.analysis import extract_rules, validate_grounding
from app.services.dates import dates_in_text
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
    data,_=extract_rules("RAIL 안내","normal message")
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

def test_rule_fallback_extracts_literal_application_method():
    body = "○ 신청방법 : SW중심대학사업단 홈페이지 - 재학생 프로그램 참여신청\n상금: 없음\nNOVA 마일리지 20점 제공"
    data, _ = extract_rules("AI 교육", body)
    assert data.application_method == "SW중심대학사업단 홈페이지 - 재학생 프로그램 참여신청"
    assert data.prize.status == "none"
    assert data.mileages[0].points_text == "20점"
    assert extract_rules("AI 교육", "신청 방법은 추후 안내합니다.")[0].application_method is None

def test_rule_fallback_handles_spaced_method_and_one_sided_deadline():
    body = "신청 기간: ~ 2026. 9. 15.(화)까지\n- 신 청방법 : 담당자 이메일로 신청서류 제출"
    data, _ = extract_rules("학술대회 지원", body)
    assert data.application_method == "담당자 이메일로 신청서류 제출"
    assert len(data.schedules) == 1
    assert data.schedules[0].start_date is None
    assert data.schedules[0].end_date == date(2026, 9, 15)
    abbreviated, _ = extract_rules("교육", "신청기간: 2026. 9. 21. ~ 10. 8.까지")
    assert abbreviated.schedules[0].start_date == date(2026, 9, 21)
    assert abbreviated.schedules[0].end_date == date(2026, 10, 8)


def test_schedule_heading_without_dates_is_not_a_schedule():
    body = "○ 대회 일정\n참가 안내는 추후 공지합니다."
    data, _ = extract_rules("해커톤", body)
    assert data.schedules == []
    assert data.summary_lines[2] == "일정: 일정 미정 · 원문 확인"


def test_event_date_and_flattened_schedule_table_are_extracted():
    body = ("○ 일시 : 2026. 10. 29.( 목 ) ~ 10. 30.( 금 )\n"
            "○ 모집기간 : 2026. 9. 16.( 수 ) ~ 9. 28.( 월 ) 17:00 까지\n"
            "○ 대회 일정\n사전 온라인 교육 | → | 팀 빌딩 | → | 해커톤\n"
            "'26.10.12. ~ 10.18. | '26.10.19. ~ 10.21. | '26.10.29. ~ 10.30.")
    data, _ = extract_rules("해커톤 참가 안내", body)
    assert [(s.kind, s.start_date, s.end_date) for s in data.schedules] == [
        ("event", date(2026, 10, 29), date(2026, 10, 30)),
        ("application", date(2026, 9, 16), date(2026, 9, 28)),
        ("event", date(2026, 10, 12), date(2026, 10, 18)),
        ("event", date(2026, 10, 19), date(2026, 10, 21)),
        ("event", date(2026, 10, 29), date(2026, 10, 30)),
    ]
    assert "대회 일정" not in data.summary_lines[2]
    assert "'26.10.12. ~ 10.18." in data.summary_lines[2]
    assert validate_grounding(data, "해커톤 참가 안내", body).schedules == data.schedules


def test_abbreviated_year_needs_explicit_year_and_same_line_range():
    assert dates_in_text("행사: 10. 29. ~ 10. 30.") == []
    assert dates_in_text("행사: 2026. 12. 31. ~ 1. 1.") == [(date(2026, 12, 31), None)]
    data, _ = extract_rules("행사", "행사 일정: 9월 29일(화)까지")
    assert data.schedules[0].start_date is None
    assert "9월 29일" in data.summary_lines[2]


def test_ai_schedule_cannot_use_heading_only_as_evidence():
    body = "○ 대회 일정\n○ 일시: 2026.10.29."
    data, _ = extract_rules("대회", body)
    data.schedules[0].evidence = "○ 대회 일정"
    data.schedules[0].start_date = None
    data.schedules[0].end_date = None
    with pytest.raises(ValueError, match="no date expression"):
        validate_grounding(data, "대회", body)


def test_recruitment_and_flattened_award_table_keep_literal_evidence():
    body = ("○ 모집인원 : 10 명 (AI·SW 전공자 8 명 , 비전공자 2 명 )\n"
            "○ 시상 내역 구분\n팀 수\n상금 ( 팀당 )\n비고\n"
            "대상\n1 팀\n200만 원 + 현물 (100만 원 상당 )\n기관장상\n"
            "최우수상\n2 팀\n각 200만 원\n총장상\n▼ 자세한 안내")
    data, _ = extract_rules("SUMTECH Hackathon", body)
    assert data.target_text is None
    assert data.recruitment_text == "○ 모집인원 : 10 명 (AI·SW 전공자 8 명 , 비전공자 2 명 )"
    assert "모집인원" in data.summary_lines[0]
    assert data.prize.status == "present"
    assert "대상\n1 팀\n200만 원" in data.prize.evidence
    assert "최우수상\n2 팀\n각 200만 원" in data.prize.description
    assert "자세한 안내" not in data.prize.description
    assert validate_grounding(data, "SUMTECH Hackathon", body).prize.status == "present"


def test_unrelated_amount_does_not_become_prize():
    data, _ = extract_rules("교육", "모집인원: 10명\n참가 경비 100만 원 지원")
    assert data.recruitment_text == "모집인원: 10명"
    assert data.prize.status == "not_stated"


def test_ai_cannot_treat_recruitment_capacity_as_eligibility():
    body = "모집인원: 10명 (AI·SW 전공자 8명, 비전공자 2명)"
    data, _ = extract_rules("프로그램", body)
    data.target_text = body
    checked = validate_grounding(data, "프로그램", body)
    assert checked.target_text is None
    assert checked.recruitment_text == body
    assert checked.summary_lines[0].startswith("대상: 미기재")

def test_application_method_reaches_notice_detail(client, notice_factory):
    body = "○ 신청방법 : SW중심대학사업단 홈페이지 - 재학생 프로그램 참여신청"
    notice_id = notice_factory(body=body)
    detail = client.get(f"/api/notices/{notice_id}").json()
    assert detail["analysis"]["data"]["application_method"] == "SW중심대학사업단 홈페이지 - 재학생 프로그램 참여신청"

@pytest.mark.parametrize("status,expected_calls,expected_code", [
    (400, 1, "AI_REQUEST_ERROR"), (429, 2, "AI_RATE_LIMITED"),
])
def test_openai_http_failures_are_classified(settings, monkeypatch, status, expected_calls, expected_code):
    settings.ai_provider = "openai"
    monkeypatch.setattr(module.time, "sleep", lambda _: None)
    calls = []

    def fail(*_):
        calls.append(1)
        raise module.AnalysisFailure(expected_code, status == 429)

    monkeypatch.setattr(module, "openai_extract", fail)
    _data, provider, state, warnings = module.analyze(settings, "AI 교육", "신청방법: 홈페이지")
    assert len(calls) == expected_calls
    assert (provider, state) == ("rules_fallback", "failed")
    assert expected_code in warnings

def test_openai_configuration_requires_key_and_model():
    with pytest.raises(ValidationError, match="OPENAI_API_KEY"):
        Settings(_env_file=None, secret_key="x"*40, ai_provider="openai", openai_api_key="")
    configured = Settings(_env_file=None, secret_key="x"*40, ai_provider="openai",
                          openai_api_key="test-key", openai_model="gpt-5.6-sol")
    assert configured.ai_provider == "openai"

def openai_response(output):
    return {"status": "completed", "output": [{"type": "message", "status": "completed",
            "content": [{"type": "output_text", "text": json.dumps(output, default=str, ensure_ascii=False)}]}]}


def test_openai_uses_structured_output_and_server_side_key(settings):
    title = "AI 교육"
    body = "대상: 전 학과 재학생\n신청 마감: 2026.09.30 18:00"
    expected, _ = extract_rules(title, body)
    settings.openai_api_key = "test-openai-key"
    settings.openai_model = "gpt-5.6-sol"

    def handler(request):
        assert request.url.host == "api.openai.com"
        assert request.url.path == "/v1/responses"
        assert request.headers["Authorization"] == "Bearer test-openai-key"
        assert "test-openai-key" not in str(request.url)
        payload = json.loads(request.content)
        assert payload["store"] is False
        assert payload["model"] == "gpt-5.6-sol"
        output = payload["text"]["format"]
        assert output["type"] == "json_schema" and output["strict"] is True
        assert output["schema"]["additionalProperties"] is False
        assert set(output["schema"]["properties"]) == set(output["schema"]["required"])
        assert "schedules" in output["schema"]["properties"]
        schedule_schema = output["schema"]["properties"]["schedules"]["items"]
        assert set(schedule_schema["properties"]) == set(schedule_schema["required"])
        values = expected.model_dump(mode="json")
        return httpx.Response(200, json=openai_response({name: values[name]
            for name in module.openai_schema()["properties"]}))

    result = module.openai_extract(settings, title, body, httpx.MockTransport(handler))
    assert result.summary_lines == expected.summary_lines


def test_openai_schedule_output_overrides_rule_schedule(settings):
    title = "행사 안내"
    body = "신청 마감: 2026.09.30\n행사 일정: 2026.10.01"
    expected, _ = extract_rules(title, body)
    values = expected.model_dump(mode="json")
    output = {name: values[name] for name in module.openai_schema()["properties"]}
    output["schedules"] = [values["schedules"][1]]
    output["schedules"][0]["label"] = "AI 행사 일정"
    transport = httpx.MockTransport(lambda _request: httpx.Response(200, json=openai_response(output)))
    result = module.openai_extract(settings, title, body, transport)
    assert len(result.schedules) == 2
    assert result.schedules[0].kind == "event"
    assert result.schedules[0].label == "AI 행사 일정"
    assert result.schedules[1].kind == "application"
    assert "2026.10.01" in result.summary_lines[2]


def test_refresh_schedules_preserves_ai_and_manual_review(
        client, app, settings, notice_factory, monkeypatch, capsys):
    from app import cli

    body = "○ 대회 일정\n○ 일시: 2026.10.29."
    ai_id = notice_factory(body=body)
    manual_id = notice_factory(body=body, title="다른 대회")
    for ident, provider, status in [(ai_id, "openai", "analyzed"),
                                    (manual_id, "manual", "reviewed")]:
        with app.state.sessions() as db:
            analysis = db.get(Notice, ident).analysis
            data = copy.deepcopy(analysis.data)
            data["schedules"] = [{"kind": "event", "label": "행사 일정",
                "start_date": None, "end_date": None, "start_time": None, "end_time": None,
                "evidence": "○ 대회 일정"}]
            data["summary_lines"][2] = "일정: 대회 일정"
            analysis.data = data
            analysis.provider, analysis.status = provider, status
            db.commit()
    monkeypatch.setattr(cli, "get_settings", lambda: settings)
    monkeypatch.setattr(cli, "analyze", lambda *_: pytest.fail("AI must not be called"))
    monkeypatch.setattr(sys, "argv", ["app.cli", "refresh-schedules"])
    cli.main()
    assert "1건 갱신 예정, 관리자 검수 1건 보존" in capsys.readouterr().out
    assert client.get(f"/api/notices/{ai_id}").json()["summary_lines"][2] == "일정: 대회 일정"
    monkeypatch.setattr(sys, "argv", ["app.cli", "refresh-schedules", "--apply"])
    cli.main()
    assert "1건 갱신, 관리자 검수 1건 보존" in capsys.readouterr().out
    ai = client.get(f"/api/notices/{ai_id}").json()
    manual = client.get(f"/api/notices/{manual_id}").json()
    assert ai["summary_lines"][2] == "일정: 2026.10.29."
    assert ai["analysis"]["provider"] == "openai"
    assert ai["analysis"]["status"] == "analyzed"
    assert ai["analysis"]["data"]["schedules"][0]["start_date"] == "2026-10-29"
    assert manual["summary_lines"][2] == "일정: 대회 일정"

@pytest.mark.parametrize("status,code,retryable", [
    (400, "AI_REQUEST_ERROR", False), (404, "AI_MODEL_ERROR", False),
    (429, "AI_RATE_LIMITED", True), (503, "AI_SERVER_ERROR", True),
])
def test_openai_http_response_classification(settings, status, code, retryable):
    settings.openai_api_key = "test-openai-key"
    transport = httpx.MockTransport(lambda _request: httpx.Response(status))
    with pytest.raises(module.AnalysisFailure) as error:
        module.openai_extract(settings, "교육", "신청방법: 홈페이지", transport)
    assert (error.value.code, error.value.retryable) == (code, retryable)
    assert error.value.diagnostics == (f"AI_HTTP_{status}",)

def test_openai_error_diagnostics_exclude_message_and_unrecognized_code(settings):
    settings.openai_api_key = "test-openai-key"
    body = {"error": {"code": "rate_limit_exceeded", "message": "secret-key and private notice body"}}
    transport = httpx.MockTransport(lambda _request: httpx.Response(503, json=body))
    with pytest.raises(module.AnalysisFailure) as error:
        module.openai_extract(settings, "교육", "신청방법: 홈페이지", transport)
    assert error.value.diagnostics == ("AI_HTTP_503", "AI_REMOTE_RATE_LIMIT_EXCEEDED")
    assert "secret-key" not in repr(error.value)
    body["error"]["code"] = "PRIVATE_VALUE"
    with pytest.raises(module.AnalysisFailure) as error:
        module.openai_extract(settings, "교육", "신청방법: 홈페이지", transport)
    assert error.value.diagnostics == ("AI_HTTP_503",)

def test_openai_error_diagnostics_reach_fallback_warnings(settings, monkeypatch):
    settings.ai_provider = "openai"
    monkeypatch.setattr(module.time, "sleep", lambda _: None)
    def fail(*_):
        raise module.AnalysisFailure("AI_SERVER_ERROR", True, ("AI_HTTP_503", "AI_REMOTE_RATE_LIMIT_EXCEEDED"))
    monkeypatch.setattr(module, "openai_extract", fail)
    _data, provider, status, warnings = module.analyze(settings, "교육", "신청방법: 홈페이지")
    assert (provider, status) == ("rules_fallback", "failed")
    assert warnings[-3:] == ["AI_SERVER_ERROR", "AI_HTTP_503", "AI_REMOTE_RATE_LIMIT_EXCEEDED"]

def test_openai_malformed_response_is_classified(settings):
    settings.openai_api_key = "test-openai-key"
    transport = httpx.MockTransport(lambda _request: httpx.Response(200, json={"status": "completed", "output": []}))
    with pytest.raises(module.AnalysisFailure) as error:
        module.openai_extract(settings, "교육", "신청방법: 홈페이지", transport)
    assert error.value.code == "AI_RESPONSE_INVALID"


@pytest.mark.parametrize("response,code,retryable", [
    ({"status": "incomplete", "incomplete_details": {"reason": "max_output_tokens"}},
     "AI_RESPONSE_INCOMPLETE", True),
    ({"status": "completed", "output": [{"type": "message", "status": "completed",
        "content": [{"type": "refusal", "refusal": "private text"}]}]},
     "AI_RESPONSE_REFUSED", False),
])
def test_openai_incomplete_and_refusal(settings, response, code, retryable):
    settings.openai_api_key = "test-openai-key"
    transport = httpx.MockTransport(lambda _request: httpx.Response(200, json=response))
    with pytest.raises(module.AnalysisFailure) as error:
        module.openai_extract(settings, "교육", "신청방법: 홈페이지", transport)
    assert (error.value.code, error.value.retryable) == (code, retryable)
    assert "private text" not in repr(error.value)


def test_openai_insufficient_quota_is_not_retried(settings):
    settings.openai_api_key = "test-openai-key"
    transport = httpx.MockTransport(lambda _request: httpx.Response(429,
        json={"error": {"code": "insufficient_quota"}}))
    with pytest.raises(module.AnalysisFailure) as error:
        module.openai_extract(settings, "교육", "신청방법: 홈페이지", transport)
    assert error.value.code == "AI_RATE_LIMITED"
    assert error.value.retryable is False
    assert error.value.diagnostics == ("AI_HTTP_429", "AI_REMOTE_INSUFFICIENT_QUOTA")

def test_openai_rejects_ungrounded_method(settings):
    settings.openai_api_key = "test-openai-key"
    expected, _ = extract_rules("AI 교육", "신청방법: 홈페이지")
    values = expected.model_dump(mode="json")
    output = {name: values[name] for name in module.openai_schema()["properties"]}
    output["application_method"] = "원문에 없는 포털"
    transport = httpx.MockTransport(lambda _request: httpx.Response(200, json=openai_response(output)))
    with pytest.raises(module.AnalysisFailure) as error:
        module.openai_extract(settings, "AI 교육", "신청방법: 홈페이지", transport)
    assert error.value.code == "AI_GROUNDING_FAILED"


def test_openai_analysis_is_saved_and_returned(client, settings, notice_factory, monkeypatch):
    body = "신청방법: SW중심대학사업단 홈페이지 - 재학생 프로그램 참여신청"
    settings.ai_provider = "openai"

    def extract(_settings, title, text):
        assert text == body
        data, _ = extract_rules(title, text)
        data.confidence = 0.9
        return data

    monkeypatch.setattr(module, "openai_extract", extract)
    notice_id = notice_factory(body=body)
    detail = client.get(f"/api/notices/{notice_id}").json()
    assert detail["analysis"]["provider"] == "openai"
    assert detail["analysis"]["status"] == "analyzed"
    assert detail["analysis"]["data"]["application_method"] == \
        "SW중심대학사업단 홈페이지 - 재학생 프로그램 참여신청"


def test_purge_gemini_analyses_keeps_notices_and_bookmarks(
        client, app, settings, user_factory, notice_factory, monkeypatch, capsys):
    from app import cli

    headers, _ = user_factory()
    legacy_id = notice_factory(body="신청방법: 홈페이지에서 신청")
    current_id = notice_factory(body="신청방법: 방문 신청")
    failed_id = notice_factory(body="신청방법: 이메일로 접수")
    with app.state.sessions() as db:
        legacy = db.get(Notice, legacy_id)
        legacy.analysis.provider = "gemini"
        legacy.analysis.status = "analyzed"
        legacy.analysis.warnings = ["AI_REQUIRES_ORIGINAL_CHECK"]
        current = db.get(Notice, current_id)
        current.analysis.provider = "openai"
        current.analysis.status = "analyzed"
        failed = db.get(Notice, failed_id)
        failed.analysis.provider = "rules_fallback"
        failed.analysis.status = "failed"
        failed.analysis.warnings = ["AI_EXTRACTION_FAILED", "AI_RATE_LIMITED"]
        db.commit()
    assert client.post(f"/api/bookmarks/{legacy_id}", headers=headers).status_code == 204
    monkeypatch.setattr(cli, "get_settings", lambda: settings)
    monkeypatch.setattr(sys, "argv", ["app.cli", "purge-gemini-analyses"])
    cli.main()
    assert "Gemini 분석 1건" in capsys.readouterr().out
    detail = client.get(f"/api/notices/{legacy_id}", headers=headers).json()
    assert detail["is_bookmarked"] is True
    assert detail["analysis"]["provider"] == "rules"
    assert detail["analysis"]["status"] == "needs_review"
    assert detail["analysis"]["data"]["application_method"] == "홈페이지에서 신청"
    assert all(not warning.startswith("AI_") for warning in detail["analysis"]["warnings"])
    assert client.get(f"/api/notices/{current_id}").json()["analysis"]["provider"] == "openai"
    assert client.get(f"/api/notices/{failed_id}").json()["analysis"]["provider"] == "rules_fallback"

    monkeypatch.setattr(sys, "argv", ["app.cli", "purge-gemini-analyses", "--include-failed-fallbacks"])
    cli.main()
    failed_detail = client.get(f"/api/notices/{failed_id}").json()
    assert failed_detail["analysis"]["provider"] == "rules"
    assert failed_detail["analysis"]["status"] == "needs_review"
    assert all(not warning.startswith("AI_") for warning in failed_detail["analysis"]["warnings"])
    assert client.get(f"/api/notices/{current_id}").json()["analysis"]["provider"] == "openai"

def test_reanalysis_failure_preserves_analyzed_result(app, settings, notice_factory, monkeypatch, capsys):
    from app import cli

    notice_id = notice_factory(body="신청방법: 홈페이지")
    with app.state.sessions() as db:
        notice = db.get(Notice, notice_id)
        notice.analysis.status = "analyzed"
        notice.analysis.provider = "gemini"
        db.commit()
    monkeypatch.setattr(cli, "get_settings", lambda: settings)
    def failed_analysis(*_):
        data, warnings = extract_rules("AI 교육", "신청방법: 홈페이지")
        return data, "rules_fallback", "failed", warnings + ["AI_REQUEST_ERROR"]
    monkeypatch.setattr(cli, "analyze", failed_analysis)
    monkeypatch.setattr(sys, "argv", ["app.cli", "reanalyze", "--notice-id", str(notice_id)])
    cli.main()
    assert f"notice_id={notice_id} provider=rules_fallback status=failed saved=False codes=AI_REQUEST_ERROR" in capsys.readouterr().out
    with app.state.sessions() as db:
        notice = db.get(Notice, notice_id)
        assert (notice.analysis.provider, notice.analysis.status) == ("gemini", "analyzed")

def test_reanalysis_failed_only_skips_successful_notice(app, settings, notice_factory, monkeypatch):
    from app import cli

    failed_id = notice_factory(body="신청방법: 홈페이지에서 신청")
    successful_id = notice_factory(body="신청방법: 담당 부서 방문 신청")
    with app.state.sessions() as db:
        db.get(Notice, failed_id).analysis.status = "failed"
        db.get(Notice, successful_id).analysis.status = "analyzed"
        db.commit()
    visited = []
    monkeypatch.setattr(cli, "get_settings", lambda: settings)

    def record_analysis(_settings, _title, body, _image_only):
        visited.append(body)
        data, warnings = extract_rules("교육", body)
        return data, "rules_fallback", "failed", warnings

    monkeypatch.setattr(cli, "analyze", record_analysis)
    monkeypatch.setattr(sys, "argv", ["app.cli", "reanalyze", "--failed-only"])
    cli.main()
    assert len(visited) == 1
    assert "홈페이지에서 신청" in visited[0]

@pytest.mark.parametrize("first_status", ["failed", "analyzed"])
def test_reanalysis_stops_after_rate_limit(app, settings, notice_factory, monkeypatch, first_status):
    from app import cli

    first_id = notice_factory(body="신청방법: 홈페이지에서 신청")
    notice_factory(body="신청방법: 담당 부서 방문 신청")
    with app.state.sessions() as db:
        db.get(Notice, first_id).analysis.status = first_status
        db.commit()
    visited = []
    monkeypatch.setattr(cli, "get_settings", lambda: settings)

    def rate_limited(_settings, _title, body, _image_only):
        visited.append(body)
        data, warnings = extract_rules("교육", body)
        return data, "rules_fallback", "failed", warnings + ["AI_RATE_LIMITED"]

    monkeypatch.setattr(cli, "analyze", rate_limited)
    monkeypatch.setattr(sys, "argv", ["app.cli", "reanalyze"])
    cli.main()
    assert len(visited) == 1
    with app.state.sessions() as db:
        assert db.get(Notice, first_id).analysis.status == first_status

def test_refresh_fallback_preserves_failure_and_skips_openai(app, settings, notice_factory, monkeypatch):
    from app import cli

    notice_id = notice_factory(body="신 청방법: 홈페이지에서 신청")
    with app.state.sessions() as db:
        notice = db.get(Notice, notice_id)
        notice.analysis.status = "failed"
        notice.analysis.warnings = ["AI_EXTRACTION_FAILED", "AI_RATE_LIMITED"]
        db.commit()
    monkeypatch.setattr(cli, "get_settings", lambda: settings)
    monkeypatch.setattr(cli, "analyze", lambda *_: pytest.fail("OpenAI must not be called"))
    monkeypatch.setattr(sys, "argv", ["app.cli", "reanalyze", "--refresh-fallback"])
    cli.main()
    with app.state.sessions() as db:
        analysis = db.get(Notice, notice_id).analysis
        assert analysis.status == "failed"
        assert analysis.data["application_method"] == "홈페이지에서 신청"
        assert "AI_RATE_LIMITED" in analysis.warnings

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
    assert score_notice(a,profile,load_policy(),title="AI 해커톤",body_text="대상: 컴퓨터공학과 2학년 재학생\n신청 마감: 2026.09.30")==score_notice(
        b,profile,load_policy(),title="AI 해커톤",body_text="대상: 컴퓨터공학과 2학년 재학생\n신청 마감: 2070.09.30")

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
    assert client.post("/api/auth/register",json={"username":"hack","password":PASSWORD,"is_admin":True}).status_code == 422
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

@pytest.mark.parametrize("origin", ["http://localhost:5173", "http://127.0.0.1:5173"])
def test_cors_allows_vite_development_origins(client, origin):
    response = client.options("/api/notices", headers={
        "Origin": origin,
        "Access-Control-Request-Method": "GET",
        "Access-Control-Request-Headers": "Authorization, Content-Type",
    })
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin
    allowed_headers = response.headers["access-control-allow-headers"].lower()
    assert "authorization" in allowed_headers
    assert "content-type" in allowed_headers
    assert "access-control-allow-credentials" not in response.headers

@pytest.mark.parametrize("method", ["GET", "POST", "PUT", "DELETE", "OPTIONS"])
def test_cors_preflight_allows_api_methods(client, method):
    response = client.options("/api/notices", headers={
        "Origin": "http://localhost:5173",
        "Access-Control-Request-Method": method,
    })
    assert response.status_code == 200
    assert method in response.headers["access-control-allow-methods"].split(", ")

@pytest.mark.parametrize("origin", ["http://localhost:3000", "https://evil.example"])
def test_cors_rejects_unlisted_origins(client, origin):
    response = client.options("/api/notices", headers={
        "Origin": origin,
        "Access-Control-Request-Method": "GET",
    })
    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers

@pytest.mark.parametrize("path, status", [("/health", 200), ("/api/auth/me", 401)])
def test_cors_headers_are_present_on_actual_responses(client, path, status):
    response = client.get(path, headers={"Origin": "http://localhost:5173"})
    assert response.status_code == status
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    exposed = response.headers["access-control-expose-headers"].lower()
    assert "x-request-id" in exposed
    assert "retry-after" in exposed
    assert "access-control-allow-credentials" not in response.headers

def test_default_cors_origins_are_vite_only():
    settings = Settings(_env_file=None, secret_key="x"*40)
    assert settings.origins == ["http://localhost:5173", "http://127.0.0.1:5173"]

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
    body={"username":"unknown","password":"wrong"}
    assert client.post("/api/auth/login",json=body).status_code == 401
    r=client.post("/api/auth/login",json=body)
    assert r.status_code == 429 and int(r.headers["retry-after"]) > 0

def test_basic_auth_cannot_silently_be_anonymous(client):
    assert client.get("/api/notices",headers={"Authorization":"Basic abc"}).status_code == 401

def test_production_rejects_sqlite():
    with pytest.raises(ValidationError):
        Settings(_env_file=None,secret_key="x"*40,app_env="production")
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


def test_ai_prize_requires_award_label_in_evidence():
    body = "행사 참가 경비 200만 원 지원"
    data, _ = extract_rules("교육", body)
    data.prize.status = "present"
    data.prize.evidence = body
    with pytest.raises(ValueError, match="award label"):
        validate_grounding(data, "교육", body)

def test_ai_summary_cannot_invent_freeform_benefit():
    body = "대상: 전 학과 재학생"
    data, _ = extract_rules("교육 안내", body)
    data.summary_lines[1] = "활동: 참가자 전원에게 상금 100만원 지급"
    checked = validate_grounding(data, "교육 안내", body)
    assert checked.summary_lines[1] == "내용: 교육 안내"
