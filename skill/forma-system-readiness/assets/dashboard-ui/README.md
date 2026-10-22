# FOMO1 dashboard UI (React + shadcn/ui)

    npm install
    npm run build        # -> dist/index.html (single file)
    npm run dev          # live preview with public/sample-data.json
    npm run test:logic   # model + graph layout checks (Node 22+)

`python fomo1.py render --open` (in ../fomo1-app) injects the day's data into `dist/index.html`.
Without a build, FOMO1 falls back to a plain-HTML dashboard.
