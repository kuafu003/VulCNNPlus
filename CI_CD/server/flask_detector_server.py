#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
import subprocess
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from flask import Flask, jsonify, request


ROOT = Path(__file__).resolve().parents[2]
DETECTOR_SCRIPT = ROOT / "CI_CD" / "vulcnn_cicd_detector.py"


def create_app() -> Flask:
    app = Flask(__name__)

    @app.get("/healthz")
    def healthz():
        return jsonify({"status": "ok", "time": datetime.utcnow().isoformat() + "Z"})

    @app.post("/api/v1/detect-pr")
    def detect_pr():
        expected_token = os.getenv("VULCNN_SERVER_TOKEN", "")
        if expected_token:
            auth_header = request.headers.get("Authorization", "")
            if not auth_header.startswith("Bearer "):
                return jsonify({"error": "missing bearer token"}), 401
            got = auth_header.split(" ", 1)[1].strip()
            if got != expected_token:
                return jsonify({"error": "invalid bearer token"}), 403

        checkpoint = os.getenv("VULCNN_CHECKPOINT_PATH", "").strip()
        if not checkpoint:
            return jsonify({"error": "VULCNN_CHECKPOINT_PATH is not configured on server"}), 500
        if not os.path.exists(checkpoint):
            return jsonify({"error": f"checkpoint not found: {checkpoint}"}), 500

        payload = request.get_json(silent=True) or {}
        files = payload.get("files", [])
        repo = payload.get("repo", "unknown")
        pr_number = payload.get("pr_number", "unknown")
        sha = payload.get("sha", "unknown")

        c_files = [x for x in files if str(x.get("path", "")).endswith(".c")]
        if not c_files:
            report = build_markdown_report(repo, pr_number, sha, [])
            return jsonify({"report_md": report, "results": []})

        run_id = str(uuid.uuid4())[:12]
        base_tmp = Path(tempfile.gettempdir()) / "vulcnn_server_runs" / run_id
        base_tmp.mkdir(parents=True, exist_ok=True)

        results: List[Dict] = []
        errors: List[Dict] = []
        device = os.getenv("VULCNN_DEVICE", "auto")

        for index, file_item in enumerate(c_files):
            src_rel_path = str(file_item.get("path", "")).strip()
            src_content = str(file_item.get("content", ""))
            safe_name = src_rel_path.replace("/", "__")
            if not safe_name.endswith(".c"):
                safe_name += ".c"

            input_c = base_tmp / safe_name
            input_c.write_text(src_content, encoding="utf-8")

            one_jsonl = base_tmp / f"one_{index}.jsonl"
            pipeline_dir = base_tmp / "pipeline"
            cmd = [
                "python",
                str(DETECTOR_SCRIPT),
                "--input-c",
                str(input_c),
                "--run-mature-pipeline",
                "--pipeline-work-dir",
                str(pipeline_dir),
                "--checkpoint",
                checkpoint,
                "--output-jsonl",
                str(one_jsonl),
                "--device",
                device,
            ]

            proc = subprocess.run(cmd, cwd=str(ROOT), text=True, capture_output=True)
            if proc.returncode != 0:
                errors.append(
                    {
                        "path": src_rel_path,
                        "type": "detector_failed",
                        "stderr": proc.stderr[-4000:],
                        "stdout": proc.stdout[-4000:],
                    }
                )
                continue

            if not one_jsonl.exists():
                errors.append({"path": src_rel_path, "type": "missing_output_jsonl"})
                continue

            lines = [line.strip() for line in one_jsonl.read_text(encoding="utf-8").splitlines() if line.strip()]
            if not lines:
                errors.append({"path": src_rel_path, "type": "empty_output_jsonl"})
                continue

            try:
                result = json.loads(lines[0])
            except Exception as ex:
                errors.append({"path": src_rel_path, "type": "json_parse_error", "detail": str(ex)})
                continue

            result["pr_file_path"] = src_rel_path
            results.append(result)

        report = build_markdown_report(repo, pr_number, sha, results, errors)
        return jsonify({"report_md": report, "results": results, "errors": errors})

    return app


def build_markdown_report(repo: str, pr_number, sha: str, results: List[Dict], errors: List[Dict] = None) -> str:
    errors = errors or []
    total = len(results)
    risky = [r for r in results if r.get("detection_result") == 1]

    lines = []
    lines.append("# VulCNN CI 检测报告")
    lines.append("")
    lines.append(f"- 仓库: `{repo}`")
    lines.append(f"- PR: `{pr_number}`")
    lines.append(f"- Commit: `{sha}`")
    lines.append(f"- 扫描文件数: `{total}`")
    lines.append(f"- 检测为漏洞(class=1)数: `{len(risky)}`")
    lines.append("")

    if total == 0:
        lines.append("未发现可扫描的 `.c` 变更文件。")
        lines.append("")

    if results:
        lines.append("## 文件级结果")
        lines.append("")
        lines.append("| 文件 | 结果(0/1) | 预测置信度 | 漏洞概率(class=1) | 可疑行 |")
        lines.append("|---|---:|---:|---:|---|")
        for r in results:
            path = r.get("pr_file_path", r.get("file_name", "unknown"))
            det = r.get("detection_result")
            conf = r.get("predicted_class_confidence")
            vulp = r.get("vuln_probability")
            lines_no = r.get("suspicious_lines") or []
            conf_s = "-" if conf is None else f"{float(conf):.4f}"
            vulp_s = "-" if vulp is None else f"{float(vulp):.4f}"
            lines.append(f"| `{path}` | `{det}` | `{conf_s}` | `{vulp_s}` | `{lines_no}` |")
        lines.append("")

    if risky:
        lines.append("## 高风险文件")
        lines.append("")
        for r in risky:
            path = r.get("pr_file_path", r.get("file_name", "unknown"))
            lines.append(f"- `{path}`: vuln_probability={r.get('vuln_probability')}")
        lines.append("")

    if errors:
        lines.append("## 处理失败")
        lines.append("")
        for e in errors:
            lines.append(f"- `{e.get('path', 'unknown')}`: `{e.get('type', 'unknown_error')}`")
        lines.append("")

    return "\n".join(lines)


if __name__ == "__main__":
    host = os.getenv("VULCNN_SERVER_HOST", "0.0.0.0")
    port = int(os.getenv("VULCNN_SERVER_PORT", "5001"))
    app = create_app()
    app.run(host=host, port=port, debug=False)
