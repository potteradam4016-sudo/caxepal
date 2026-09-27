import pytest

from app.services.analysis import extract_rules
from app.services.recommendations import has_ai_sw_topic, load_policy, score_notice


def profile(department="컴퓨터공학과", interests=()):
    return {"department": department, "grade": 2, "academic_status": "enrolled",
            "interests": [{"id": ident, "name": ident, "type": kind} for ident, kind in interests]}


def department_part(result):
    return next(part for part in result["breakdown"] if part["criterion"] == "department")


@pytest.mark.parametrize("title,body", [
    ("AI 해커톤", "참가자를 모집합니다."),
    ("SUMTECH Hackathon", "주제: AI 에이전트 개발"),
    ("SW 캠프", "참가자를 모집합니다."),
    ("일반 해커톤", "○ 모집인원 : 10 명 (AI·SW 전공자 8 명, 비전공자 2 명)"),
    ("일반 교육", "프로그램 내용: 인공지능과 소프트웨어 실습"),
])
def test_ai_sw_topic_from_relevant_evidence(title, body):
    assert has_ai_sw_topic(title, body)


@pytest.mark.parametrize("title,body", [
    ("[SW중심대학사업단] 일반 공지", "신청방법: SW중심대학사업단 홈페이지"),
    ("AI인재양성부트캠프사업단 프로그램", "활동 내용: 팀워크 실습"),
    ("일반 공지", "발행기관: SW중심대학사업단\n하단 안내: AI 관련 문의"),
    ("일반 공지", "프로그램 내용: SW중심대학사업단 주관 행사"),
    ("MAIL 서비스", "모집인원: 10명"),
])
def test_publisher_footer_and_incidental_terms_do_not_create_topic(title, body):
    assert not has_ai_sw_topic(title, body)


@pytest.mark.parametrize("department", ["컴퓨터공학과", "컴퓨터공학전공", "인공지능공학부",
                                         "인공지능공학전공", "컴퓨터교육과", " 컴퓨터 공학과 "])
def test_curated_departments_get_soft_score(department):
    title = "[SW중심대학사업단] SUMTECH Hackathon 2026 참가 안내"
    body = "주제: AI 에이전트 개발\n○ 모집인원 : 10 명 (AI·SW 전공자 8 명, 비전공자 2 명)"
    data, _ = extract_rules(title, body)
    assert data.eligibility_confirmed is False
    result = score_notice(data, profile(department), load_policy(), title=title, body_text=body)
    assert department_part(result)["score"] == 10
    assert "주제가 관련" in department_part(result)["reason"]
    assert "대상" not in department_part(result)["reason"]
    assert result["policy_version"] == "proposal-2"


def test_non_related_major_is_not_excluded_or_guessed():
    title = "SUMTECH Hackathon 2026"
    body = "모집인원: AI·SW 전공자 8명, 비전공자 2명"
    data, _ = extract_rules(title, body)
    for department in ("경영학과", "소프트웨어공학과"):
        result = score_notice(data, profile(department, (("ai_sw", "field"),)), load_policy(),
                              title=title, body_text=body)
        assert result is not None
        assert department_part(result)["score"] == 0
        assert result["score"] == 35


def test_field_ids_without_source_topic_do_not_create_major_affinity():
    data, _ = extract_rules("일반 공지", "프로그램 내용: 협업 실습")
    data.field_ids = ["ai_sw"]
    result = score_notice(data, profile(), load_policy(), title="일반 공지",
                          body_text="프로그램 내용: 협업 실습")
    assert department_part(result)["score"] == 0


def test_eligibility_scores_take_precedence_and_explicit_mismatch_still_excludes():
    title = "AI 캠프"
    policy = load_policy()
    direct, _ = extract_rules(title, "대상: 컴퓨터공학과 2학년 재학생")
    all_departments, _ = extract_rules(title, "대상: 전 학과 2학년 재학생")
    assert department_part(score_notice(direct, profile(), policy, title=title))["score"] == 25
    assert department_part(score_notice(all_departments, profile(), policy, title=title))["score"] == 12
    assert score_notice(direct, profile("경영학과"), policy, title=title) is None


def test_interest_score_is_independent_and_reasons_still_top_three():
    title = "AI 해커톤"
    data, _ = extract_rules(title, "참가자를 모집합니다.")
    result = score_notice(data, profile(interests=(("ai_sw", "field"), ("hackathon", "activity"))),
                          load_policy(), title=title)
    assert result["score"] == 60
    assert [part["score"] for part in result["breakdown"]] == [35, 10, 0, 0, 15]
    assert len(result["reasons"]) == 3
    assert any("주제가 관련" in reason for reason in result["reasons"])
    data.target_statuses = ["enrolled"]
    data.eligibility_confirmed = True
    data.target_text = "대상: 재학생"
    result = score_notice(data, profile(interests=(("ai_sw", "field"), ("hackathon", "activity"))),
                          load_policy(), title=title)
    assert len(result["reasons"]) == 3
    assert all("주제가 관련" not in reason for reason in result["reasons"])


def test_recommended_list_and_detail_share_affinity_score(client, user_factory, notice_factory):
    headers, _ = user_factory()
    title = "[SW중심대학사업단] SUMTECH Hackathon 2026 참가 안내"
    body = "주제: AI 에이전트 개발\n○ 모집인원 : 10 명 (AI·SW 전공자 8 명, 비전공자 2 명)"
    first = notice_factory(title=title, body=body, source="SCNU_MAIN")
    second = notice_factory(title=title, body=body, source="SCNU_MAIN")
    page = client.get("/api/notices/recommended", headers=headers).json()
    assert {item["id"] for item in page["items"]} == {first, second}
    for item in page["items"]:
        detail = client.get(f"/api/notices/{item['id']}", headers=headers).json()
        assert item["recommendation"] == detail["recommendation"]
        assert department_part(item["recommendation"])["score"] == 10

    updated = client.put("/api/profile", headers=headers, json={"department": "경영학과", "grade": 2,
                        "academic_status": "enrolled", "interest_ids": ["ai_sw", "hackathon"]})
    assert updated.status_code == 200
    page = client.get("/api/notices/recommended", headers=headers).json()
    assert {item["id"] for item in page["items"]} == {first, second}
    assert all(department_part(item["recommendation"])["score"] == 0 for item in page["items"])
