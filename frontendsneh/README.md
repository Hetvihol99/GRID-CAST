# GreenWatt Forecast

AI-powered renewable generation forecasting dashboard — solar/wind output vs.
grid demand over the next 24–72 hours, with flagged over/under-generation
windows and recommended grid actions (curtailment, storage dispatch, backup
activation).

Built to match the visual identity of greenwattt.vercel.app (deep forest
green `#173d2b`, solar-amber and wind-teal accents).

## Stack

- Next.js 14 (App Router) + TypeScript
- Tailwind CSS
- Recharts (forecast chart)

## Run it

```bash
npm install
npm run dev
```

Then open http://localhost:3000.

## Where the mock data lives

`lib/mockData.ts` generates a realistic-looking 72-hour forecast plus sample
alerts, recommendations, and site list. Every component reads from this one
file — swap its exported functions for real calls to your weather API and
forecasting model service, and the UI needs no changes.

## Structure

```
app/
  layout.tsx        Fonts, metadata, global background
  page.tsx           Assembles the dashboard sections
  globals.css        Tailwind + base styles
components/
  Header.tsx
  HeroForecast.tsx    Headline + the main forecast chart
  ForecastChart.tsx   Recharts composed chart (client component)
  KpiRow.tsx
  AlertsPanel.tsx
  RecommendationsPanel.tsx
  SitesTable.tsx
  Footer.tsx
lib/
  mockData.ts
```

## Next steps for the real system

- Replace `buildForecast()` with calls to your Prophet/LSTM/XGBoost
  forecasting service, fed by a weather/satellite API and each site's
  historical generation records.
- Replace the hardcoded `alerts`/`recommendations` with output from the
  rules engine that compares forecast vs. scheduled demand and storage
  capacity per site.
- Add auth + per-utility site scoping before this goes further than a demo.
