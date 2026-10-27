# apps/web

The Next.js front end for `apps/server` (npm package `@alloy/web`).

```sh
vp run dev:web      # from the repo root, http://localhost:3000
vp run dev:api      # the API it talks to, in another terminal
```

```text
apps/web/src/
├── proxy.ts          # redirects on the session cookie's presence
├── app/              # routes only; each page composes feature components behind <Suspense>
│   ├── api/[...path]/route.ts   # forwards /api/* to the API with the cookie and the visitor's address
│   ├── (auth)/                  # login, signup, and the emailed-link pages
│   ├── (onboarding)/            # pending invitations, name a workspace, import or skip
│   └── (app)/[workspaceId]/     # sidebar layout; dashboard, contacts, companies, tasks, assistant, imports, members, settings, account
├── features/         # product code by domain, mirroring the API: auth, workspaces (+ invites/), crm/*, assistant
│   └── <feature>/    # components/, hooks/, queries.ts, mutations.ts, schemas.ts, server.ts
├── components/       # ui/ (shadcn) and shared/ (layout, form, chat, data-table, ...)
├── hooks/            # generic hooks
└── lib/              # api/, formatting/, time-zone/, lists.ts, validation.ts, routes.ts
```

## Rules the code relies on

- **The browser never sees `API_URL`.** Every request goes through the proxy route handler.
- **Routes only in `app/`.** Product code lives in `features/`, one folder per API module.
- **The API is the real permission check.** `useCan()` and `<Can permission="crm:write">` only hide what the API would reject.
- **One key per query.** Query definitions in `queries.ts` take the client as a parameter, so server and client build identical keys.
- **List state lives in the URL.** Filters, page, and sort are search params.
- **Workspace links come from `workspacePaths(id)`**, never hand-built strings.

## Adding things

- **A page**: a route under `app/(app)/[workspaceId]/` that composes feature components behind `<Suspense>`.
- **A feature**: a folder in `features/` with the parts it needs from `components/`, `hooks/`, `queries.ts`, `mutations.ts`, `schemas.ts`, and `server.ts`.
- **A CRM write**: a plain function in `mutations.ts`, followed by `invalidateCrm()`.
- **A shadcn component**: `cd apps/web && pnpm dlx shadcn@latest add card dialog`.
- **A call to a new or changed API route**: run `vp run generate` from the root first, so the client knows its types.

## How it works

- **Calling the API**: the proxy route handler forwards each request with the session cookie, and passes the visitor's address (from the header `CLIENT_IP_HEADER` names) to the API for rate limits. Server Components use `getSessionApi()` and `requireUser()`; Client Components use `browserApi` from `@/lib/api/client`. `unwrap()` turns a non-2xx result into an `ApiError`.
- **Data flow**: pages are Server Components. Read-only pages fetch and render. Pages that mutate or filter prefetch into a per-request `QueryClient` and hand the cache over with `<HydrationBoundary>`, and a Client Component continues with `useSuspenseQuery` on the same key.
- **Workspaces**: every app page lives under `/{workspaceId}`. The layout starts `requireWorkspace()`, and Client Components read it with `useWorkspace()`.
- **Forms**: TanStack Form bound to shadcn `Field` via `useAppForm`, validated with the Zod schemas in each feature's `schemas.ts`.
- **Tables**: TanStack Table v9 in manual mode, one page of 50 rows, with sorting and paging done by the API.
- **Styling**: Tailwind CSS v4 and shadcn/ui (`base-nova` style on Base UI, zinc, Geist). Everything lives in `src/app/globals.css`; prefer semantic utilities (`bg-background`, `text-muted-foreground`).
- **React Compiler** is on: write plain React, and use `useMemo`/`useCallback` only where needed.
- **Time zones**: `<TimeZoneSync>` writes the browser's zone to a `tz` cookie, so server and client format dates the same way.
- **Generated files**: `next-env.d.ts` and `.next/types/` are generated and gitignored.
