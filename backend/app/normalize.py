"""IOC type detection and canonicalisation.

`normalize(raw)` returns `(ioc_type, canonical_value)`. Two inputs that mean the
same indicator always produce the same canonical value, which is what the
database uses for its uniqueness constraint.

Canonicalisation rules
----------------------
* Surrounding whitespace is stripped; internal whitespace is invalid.
* Defanging is reversed: hxxp -> http, fxp -> ftp, [.] (.) {.} [dot] -> '.',
  [:] -> ':', [://] -> '://'.
* md5 / sha1 / sha256: lowercased hex of length 32 / 40 / 64.
* ipv4: dotted quad, no leading zeros (ambiguous octal), trailing dots/slashes dropped.
* domain: lowercased, IDN converted to punycode, trailing dots/slashes dropped,
  needs >= 2 labels and an alphabetic TLD.
* url: scheme (http/https/ftp) and host lowercased, trailing dot on host removed,
  default port removed, fragment dropped, trailing slashes on the path removed.
  Path and query keep their case because they are case-sensitive.
"""
from __future__ import annotations

import ipaddress
import re
from urllib.parse import urlsplit

IOC_TYPES = ("ipv4", "domain", "url", "md5", "sha1", "sha256")

_HASH_TYPES = {32: "md5", 40: "sha1", 64: "sha256"}
_HEX_RE = re.compile(r"[0-9a-f]+")
_LABEL_RE = re.compile(r"(?!-)[a-z0-9-]{1,63}(?<!-)")
_TLD_RE = re.compile(r"[a-z]{2,63}|xn--[a-z0-9-]{1,59}")
_SCHEMES = {"http": 80, "https": 443, "ftp": 21}


class InvalidIOC(ValueError):
    """Raised when a value is not a valid indicator of any supported type."""


def refang(value: str) -> str:
    v = re.sub(r"(?i)^hxxp", "http", value)
    v = re.sub(r"(?i)^fxp", "ftp", v)
    v = v.replace("[://]", "://").replace("[:]", ":")
    v = re.sub(r"(?i)[\[\(\{]\.[\]\)\}]", ".", v)
    v = re.sub(r"(?i)[\[\(\{]dot[\]\)\}]", ".", v)
    return v


def _canonical_host(host: str) -> tuple[str, str]:
    """Validate a hostname/IP and return (kind, canonical). kind is 'ipv4' or 'domain'."""
    host = host.lower().rstrip(".")
    if not host:
        raise InvalidIOC("Host is empty.")
    try:
        return "ipv4", str(ipaddress.IPv4Address(host))
    except ValueError:
        pass
    try:
        ascii_host = host.encode("idna").decode("ascii")
    except UnicodeError:
        raise InvalidIOC(f"'{host}' is not a valid domain name.") from None
    labels = ascii_host.split(".")
    if len(ascii_host) > 253 or len(labels) < 2:
        raise InvalidIOC(f"'{host}' is not a valid domain name.")
    if not all(_LABEL_RE.fullmatch(label) for label in labels) or not _TLD_RE.fullmatch(labels[-1]):
        raise InvalidIOC(f"'{host}' is not a valid domain name.")
    return "domain", ascii_host


def _canonical_url(value: str) -> str:
    try:
        parts = urlsplit(value)
        port = parts.port
        host = parts.hostname
    except ValueError:
        raise InvalidIOC("Malformed URL.") from None
    scheme = parts.scheme.lower()
    if scheme not in _SCHEMES:
        raise InvalidIOC(f"Unsupported URL scheme '{parts.scheme}'. Use http, https or ftp.")
    if not host:
        raise InvalidIOC("URL has no host.")
    _, host = _canonical_host(host)
    userinfo = parts.netloc.rpartition("@")[0]
    out = f"{scheme}://"
    if userinfo:
        out += f"{userinfo}@"
    out += host
    if port is not None and port != _SCHEMES[scheme]:
        out += f":{port}"
    out += parts.path.rstrip("/")
    if parts.query:
        out += f"?{parts.query}"
    return out  # fragment intentionally dropped


def normalize(raw: str) -> tuple[str, str]:
    if not isinstance(raw, str):
        raise InvalidIOC("Value must be a string.")
    value = refang(raw.strip()).strip()
    if not value:
        raise InvalidIOC("Value is empty.")
    if re.search(r"\s", value):
        raise InvalidIOC("Value must not contain whitespace.")

    lower = value.lower()
    if _HEX_RE.fullmatch(lower) and len(lower) in _HASH_TYPES:
        return _HASH_TYPES[len(lower)], lower

    if "://" in value:
        return "url", _canonical_url(value)

    kind, canonical = _canonical_host(value.rstrip("./"))
    return kind, canonical
