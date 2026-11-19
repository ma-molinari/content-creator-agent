"""Summarize API metric events from stdin without emitting job data."""

import json
import math
import sys


FORMATS = ("legacy_html", "structured_v1")
OUTCOMES = ("done", "failed", "conflict")


def summarize(lines):
    jobs = {name: {"done": 0, "failed": 0, "conflict": 0, "durations": []} for name in FORMATS}
    cleanup = {"done_batches": 0, "failed_batches": 0, "attempted_objects": 0}
    watchdog = {"done_runs": 0, "failed_runs": 0, "jobs": 0}
    for line in lines:
        if "[metrics] " not in line:
            continue
        fields = {}
        for part in line.split("[metrics] ", 1)[1].split():
            key, sep, value = part.partition("=")
            if sep:
                fields[key] = value
        event = fields.get("event")
        outcome = fields.get("outcome")
        if event == "job_terminal" and fields.get("format") in FORMATS and outcome in OUTCOMES:
            try:
                duration = int(fields["duration_ms"])
                if duration < 0:
                    continue
            except (KeyError, ValueError):
                continue
            item = jobs[fields["format"]]
            item[outcome] += 1
            item["durations"].append(duration)
        elif event == "artifact_cleanup" and outcome in ("done", "failed"):
            try:
                count = int(fields["objects"])
                if count < 0:
                    continue
            except (KeyError, ValueError):
                continue
            cleanup[outcome + "_batches"] += 1
            cleanup["attempted_objects"] += count
        elif event == "stuck_job_cleanup" and outcome in ("done", "failed"):
            try:
                count = int(fields.get("jobs", "0"))
                if count < 0:
                    continue
            except ValueError:
                continue
            watchdog[outcome + "_runs"] += 1
            watchdog["jobs"] += count
    for item in jobs.values():
        durations = sorted(item.pop("durations"))
        item["total"] = sum(item[name] for name in OUTCOMES)
        item["duration_p95_ms"] = durations[math.ceil(len(durations) * 0.95) - 1] if durations else None
    return {"jobs": jobs, "cleanup": cleanup, "watchdog": watchdog}


if __name__ == "__main__":
    print(json.dumps(summarize(sys.stdin), ensure_ascii=False, indent=2))
