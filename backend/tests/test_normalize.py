import pytest

from app.normalize import InvalidIOC, normalize

MD5 = "d41d8cd98f00b204e9800998ecf8427e"
SHA1 = "da39a3ee5e6b4b0d3255bfef95601890afd80709"
SHA256 = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"


@pytest.mark.parametrize(
    "raw,expected",
    [
        (MD5, ("md5", MD5)),
        (MD5.upper(), ("md5", MD5)),
        (f"  {SHA1.upper()}\n", ("sha1", SHA1)),
        (SHA256.upper(), ("sha256", SHA256)),
        ("192.168.1.10", ("ipv4", "192.168.1.10")),
        ("192[.]168[.]1[.]10", ("ipv4", "192.168.1.10")),
        ("192(.)168(.)1(.)10.", ("ipv4", "192.168.1.10")),
        ("  8.8.8.8 ", ("ipv4", "8.8.8.8")),
        ("Evil.Example.COM", ("domain", "evil.example.com")),
        ("evil[.]example[.]com", ("domain", "evil.example.com")),
        ("evil[dot]example[dot]com", ("domain", "evil.example.com")),
        ("evil.example.com.", ("domain", "evil.example.com")),
        ("evil.example.com/", ("domain", "evil.example.com")),
        ("bücher.example", ("domain", "xn--bcher-kva.example")),
        ("hxxps://evil[.]example[.]com/login", ("url", "https://evil.example.com/login")),
        ("HXXPS://EVIL.example.COM/login/", ("url", "https://evil.example.com/login")),
        ("https://evil.example.com/login#section", ("url", "https://evil.example.com/login")),
        ("http://evil.com/", ("url", "http://evil.com")),
        ("http://evil.com", ("url", "http://evil.com")),
        ("http://evil.com.:80/a", ("url", "http://evil.com/a")),
        ("https://evil.com:443", ("url", "https://evil.com")),
        ("https://evil.com:8443/x", ("url", "https://evil.com:8443/x")),
        ("hxxp[:]//evil[.]com/a?b=1#frag", ("url", "http://evil.com/a?b=1")),
        ("hxxp://1[.]2[.]3[.]4/payload.exe", ("url", "http://1.2.3.4/payload.exe")),
        ("http://evil.com/Path/CaseMatters", ("url", "http://evil.com/Path/CaseMatters")),
    ],
)
def test_valid(raw, expected):
    assert normalize(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "   ",
        "not an ioc",
        "hello",
        "256.1.1.1",
        "1.2.3",
        "01.2.3.4",
        "evil",
        "-bad.com",
        "bad-.com",
        "evil.123",
        "a..b.com",
        "evil.com/path",  # path without a scheme is not a supported form
        "gopher://evil.com",
        "javascript://evil.com",
        "http://",
        "http://localhost",
        "http://evil.com:abc",
        "d41d8cd98f00b204e9800998ecf8427",  # 31 hex chars
        "g41d8cd98f00b204e9800998ecf8427e",  # non-hex char
        "http://evil .com",
    ],
)
def test_invalid(raw):
    with pytest.raises(InvalidIOC):
        normalize(raw)


def test_equivalent_forms_collapse():
    forms = [
        "hxxps://Evil[.]example[.]com/login/",
        "https://evil.example.com/login",
        "  https://EVIL.example.com/login#top ",
        "https://evil.example.com:443/login",
    ]
    assert len({normalize(f) for f in forms}) == 1
