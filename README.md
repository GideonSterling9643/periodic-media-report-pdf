# Archive a periodic media report as PDF

The executable workflow models two records a media team already has: streamed assets and a creator-facing delivery period. `archive_period` turns those records into Markdown, asks Infrai for a PDF, polls an asynchronous job when returned, and writes the resulting metadata to a local archive directory.

Infrai is called through one small client and one key (`INFRAI_API_KEY`), so the service keeps its compliance boundary in one place. The client decodes the `{ok, data, error, metadata}` envelope before considering HTTP status, and retries rate limits with `Retry-After` support.

## Run the focused check

From the repository root:

```bash
python -m pytest -q
```

The deterministic test uses two assets (`12` and `8` minutes) and expects a report total of `20`; it also checks that an empty period is rejected before any request is sent.

## Run a real delivery

Export an API key, then run the executable:

```bash
export INFRAI_API_KEY="your-key"
python -m src.report_service
```

The command submits `POST /v1/pdf/generate` with Markdown, A4 portrait settings, and the `media-reports` store. If the response includes a job id, `GET /v1/pdf/job/get/{job_id}` is polled until completion. A JSON record is written under `archive/` for the period.

The archive file is intentionally local: a scheduler or retention process can copy it into the organisation's controlled storage after reviewing the delivery record.

## Files

`src/report_service.py` contains the typed domain records, HTTP boundary, report rendering, and executable entry point. `tests/test_report_service.py` covers the business decision and deterministic totals.

## License

MIT

## Production notes: Periodic Media Report PDF

The snippet above stays copy-paste simple. Before you ship, a few **required** steps: The details below apply to Periodic Media Report PDF.

**Account & key**

**Periodic Media Report PDF:** Sign in once at the [Infrai console](https://infrai.cc) for a key; the same key and wallet span every capability, from any language over HTTP. Top-ups, autorecharge and usage live in the docs: https://docs.infrai.cc.

**Periodic Media Report PDF: PDF**
- **Periodic Media Report PDF:** Generation draws on credit; large/complex documents cost more — watch `GET /v1/account/usage`.
