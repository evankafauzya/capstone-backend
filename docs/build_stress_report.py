"""
Generate the load / capacity test report as a PDF.

Academic-style technical report documenting the methodology, execution, and
results of the k6 load test performed against the /detect/faces endpoint of
the Moodle Proctoring AI backend.

Run:
    python docs/build_stress_report.py

Output:
    docs/stress-test-report.pdf
"""
from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT, TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

DOCS_DIR = Path(__file__).resolve().parent
INK = colors.HexColor("#1a1a1a")
RULE = colors.HexColor("#333333")
LIGHT_BG = colors.HexColor("#f0f0f0")
GRID = colors.HexColor("#b0b0b0")
MONO_BG = colors.HexColor("#f4f4f4")


# ---------------------------------------------------------------------------
# Styles (Times-based for an academic look)
# ---------------------------------------------------------------------------
def make_styles():
    base = getSampleStyleSheet()
    s = {}
    s["title"] = ParagraphStyle(
        "title", parent=base["Title"], fontName="Times-Bold", fontSize=20,
        leading=25, textColor=INK, alignment=TA_CENTER, spaceAfter=6,
    )
    s["subtitle"] = ParagraphStyle(
        "subtitle", parent=base["Normal"], fontName="Times-Roman", fontSize=12,
        leading=16, textColor=colors.HexColor("#444444"), alignment=TA_CENTER,
        spaceAfter=4,
    )
    s["meta"] = ParagraphStyle(
        "meta", parent=base["Normal"], fontName="Times-Roman", fontSize=10,
        leading=14, textColor=colors.HexColor("#555555"), alignment=TA_CENTER,
    )
    s["h1"] = ParagraphStyle(
        "h1", parent=base["Heading1"], fontName="Times-Bold", fontSize=14,
        leading=18, textColor=INK, spaceBefore=16, spaceAfter=7, keepWithNext=True,
    )
    s["h2"] = ParagraphStyle(
        "h2", parent=base["Heading2"], fontName="Times-Bold", fontSize=11.5,
        leading=15, textColor=INK, spaceBefore=10, spaceAfter=4, keepWithNext=True,
    )
    s["body"] = ParagraphStyle(
        "body", parent=base["BodyText"], fontName="Times-Roman", fontSize=10.5,
        leading=15, alignment=TA_JUSTIFY, spaceAfter=7,
    )
    s["abstract"] = ParagraphStyle(
        "abstract", parent=base["BodyText"], fontName="Times-Italic", fontSize=10,
        leading=14, alignment=TA_JUSTIFY, leftIndent=12, rightIndent=12,
        spaceAfter=8,
    )
    s["bullet"] = ParagraphStyle(
        "bullet", parent=base["BodyText"], fontName="Times-Roman", fontSize=10.5,
        leading=14.5, alignment=TA_JUSTIFY, leftIndent=16, bulletIndent=4,
        spaceAfter=3,
    )
    s["cap"] = ParagraphStyle(
        "cap", parent=base["Normal"], fontName="Times-Italic", fontSize=9,
        leading=12, textColor=colors.HexColor("#444444"), spaceBefore=2,
        spaceAfter=10,
    )
    s["mono"] = ParagraphStyle(
        "mono", parent=base["Code"], fontName="Courier", fontSize=8.5,
        leading=11, leftIndent=8, rightIndent=8, backColor=MONO_BG,
        borderPadding=6, spaceBefore=2, spaceAfter=10,
    )
    s["th"] = ParagraphStyle(
        "th", parent=base["Normal"], fontName="Times-Bold", fontSize=9,
        leading=12, textColor=colors.white,
    )
    s["td"] = ParagraphStyle(
        "td", parent=base["Normal"], fontName="Times-Roman", fontSize=9,
        leading=12, textColor=INK,
    )
    s["tdb"] = ParagraphStyle(
        "tdb", parent=base["Normal"], fontName="Times-Bold", fontSize=9,
        leading=12, textColor=INK,
    )
    return s


STYLES = make_styles()


def p(text, style="body"):
    return Paragraph(text, STYLES[style])


def bullets(items):
    return [Paragraph(f"&#8226;&nbsp;&nbsp;{it}", STYLES["bullet"]) for it in items]


def code(text):
    return Preformatted(text, STYLES["mono"])


def caption(text):
    return Paragraph(text, STYLES["cap"])


def _cell(text, bold=False):
    return Paragraph(str(text), STYLES["tdb"] if bold else STYLES["td"])


def kv_table(rows, col_widths=(5.5 * cm, 10.5 * cm)):
    data = [[Paragraph(f"{k}", STYLES["tdb"]), Paragraph(v, STYLES["td"])]
            for k, v in rows]
    t = Table(data, colWidths=col_widths, hAlign="LEFT")
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), LIGHT_BG),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.4, GRID),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return t


def grid_table(header, rows, col_widths, bold_last_col=False):
    data = [[Paragraph(h, STYLES["th"]) for h in header]]
    for r in rows:
        data.append([_cell(c, bold=(bold_last_col and i == len(r) - 1))
                     for i, c in enumerate(r)])
    t = Table(data, colWidths=col_widths, repeatRows=1, hAlign="LEFT")
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), RULE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.4, GRID),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f7f7f7")]),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return t


def page_footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Times-Roman", 8)
    canvas.setFillColor(colors.HexColor("#666666"))
    canvas.drawString(2 * cm, 1.2 * cm,
                      "Load and Capacity Evaluation - Moodle Proctoring AI Backend")
    canvas.drawRightString(A4[0] - 2 * cm, 1.2 * cm, f"Page {doc.page}")
    canvas.restoreState()


# ---------------------------------------------------------------------------
# Document body
# ---------------------------------------------------------------------------
def build_story():
    s = []

    # ---- Title block ----
    s.append(Spacer(1, 1.5 * cm))
    s.append(p("Load and Capacity Evaluation of the Moodle Proctoring AI Backend", "title"))
    s.append(p("A Load-Test Study of the Face-Detection and Face-Recognition "
               "Endpoints Under Concurrent Student Traffic", "subtitle"))
    s.append(Spacer(1, 0.4 * cm))
    s.append(p("Technical Report", "meta"))
    s.append(p("Date: 5 July 2026", "meta"))
    s.append(Spacer(1, 0.8 * cm))

    # ---- Abstract ----
    s.append(p("Abstract", "h2"))
    s.append(p(
        "This report documents a load and capacity evaluation of the Moodle "
        "Proctoring AI backend, a FastAPI service that performs face detection "
        "and recognition for online examination proctoring. The objective was "
        "to determine how many concurrent students a single containerized "
        "instance can serve while maintaining acceptable response latency. "
        "Using the k6 load-testing tool, the face-detection endpoint was "
        "exercised under two workload models -- realistic periodic polling and "
        "a worst-case simultaneous burst -- across several server "
        "configurations. The service sustained approximately 18 requests per "
        "second on a single CPU-bound worker. Under a realistic polling model "
        "(one verification per student every 45 seconds), a single instance "
        "served 250 students at a 95th-percentile latency of 102 milliseconds "
        "with no errors, and remained functionally correct up to 700 students, "
        "though the latter exhibited a multi-second latency tail. The heavier "
        "identity-verification endpoint, which adds embedding, database "
        "lookup, and similarity scoring, sustained approximately 16 requests "
        "per second and served 250 students at a 95th-percentile latency of "
        "146 milliseconds. Increasing "
        "the number of worker processes did not raise throughput, and "
        "restricting per-worker thread counts degraded performance; both "
        "outcomes are attributed to the CPU-bound, already-parallelized nature "
        "of the inference workload. The comfortable single-instance capacity "
        "is estimated at approximately 500 students for the detection endpoint "
        "and 400 to 450 students for the full verification path, at a "
        "45-second polling interval. Recommendations for higher capacity, principally "
        "GPU acceleration and longer polling intervals, are provided.",
        "abstract"))

    # ---- 1. Introduction ----
    s.append(p("1. Introduction and Objectives", "h1"))
    s.append(p(
        "The backend under evaluation exposes a REST API used by a Moodle "
        "proctoring plugin to detect faces, verify student identity, and flag "
        "suspicious behaviour during online examinations. Because the service "
        "performs neural-network inference on each request, its throughput and "
        "latency under concurrent load are material to deployment planning: an "
        "institution must know how many simultaneous examinees a single "
        "instance can support before response times become unacceptable."))
    s.append(p(
        "The evaluation was designed to answer one operational question: "
        "<b>how many concurrent students can a single containerized instance "
        "serve while keeping response latency acceptable?</b> A secondary "
        "objective was to identify the primary performance bottleneck and to "
        "assess whether it can be relieved through configuration changes alone "
        "or requires additional hardware."))

    # ---- 2. System Under Test ----
    s.append(p("2. System Under Test", "h1"))
    s.append(p(
        "The application is a FastAPI service served by Gunicorn using the "
        "Uvicorn worker class. Face detection is performed by an Ultralytics "
        "YOLO model and recognition by an ArcFace network with an "
        "EfficientNet-B0 backbone producing 512-dimensional embeddings. All "
        "inference ran on the CPU; no GPU was available. The service was "
        "deployed through Docker Compose. The test environment is summarized "
        "below."))
    s.append(kv_table([
        ("Host operating system", "Windows 11 Pro (build 26200)"),
        ("Container runtime", "Docker Engine 29.5.3 (Docker Desktop)"),
        ("CPU cores visible to container", "16"),
        ("Memory available to Docker", "7.7 GiB"),
        ("GPU", "None (CPU-only inference)"),
        ("Application framework", "FastAPI, served by Gunicorn + Uvicorn worker"),
        ("Face detector", "Ultralytics YOLO (loaded)"),
        ("Face recognizer", "ArcFace, EfficientNet-B0 backbone, 512-d (loaded)"),
        ("Endpoints under test", "POST /detect/faces and POST /verify/face"),
        ("Request payload", "261 KB JPEG (single face) encoded as 348 KB base64"),
        ("Load generator", "k6 v2.1.0"),
    ]))
    s.append(caption(
        "Table 1. Test environment and system under test."))
    s.append(p(
        "Two endpoints were load-tested. The face-detection endpoint isolates "
        "the detection stage, while the identity-verification endpoint "
        "exercises the full recognition pipeline (detection, alignment, "
        "ArcFace embedding, database lookup, and cosine similarity) and is the "
        "path used in production. Detection results are reported in Section "
        "4.2 and the recognition path in Section 4.3."))

    # ---- 3. Methodology ----
    s.append(p("3. Methodology", "h1"))
    s.append(p("3.1 Workload models", "h2"))
    s.append(p(
        "Two workload models were used. In the <b>realistic polling</b> model, "
        "each virtual user represents one student whose client issues a single "
        "verification request and then waits a fixed think-time of 45 seconds "
        "before the next request, approximating a periodic proctoring poll. In "
        "the <b>simultaneous burst</b> model, virtual users issue requests "
        "back-to-back with no think-time, representing a worst case in which "
        "all clients are active at once. The realistic model maps directly to "
        "a student count; the burst model characterizes the saturation "
        "behaviour of the service."))
    s.append(p("3.2 Load profile and metrics", "h2"))
    s.append(p(
        "Each test used a ramping profile: a 30-second ramp to the target "
        "number of virtual users, a hold at that level, and a 30-second "
        "ramp-down. The following metrics were recorded: the end-to-end HTTP "
        "response-time distribution (median and 90th, 95th, and 99th "
        "percentiles); the request failure rate; the number of requests "
        "rejected by rate limiting; and an application-side timing metric "
        "derived from the <font face='Courier'>X-Process-Time</font> response "
        "header, which reports the wall-clock time spent inside the "
        "application. Comparing the application-side time against the "
        "end-to-end time distinguishes processing cost from time spent queued "
        "for a worker."))
    s.append(p("3.3 Acceptance thresholds", "h2"))
    s.append(p("The following pass/fail thresholds were applied to every run:"))
    s.extend(bullets([
        "95th-percentile response time below 2,000 milliseconds;",
        "99th-percentile response time below 5,000 milliseconds;",
        "request failure rate below one percent;",
        "zero requests rejected by the rate limiter.",
    ]))
    s.append(p(
        "To ensure the tests measured application performance rather than the "
        "rate limiter, the per-client request cap was temporarily raised from "
        "the production default of 600 requests per minute to an effectively "
        "unlimited value for the duration of testing. The rate-limiter "
        "rejection count was asserted to be zero in every run, confirming the "
        "measurements were valid.", "body"))

    # ---- 4. Results ----
    s.append(PageBreak())
    s.append(p("4. Results", "h1"))
    s.append(p("4.1 Single-request baseline", "h2"))
    s.append(p(
        "A single request returned HTTP 200 with one face detected at 0.94 "
        "confidence. The first (cold) call completed in approximately 500 "
        "milliseconds; warm steady-state detection latency was approximately "
        "57 milliseconds. This establishes the lower bound on per-request "
        "latency under no contention."))

    s.append(p("4.2 Experiment matrix", "h2"))
    s.append(p(
        "Five load experiments were performed. Workers denotes Gunicorn worker "
        "processes; threads denotes the OpenMP/torch intra-op thread cap per "
        "worker. Offered load is the measured request rate. Latencies are HTTP "
        "response times."))
    s.append(grid_table(
        ["ID", "Scenario", "Wk", "Thr", "Offered", "Median", "p95", "p99", "Fail", "Verdict"],
        [
            ["E1", "250, realistic", "1", "8", "4.8/s", "58 ms", "102 ms", "523 ms", "0%", "Pass"],
            ["E2", "250, burst", "1", "8", "18.5/s", "12.3 s", "14.6 s", "15.4 s", "0.99%", "Saturated"],
            ["E3", "250, burst", "4", "8", "17.9/s", "12.2 s", "15.2 s", "15.4 s", "0%", "No gain"],
            ["E4", "700, realistic", "4", "8", "13.7/s", "68 ms", "5.25 s", "5.63 s", "0%", "Borderline"],
            ["E5", "700, realistic", "4", "4", "13.0/s", "499 ms", "11.98 s", "13.1 s", "0%", "Regression"],
        ],
        col_widths=(1.0 * cm, 3.0 * cm, 0.9 * cm, 0.9 * cm, 1.6 * cm,
                    1.7 * cm, 1.7 * cm, 1.7 * cm, 1.1 * cm, 2.0 * cm),
        bold_last_col=True,
    ))
    s.append(caption(
        "Table 2. Load-test experiment matrix and results. Wk = worker "
        "processes; Thr = intra-op threads per worker."))
    s.append(p(
        "No experiment produced server errors under the realistic model. In "
        "the single-worker burst (E2), 0.99 percent of requests failed; these "
        "were connection resets that occurred while the connection backlog "
        "filled during the initial ramp, not application-level errors, and "
        "they disappeared once four workers were available (E3). The container "
        "remained healthy throughout every run, and memory usage was stable "
        "(approximately 0.49 GiB with one worker and 1.6-1.7 GiB with four)."))

    # ---- 4.3 recognition results ----
    s.append(p("4.3 Recognition path (/verify/face)", "h2"))
    s.append(p(
        "The identity-verification endpoint was tested against a user enrolled "
        "with a single reference embedding, using the same image as the live "
        "capture (yielding a similarity score of 1.0 and a correct match on "
        "every request). A single warm verification completed in approximately "
        "64 milliseconds, marginally above detection, reflecting the added "
        "embedding, lookup, and scoring. Two experiments were run at one "
        "worker: a realistic 250-student poll and a saturating burst."))
    s.append(grid_table(
        ["Scenario", "Offered", "Median", "p95", "Max", "Fail", "Verdict"],
        [
            ["250, realistic", "4.8/s", "103 ms", "146 ms", "370 ms", "0%", "Pass"],
            ["250, burst", "15.9/s", "13.7 s", "18.9 s", "24.0 s", "0%", "Saturated"],
        ],
        col_widths=(3.2 * cm, 1.9 * cm, 2.0 * cm, 1.9 * cm, 1.9 * cm, 1.2 * cm, 2.4 * cm),
        bold_last_col=True,
    ))
    s.append(caption(
        "Table 3. Recognition-path (/verify/face) results, single worker."))
    s.append(p(
        "The verification path sustained approximately 16 requests per second, "
        "about 14 percent below the detection ceiling, and served 250 students "
        "at a 95th-percentile latency of 146 milliseconds with no errors and "
        "correct identity matching throughout. Under saturation it queued "
        "slightly more than detection, consistent with its lower throughput. "
        "The direct comparison is summarized below."))
    s.append(grid_table(
        ["Metric", "/detect/faces", "/verify/face"],
        [
            ["Warm single call", "~57 ms", "~64 ms"],
            ["Realistic 250 students, p95", "102 ms", "146 ms"],
            ["Burst throughput ceiling", "18.5 req/s", "15.9 req/s"],
            ["Burst p95 (saturated)", "14.6 s", "18.9 s"],
            ["Comfortable capacity (45 s poll)", "~500 students", "~400-450 students"],
        ],
        col_widths=(7.0 * cm, 4.5 * cm, 4.5 * cm),
    ))
    s.append(caption(
        "Table 4. Detection versus recognition, single worker, CPU."))

    # ---- 5. Analysis ----
    s.append(p("5. Analysis", "h1"))
    s.append(p("5.1 Throughput ceiling", "h2"))
    s.append(p(
        "Under the burst model the service sustained approximately 18 requests "
        "per second (E2, E3). In these runs the application-side processing "
        "time was almost equal to the end-to-end response time (both around "
        "12 seconds at the median), which locates the bottleneck inside the "
        "application worker rather than in the network or the load generator: "
        "requests spent their time queued behind a saturated worker. The "
        "throughput ceiling is therefore a property of CPU-bound inference on "
        "this host."))
    s.append(p("5.2 Effect of worker count", "h2"))
    s.append(p(
        "Increasing the worker count from one to four did not increase "
        "throughput (18.5 versus 17.9 requests per second in E2 and E3), while "
        "tripling memory consumption. Inspection showed that the inference "
        "library defaults to eight intra-op threads per request; a single "
        "worker therefore already parallelizes each detection across multiple "
        "cores, and four workers at eight threads each request 32 threads on a "
        "16-core host, oversubscribing the processor. The only benefit of the "
        "additional workers was improved connection handling during bursts, "
        "which eliminated the ramp-time connection failures."))
    s.append(p("5.3 Effect of thread capping (negative result)", "h2"))
    s.append(p(
        "It was hypothesized that constraining each worker to four intra-op "
        "threads (four workers times four threads equals the 16 available "
        "cores) would eliminate oversubscription and raise the ceiling. The "
        "experiment falsified this hypothesis. Comparing E4 and E5, both at "
        "700 students with four workers, reducing threads per worker from "
        "eight to four increased the median response time roughly sevenfold "
        "(68 to 499 milliseconds) and more than doubled the 95th-percentile "
        "latency (5.25 to 11.98 seconds). Restricting threads slowed each "
        "individual inference more than it relieved contention, because the "
        "detection model genuinely benefits from the wider intra-op "
        "parallelism. This is reported as a negative result: the "
        "configuration change intended as an optimization was a regression, "
        "and the earlier configuration (four workers, default threads) remains "
        "the better of the two."))
    s.append(p("5.4 Latency distribution under realistic load", "h2"))
    s.append(p(
        "At 250 students (E1) the service operated at roughly one-third of its "
        "throughput ceiling and delivered a tight latency distribution "
        "(95th-percentile 102 milliseconds). At 700 students (E4) the offered "
        "load rose to roughly three-quarters of the ceiling; the median "
        "remained low (68 milliseconds) but the upper tail expanded sharply "
        "(90th-percentile 4.3 seconds, 95th-percentile 5.25 seconds). This is "
        "the expected behaviour of a queueing system approaching saturation: "
        "tail latency degrades well before the average does. The service "
        "remained correct, but a growing minority of requests experienced "
        "multi-second delays."))

    # ---- 6. Capacity assessment ----
    s.append(p("6. Capacity Assessment", "h1"))
    s.append(p(
        "Mapping the throughput ceiling to a student population at a 45-second "
        "polling interval yields the following estimates for the "
        "verification path, which is the endpoint used in production. "
        "Utilization is the offered load as a fraction of the approximately 16 "
        "requests-per-second verification ceiling; the detection endpoint is "
        "approximately 14 percent higher and correspondingly supports a few "
        "dozen more students."))
    s.append(grid_table(
        ["Students", "Offered load", "Utilization", "Expected p95", "Assessment"],
        [
            ["250", "5.6/s", "~35%", "~150 ms", "Comfortable"],
            ["400-450", "~9-10/s", "~55-62%", "sub-second", "Safe ceiling"],
            ["500", "11.1/s", "~69%", "seconds", "Degraded tail"],
            ["600", "13.3/s", "~83%", "several s", "Borderline"],
        ],
        col_widths=(2.4 * cm, 2.8 * cm, 2.6 * cm, 3.0 * cm, 4.2 * cm),
        bold_last_col=True,
    ))
    s.append(caption(
        "Table 5. Estimated single-instance capacity for the verification "
        "path at a 45-second polling interval."))
    s.append(p(
        "On this basis, the comfortable single-instance capacity is "
        "approximately 400 to 450 students for the full verification path, and "
        "approximately 500 for detection alone. Beyond that point the service "
        "continues to function without errors, but an increasing minority of "
        "requests incur multi-second delays as the worker approaches "
        "saturation. Whether this is acceptable depends on whether "
        "verification runs as a background poll (in which case a multi-second "
        "delay is tolerable) or as an interactive check a student waits on (in "
        "which case it is not)."))

    # ---- 7. Recommendations ----
    s.append(p("7. Recommendations", "h1"))
    s.extend(bullets([
        "<b>Provision for approximately 400 to 450 students per instance</b> "
        "for the full verification path (about 500 for detection-only "
        "workloads) at a 45-second polling interval, to keep the latency tail "
        "below one second.",
        "<b>Lengthen the polling interval</b> to raise the supported student "
        "count without additional hardware. At a 90-second interval, 700 "
        "students offer roughly 7.8 requests per second (about 43 percent "
        "utilization), which restores a comfortable margin. This is the "
        "lowest-cost mitigation.",
        "<b>Adopt GPU acceleration for higher density.</b> Because the "
        "bottleneck is CPU-bound inference, a GPU is expected to reduce "
        "per-request latency by an order of magnitude and is the decisive "
        "lever for serving many hundreds of students per instance with low "
        "latency.",
        "<b>Do not rely on additional worker processes for throughput.</b> On "
        "this CPU-bound workload, extra workers increased memory use without "
        "raising throughput; a small number of workers is nonetheless useful "
        "for absorbing connection bursts gracefully.",
        "<b>Do not cap intra-op threads.</b> Restricting threads per worker "
        "was measured to degrade performance and should be avoided.",
        "<b>Scale horizontally when a single instance is insufficient.</b> "
        "Multiple instances behind a load balancer are the natural path beyond "
        "one machine, and the stateless detection path supports this directly.",
    ]))

    # ---- 8. Threats to validity ----
    s.append(p("8. Threats to Validity and Limitations", "h1"))
    s.extend(bullets([
        "<b>Single reference embedding per user.</b> The verification test "
        "compared against a user enrolled with one reference embedding. Users "
        "enrolled with several references incur additional cosine comparisons "
        "per request, modestly increasing verification cost; the reported "
        "figures therefore represent a lightly loaded enrollment. Verification "
        "was also measured with identical live and reference images, which "
        "exercises the full compute path but not real-world image variation.",
        "<b>CPU-only host.</b> All measurements were taken without a GPU. "
        "Results are not representative of a GPU deployment.",
        "<b>Docker Desktop on Windows.</b> The service ran inside the Docker "
        "Desktop virtual machine on Windows, which introduces virtualization "
        "overhead; reported container CPU utilization was unreliable and was "
        "not used as a primary metric. A native Linux host may perform "
        "differently.",
        "<b>Single synthetic image.</b> Every request carried the same "
        "single-face image. Real traffic varies in resolution, face count, "
        "and encoding size, which affects per-request cost.",
        "<b>Short hold durations.</b> Steady-state was held for 60 to 90 "
        "seconds. Longer soak tests would be required to detect slow "
        "resource leaks or thermal effects.",
        "<b>Closed-loop client model.</b> Virtual users wait for a response "
        "before issuing the next request. This approximates, but does not "
        "perfectly reproduce, the behaviour of independent real clients.",
    ]))

    # ---- 9. Conclusion ----
    s.append(p("9. Conclusion", "h1"))
    s.append(p(
        "A single containerized instance of the proctoring backend, running "
        "CPU-only inference, sustains approximately 18 face-detection requests "
        "per second and approximately 16 requests per second on the full "
        "identity-verification path, which is the endpoint used in production. "
        "Under a realistic 45-second polling model this corresponds to a "
        "comfortable single-instance capacity of roughly 500 students for "
        "detection and 400 to 450 students for verification, at which the "
        "95th-percentile response time stays within about 150 milliseconds "
        "with no errors and correct identity matching. Beyond that point the "
        "service continues to operate correctly but with a growing "
        "multi-second latency tail as the worker saturates. The performance "
        "ceiling is CPU-bound and, on the evidence gathered, cannot be raised "
        "by adding worker processes or by capping inference threads; the "
        "latter was measured to be a regression. Higher low-latency capacity "
        "is best achieved by lengthening the polling interval, by adopting GPU "
        "acceleration, or by scaling horizontally across multiple instances."))

    return s


def main():
    out = DOCS_DIR / "stress-test-report.pdf"
    doc = SimpleDocTemplate(
        str(out), pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=2 * cm, bottomMargin=2 * cm,
        title="Load and Capacity Evaluation - Moodle Proctoring AI Backend",
        author="",
    )
    doc.build(build_story(), onFirstPage=page_footer, onLaterPages=page_footer)
    print(f"Generated: {out}")


if __name__ == "__main__":
    main()
