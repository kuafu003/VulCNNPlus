#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import json
from pathlib import Path

import requests


def parse_args():
    parser = argparse.ArgumentParser(description="Send changed C files to VulCNN Flask server")
    parser.add_argument("--server-url", required=True, help="Server endpoint, e.g. https://server/api/v1/detect-pr")
    parser.add_argument("--token", required=True, help="Bearer token for server auth")
    parser.add_argument("--paths-file", required=True, help="Text file: each line is a changed file path")
    parser.add_argument("--repo", required=True)
    parser.add_argument("--pr-number", required=True)
    parser.add_argument("--sha", required=True)
    parser.add_argument("--output-report", required=True, help="Path to write returned report.md")
    parser.add_argument("--timeout", type=int, default=1800)
    return parser.parse_args()


def main():
    args = parse_args()
    paths_file = Path(args.paths_file)
    if not paths_file.exists():
        raise FileNotFoundError(f"paths file not found: {paths_file}")

    changed_files = []
    for line in paths_file.read_text(encoding="utf-8").splitlines():
        p = line.strip()
        if not p or not p.endswith(".c"):
            continue
        fp = Path(p)
        if not fp.exists() or not fp.is_file():
            continue
        changed_files.append({"path": p, "content": fp.read_text(encoding="utf-8", errors="ignore")})

    payload = {
        "repo": args.repo,
        "pr_number": args.pr_number,
        "sha": args.sha,
        "files": changed_files,
    }

    headers = {
        "Authorization": f"Bearer {args.token}",
        "Content-Type": "application/json",
    }
    resp = requests.post(args.server_url, headers=headers, json=payload, timeout=args.timeout)
    if resp.status_code != 200:
        raise RuntimeError(f"server returned {resp.status_code}: {resp.text[:2000]}")

    body = resp.json()
    report_md = body.get("report_md", "# VulCNN CI 检测报告\n\n服务端未返回 report_md")

    output_report = Path(args.output_report)
    output_report.parent.mkdir(parents=True, exist_ok=True)
    output_report.write_text(report_md, encoding="utf-8")

    raw_path = output_report.with_suffix(".raw.json")
    raw_path.write_text(json.dumps(body, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[Done] report saved -> {output_report}")
    print(f"[Done] raw response -> {raw_path}")


if __name__ == "__main__":
    main()
