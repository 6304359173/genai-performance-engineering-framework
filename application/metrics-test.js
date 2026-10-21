const express = require("express");

const app = express();

app.get("/metrics", (req, res) => {
    res.send("METRICS_ROUTE_WORKS");
});

app.listen(3003, () => {
    console.log("Test server running on port 3003");
});