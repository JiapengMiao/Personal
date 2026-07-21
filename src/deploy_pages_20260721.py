# -*- coding: utf-8 -*-
"""部署 docs/ 到 GitHub Pages（Contents API，不用 git push）。
- PUT docs/index.html 与 index.html 引用的 js/css
- DELETE 远端 docs/assets 下不再被引用的 index-*.js/css
- 最后查询 Pages 构建状态
"""
import base64
import json
import re
import subprocess
import sys
import time
import urllib.request

REPO = "JiapengMiao/Personal"
BRANCH = "main"

remote = subprocess.run(
    ["git", "remote", "get-url", "origin"], capture_output=True, text=True, check=True
).stdout.strip()
m = re.search(r"https://([^@]+)@", remote)
TOKEN = m.group(1)
if not TOKEN:
    print("no token in remote url")
    sys.exit(1)


def api(method, path, payload=None):
    req = urllib.request.Request(
        f"https://api.github.com/repos/{REPO}/contents/{path}",
        method=method,
        headers={
            "Authorization": f"token {TOKEN}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "deploy-script",
        },
        data=json.dumps(payload).encode() if payload is not None else None,
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        body = r.read().decode()
        return json.loads(body) if body else {}


def api_pages_build():
    req = urllib.request.Request(
        f"https://api.github.com/repos/{REPO}/pages/builds/latest",
        headers={
            "Authorization": f"token {TOKEN}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "deploy-script",
        },
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


index_html = open("docs/index.html", encoding="utf-8").read()
refs = sorted(set(re.findall(r"index-[A-Za-z0-9_-]+\.(?:js|css)", index_html)))
print("引用文件:", refs)
files = ["docs/index.html"] + [f"docs/assets/{r}" for r in refs]

# 取远端 sha
def get_sha(path):
    try:
        d = api("GET", f"{path}?ref={BRANCH}")
        return d.get("sha")
    except Exception:
        return None

for f in files:
    content = open(f, "rb").read()
    sha = get_sha(f)
    payload = {
        "message": f"deploy: fix zoom hit-testing ({f.split('/')[-1]})",
        "content": base64.b64encode(content).decode(),
        "branch": BRANCH,
    }
    if sha:
        payload["sha"] = sha
    api("PUT", f, payload)
    print("PUT", f, len(content), "bytes")

# 清理远端旧 hash 资源
assets = api("GET", f"docs/assets?ref={BRANCH}")
for item in assets:
    name = item["name"]
    if re.match(r"index-[A-Za-z0-9_-]+\.(js|css)$", name) and name not in refs:
        api("DELETE", f"docs/assets/{name}", {
            "message": f"cleanup stale asset {name}",
            "sha": item["sha"],
            "branch": BRANCH,
        })
        print("DELETE", name)

# 等 Pages 构建
for _ in range(20):
    time.sleep(15)
    try:
        b = api_pages_build()
        print("pages build:", b.get("status"), b.get("commit", "")[:7])
        if b.get("status") == "built":
            break
    except Exception as e:
        print("pages query error:", e)
