# connect.li.api (Lean In Connect Circles API Project)

A stateless, RESTful Python API for recommending Lean In Connect Circles to users.

## Setup Instructions

This project requires **Python 3.9+** (and standard Unix utilities like `make`). 

**Prerequisite:** Ensure that you have placed the provided `data` folder (containing `users.json`, `circles.json`, etc.) in the root directory of this project. It should look like `./data/users.json`.

To scaffold the virtual environment, install dependencies, and automatically seed the SQLite database from the provided JSON dataset, simply run:

```bash
make setup
```

## Running the API

To start the local FastAPI server (runs on `http://127.0.0.1:8000`):

```bash
make run
```

Once running, you can view the interactive Swagger API documentation at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

### Evaluating the Assignment Scenarios
With the server running locally, you can evaluate the planted scenario records using the following `curl` commands:

**0. Normal User Baseline (User 1)**
A standard user who has an established profile and some topic interests.
```bash
curl -s http://127.0.0.1:8000/v1/recommendations/1?limit=5
```

**1. Cold-start (User 42)**
```bash
curl -s http://127.0.0.1:8000/v1/recommendations/42?limit=5
```

**2. Obvious matches (User 7)**
```bash
curl -s http://127.0.0.1:8000/v1/recommendations/7?limit=5
```

**3. Duplicate Circles (User 15)**
```bash
curl -s http://127.0.0.1:8000/v1/recommendations/15?limit=10
```

**4. Full / inactive (User 23)**
```bash
curl -s http://127.0.0.1:8000/v1/recommendations/23?limit=5
```

## Running Tests

The project uses `pytest` with a suite of unit, integration, and E2E scenario tests to ensure all recommendations mathematically align with our requirements. To run the test suite:

```bash
make test
```

## Technical Design

For a deep dive into the architecture, mathematical scoring formulas (Greedy MMR Diversity, Log-Norm Activity), SQLite CTE single-query filters, and production scalability considerations, please see [TECHNICAL_DESIGN.md](./TECHNICAL_DESIGN.md).

---

Author: Handell Desulme