# CLAUDE.md — Networkify Codebase Guide

> Networkify transforms LinkedIn connection CSV exports into an interactive 3D graph that surfaces warm referral paths to target companies.

---

## Project Architecture

Three-tier full-stack application:

```
HackCanada/
├── backend/          # Python FastAPI + Neo4j graph database
├── frontend/         # Next.js 14 / React / TypeScript
├── extension/        # Chrome MV3 extension for LinkedIn scraping
├── neo4j/            # Standalone Cypher query files
└── docker-compose.yml
```

---

## Running the Project

### Prerequisites
- Docker & Docker Compose
- Python 3.11+
- Node.js 18+

### Quick Start

```bash
# 1. Start Neo4j
docker-compose up -d neo4j

# 2. Start Backend
cd backend
pip install -r requirements.txt
cp .env.example .env   # fill in your keys
uvicorn main:app --reload --port 8000

# 3. Start Frontend
cd frontend
npm install
cp .env.example .env.local  # set NEXT_PUBLIC_API_URL
npm run dev
```

Access at `http://localhost:3000`. Neo4j browser at `http://localhost:7474`.

### Full Docker Stack

```bash
docker-compose up --build
```

---

## Backend (`/backend`)

### Stack
- **FastAPI** 0.109 — REST API framework
- **Uvicorn** — ASGI server
- **Neo4j** Python driver — graph database client
- **Pandas** — CSV parsing
- **Pydantic** — settings & data validation
- **Google Gemini / Backboard.io** — AI message generation
- **Scrapfly** — LinkedIn profile enrichment
- **Authlib / python-jose** — Auth0 + JWT

### Directory Layout

```
backend/
├── main.py                        # App factory, middleware, router registration
├── config.py                      # Pydantic BaseSettings (reads .env)
├── requirements.txt
├── Dockerfile
├── db/
│   ├── neo4j_client.py            # Thin Neo4j driver wrapper
│   └── constraints.py             # Schema constraints & indexes
└── api/
    ├── routes/
    │   ├── upload.py              # CSV ingestion & network merge
    │   ├── graph.py               # Graph overview, stats, connections list
    │   ├── search.py              # Company search & path-finding
    │   ├── messages.py            # AI outreach generation & logging
    │   ├── enrich.py              # Profile enrichment via Scrapfly
    │   └── auth.py                # Auth0 OAuth2 + JWT issuance
    └── dependencies.py            # get_current_user() FastAPI dependency
└── services/
    ├── graph/
    │   ├── builder.py             # CSV parser, Neo4j node/edge builder
    │   └── path_finder.py         # 1st/2nd/3rd degree path queries
    ├── scoring/
    │   └── relevance.py           # Connection relevance scoring
    ├── ai/
    │   ├── message_generator.py   # Multi-tier AI message generation
    │   └── backboard_service.py   # Backboard.io threaded LLM wrapper
    └── enrichment/
        └── scrapfly_enricher.py   # On-demand LinkedIn profile scraper
```

### Environment Variables (`backend/.env`)

```
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=testpassword
GEMINI_API_KEY=
BACKBOARD_API_KEY=
SCRAPFLY_API_KEY=
LOGO_DEV_TOKEN=
AUTH0_DOMAIN=
AUTH0_CLIENT_ID=
AUTH0_CLIENT_SECRET=
APP_SECRET_KEY=
FRONTEND_URL=http://localhost:3000
```

### API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/upload/csv` | Upload LinkedIn CSV, build graph |
| POST | `/api/upload/network` | Merge an additional network |
| GET | `/api/search/company` | Find connection paths to a company |
| GET | `/api/graph/connections` | List 1st-degree connections |
| GET | `/api/graph/overview` | Full visualization data |
| GET | `/api/graph/stats` | Network statistics |
| POST | `/api/messages/generate` | Generate AI outreach message |
| POST | `/api/messages/log` | Log message send / visit event |
| GET/POST | `/api/messages/active-time` | Track session activity |
| POST | `/api/enrich/profile` | Enrich a profile via Scrapfly |
| GET | `/auth/login` | OAuth2 PKCE redirect |
| POST | `/auth/login/password` | Email/password auth |
| POST | `/auth/signup` | User registration |
| POST | `/auth/refresh` | Refresh JWT tokens |
| GET | `/auth/callback` | OAuth callback handler |
| GET | `/auth/me` | Current user info |

### Neo4j Data Model

**Nodes**
- `Person` — LinkedIn connection (properties: id, name, title, email, profile_url, connected_on, is_recruiter, is_user, is_source, network_name, owner_user_id, enriched, headline, location)
- `Company` — Employer (properties: name, domain, logo, url)
- `SentMessage` — Outreach record
- `LinkedInVisit` — Profile visit record

**Relationships**
- `(Person)-[:KNOWS]->(Person)` — Network connection
- `(Person)-[:WORKS_AT]->(Company)` — Employment
- `(Person)-[:SENT]->(SentMessage)`
- `(Person)-[:VISITED]->(LinkedInVisit)`

**Schema Constraints (constraints.py)**
- `UNIQUE` on `Person.id` and `Company.name`
- `INDEX` on `Person.name` and `Person.title`

### Key Backend Patterns

- **Person ID**: stable MD5 hash of `name + email` (see `builder.py:make_id`)
- **Async I/O**: CPU-bound CSV parsing and HTTP lookups run in a thread pool via `asyncio.get_event_loop().run_in_executor()`
- **In-process cache**: Company URL → domain mapping cached in-memory within the process lifetime
- **AI fallback chain**: Backboard.io → Gemini 2.0 Flash REST → template-based message
- **Deduplication**: `_find_existing_person_id()` matches by email or name+company before creating new nodes
- **Multi-network merging**: `owner_user_id` field lets multiple LinkedIn exports coexist; import removes redundant edges

---

## Frontend (`/frontend`)

### Stack
- **Next.js 14** (App Router, `"use client"` where interactive)
- **React 18** / **TypeScript**
- **Tailwind CSS 3** with custom theme
- **react-force-graph-3d** + **Three.js** — 3D graph
- **Axios** — HTTP client
- **lucide-react** — Icons

### Directory Layout

```
frontend/
├── app/
│   ├── layout.tsx             # Root layout with AuthProvider
│   ├── page.tsx               # Landing / hero page
│   ├── login/page.tsx
│   ├── upload/page.tsx        # CSV upload flow
│   ├── dashboard/page.tsx     # Stats + 3D graph + heatmap
│   ├── graph/page.tsx         # Full-screen 3D graph
│   ├── search/page.tsx        # Company search + results
│   ├── connections/page.tsx   # Browse 1st-degree connections
│   └── expand-network/page.tsx
├── components/
│   ├── AuthContext.tsx         # Global auth state + token refresh
│   ├── Sidebar.tsx
│   ├── graph/
│   │   ├── Graph.tsx          # 3D force-directed graph
│   │   └── DemoGraph3D.tsx
│   ├── search/
│   │   └── ConnectionCard.tsx
│   └── messages/
│       └── MessageModal.tsx
├── next.config.js
├── tailwind.config.js
├── tsconfig.json
└── package.json
```

### Environment Variables (`frontend/.env.local`)

```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Frontend Conventions

- **"use client"** directive required for all interactive components (hooks, state, event handlers)
- **AuthContext** provides `user`, `accessToken`, `getAuthenticatedAxios()` — always use the hook for authenticated requests
- **Token storage**: localStorage (`access_token`, `refresh_token`, `user`) — proactively refreshed 15 min before expiry
- **TypeScript strictness**: `"strict": false` in tsconfig — avoid enabling strict mode without updating all components
- **Styling**: All styles via Tailwind utility classes. Custom theme defined in `tailwind.config.js`:
  - Brand palette: `bg-dark`, `bg-surface`, `bg-elevated`, `bg-glass`
  - Animations: `animate-fade-in`, `animate-slide-up`, `animate-float`, `animate-glow`
- **Path alias**: `@/` resolves to the root of `frontend/`

### Available Scripts

```bash
npm run dev      # Development server (port 3000)
npm run build    # Production build
npm start        # Serve production build
```

---

## Chrome Extension (`/extension`)

- **Manifest V3**
- Runs content scripts on `https://www.linkedin.com/mynetwork/*` and `/in/*`
- Collects connection name, title, profile URL, degree
- Background service worker relays data to popup

---

## Neo4j Queries (`/neo4j/queries`)

`path_queries.cypher` contains reference Cypher for:
- 1st/2nd/3rd degree path finding
- Top companies by connection density
- Recruiter-only filtering

---

## Authentication Flow

1. User authenticates via Auth0 (OAuth2 PKCE or email/password)
2. Backend verifies with Auth0 and issues its own HS256 JWT:
   - Access token: **15 minutes**
   - Refresh token: **7 days**
3. Frontend stores tokens in localStorage; `AuthContext` auto-refreshes access tokens
4. All protected API calls include `Authorization: Bearer <access_token>`
5. Backend's `get_current_user()` dependency validates the JWT on every request

---

## Third-Party Service Dependencies

| Service | Purpose | Key Location |
|---------|---------|-------------|
| **Auth0** | Identity / OAuth2 | `backend/api/routes/auth.py` |
| **Google Gemini 2.0 Flash** | AI outreach messages (fallback) | `services/ai/message_generator.py` |
| **Backboard.io** | Primary LLM with persistent threads | `services/ai/backboard_service.py` |
| **Scrapfly** | LinkedIn profile scraping | `services/enrichment/scrapfly_enricher.py` |
| **Clearbit** | Company domain resolution | `services/graph/builder.py` |
| **logo.dev** | Company logo URLs | `services/graph/builder.py` |
| **Neo4j AuraDB / local** | Graph database | `db/neo4j_client.py` |

---

## Development Notes

### No Automated Test Suite
There are currently no unit or integration tests. When adding features, manually verify:
1. CSV upload correctly creates Person + Company nodes with expected properties
2. Search returns correct 1st/2nd/3rd degree results
3. Token refresh works without logging the user out
4. AI message generation gracefully falls back when API keys are absent

### CSV Format
LinkedIn exports have a 3-line header before the actual CSV header row. `builder.py` skips these with `skiprows=3`. Do not change this without checking the upstream export format.

### CORS
Backend currently uses `allow_origins=["*"]`. Tighten this in production using the `FRONTEND_URL` env var already present in `config.py`.

### Recruiter Detection
`is_recruiter` is inferred at CSV import time from job title keywords. This heuristic lives in `builder.py`; update the keyword list there if detection quality needs improvement.

### Deployment
- **Frontend**: Vercel (`.vercel/` in gitignore)
- **Backend**: Google Cloud Run (uvicorn configured with `--proxy-headers` in Dockerfile)
- **Database**: Neo4j AuraDB or self-hosted via Docker

---

## Common Tasks

### Add a New API Endpoint
1. Add route function in the relevant `backend/api/routes/*.py` file
2. If it needs auth, add `current_user: dict = Depends(get_current_user)` as a parameter
3. Router is already registered in `main.py` — no changes needed there unless adding a new router file

### Add a New Frontend Page
1. Create `frontend/app/<route>/page.tsx`
2. Add `"use client"` if the page uses hooks or event handlers
3. Add the route to `Sidebar.tsx` navigation links

### Modify the Graph Schema
1. Update Cypher in `db/constraints.py` and `neo4j/queries/`
2. Update `services/graph/builder.py` for write operations
3. Update `services/graph/path_finder.py` for read queries
4. Update relevant Pydantic response models in `api/routes/`

### Update AI Message Templates
Templates (fallback when APIs unavailable) are defined in `services/ai/message_generator.py`. The prompt sent to Gemini/Backboard is also constructed there.
