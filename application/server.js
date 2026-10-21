
const express = require("express");
const client = require("prom-client");
const path = require("path");
const fs = require("fs");
const { spawn } = require("child_process");
const crypto = require("crypto");

const app = express();
app.use(express.json({ limit: "32kb" }));

const ROOT = path.resolve(__dirname, "..");
const PUBLIC_DIR = path.join(__dirname, "public");
const REPORTS_DIR = path.join(ROOT, "reports");
const PIPELINE = path.join(
    ROOT, "agent", "pipeline_orchestrator.py"
);

const PYTHON = process.env.PYTHON_EXE ||
    "C:\\Users\\LENOVO\\AppData\\Local\\Programs\\Python\\Python314\\python.exe";

const K6_DIR = "C:\\Program Files\\k6";
const PHASE_ORDER = ["baseline", "load", "stress", "spike", "soak"];
const runs = new Map();
let activeRunId = null;

// ---------------- Prometheus metrics ----------------

const register = new client.Registry();
register.setDefaultLabels({ application: "ai-order-service" });

client.collectDefaultMetrics({
    register,
    prefix: "nodejs_"
});

const httpRequestsTotal = new client.Counter({
    name: "http_requests_total",
    help: "Total HTTP requests received",
    labelNames: ["method", "route", "status_code"],
    registers: [register]
});

const httpRequestDuration = new client.Histogram({
    name: "http_request_duration_seconds",
    help: "HTTP response duration in seconds",
    labelNames: ["method", "route", "status_code"],
    buckets: [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2, 5],
    registers: [register]
});

app.use((req, res, next) => {
    if (req.path === "/metrics") return next();

    const start = process.hrtime.bigint();

    res.on("finish", () => {
        const duration =
            Number(process.hrtime.bigint() - start) / 1e9;

        const route = req.route?.path
            ? `${req.baseUrl || ""}${req.route.path}`
            : req.path;

        const labels = {
            method: req.method,
            route,
            status_code: String(res.statusCode)
        };

        httpRequestsTotal.inc(labels);
        httpRequestDuration.observe(labels, duration);
    });

    next();
});

// ---------------- Existing application APIs ----------------

app.get("/products", (req, res) => {
    res.json([
        { id: 101, name: "Laptop", price: 75000 },
        { id: 102, name: "Mobile", price: 30000 },
        { id: 103, name: "Headphones", price: 5000 }
    ]);
});

let orders = [];
let orderId = 1000;

app.post("/orders", (req, res) => {
    const order = {
        orderId: ++orderId,
        customerId: req.body.customerId,
        productId: req.body.productId,
        quantity: req.body.quantity,
        status: "CREATED"
    };

    orders.push(order);
    res.status(201).json(order);
});

app.get("/orders/:orderId", (req, res) => {
    const order = orders.find(
        item => item.orderId === Number(req.params.orderId)
    );

    if (!order) {
        return res.status(404).json({ message: "Order not found" });
    }

    res.json(order);
});

app.get("/health", (req, res) => {
    res.json({ status: "UP" });
});

app.get("/metrics", async (req, res, next) => {
    try {
        res.set("Content-Type", register.contentType);
        res.end(await register.metrics());
    } catch (error) {
        next(error);
    }
});

// ---------------- Browser portal ----------------

app.use(express.static(PUBLIC_DIR));

app.get("/api/health", (req, res) => {
    res.json({
        status: "UP",
        pipelineExists: fs.existsSync(PIPELINE),
        pythonExists: fs.existsSync(PYTHON),
        k6Exists: fs.existsSync(path.join(K6_DIR, "k6.exe")),
        aiIntegration: "Not connected yet"
    });
});

// Only serve report files from the framework reports directory.
app.get("/reports/:filename", (req, res) => {
    const filename = req.params.filename;

    if (!/^[A-Za-z0-9_.-]+\.md$|^[A-Za-z0-9_.-]+\.json$/i.test(filename)) {
        return res.status(400).json({ error: "Invalid report filename" });
    }

    const filePath = path.resolve(REPORTS_DIR, filename);

    if (path.dirname(filePath) !== path.resolve(REPORTS_DIR) ||
        !fs.existsSync(filePath) ||
        !fs.statSync(filePath).isFile()) {
        return res.status(404).json({ error: "Report not found" });
    }

    res.sendFile(filePath);
});



function getReports(run) {
    const output = String(run.output || "");

    const match =
        output.match(/Session\s*(?:ID)?\s*:\s*(PERF-\d{8}-\d{6})/i) ||
        output.match(/(PERF-\d{8}-\d{6})-pipeline-report\.(?:md|json)/i);

    const sessionId = match
        ? match[1]
        : (/^PERF-\d{8}-\d{6}$/.test(String(run.id || ""))
            ? String(run.id)
            : null);

    if (!sessionId) return [];

    return ["md", "json"].flatMap(ext => {
        const filename = `${sessionId}-pipeline-report.${ext}`;
        const filePath = path.join(REPORTS_DIR, filename);

        if (!fs.existsSync(filePath)) return [];

        return [{
            name: ext === "md" ? "Markdown report" : "JSON report",
            url: `/reports/${filename}`
        }];
    });
}

app.get("/api/debug-reports", (req, res) => {
    const sessionId = "PERF-20261021-105431";
    const files = ["md", "json"].map(ext => {
        const filename = `${sessionId}-pipeline-report.${ext}`;
        const filePath = path.join(REPORTS_DIR, filename);

        return {
            filename,
            reportsDir: REPORTS_DIR,
            filePath,
            exists: fs.existsSync(filePath)
        };
    });

    res.json({ reportsDir: REPORTS_DIR, files });
});
function publicRun(run) {
    return {
        id: run.id,
        status: run.status,
        phases: run.phases,
        baseUrl: run.baseUrl,
        startedAt: run.startedAt,
        finishedAt: run.finishedAt || null,
        exitCode: run.exitCode ?? null,
        output: run.output,
        reports: getReports(run)
    };
}

// ---------------- Start a real pipeline run ----------------

app.post("/api/runs", (req, res) => {
    if (activeRunId) {
        const active = runs.get(activeRunId);
        if (active && active.status === "running") {
            return res.status(409).json({
                error: "A performance test is already running.",
                activeRunId
            });
        }
        activeRunId = null;
    }

    const body = req.body || {};
    const phases = body.phases;

    if (!Array.isArray(phases) || phases.length === 0 ||
        phases.some(p => !PHASE_ORDER.includes(p)) ||
        new Set(phases).size !== phases.length ||
        phases.some((p, i) => i > 0 &&
            PHASE_ORDER.indexOf(p) <= PHASE_ORDER.indexOf(phases[i - 1]))) {
        return res.status(400).json({
            error: "Select unique phases in this order: baseline, load, stress, spike, soak."
        });
    }

    const intensive = phases.some(p => p !== "baseline");

    if (intensive && body.allowIntensive !== true) {
        return res.status(400).json({
            error: "Intensive phases require explicit authorization."
        });
    }

    let target;
    try {
        target = new URL(String(body.baseUrl || ""));
    } catch {
        return res.status(400).json({ error: "Enter a valid application URL." });
    }

    // Initial MVP only allows loopback targets to prevent remote or
    // unintended systems from being load-tested through this endpoint.
    if (!["http:", "https:"].includes(target.protocol) ||
        !["localhost", "127.0.0.1", "[::1]"].includes(target.hostname)) {
        return res.status(400).json({
            error: "For this initial version, use an authorized localhost endpoint."
        });
    }

    if (!fs.existsSync(PYTHON) || !fs.existsSync(PIPELINE) ||
        !fs.existsSync(path.join(K6_DIR, "k6.exe"))) {
        return res.status(500).json({
            error: "Python, the pipeline, or k6 executable could not be found. Check installation paths."
        });
    }

    const id = "WEB-" + Date.now() + "-" +
        crypto.randomBytes(3).toString("hex");

    const args = [
        PIPELINE,
        "--phases", phases.join(","),
        "--base-url", target.toString()
    ];

    if (intensive) args.push("--allow-intensive");

    const run = {
        id,
        phases,
        baseUrl: target.toString(),
        status: "running",
        startedAt: new Date().toISOString(),
        output: "",
        exitCode: null
    };

    runs.set(id, run);
    activeRunId = id;

    const env = {
        ...process.env,
        PATH: K6_DIR + path.delimiter + (process.env.PATH || "")
    };

    let child;

    try {
        child = spawn(PYTHON, args, {
            cwd: ROOT,
            env,
            windowsHide: true,
            shell: false,
            stdio: ["ignore", "pipe", "pipe"]
        });
    } catch (error) {
        run.status = "failed";
        run.output += `Could not start pipeline: ${error.message}\n`;
        activeRunId = null;
        return res.status(500).json({ error: run.output });
    }

    function appendOutput(chunk) {
        // Bound memory use while keeping the latest diagnostic output.
        run.output = (run.output + chunk.toString()).slice(-60000);
    }

    child.stdout.on("data", appendOutput);
    child.stderr.on("data", appendOutput);

    child.on("error", error => {
        appendOutput(`\nProcess error: ${error.message}\n`);
        run.status = "failed";
        run.finishedAt = new Date().toISOString();
        activeRunId = null;
    });

    child.on("close", code => {
        run.exitCode = code;
        run.status = code === 0 ? "completed" : "failed";
        run.finishedAt = new Date().toISOString();

        if (activeRunId === id) activeRunId = null;
    });

    res.status(202).json({
        id,
        status: run.status,
        message: "Pipeline started. Poll the run status endpoint for progress."
    });
});

app.get("/api/runs/:id", (req, res) => {
    const run = runs.get(req.params.id);

    if (!run) {
        return res.status(404).json({ error: "Run not found in this server session." });
    }

    res.json(publicRun(run));
});


app.get("/api/runs", (req, res) => {
    const inMemoryRuns = [...runs.values()].map(publicRun);

    const reportFiles = fs.readdirSync(REPORTS_DIR)
        .filter(filename =>
            /^PERF-\d{8}-\d{6}-pipeline-report\.(md|json)$/i.test(filename)
        );

    const sessionIds = [...new Set(
        reportFiles.map(filename =>
            filename.match(/^(PERF-\d{8}-\d{6})-pipeline-report\./i)[1]
        )
    )];

    const reportRuns = sessionIds.map(sessionId => {
        const mdFile = `${sessionId}-pipeline-report.md`;
        const jsonFile = `${sessionId}-pipeline-report.json`;

        const reports = [];

        if (fs.existsSync(path.join(REPORTS_DIR, mdFile))) {
            reports.push({
                name: "Markdown report",
                url: `/reports/${mdFile}`
            });
        }

        if (fs.existsSync(path.join(REPORTS_DIR, jsonFile))) {
            reports.push({
                name: "JSON report",
                url: `/reports/${jsonFile}`
            });
        }

        return {
            id: sessionId,
            status: "completed",
            phases: [],
            baseUrl: null,
            startedAt: null,
            finishedAt: null,
            exitCode: 0,
            output: `Existing performance report: ${sessionId}`,
            reports
        };
    });

    const allRuns = new Map();

    for (const run of reportRuns) allRuns.set(run.id, run);
    for (const run of inMemoryRuns) allRuns.set(run.id, run);

    res.json([...allRuns.values()].reverse());
});


// ---------------- Start server ----------------

const PORT = 3002;

app.listen(PORT, () => {
    console.log(`Order service and GenAI workbench server: http://localhost:${PORT}`);
    console.log(`Prometheus metrics: http://localhost:${PORT}/metrics`);
    console.log(`Pipeline found: ${fs.existsSync(PIPELINE)}`);
});
