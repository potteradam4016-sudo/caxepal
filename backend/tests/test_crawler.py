from dataclasses import replace
from datetime import date
from pathlib import Path
import httpx
import pytest
from sqlalchemy import func, select
from app.crawlers.client import CrawlError, SafeClient
from app.crawlers.parser import ListedNotice, ParseError, parse_detail, parse_list
from app.models import CrawlJob, CrawlRun, Notice
from app.reference import list_url
from app.schemas import CrawlInput
from app.services.crawl import upsert_notice
from app.services.jobs import acquire_lease, enqueue, release_lease, run_next_job

FIXTURES=Path(__file__).parent/"fixtures"
LIST=(FIXTURES/"list.html").read_text(encoding="utf-8")
DETAIL=(FIXTURES/"detail.html").read_text(encoding="utf-8")

def test_list_parser_deduplicates_pinned_and_supports_data_id():
    rows=parse_list(LIST,"SCNU_SW")
    assert len(rows)==2
    assert rows[0].pinned
    assert rows[1].external_id=="12346"
    assert rows[0].posted_date==date(2026,9,18)
    assert "nttSn=12345" in rows[0].original_url

def test_detail_parser_strips_scripts_and_retains_dates():
    listed=parse_list(LIST,"SCNU_SW")[0]
    parsed=parse_detail(DETAIL,listed)
    assert "alert" not in parsed.body_text
    assert "신청 마감" in parsed.body_text
    assert parsed.attachments[0]["name"]=="안내문.pdf"
    assert parsed.attachments[0]["url"].startswith("https://www.scnu.ac.kr/")
    assert len(parsed.content_hash)==64

def test_parser_fails_closed_for_unknown_html():
    with pytest.raises(ParseError):
        parse_list("<html>Maintenance/login page</html>","SCNU_SW")
    with pytest.raises(ParseError):
        parse_detail("<html>Error page</html>",parse_list(LIST,"SCNU_SW")[0])
    assert parse_list("<table>등록된 게시물이 없습니다</table>","SCNU_SW")==[]

def test_untrusted_links_are_not_fetch_targets():
    malicious=LIST.replace('/scnusw/na/ntt/selectNttInfo.do?nttSn=12345','http://127.0.0.1/secret?nttSn=12345')
    rows=parse_list(malicious,"SCNU_SW")
    assert rows[0].original_url.startswith("https://www.scnu.ac.kr/scnusw/")
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
    transport=httpx.MockTransport(lambda req:httpx.Response(200,text="User-agent: *\nDisallow: /scnusw/"))
    with SafeClient(settings,transport=transport,sleeper=lambda _:None) as client:
        client.prepare_robots()
        with pytest.raises(CrawlError,match="ROBOTS_DISALLOWED"):
            client.get_html(list_url("SCNU_SW"))

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
    parsed=parse_detail(DETAIL,parse_list(LIST,"SCNU_SW")[0])
    assert upsert_notice(app.state.sessions,settings,"SCNU_SW",parsed)=="created"
    def should_not_run(*_):
        raise AssertionError("Unchanged body must not be analyzed again.")
    assert upsert_notice(app.state.sessions,settings,"SCNU_SW",parsed,analyzer=should_not_run)=="unchanged"
    changed=parse_detail(DETAIL.replace("10점","20점"),parse_list(LIST,"SCNU_SW")[0])
    assert upsert_notice(app.state.sessions,settings,"SCNU_SW",changed)=="updated"
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
        ident=enqueue(db,CrawlInput(sources=["SCNU_SW"],max_age_days=365)).id
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
        job_id=enqueue(db,CrawlInput(sources=["SCNU_SW"])).id
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
