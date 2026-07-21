#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""deploy_git_api.py — 通过 Git Data API 模拟 git push。

github.com:443 不通但 api.github.com 可达时使用。
PAT 从 git remote get-url origin 动态提取。

用法: python src/deploy_git_api.py
"""
import base64, json, os, re, subprocess, sys, urllib.request, urllib.error

REPO = "JiapengMiao/Personal"
API = f"https://api.github.com/repos/{REPO}"
BRANCH = "main"


def get_pat() -> str:
    url = subprocess.check_output(["git", "remote", "get-url", "origin"], text=True).strip()
    m = re.search(r"https://([^@]+)@", url)
    if not m:
        sys.exit("ERROR: no PAT in remote URL")
    return m.group(1)


def api(method: str, path: str, pat: str, body: dict | None = None) -> dict:
    url = f"https://api.github.com{path}" if path.startswith("/") else path
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"token {pat}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")[:600]
        print(f"API ERROR {e.code} {method} {path}: {detail}", file=sys.stderr)
        raise


def main():
    pat = get_pat()
    print(f"PAT len={len(pat)}")

    # local HEAD commit msg
    msg = subprocess.check_output(["git", "log", "-1", "--format=%s"], text=True).strip()
    # remote base SHA
    remote_sha = subprocess.check_output(["git", "rev-parse", f"origin/{BRANCH}"], text=True).strip()
    # cumulative diff remote..HEAD (all commits)
    raw = subprocess.check_output(
        ["git", "diff", "--name-status", remote_sha, "HEAD"], text=True,
    ).strip()
    changes = []
    for line in raw.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        status = parts[0][0]
        fpath = parts[-1]
        changes.append((status, fpath))
    print(f"msg: {msg}")
    print(f"remote: {remote_sha[:8]}  changes: {len(changes)}")

    # base tree
    commit_obj = api("GET", f"{API}/git/commits/{remote_sha}", pat)
    base_tree_sha = commit_obj["tree"]["sha"]

    tree_entries = []
    for status, fpath in changes:
        if status == "D":
            tree_entries.append({"path": fpath, "mode": "100644", "type": "blob", "sha": None})
            print(f"  DEL  {fpath}")
            continue
        local_path = fpath.replace("/", os.sep)
        if not os.path.isfile(local_path):
            print(f"  SKIP missing: {fpath}")
            continue
        with open(local_path, "rb") as f:
            content = f.read()
        b64 = base64.b64encode(content).decode()
        blob = api("POST", f"{API}/git/blobs", pat, {"content": b64, "encoding": "base64"})
        sha = blob["sha"]
        print(f"  blob {sha[:8]} {len(content)/1024:7.1f}KB {fpath}")
        tree_entries.append({"path": fpath, "mode": "100644", "type": "blob", "sha": sha})

    print(f"tree entries: {len(tree_entries)}")

    # create tree (base_tree inherits unchanged files)
    new_tree = api("POST", f"{API}/git/trees", pat, {
        "base_tree": base_tree_sha,
        "tree": tree_entries,
    })
    print(f"new tree: {new_tree['sha'][:8]}")

    # create commit
    new_commit = api("POST", f"{API}/git/commits", pat, {
        "message": msg,
        "tree": new_tree["sha"],
        "parents": [remote_sha],
    })
    print(f"new commit: {new_commit['sha'][:8]}")

    # update ref
    ref = api("PATCH", f"{API}/git/refs/heads/{BRANCH}", pat, {
        "sha": new_commit["sha"],
        "force": False,
    })
    print(f"ref updated: {ref['object']['sha'][:8]}")
    print("DONE")


if __name__ == "__main__":
    main()
