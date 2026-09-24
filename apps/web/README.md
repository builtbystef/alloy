# @alloy/web

The Next.js front end for `apps/server`.

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

## Calling the API

The browser never sees `API_URL`. Every request goes through the proxy route
handler, which forwards the request with the session cookie and passes the
visitor's address (read from the header `CLIENT_IP_HEADER` names) to the API
for rate limits. Server Components use `getSessionApi()` and `requireUser()`;
Client Components use `browserApi` from `@/lib/api/client`. `unwrap()` turns
a non-2xx result into an `ApiError`.

## Data flow

Pages are Server Components. Read-only pages fetch and render. Pages that
mutate or filter prefetch into a per-request `QueryClient`, hand the cache
over with `<HydrationBoundary>`, and a Client Component continues with
`useSuspenseQuery` on the same key. Query definitions in each feature's
`queries.ts` take the client as a parameter so both sides build identical
keys. Writes are plain functions in `mutations.ts`; after a CRM write,
`invalidateCrm()` drops every CRM query. List filters, page, and sort live in
the URL.

## Workspaces

Every app page lives under `/{workspaceId}`. The layout starts
`requireWorkspace()` and Client Components read it with `useWorkspace()`.
`useCan()` and `<Can permission="crm:write">` hide what the API would
reject; the API stays the real check. Build links with `workspacePaths(id)`.

## Forms and tables

Forms: TanStack Form bound to shadcn `Field` via `useAppForm`, validated with
the Zod schemas in each feature's `schemas.ts`. Tables: TanStack Table v9 in
manual mode, one page of 50 rows, sorting and paging done by the API.

## Styling

Tailwind CSS v4 and shadcn/ui (`base-nova` style on Base UI, zinc, Geist).
Everything lives in `src/app/globals.css`; prefer semantic utilities
(`bg-background`, `text-muted-foreground`). Add components with:

```sh
cd apps/web && pnpm dlx shadcn@latest add card dialog
```

## Notes

- `reactCompiler` is on: write plain React, use `useMemo`/`useCallback` only where needed.
- `<TimeZoneSync>` writes the browser's zone to a `tz` cookie so server and client format dates the same way.
- `next-env.d.ts` and `.next/types/` are generated and gitignored.
