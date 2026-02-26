# ZeelOS Agent Template

> **Template Version:** 1.0.0
> **Last Updated:** 2026-02-12
> **Progress Tracking:** Each section has a status marker for agent handoff

---

## How to Use This Template (Ralph Loop)

Run tasks using the ralph-loop command with this format:

```bash
/ralph-loop:ralph-loop "[TASK DESCRIPTION]

Requirements:
- [Requirement 1]
- [Requirement 2]
- [Requirement 3]

Success Criteria:
- All requirements implemented
- No TypeScript/ESLint errors
- Build passes (npm run build)

Output <promise>DONE</promise> when complete." --completion-promise "DONE" --max-iterations [N]
```

### Example Commands

**Simple task:**
```bash
/ralph-loop:ralph-loop "Add a hello world API endpoint.

Requirements:
- Create GET /api/hello endpoint in convex/http.ts
- Return { message: 'Hello World' }

Success Criteria:
- Endpoint works when tested
- No errors

Output <promise>DONE</promise> when complete." --completion-promise "DONE" --max-iterations 10
```

**Feature implementation:**
```bash
/ralph-loop:ralph-loop "Add dark mode toggle to settings.

Requirements:
- Add toggle switch in Settings modal
- Persist preference to userSettings
- Apply theme class to root element

Success Criteria:
- Toggle works and persists
- No TypeScript errors
- Build passes

Output <promise>DONE</promise> when complete." --completion-promise "DONE" --max-iterations 20
```

**Bug fix:**
```bash
/ralph-loop:ralph-loop "Fix habit completion not saving.

Bug:
- Clicking habit checkbox doesn't persist

Requirements:
- Debug the mutation in convex/habits.ts
- Fix the issue
- Verify fix works

Output <promise>DONE</promise> when complete." --completion-promise "DONE" --max-iterations 15
```

---

## Section 1: Project Overview
<!-- STATUS: TESTED -->

**ZeelOS** is a personal life operating system and productivity dashboard built with React + TypeScript and Convex backend. It helps users manage 7 strategic life domains:

- **HQ** - Dashboard with clock, weather, quick tasks
- **Focus** - Pomodoro timer, time blocking, habits
- **Vision** - Goals (OKRs), life pillars, journal, reviews
- **Health** - Sleep, mood, energy, workouts
- **Finance** - Income/expenses, budgets, net worth
- **Brain** - Quick capture, reading lists, learning
- **People** - CRM with Google Sheets sync

**AI Agent Integration:** The system supports autonomous AI agents (Vaani, Prospector) via OpenClaw CLI on EC2, bridged through Cloudflare tunnel.

---

## Section 2: Technology Stack
<!-- STATUS: TESTED -->

### Frontend
| Technology | Version | Purpose |
|------------|---------|---------|
| React | ^19.2.0 | UI Framework |
| TypeScript | ~5.9.3 | Type safety |
| Vite | ^7.2.4 | Build tool + HMR |
| Tailwind CSS | ^4.1.18 | Styling |
| Lucide React | ^0.563.0 | Icons (563+) |
| @dnd-kit/* | ^6-10 | Drag and drop (core, sortable, modifiers) |
| Sonner | ^2.0.7 | Toast notifications |
| date-fns | ^4.1.0 | Date manipulation |

### Backend
| Technology | Version | Purpose |
|------------|---------|---------|
| Convex | ^1.31.7 | Real-time backend with TypeScript-first architecture |
| @convex-dev/auth | ^0.0.90 | Authentication with Google OAuth |
| OpenClaw Bridge | - | Node.js HTTP server bridging to OpenClaw agents |

### External Services
- Google OAuth (authentication)
- Google Calendar API (read-only sync)
- Google Sheets API (bi-directional CRM sync)
- Open-Meteo API (weather data)

---

## Section 3: Architecture & Key Files
<!-- STATUS: TESTED -->

### Directory Structure
```
ZeelOS/
├── src/                          # Frontend React application
│   ├── components/               # React components (25 subdirectories)
│   │   ├── agents/              # Agent UI (AgentCard, TaskBoard, etc.)
│   │   ├── layout/              # Dashboard, Header, Sidebar, BottomNav
│   │   ├── finance/             # Financial tracking
│   │   ├── habits/              # Habit tracking with heatmap
│   │   ├── goals/               # Goal management with OKRs
│   │   ├── health/              # Health tracking
│   │   ├── journal/             # Journal entries
│   │   ├── people/              # CRM and contacts
│   │   ├── learning/            # Learning tracker
│   │   ├── protocol/            # Routines/protocols
│   │   ├── quick-capture/       # Quick capture inbox
│   │   ├── reading-list/        # Reading list management
│   │   ├── reviews/             # Daily/weekly reviews
│   │   ├── timer/               # Pomodoro timer
│   │   ├── time/                # Clock and calendar
│   │   ├── weather/             # Weather widget
│   │   └── ui/                  # Shared UI components
│   ├── context/                 # React Context Providers
│   ├── hooks/                   # Custom React hooks (20+)
│   ├── services/                # External API services
│   ├── types/                   # TypeScript type definitions
│   └── utils/                   # Utility functions
├── convex/                      # Convex backend functions (17 files)
│   ├── schema.ts               # Database schema (~24 app tables + auth tables)
│   ├── auth.config.ts          # Auth configuration
│   ├── auth.ts                 # Auth helpers
│   ├── agents.ts               # Agent CRUD operations
│   ├── agentTasks.ts           # Task management
│   ├── agentActivities.ts      # Activity logging
│   ├── dispatch.ts             # Task dispatch to OpenClaw
│   ├── triage.ts               # Task triage logic
│   ├── http.ts                 # HTTP webhook endpoints
│   ├── crons.ts                # Scheduled jobs
│   ├── debug.ts                # Debug utilities
│   └── _generated/             # Auto-generated API types
├── openclaw-bridge/            # HTTP bridge to OpenClaw agents
│   └── server.js               # Bridge server (port 3847)
└── plan/                       # Planning documents
```

### Critical Files Reference
| File | Purpose |
|------|---------|
| `convex/schema.ts` | All 28 database table definitions |
| `convex/dispatch.ts` | Agent task dispatch with logging |
| `convex/http.ts` | Webhook endpoints for agent callbacks |
| `src/App.tsx` | Root component with routing |
| `src/context/*.tsx` | Auth, Theme, Navigation providers |
| `openclaw-bridge/server.js` | Bridge server implementation |

### Database Schema (28 Tables)
**Core:** `users`, `userSettings`
**Tasks:** `tasks`, `agentTasks`, `agentActivities`, `agentTaskComments`
**Life:** `habits`, `habitCompletions`, `goals`, `milestones`, `keyResults`
**Health:** `healthEntries`, `workouts`
**Finance:** `transactions`, `budgets`, `savingsGoals`, `assets`, `liabilities`
**Time:** `timeBlocks`, `timerSessions`, `routines`, `routineCompletions`
**Other:** `journalEntries`, `reviews`, `pillarScores`, `pillarAssessments`, `contacts`, `interactions`, `agents`

---

## Section 4: Coding Standards & Patterns
<!-- STATUS: TESTED -->

### React Component Pattern
```tsx
// Always use functional components with TypeScript
interface ComponentProps {
  propName: PropType;
}

export function ComponentName({ propName }: ComponentProps) {
  // Use Convex hooks for data
  const data = useQuery(api.module.queryName, { arg });
  const mutation = useMutation(api.module.mutationName);

  // Event handlers
  const handleAction = async () => {
    await mutation({ args });
  };

  return (
    <div className="tailwind-classes">
      {/* JSX content */}
    </div>
  );
}
```

### Convex Function Pattern
```typescript
// convex/module.ts
import { v } from "convex/values";
import { query, mutation, action } from "./_generated/server";
import { getAuthUserId } from "@convex-dev/auth/server";

// Query - for reading data (real-time subscriptions)
export const list = query({
  args: {},
  handler: async (ctx) => {
    const userId = await getAuthUserId(ctx);
    if (!userId) return [];

    return await ctx.db
      .query("tableName")
      .withIndex("by_user", (q) => q.eq("userId", userId))
      .collect();
  },
});

// Mutation - for writing data
export const create = mutation({
  args: { field: v.string() },
  handler: async (ctx, args) => {
    const userId = await getAuthUserId(ctx);
    if (!userId) throw new Error("Not authenticated");

    return await ctx.db.insert("tableName", {
      userId,
      field: args.field,
      createdAt: Date.now(),
    });
  },
});

// Action - for external API calls
export const fetchExternal = action({
  args: { url: v.string() },
  handler: async (ctx, args) => {
    const response = await fetch(args.url);
    return await response.json();
  },
});
```

### Naming Conventions
- **Components:** PascalCase (`AgentCard.tsx`)
- **Hooks:** camelCase with `use` prefix (`useAgentTasks.ts`)
- **Convex functions:** camelCase (`createTask`, `listByUser`)
- **Types:** PascalCase with descriptive names (`AgentTask`, `HealthEntry`)
- **Files:** kebab-case for multi-word (`agent-task-card.tsx`) or PascalCase matching component

### Import Order
1. React imports
2. Third-party libraries
3. Convex imports (`convex/react`, generated API)
4. Local components
5. Local hooks/utils
6. Types
7. Styles (if any)

---

## Section 5: Agent Task Guidelines
<!-- STATUS: TESTED -->

### Task Types for Agents

#### 1. Feature Implementation
```
Requirements:
- [Specific feature description]
- [UI/UX requirements]
- [Data model changes needed]

Success Criteria:
- All requirements implemented
- No TypeScript/ESLint errors
- Component renders correctly
- Convex functions work with auth
```

#### 2. Bug Fixes
```
Bug Description:
- [What's broken]
- [How to reproduce]
- [Expected behavior]

Success Criteria:
- Bug is fixed
- No regressions introduced
- Related tests pass (if any)
```

#### 3. Refactoring
```
Scope:
- [Files/components to refactor]
- [Pattern to apply]

Success Criteria:
- Functionality unchanged
- Code follows project patterns
- No new errors introduced
```

### Agent Workflow States
```
inbox → assigned → in_progress → review → done
```

### Logging Convention for Agents
Use prefixed logging for traceability:
```typescript
console.log("[DISPATCH] Starting task dispatch...");
console.log("[BRIDGE] Received request:", data);
console.log("[AGENT] Processing task:", taskId);
```

---

## Section 6: Common Operations Reference
<!-- STATUS: TESTED -->

### Adding a New Feature

1. **Define types** in `src/types/` (if needed)
2. **Add schema** in `convex/schema.ts` (defineTable with indexes)
3. **Create Convex functions** in `convex/feature.ts` (query/mutation/action)
4. **Build components** in `src/components/feature/`
5. **Add to navigation** if new view in Dashboard
6. **Test** with `npm run dev` and Convex dashboard

### Working with Convex

```bash
# Development (runs both Vite and Convex dev server)
npm run dev             # Start Vite dev server (port 5173)
npx convex dev          # Start Convex dev server (separate terminal)

# Building
npm run build           # Runs: convex codegen && tsc && vite build

# Linting
npm run lint            # Run ESLint

# Deployment
npx convex deploy       # Deploy Convex functions to production

# Debug
# Use Convex Dashboard at https://dashboard.convex.dev
```

### Authentication Checks
Always verify auth in Convex functions:
```typescript
import { getAuthUserId } from "@convex-dev/auth/server";

// In query/mutation handler:
const userId = await getAuthUserId(ctx);
if (!userId) throw new Error("Not authenticated");
// or for queries that return empty:
if (!userId) return [];
```

### Common UI Patterns
- **Toasts:** `import { toast } from "sonner";` then `toast.success("Message")`
- **Icons:** `import { IconName } from "lucide-react";`
- **Loading states:** Check `data === undefined` from `useQuery()`
- **Convex hooks:** `useQuery(api.module.fn)`, `useMutation(api.module.fn)`

### Environment Variables (in .env.local)
```
VITE_CONVEX_URL         # Convex deployment URL (auto-set by convex dev)
```

### Convex Environment Variables (set via dashboard or CLI)
```
OPENCLAW_BRIDGE_URL     # Bridge URL (https://bridge.zeelpatel.ca)
OPENCLAW_BRIDGE_TOKEN   # Auth token for bridge
```

---

## Section 7: Testing & Validation
<!-- STATUS: TESTED -->

### Pre-Commit Checklist
- [ ] `npm run build` passes
- [ ] No TypeScript errors
- [ ] No ESLint warnings
- [ ] UI renders correctly
- [ ] Convex functions work (test in dashboard)
- [ ] Auth protected routes work

### Build Commands
```bash
npm run dev        # Start dev server (Vite + Convex)
npm run build      # Production build
npm run lint       # Run ESLint
npm run preview    # Preview production build
```

---

## Agent Handoff Protocol

When completing a section or task:

1. **Update status marker** from `PENDING` to `TESTED`
2. **Commit changes** with descriptive message
3. **Push to remote** for next agent pickup
4. **Document any blockers** in this file

### Status Markers
- `<!-- STATUS: PENDING -->` - Not yet worked on
- `<!-- STATUS: IN_PROGRESS -->` - Currently being worked on
- `<!-- STATUS: TESTED -->` - Completed and verified
- `<!-- STATUS: BLOCKED -->` - Blocked, see notes below

---

## Notes & Blockers

### Known Issues
- `.env.example` is outdated (references Supabase, but project now uses Convex)
- ESLint has 52 errors / 5 warnings (pre-existing, not blocking)
- Build produces chunk size warning (728KB, should consider code splitting)

### Completion Log
- **2026-02-12**: All 7 sections tested and verified against codebase
  - Section 1: Project Overview - verified agents (Vaani, Prospector) and domains
  - Section 2: Technology Stack - verified versions against package.json, build passes
  - Section 3: Architecture - verified 25 component dirs, 17 convex files
  - Section 4: Coding Standards - verified patterns in AgentCard.tsx and agents.ts
  - Section 5: Agent Guidelines - verified task states and [DISPATCH]/[BRIDGE] logging
  - Section 6: Common Operations - verified npm scripts and Convex commands
  - Section 7: Testing - verified build commands work

---

**Template Created:** 2026-02-12
**Created By:** Claude Agent
**All Sections Tested:** Yes
