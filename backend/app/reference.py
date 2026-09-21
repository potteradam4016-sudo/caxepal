"""Proposal values, not a claim that the team has approved these taxonomies."""
from sqlalchemy import select
from app.models import Interest, Source
from app.db import dialect_insert

SOURCES = {
    "SCNU_MAIN": {"name": "순천대학교 대표 공지", "site": "SCNU", "mi": "1131", "bbs_id": "1040"},
    "SCNU_SW": {"name": "SW중심대학사업단", "site": "scnusw", "mi": "8889", "bbs_id": "4548"},
    "SCNU_AI": {"name": "AI인재양성부트캠프사업단", "site": "scnuai", "mi": "10241", "bbs_id": "5045"},
}
INTERESTS = [
    ("ai_sw", "AI·SW", "field", ["인공지능", "소프트웨어", "프로그래밍", "코딩", "AI", "SW", "OSS"]),
    ("data", "데이터", "field", ["데이터", "빅데이터", "통계"]),
    ("career", "취업·진로", "field", ["취업", "채용", "진로", "인턴"]),
    ("startup", "창업", "field", ["창업", "스타트업"]),
    ("global", "외국어·해외", "field", ["해외", "외국어", "국제교류", "어학"]),
    ("community", "봉사·사회", "field", ["봉사", "사회공헌"]),
    ("arts", "문화·예술", "field", ["문화", "예술", "디자인", "콘텐츠"]),
    ("academics", "장학·학업", "field", ["장학", "학업", "학술", "마일리지"]),
    ("hackathon", "해커톤", "activity", ["해커톤", "hackathon"]),
    ("contest", "공모전·경진대회", "activity", ["공모전", "경진대회", "대회"]),
    ("education", "교육·캠프", "activity", ["교육", "캠프", "강좌", "특강", "부트캠프"]),
    ("scholarship", "장학금", "activity", ["장학금", "학업장려"]),
    ("internship", "인턴·현장실습", "activity", ["인턴", "현장실습"]),
    ("volunteer", "봉사활동", "activity", ["봉사"]),
    ("exchange", "해외교류", "activity", ["해외", "교환학생", "어학연수"]),
]

def list_url(code: str, page: int = 1) -> str:
    from urllib.parse import urlencode
    s = SOURCES[code]
    return f"https://www.scnu.ac.kr/{s['site']}/na/ntt/selectNttList.do?" + urlencode(
        {"mi": s["mi"], "bbsId": s["bbs_id"], "currPage": page}
    )

def detail_url(code: str, external_id: str) -> str:
    from urllib.parse import urlencode
    if not external_id.isdigit() or len(external_id) > 32:
        raise ValueError("Invalid external ID")
    s = SOURCES[code]
    return f"https://www.scnu.ac.kr/{s['site']}/na/ntt/selectNttInfo.do?" + urlencode(
        {"mi": s["mi"], "bbsId": s["bbs_id"], "nttSn": external_id}
    )

def seed_reference(db):
    for code, item in SOURCES.items():
        db.execute(dialect_insert(db, Source).values(code=code, name=item["name"],
            list_url=list_url(code), enabled=True).on_conflict_do_nothing(index_elements=["code"]))
    for ident, name, kind, keywords in INTERESTS:
        db.execute(dialect_insert(db, Interest).values(id=ident, name=name, type=kind,
            keywords=keywords).on_conflict_do_nothing(index_elements=["id"]))
    db.commit()
