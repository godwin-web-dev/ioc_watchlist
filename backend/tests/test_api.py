MD5 = "d41d8cd98f00b204e9800998ecf8427e"


def add(client, value, tags=None, note=None):
    return client.post("/api/iocs", json={"value": value, "tags": tags or [], "note": note})


def test_create_and_list(client):
    r = add(client, "hxxps://evil[.]example[.]com/login", ["Phishing", " c2 ", "phishing"], "seen in mail")
    assert r.status_code == 201
    body = r.json()
    assert body["type"] == "url"
    assert body["value"] == "https://evil.example.com/login"
    assert body["raw_value"] == "hxxps://evil[.]example[.]com/login"
    assert body["tags"] == ["c2", "phishing"]
    assert body["note"] == "seen in mail"
    assert client.get("/api/iocs").json()[0]["id"] == body["id"]


def test_invalid_value_rejected(client):
    r = add(client, "definitely not an ioc")
    assert r.status_code == 422
    detail = r.json()["detail"]
    assert detail["code"] == "invalid_ioc"
    assert "Supported types" in detail["message"]


def test_missing_value_is_validation_error(client):
    r = client.post("/api/iocs", json={})
    assert r.status_code == 422
    assert r.json()["detail"]["code"] == "validation_error"


def test_invalid_tag_rejected(client):
    r = add(client, MD5, ["bad tag!"])
    assert r.status_code == 422


def test_duplicate_identifies_existing_entry(client):
    first = add(client, "https://evil.example.com/login", ["phishing"]).json()
    for variant in [
        "hxxps://evil[.]example[.]com/login",
        "  HTTPS://EVIL.EXAMPLE.COM/login/  ",
        "https://evil.example.com/login#frag",
    ]:
        r = add(client, variant)
        assert r.status_code == 409, variant
        detail = r.json()["detail"]
        assert detail["code"] == "duplicate"
        assert detail["existing"]["id"] == first["id"]
        assert f"#{first['id']}" in detail["message"]
    assert len(client.get("/api/iocs").json()) == 1


def test_duplicate_hash_and_ip_and_domain(client):
    assert add(client, MD5).status_code == 201
    assert add(client, MD5.upper()).status_code == 409
    assert add(client, "1.2.3.4").status_code == 201
    assert add(client, "1[.]2[.]3[.]4").status_code == 409
    assert add(client, "evil.com").status_code == 201
    assert add(client, "EVIL.com.").status_code == 409


def test_filters(client):
    add(client, "evil.com", ["phishing", "c2"])
    add(client, "1.2.3.4", ["c2"])
    add(client, MD5, ["ransomware"])
    ids = lambda params: {i["value"] for i in client.get("/api/iocs", params=params).json()}
    assert ids({"tag": "c2"}) == {"evil.com", "1.2.3.4"}
    assert ids({"tag": "C2"}) == {"evil.com", "1.2.3.4"}
    assert ids({"type": "ipv4"}) == {"1.2.3.4"}
    assert ids({"tag": "c2", "type": "domain"}) == {"evil.com"}
    assert ids({"tag": "nope"}) == set()
    assert client.get("/api/iocs", params={"type": "bogus"}).status_code == 422


def test_delete_and_tag_cleanup(client):
    a = add(client, "evil.com", ["shared", "only-a"]).json()
    add(client, "1.2.3.4", ["shared"])
    assert client.delete(f"/api/iocs/{a['id']}").status_code == 204
    assert client.get("/api/tags").json() == ["shared"]
    assert client.delete(f"/api/iocs/{a['id']}").status_code == 404
    # Re-adding after delete is allowed.
    assert add(client, "evil.com").status_code == 201


def test_many_to_many(client):
    add(client, "evil.com", ["a", "b"])
    add(client, "1.2.3.4", ["b", "c"])
    assert client.get("/api/tags").json() == ["a", "b", "c"]
    assert len(client.get("/api/iocs", params={"tag": "b"}).json()) == 2
