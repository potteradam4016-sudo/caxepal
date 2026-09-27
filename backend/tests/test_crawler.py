from dataclasses import replace
from datetime import date
from pathlib import Path
import httpx
import pytest
from sqlalchemy import func, select
from app.crawlers.client import CrawlError, SafeClient
from app.crawlers.parser import ListedNotice, ParseError, parse_detail, parse_list
from app.models import Bookmark, CrawlJob, CrawlRun, Notice, Source
from app.reference import list_url, publisher_category
from app.schemas import CrawlInput
from app.services.crawl import upsert_notice
from app.services.jobs import acquire_lease, enqueue, maybe_schedule, release_lease, run_next_job

FIXTURES=Path(__file__).parent/"fixtures"
LIST=(FIXTURES/"list.html").read_text(encoding="utf-8")
DETAIL=(FIXTURES/"detail.html").read_text(encoding="utf-8")
AWARDS=(FIXTURES/"detail_awards.html").read_text(encoding="utf-8")

def test_list_parser_deduplicates_pinned_and_supports_data_id():
    rows=parse_list(LIST,"SCNU_MAIN")
    assert len(rows)==2
    assert rows[0].pinned
    assert rows[1].external_id=="12346"
    assert rows[0].posted_date==date(2026,9,18)
    assert rows[0].author_name == "SW중심대학사업단"
    assert "nttSn=12345" in rows[0].original_url

def test_detail_parser_strips_scripts_and_retains_dates():
    listed=parse_list(LIST,"SCNU_MAIN")[0]
    parsed=parse_detail(DETAIL,listed)
    assert "alert" not in parsed.body_text
    assert "신청 마감" in parsed.body_text
    assert parsed.attachments[0]["name"]=="안내문.pdf"
    assert parsed.attachments[0]["url"].startswith("https://www.scnu.ac.kr/")
    assert len(parsed.content_hash)==64
    assert parsed.author_name == "SW중심대학사업단"


def test_award_table_preserves_rows_and_cells():
    listed = ListedNotice("12345", "SUMTECH Hackathon", date(2026, 9, 18),
                          "https://www.scnu.ac.kr/SCNU/na/ntt/selectNttInfo.do?nttSn=12345")
    parsed = parse_detail(AWARDS, listed)
    assert "구분 | 팀 수 | 상금 (팀당) | 비고" in parsed.body_text
    assert "대상 | 1 팀 | 200만 원 + 현물 (100만 원 상당) | 기관장상" in parsed.body_text
    assert "최우수상 | 2 팀 | 각 200만 원 | 총장상" in parsed.body_text


def test_award_table_reaches_notice_api(client, app, settings):
    listed = ListedNotice("12345", "SUMTECH Hackathon", date(2026, 9, 18),
                          "https://www.scnu.ac.kr/SCNU/na/ntt/selectNttInfo.do?nttSn=12345")
    parsed = parse_detail(AWARDS, listed)
    assert upsert_notice(app.state.sessions, settings, "SCNU_MAIN", parsed) == "created"
    with app.state.sessions() as db:
        notice_id = db.scalar(select(Notice.id))
    detail = client.get(f"/api/notices/{notice_id}").json()
    data = detail["analysis"]["data"]
    assert data["target_text"] is None
    assert "모집인원 : 10 명" in data["recruitment_text"]
    assert data["prize"]["status"] == "present"
    assert "대상 | 1 팀 | 200만 원" in data["prize"]["description"]

def test_parser_fails_closed_for_unknown_html():
    with pytest.raises(ParseError):
        parse_list("<html>Maintenance/login page</html>","SCNU_MAIN")
    with pytest.raises(ParseError):
        parse_detail("<html>Error page</html>",parse_list(LIST,"SCNU_MAIN")[0])
    assert parse_list("<table>등록된 게시물이 없습니다</table>","SCNU_MAIN")==[]

def test_untrusted_links_are_not_fetch_targets():
    malicious=LIST.replace('/SCNU/na/ntt/selectNttInfo.do?nttSn=12345','http://127.0.0.1/secret?nttSn=12345')
    rows=parse_list(malicious,"SCNU_MAIN")
    assert rows[0].original_url.startswith("https://www.scnu.ac.kr/SCNU/")
    parsed=parse_detail(DETAIL.replace('/common/fileDownload.do?fileKey=test','javascript:alert(1)'),rows[0])
    assert parsed.attachments[0]["url"] is None

@pytest.mark.parametrize("url",[
    "http://www.scnu.ac.kr/robots.txt","https://127.0.0.1/robots.txt",
    "https://www.scnu.ac.kr.evil.test/robots.txt","https://www.scnu.ac.kr@evil.test/robots.txt",
    "https://www.scnu.ac.kr/glocal/na/ntt/selectNttList.do","https://www.scnu.ac.kr:444/robots.txt",
    "https://www.scnu.ac.kr/admin",
])
def test_http_allowlist(settings,url):
    with SafeClient(settings) as client:
        with pytest.raises(CrawlError):
            client.validate_url(url)

def test_robots_disallow_stops_crawl(settings):
    transport=httpx.MockTransport(lambda req:httpx.Response(200,text="User-agent: *\nDisallow: /SCNU/"))
    with SafeClient(settings,transport=transport,sleeper=lambda _:None) as client:
        client.prepare_robots()
        with pytest.raises(CrawlError,match="ROBOTS_DISALLOWED"):
            client.get_html(list_url("SCNU_MAIN"))

def test_robots_unavailable_fails_closed(settings):
    transport=httpx.MockTransport(lambda req:httpx.Response(503,text="error"))
    with SafeClient(settings,transport=transport,sleeper=lambda _:None) as client:
        with pytest.raises(CrawlError,match="ROBOTS_HTTP_503"):
            client.prepare_robots()

def test_redirect_not_followed(settings):
    transport=httpx.MockTransport(lambda req:httpx.Response(302,headers={"Location":"http://127.0.0.1/secret"}))
    with SafeClient(settings,transport=transport,sleeper=lambda _:None) as client:
        with pytest.raises(CrawlError,match="REDIRECT_NOT_ALLOWED"):
            client.request("https://www.scnu.ac.kr/robots.txt")

def test_retry_is_bounded_and_respects_retry_after(settings):
    calls=[]
    waits=[]
    def handler(req):
        calls.append(req)
        return httpx.Response(429,headers={"Retry-After":"2"}) if len(calls)<3 else httpx.Response(200,text="ok")
    with SafeClient(settings,transport=httpx.MockTransport(handler),sleeper=waits.append) as client:
        status,text=client.request("https://www.scnu.ac.kr/robots.txt")
    assert status==200 and len(calls)==3
    assert 2 in waits

def test_http_response_size_cap(settings):
    transport=httpx.MockTransport(lambda req:httpx.Response(200,content=b"x"*4_000_001))
    with SafeClient(settings,transport=transport,sleeper=lambda _:None) as client:
        with pytest.raises(CrawlError,match="TOO_LARGE"):
            client.request("https://www.scnu.ac.kr/robots.txt")

def test_upsert_is_idempotent_and_reanalyzes_only_changes(app,settings):
    parsed=parse_detail(DETAIL,parse_list(LIST,"SCNU_MAIN")[0])
    assert upsert_notice(app.state.sessions,settings,"SCNU_MAIN",parsed)=="created"
    def should_not_run(*_):
        raise AssertionError("Unchanged body must not be analyzed again.")
    assert upsert_notice(app.state.sessions,settings,"SCNU_MAIN",parsed,analyzer=should_not_run)=="unchanged"
    assert upsert_notice(app.state.sessions,settings,"SCNU_MAIN",
                         replace(parsed, author_name="RISE사업단"),analyzer=should_not_run)=="unchanged"
    with app.state.sessions() as db:
        notice = db.scalar(select(Notice))
        assert (notice.author_name, notice.publisher_category) == ("RISE사업단", "rise")
    changed=parse_detail(DETAIL.replace("10점","20점"),parse_list(LIST,"SCNU_MAIN")[0])
    assert upsert_notice(app.state.sessions,settings,"SCNU_MAIN",changed)=="updated"
    with app.state.sessions() as db:
        assert db.scalar(select(func.count()).select_from(Notice))==1
        notice=db.scalar(select(Notice))
        assert notice.analysis.data["mileages"][0]["points_text"]=="20점"
        assert notice.analysis.content_hash==notice.content_hash

def test_lease_prevents_duplicate_workers(app):
    factory=app.state.sessions
    assert acquire_lease(factory,"test","one")
    assert not acquire_lease(factory,"test","two")
    release_lease(factory,"test","two")
    assert not acquire_lease(factory,"test","two")
    release_lease(factory,"test","one")
    assert acquire_lease(factory,"test","two")

def test_durable_worker_pipeline_success(app,settings):
    settings.crawl_enabled=True
    def handler(req):
        if req.url.path=="/robots.txt":
            return httpx.Response(200,text="User-agent: *\nDisallow:")
        return httpx.Response(200,text=LIST if req.url.path.endswith("selectNttList.do") else DETAIL)
    def client_factory(s,heartbeat):
        return SafeClient(s,transport=httpx.MockTransport(handler),sleeper=lambda _:None,heartbeat=heartbeat)
    with app.state.sessions() as db:
        ident=enqueue(db,CrawlInput(sources=["SCNU_MAIN"],max_age_days=365)).id
    assert run_next_job(app.state.sessions,settings,ident,client_factory)==ident
    with app.state.sessions() as db:
        job=db.get(CrawlJob,ident)
        assert job.status=="completed",job.result
        assert job.result["sources"][0]["counts"]["created"]==2
        assert db.scalar(select(func.count()).select_from(Notice))==2

def test_source_failure_does_not_delete_stored_notices(app,settings,notice_factory):
    ident=notice_factory()
    settings.crawl_enabled=True
    class Failed:
        def __init__(self,*_,**__): pass
        def __enter__(self): return self
        def __exit__(self,*_): pass
        def prepare_robots(self): pass
        def get_html(self,*_): raise CrawlError("SOURCE_HTTP_503")
    with app.state.sessions() as db:
        job_id=enqueue(db,CrawlInput(sources=["SCNU_MAIN"])).id
    run_next_job(app.state.sessions,settings,job_id,Failed)
    with app.state.sessions() as db:
        assert db.get(Notice,ident) is not None
        assert db.get(CrawlJob,job_id).status=="failed"
        assert db.scalar(select(CrawlRun)).status=="failed"

def test_disabled_worker_never_fetches(app,settings):
    with app.state.sessions() as db:
        ident=enqueue(db,CrawlInput()).id
    assert run_next_job(app.state.sessions,settings,ident) is None
    with app.state.sessions() as db:
        assert db.get(CrawlJob,ident).status=="queued"


def test_auto_crawl_checks_up_to_forty_notices_across_five_pages(app, settings):
    settings.crawl_enabled = True
    settings.auto_crawl = True
    assert CrawlInput().max_notices == 40
    assert CrawlInput(pages=5).pages == 5
    with pytest.raises(ValueError):
        CrawlInput(pages=6)
    with pytest.raises(ValueError):
        CrawlInput(max_notices=41)
    maybe_schedule(app.state.sessions, settings)
    maybe_schedule(app.state.sessions, settings)
    with app.state.sessions() as db:
        jobs = db.scalars(select(CrawlJob)).all()
        assert len(jobs) == 1
        assert jobs[0].parameters == {"sources": ["SCNU_MAIN"], "pages": 5,
                                      "max_notices": 40, "max_age_days": 60}


@pytest.mark.parametrize("author,expected", [
    ("SW중심대학사업단", "sw_center"), (" AI 인재양성부트캠프사업단 ", "ai_bootcamp"),
    ("RISE사업단", "rise"), ("산학협력교육센터", "industry_education"),
    ("첨단소재광양캠퍼스", "gwangyang"), ("대학일자리플러스센터", "other"),
    (None, "other"),
])
def test_author_category_uses_exact_author_name(author, expected):
    assert publisher_category(author) == expected


def test_legacy_boards_are_disabled_and_rejected(client, app, settings):
    with app.state.sessions() as db:
        assert {s.code for s in db.scalars(select(Source).where(Source.enabled.is_(True)))} == {"SCNU_MAIN"}
    assert client.get("/api/sources").json()[0]["code"] == "SCNU_MAIN"
    assert client.post("/api/admin/crawl-jobs", json={"sources": ["SCNU_SW"]}).status_code in (401, 403)
    with pytest.raises(ValueError):
        CrawlInput(sources=["SCNU_SW"])
    with SafeClient(settings) as safe:
        with pytest.raises(CrawlError, match="UNSAFE_CRAWL_URL"):
            safe.validate_url(list_url("SCNU_SW"))


def test_legacy_purge_is_previewed_and_cascades_only_legacy_rows(app, notice_factory, user_factory):
    from app.cli import purge_legacy_notices
    _, user_id = user_factory()
    main_id = notice_factory(source="SCNU_MAIN")
    sw_id = notice_factory(source="SCNU_SW")
    ai_id = notice_factory(source="SCNU_AI")
    with app.state.sessions() as db:
        db.add_all([Bookmark(user_id=user_id, notice_id=ident) for ident in (main_id, sw_id, ai_id)])
        db.commit()
        assert purge_legacy_notices(db) == (2, 2)
        assert db.get(Notice, sw_id) is not None
        assert purge_legacy_notices(db, apply=True) == (2, 2)
    with app.state.sessions() as db:
        assert db.get(Notice, main_id) is not None
        assert db.get(Notice, sw_id) is None and db.get(Notice, ai_id) is None
        assert [b.notice_id for b in db.scalars(select(Bookmark))] == [main_id]
