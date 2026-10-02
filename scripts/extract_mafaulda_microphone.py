"""Extract MAFAULDA microphone channels from the archive into a local float32 cache."""

import argparse
import hashlib
import json
import zipfile
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

COLUMNS = 8
MICROPHONE = 7


def extract(task):
    archive, member, output = task
    target = Path(output) / (member.replace("/", "__")[:-4] + ".npy")
    if target.exists():
        return member, str(target), None
    with zipfile.ZipFile(archive) as source:
        text = source.read(member).decode("ascii").replace("\r", "").strip()
    values = np.fromstring(text.replace("\n", ","), sep=",").reshape(-1, COLUMNS)
    mic = values[:, MICROPHONE].astype(np.float32)
    np.save(target, mic)
    return member, str(target), hashlib.sha256(mic.tobytes()).hexdigest()


def run(archive, output, workers):
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as source:
        members = sorted(name for name in source.namelist() if name.endswith(".csv"))
    tasks = [(str(Path(archive).resolve()), member, str(output)) for member in members]
    with ProcessPoolExecutor(workers) as pool:
        rows = list(pool.map(extract, tasks, chunksize=4))
    index = {member: Path(path).name for member, path, _ in rows}
    (output / "index.json").write_text(json.dumps(index, indent=1), encoding="utf-8")
    return len(index)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, default=Path("data/raw/mafaulda/full.zip"))
    parser.add_argument("--output", type=Path, default=Path("data/derived/mafaulda-microphone"))
    parser.add_argument("--workers", type=int, default=10)
    args = parser.parse_args()
    print(run(args.archive, args.output, args.workers))
