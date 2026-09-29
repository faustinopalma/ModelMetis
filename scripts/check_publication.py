import argparse
import json
import re
import subprocess
import time

SECRET_PATTERNS = {
    "private_key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"),
    "jwt": re.compile(r"eyJ[A-Za-z0-9_-]{12,}\.[A-Za-z0-9_-]{12,}\.[A-Za-z0-9_-]{12,}"),
    "github_token": re.compile(r"(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})"),
    "storage_key": re.compile(r"(?i)AccountKey\s*=\s*[A-Za-z0-9+/]{40,}={0,2}"),
    "sas_signature": re.compile(r"(?i)[?&]sig=[A-Za-z0-9%+/]{24,}"),
    "literal_secret": re.compile(
        r'''(?i)["']?(?:access_token|accessToken|refresh_token|client_secret|api_key|api-key)'''
        r'''["']?\s*[:=]\s*["'][A-Za-z0-9_+/=.-]{24,}["']'''
    ),
}


def findings(path, payload):
    normalized = path.replace("\\", "/").lower()
    parts = normalized.split("/")
    filename = parts[-1]
    forbidden = any(part in {".azure", ".copilot-azure", "artifacts", "data"} for part in parts)
    if normalized in {"data/readme.md"}:
        forbidden = False
    forbidden |= (filename.startswith(".env") and filename not in {".env.sample", ".env.example"})
    forbidden |= filename.endswith((".pem", ".key", ".pfx", ".p12"))
    forbidden |= "msal_" in filename or filename == "azureprofile.json"
    result = ["forbidden_artifact_path"] if forbidden else []
    text = payload.decode("utf-8", errors="replace")
    result.extend(name for name, pattern in SECRET_PATTERNS.items() if pattern.search(text))
    return result


def git_bytes(arguments):
    process = subprocess.run(["git", *arguments], capture_output=True, check=False)
    if process.returncode:
        raise RuntimeError("Git index inspection failed; no payload is printed.")
    return process.stdout


def scan_index():
    paths = [entry.decode("utf-8") for entry in git_bytes(["ls-files", "-z"]).split(b"\0")
             if entry]
    if not paths:
        raise ValueError("Refusing a publication check with zero indexed files.")
    issues = []
    for path in paths:
        reasons = findings(path, git_bytes(["show", ":" + path]))
        if reasons:
            issues.append({"path": path, "reasons": reasons})
    return {"indexed_files_scanned": len(paths), "findings": issues,
            "scope": "Current Git index, not history or remote secrets; pattern-based check only."}


if __name__ == "__main__":
    started = time.perf_counter()
    parser = argparse.ArgumentParser(description="Redacted credential check of the Git index.")
    parser.parse_args()
    report = scan_index()
    print(json.dumps(report, indent=2))
    print(f"ElapsedSeconds={time.perf_counter() - started:.6f}")
    raise SystemExit(1 if report["findings"] else 0)