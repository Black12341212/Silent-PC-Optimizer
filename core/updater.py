import urllib.request
import urllib.error
import json
from core.logger import logger
from core.version import VERSION, GITHUB_REPO


def _normalize_version(tag):
    tag = tag.lstrip("vV")
    parts = []
    for p in tag.split("."):
        num = ""
        for ch in p:
            if ch.isdigit():
                num += ch
            else:
                break
        parts.append(int(num) if num else 0)
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts[:3])


def get_latest_release():
    try:
        url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
        req = urllib.request.Request(url, headers={"User-Agent": "SilentPCOptimizer"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return {
            "tag": data.get("tag_name", ""),
            "name": data.get("name", ""),
            "html_url": data.get("html_url", ""),
            "body": data.get("body", ""),
        }
    except (urllib.error.URLError, ValueError, Exception) as e:
        logger.debug(f"Не удалось проверить обновления: {e}")
        return None


def check_for_update():
    release = get_latest_release()
    if not release or not release.get("tag"):
        return None
    current = _normalize_version(VERSION)
    latest = _normalize_version(release["tag"])
    if latest > current:
        return release
    return None


def download_url_for(release):
    return release.get("html_url") or f"https://github.com/{GITHUB_REPO}/releases"
