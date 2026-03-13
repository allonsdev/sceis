import os
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

START_URL = "https://ableproadmin.com/"
DOMAIN = "ableproadmin.com"
SAVE_DIR = "site_clone"

visited = set()

# Create session
session = requests.Session()

# Retry strategy
retry = Retry(
    total=5,
    backoff_factor=1,
    status_forcelist=[403, 429, 500, 502, 503, 504]
)

adapter = HTTPAdapter(max_retries=retry)
session.mount("http://", adapter)
session.mount("https://", adapter)

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive"
}


def get_local_path(url):
    parsed = urlparse(url)
    path = parsed.path

    if path.endswith("/") or path == "":
        path += "index.html"

    return os.path.join(SAVE_DIR, path.lstrip("/"))


def save_file(url, content):
    filepath = get_local_path(url)

    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    with open(filepath, "wb") as f:
        f.write(content)

    print("Saved:", filepath)


def crawl(url):
    if url in visited:
        return

    visited.add(url)

    try:
        r = session.get(url, headers=headers, timeout=15)

        if r.status_code != 200:
            print("Blocked:", url, r.status_code)
            return

        save_file(url, r.content)

        if "text/html" not in r.headers.get("Content-Type", ""):
            return

        soup = BeautifulSoup(r.text, "html.parser")

        for tag in soup.find_all(["a", "link", "script", "img"]):

            attr = "href" if tag.name in ["a", "link"] else "src"

            if tag.get(attr):

                link = urljoin(url, tag[attr])
                parsed = urlparse(link)

                if parsed.netloc == DOMAIN:
                    crawl(link)

        time.sleep(0.5)  # slow down crawler

    except Exception as e:
        print("Error:", url, e)


crawl(START_URL)