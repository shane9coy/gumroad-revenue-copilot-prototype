# Gumroad Revenue Copilot Demo

This demo is a fast, standalone proof of the Revenue Copilot data flow. It is intentionally local-first and static: no Gumroad scraping, no production Gumroad data, and no network access to Gumroad is required.

## Run Locally

From this repo root:

```bash
cd "/Users/sc/Project Files/gumroad"
python3 -m http.server 8080 --directory demo
```

Open:

```text
http://localhost:8080/
```

Architecture diagram:

```text
http://localhost:8080/architecture.html
```

If port `8080` is already in use, choose another port:

```bash
python3 -m http.server 8090 --directory demo
```

Then open `http://localhost:8090/`.

## Data Boundary

The demo uses seeded local demo data only. The sample products, views, sales, refunds, referrers, and recommendation evidence are synthetic fixtures created to prove the product experience and data flow.

This demo does not:

- scrape Gumroad
- call Gumroad production services
- read production creator data
- make autonomous pricing, email, or product-page changes

## Intended Product Path

The standalone demo proves the shape of the real system without coupling to production infrastructure. The intended Gumroad implementation path is:

```text
Gumroad Rails models/database
  -> metrics builder
  -> signal detector
  -> AI suggestion service
  -> UI
```

In the real product, Rails owns the source-of-truth facts from existing models and reporting tables. A metrics builder computes creator/product metrics deterministically. A signal detector finds high-confidence revenue opportunities from those facts. An AI suggestion service packages the approved signals into creator-facing recommendations with cited evidence. The UI renders those suggestions as reviewable next moves.

The AI layer should not calculate business metrics or invent evidence. It should only explain and prioritize precomputed facts.

## Reviewer Demo Script

1. Start the static server with `python3 -m http.server 8080 --directory demo`.
2. Open `http://localhost:8080/` and confirm the demo loads without a backend.
3. Show that the recommendations cite seeded local metrics such as views, conversion, referrers, refunds, or metadata gaps.
4. Click `Review` on a suggestion to open the safe action review panel.
5. Use `Copy action` to show that the demo supports a reviewable next step without auto-applying product changes.
6. Call out that this is not scraped Gumroad data and not production data.
7. Open `http://localhost:8080/architecture.html` to explain the demo data flow.
8. Close with the real-product path: Rails models/database -> metrics builder -> signal detector -> AI suggestion service -> UI.
