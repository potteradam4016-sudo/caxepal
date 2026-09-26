from datetime import date
import pytest


@pytest.mark.parametrize("path", ["/api/notices", "/api/notices/new", "/api/notices/recommended"])
def test_category_union_before_pagination(client, user_factory, notice_factory, path):
    headers, _ = user_factory()
    def category(value):
        return lambda data: data.model_copy(update={"category": value})
    first = notice_factory(posted=date(2026, 9, 23), modify=category("education"))
    second = notice_factory(posted=date(2026, 9, 22), modify=category("contest"))
    notice_factory(posted=date(2026, 9, 24), modify=category("career"))
    params = [("category", "education"), ("category", "contest"), ("page_size", "1")]
    response = client.get(path, headers=headers, params=params)
    assert response.status_code == 200
    assert response.json()["total"] == 2
    assert response.json()["items"][0]["id"] == first
    response = client.get(path, headers=headers, params=params + [("page", "2")])
    assert response.json()["items"][0]["id"] == second
    single = client.get(path, headers=headers, params={"category": "contest"})
    assert single.json()["total"] == 1
    assert single.json()["items"][0]["id"] == second
    duplicate = client.get(path, headers=headers, params=[("category", "contest"), ("category", "contest")])
    assert duplicate.json()["total"] == 1
    assert client.get(path, headers=headers, params={"category": "invalid"}).status_code == 422
