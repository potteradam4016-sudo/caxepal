from app.models import Notice
from app.services.analysis import clean_summary_lines, extract_rules, validate_grounding


def test_summary_removes_repeated_labels_markers_and_generic_title_tag():
    raw = [
        "대상: ●대상 : 순천대학교 재학생, 졸업생, 지역청년",
        "활동: [안내]2026 대한민국 에너지 전문 JOB 박람회 참여자 모집",
        "일정: ●신청기간 : 9월 29일(화)까지",
    ]
    expected = [
        "대상: 순천대학교 재학생, 졸업생, 지역청년",
        "내용: 2026 대한민국 에너지 전문 JOB 박람회 참여자 모집",
        "일정: 9월 29일(화)까지",
    ]
    assert clean_summary_lines(raw) == expected
    assert clean_summary_lines(expected) == expected


def test_summary_keeps_meaningful_content_and_multiple_dates():
    assert clean_summary_lines([
        "대상: ○참가대상：재학생 / 모집인원: ○모집인원: 10명",
        "내용: [AI·SW] 개발 캠프",
        "일정: ○접수기간: 9월 29일까지 / ●행사일시: 10월 3일",
    ]) == [
        "대상: 재학생 / 모집인원: 10명",
        "내용: [AI·SW] 개발 캠프",
        "일정: 9월 29일까지 / 10월 3일",
    ]


def test_recommended_audience_label_is_not_repeated():
    raw = [
        "대상: 추천대상 : 대학원 재학생 및 수료후등록생 ( 특수대학원생 포함 )",
        "내용: 연구 프로그램",
        "일정: 원문 확인",
    ]
    assert clean_summary_lines(raw) == [
        "대상: 대학원 재학생 및 수료후등록생 ( 특수대학원생 포함 )",
        "내용: 연구 프로그램",
        "일정: 원문 확인",
    ]
    assert clean_summary_lines(["대상: ● 추천 대상：재학생", *raw[1:]])[0] == "대상: 재학생"


def test_new_rule_and_validated_analysis_use_clean_summary():
    title = "[안내]2026 대한민국 에너지 전문 JOB 박람회 참여자 모집"
    body = "●대상 : 순천대학교 재학생, 졸업생, 지역청년\n●신청기간 : 9월 29일(화)까지"
    data, _ = extract_rules(title, body)
    assert data.summary_lines[0] == "대상: 순천대학교 재학생, 졸업생, 지역청년"
    assert data.summary_lines[1] == "내용: 2026 대한민국 에너지 전문 JOB 박람회 참여자 모집"
    checked = validate_grounding(data, title, body)
    assert checked.summary_lines[:2] == data.summary_lines[:2]


def test_existing_stored_summary_is_cleaned_in_list_and_detail(client, app, notice_factory):
    notice_id = notice_factory()
    with app.state.sessions() as db:
        analysis = db.get(Notice, notice_id).analysis
        analysis.data = {**analysis.data, "summary_lines": [
            "대상: 추천대상 : 대학원 재학생 및 수료후등록생 ( 특수대학원생 포함 )",
            "활동: [안내]2026 대한민국 에너지 전문 JOB 박람회 참여자 모집",
            "일정: ●신청기간 : 9월 29일(화)까지",
        ]}
        db.commit()
    expected = [
        "대상: 대학원 재학생 및 수료후등록생 ( 특수대학원생 포함 )",
        "내용: 2026 대한민국 에너지 전문 JOB 박람회 참여자 모집",
        "일정: 9월 29일(화)까지",
    ]
    page = client.get("/api/notices/new").json()
    assert page["items"][0]["summary_lines"] == expected
    detail = client.get(f"/api/notices/{notice_id}").json()
    assert detail["summary_lines"] == expected
