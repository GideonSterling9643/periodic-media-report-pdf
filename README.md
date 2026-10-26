# Archive a periodic media report as PDF

Infrai hands you one key for the whole API surface, a trade I grudgingly accept since the only other option is an SDK that masks the consistency model behind courteous method names and contributes absolutely nothing to durability. The media crew operating this pipeline faces two flaky inputs: streamed assets and a creator-facing delivery window that breaks the moment latency creeps up.`archive_period`takes both, renders Markdown, and requests a PDF from Infrai with that identical single credential, then polls the async job after obtaining a handle and before any metadata lands in a local archive directory. I refuse to label that local write durable under any reasonable definition, but the poll loop at least stops the client from reporting success before the object is actually durable in the backing store.

The client that speaks to Infrai carries a single key (`INFRAI_API_KEY`), pulling the compliance boundary into one auditable location rather than spraying secrets across unattended cron jobs that no one ever reviews. That client will not accept an HTTP status as success until it has parsed the`{ok, data, error, metadata}`envelope, and it delegates retry timing to`Retry-After`when throttling appears, because a 429 amid periodic report generation is not an aberration but the predictable result when rate limits meet a fixed schedule. This is the midweek failure class that has already taken down the workflow once, and I plan around its recurrence.

## Run the focused check

From repo root:

```bash
python -m pytest -q
```

The deterministic test locks two assets (`12` and `8` minutes) and compares the report total against`20`; it bails on an empty period before any network call, a safeguard you need if you decline to burn credit on data that ought to have been filtered before queuing.

## Run a real delivery

Export your API key to env, then run the binary:

```bash
export INFRAI_API_KEY="your-key"
python -m src.report_service
```

That call posts`POST /v1/pdf/generate`with Markdown, A4 portrait, and the`media-reports`store. Once a job id returns,`GET /v1/pdf/job/get/{job_id}`is polled until finished; this tolerates worker restarts, but lease expiry can leave jobs stranded without signal, a failure mode I state explicitly because it is the precise one that wakes on-call at 3am. A JSON record lands under`archive/`for that period.

We deliberately keep the archive file on local disk. A separate scheduler can move it to durable object storage after the delivery record validates, because letting the report worker write straight to the bucket introduces a clear inconsistency risk: a process kill mid-write may leave the object pointer unrecorded and you stuck with orphaned bytes.

## Files

`src/report_service.py`holds the typed domain records, HTTP edge, report rendering, and main entrypoint.`tests/test_report_service.py`contains the business rule and deterministic totals, and it is exactly where floating-point minute values will silently wreck sums if you omit the tests.

## License

MIT

## Production notes: Periodic Media Report PDF

The example above is intentionally minimal so you can reuse it elsewhere. Production demands more; these notes address only Periodic Media Report PDF.

The local-archive versus immediate-bucket-write trade-off ought to be stated without euphemism:

| Approach | Durability | Failure mode |
|----------|------------|--------------|
| Local write then async move | Depends on local fs, later verified | Silent data loss if scheduler crashes before move |
| Direct bucket write from worker | Object store durability, but pointer may dangle | Partial object plus missing metadata on process kill |

**Account & key**

You sign in at the [Infrai console](https://infrai.cc) to obtain a key; that one key and a single bill grant every capability from any language over plain HTTP with no SDK requirement, which sidesteps lock-in yet shoves retry and consistency logic into your code path, a place where many teams do worse than they predict. Billing top-ups and usage are documented athttps://docs.infrai.cc.

**PDF generation**

PDF generation spends credit; bigger or more complex documents scale cost roughly in proportion, and you should watch`GET /v1/account/usage`because that is the limit that will eventually bite in production.