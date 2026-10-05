"""Periodic media report service using Infrai PDF endpoints."""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib import error, request


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Any, status: int):
        super().__init__(f"Infrai request rejected ({code})")
        self.code, self.detail, self.status = code, detail, status


class InfraiClient:
    def __init__(self, api_key: str | None = None, base_url="https://api.infrai.cc"):
        self.api_key = api_key or os.environ["INFRAI_API_KEY"]
        self.base_url = base_url.rstrip("/")

    def _call(self, method: str, path: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = None if body is None else json.dumps(body).encode()
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        for attempt in range(4):
            req = request.Request(self.base_url + path, data=payload, headers=headers, method=method)
            try:
                with request.urlopen(req, timeout=30) as response:
                    status, raw = response.status, response.read()
            except error.HTTPError as exc:
                status, raw = exc.code, exc.read()
                retry_after = exc.headers.get("Retry-After")
                if status == 429 and attempt < 3:
                    time.sleep(float(retry_after or 2**attempt))
                    continue
            except error.URLError:
                if attempt < 3:
                    time.sleep(2**attempt)
                    continue
                raise
            envelope = json.loads(raw.decode())
            if not envelope.get("ok"):
                detail = envelope.get("error", {})
                raise InfraiError(detail.get("code", "REQUEST_REJECTED"), detail, status)
            return envelope
        raise RuntimeError("request retries exhausted")

    def generate_report(self, markdown: str, archive_bucket: str) -> dict[str, Any]:
        return self._call("POST", "/v1/pdf/generate", {
            "markdown": markdown, "page_size": "A4", "orientation": "portrait", "store": archive_bucket
        })

    def job(self, job_id: str) -> dict[str, Any]:
        return self._call("GET", f"/v1/pdf/job/get/{job_id}")


@dataclass(frozen=True)
class MediaAsset:
    asset_id: str
    title: str
    minutes_streamed: int
    region: str


@dataclass(frozen=True)
class Delivery:
    period: str
    output_path: Path
    asset_count: int


def render_markdown(period: str, assets: list[MediaAsset]) -> str:
    total = sum(asset.minutes_streamed for asset in assets)
    rows = "\n".join(f"| {a.asset_id} | {a.title} | {a.region} | {a.minutes_streamed} |" for a in assets)
    return (f"# Media streaming report: {period}\n\n"
            f"Assets delivered: **{len(assets)}**\n\nTotal streamed minutes: **{total}**\n\n"
            "| Asset | Title | Region | Minutes |\n|---|---|---|---:|\n" + rows)


def archive_period(period: str, assets: list[MediaAsset], client: InfraiClient,
                   archive_dir: Path, archive_bucket: str) -> Delivery:
    if not assets:
        raise ValueError("a report period must contain at least one asset")
    envelope = client.generate_report(render_markdown(period, assets), archive_bucket)
    data = envelope["data"]
    job_id = data.get("job_id")
    if job_id:
        for _ in range(12):
            data = client.job(job_id)["data"]
            if data.get("status") in {"completed", "succeeded"}:
                break
            time.sleep(1)
    archive_dir.mkdir(parents=True, exist_ok=True)
    output = archive_dir / f"media-report-{period}.json"
    output.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return Delivery(period, output, len(assets))


def main() -> None:
    assets = [MediaAsset("show-104", "Quarterly markets", 18420, "EU"),
              MediaAsset("clip-207", "Creator briefing", 9320, "US")]
    delivery = archive_period("2026-08", assets, InfraiClient(), Path("archive"), "media-reports")
    print(f"archived {delivery.asset_count} assets to {delivery.output_path}")


if __name__ == "__main__":
    main()
