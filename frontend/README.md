# NetPulse Web Control Center — Frontend Application

Production-grade desktop-first web application and observability control center for **NetPulse (Network Validation & Performance Lab)**.

---

## 1. Frontend Architecture

```
frontend/
├── src/
│   ├── components/
│   │   ├── layout/            # Persistent Shell: Sidebar, TopBar, CommandPalette (Ctrl+K), AppLayout
│   │   └── ui/                # Dark-mode design system: Card, Badge, Button, Input, Slider, Tabs, Modal
│   ├── features/
│   │   ├── dashboard/         # Executive Dashboard: 8 KPI cards, Throughput/Latency trends, Suite breakdown
│   │   ├── test-runs/         # Test Runs filterable table + Granular Step-by-Step Execution Lifecycle
│   │   ├── performance/       # Interactive Benchmark Runner, Live Gauge, Percentiles (P50/P90/P95/P99)
│   │   ├── topology/          # 3-Node Routed Linux Virtual Lab (Client <-> Router <-> Server)
│   │   ├── fault-lab/         # Kernel tc netem Fault Console + Control vs Experiment Delta Impact
│   │   ├── packet-capture/    # Wireshark-grade packet table + Deep L2-L7 Scapy header inspector
│   │   ├── test-cases/        # Searchable 105-test case taxonomy catalog
│   │   ├── regression/        # Baseline diffing engine + Historical baseline manager
│   │   ├── reports/           # Artifacts explorer + 9 Verified Portfolio Claims audit table
│   │   └── settings/          # API connection URL, Demo mode toggle, Kernel capability inspector
│   ├── mock/                  # Realistic mock dataset for standalone offline exploration (DEMO DATA)
│   ├── services/              # Typed REST API service layer with automatic mock fallback
│   ├── stores/                # Zustand application store (health, active faults, notifications)
│   ├── types/                 # Comprehensive TypeScript interfaces
│   ├── App.tsx                # React Router v6 nested routes
│   └── main.tsx               # Application bootstrap
├── index.html                 # Dark-mode HTML5 shell with Inter & JetBrains Mono fonts
├── vite.config.ts             # Vite dev server + /api and /ws proxying
├── tailwind.config.js         # NetPulse dark-theme color tokens
└── package.json               # React 18, TanStack Query, Recharts, Zustand, Lucide React
```

---

## 2. Technology Stack

- **Framework**: React 18 + TypeScript + Vite
- **Styling**: Tailwind CSS (Dark-first enterprise theme)
- **State Management**: TanStack React Query + Zustand
- **Charting & Graphs**: Recharts
- **Icons**: Lucide React
- **Routing**: React Router DOM v6
- **Testing**: Vitest

---

## 3. Getting Started

### Development Mode

```bash
# 1. Install dependencies
cd frontend
npm install

# 2. Run local development server (http://localhost:5173)
npm run dev
```

### Production Build

```bash
# Compile and build production assets
npm run build
```

### Run Unit Tests

```bash
# Run Vitest test suite
npm run test
```

---

## 4. API & Mock Data Integration

The frontend automatically interfaces with the NetPulse FastAPI backend at `http://127.0.0.1:8000/api`.

If the backend server is offline or when `VITE_USE_MOCK_API=true`, the application seamlessly switches into **DEMO DATA MODE** with a persistent badge in the top bar, allowing full inspection and offline demonstration without broken requests.
