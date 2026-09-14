# @alloy/web

The Next.js front end for `apps/server`.

```sh
vp run dev:web      # from the repo root, http://localhost:3000
vp run dev:api      # the API it talks to, in another terminal
```

```text
apps/web/
├── next.config.ts        # cacheComponents, typedRoutes, reactCompiler, skipTrailingSlashRedirect
├── vite.config.ts        # the `@/` alias for the tests; Next resolves it from tsconfig
├── postcss.config.mjs    # @tailwindcss/postcss
├── components.json       # shadcn/ui: style, base color, aliases
├── tsconfig.json         # extends tsconfig/browser.json with what Next.js needs
├── .env.example          # API_URL, CLIENT_IP_HEADER; copy to .env.local
└── src/
    ├── proxy.ts          # no cookie → /login?next=…; cookie on /login → /
    ├── instrumentation.ts # runs at server start: rejects a bad CLIENT_IP_HEADER
    ├── app/              # routes only: each page composes feature components behind <Suspense>
    │   ├── layout.tsx    # root layout: Geist font, <Providers>
    │   ├── providers.tsx # QueryClientProvider, next-themes, sonner <Toaster>
    │   ├── globals.css   # Tailwind import, shadcn theme tokens
    │   ├── icon.svg, favicon.ico, apple-icon.png   # the logo, in the formats browsers ask for
    │   ├── api/[...path]/route.ts   # the proxy to the API; forwards the visitor's address
    │   ├── logout/route.ts          # clears the session cookie
    │   ├── (auth)/       # centered layout with the logo; login, signup, verify-email, forgot-password, reset-password, confirm-email, invites/[token]
    │   ├── (onboarding)/ # the same look, wider: invites (pending invitations), onboarding (name a workspace), [workspaceId]/onboarding (import, or skip)
    │   └── (app)/
    │       ├── page.tsx              # `/`: opens the last-used (cookie) or first workspace; with none, pending invitations or onboarding
    │       └── [workspaceId]/        # app layout (sidebar, <WorkspaceProvider>), error.tsx, not-found.tsx
    │           ├── page.tsx          # dashboard
    │           ├── contacts/, companies/   # list, new/, [id]/, [id]/edit/
    │           ├── tasks/, imports/, assistant/, members/, settings/, account/
    ├── features/         # product code, by domain; each has only the files it needs
    │   ├── auth/         # components/ (auth-form, the emailed-link cards, account forms), schemas.ts, mutations.ts, hooks/use-logout.ts
    │   ├── workspaces/   # components/ (switcher, members, invites, settings), workspace-provider.tsx, server.ts, queries.ts, mutations.ts, schemas.ts, roles.ts, cookie.ts
    │   ├── crm/
    │   │   ├── queries.ts            # invalidateCrm(): every CRM query, after any write
    │   │   ├── contacts/             # components/ (table, columns, form, detail, activity feed, status badge), hooks/, queries.ts, mutations.ts, schemas.ts, labels.ts
    │   │   ├── companies/, tasks/    # the same shape
    │   │   ├── attachments/          # components/attachments-card, hooks/, queries.ts, mutations.ts (the three-step upload), limits.ts
    │   │   ├── imports/              # components/ (card, table, details dialog), hooks/, queries.ts, mutations.ts, schemas.ts, labels.ts, limits.ts
    │   │   └── dashboard/            # components/dashboard.tsx (Server Component), server.ts
    │   └── assistant/    # components/ (chat-panel, conversation-list, approval-card, message-parts), hooks/use-chat-uploads, queries.ts, mutations.ts, tools.ts, types.ts
    ├── components/       # generic: knows nothing about the domain
    │   ├── ui/           # shadcn/ui components, owned by this repo
    │   └── shared/       # everything else that is reusable
    │       ├── layout/   # app-sidebar, nav-menu, user-menu, page-header
    │       ├── chat/     # chat primitives (conversation, message, prompt-input, tool, confirmation, ...)
    │       ├── form/     # useAppForm + TextField, TextareaField, SelectField, DateTimeField, SubmitButton
    │       └── data-table.tsx, confirm-dialog.tsx, entity-combobox.tsx, skeletons.tsx, logo.tsx, time-zone-sync.tsx, truncated-note.tsx
    ├── hooks/            # generic hooks: use-list-state, use-url-filters, use-debounced-value, use-mobile
    └── lib/              # infrastructure
        ├── api/          # client.ts (browserApi, pointed at /api), server-client.ts (createApi from API_URL), errors.ts (ApiError, unwrap, errorMessage), upload.ts (presigned PUT)
        ├── auth/session.ts   # server-only: getSessionApi(), getCurrentUser(), requireUser()
        ├── formatting/   # dates.ts (ISO ⇄ datetime-local in a zone; relative days), bytes.ts
        ├── time-zone/    # server.ts: the zone from the `tz` cookie; cookie.ts
        ├── lists.ts      # paging: PAGE_SIZE, listPage(), paged(); URL search parsing shared by the list schemas
        ├── validation.ts # Zod field builders: requiredText, optionalEmail, optionalDateTime, ...
        ├── routes.ts     # workspacePaths(id): every href under /{workspaceId}
        └── client-address.ts, query-client.ts, utils.ts
```

## Workspaces

Every app page lives under `/{workspaceId}`. The layout for that segment
calls `requireWorkspace()` but does not await it: the promise goes into
`<WorkspaceProvider>`, and Client Components read it with `useWorkspace()`
(`use()` under the hood), each suspending inside the page's own `<Suspense>`.
The static shell therefore stays prerendered while the workspace, with the
caller's role and permissions, streams in once. `requireWorkspace()` is
`cache()`d, so the layout, the sidebar, and the page share one request; a
non-member gets the segment's `not-found.tsx`.

Permissions come from the API (`WorkspaceRead.permissions`). `useCan()` and
`<Can permission="crm:write">` hide what the request would reject: new/edit/
delete buttons, the task checkboxes, the invitation form, the role selects.
The API stays the real check. Links are built with `workspacePaths(id)` from
`lib/routes.ts`, typed as template literals so `typedRoutes` verifies them.

`/` picks a workspace: the one in the `workspace` cookie that
`<RememberWorkspace>` writes on every visit, else the first. A user with none
goes to `/invites` when invitations are waiting for their address (accept
opens the workspace; declining the last one, or the link below, moves on), else
to `/onboarding`. Onboarding is per workspace: name it, then import a CSV or
skip, which stamps `onboarded_at`; the app layout sends owners and admins of
a workspace still in onboarding back to `/{id}/onboarding`. "New workspace"
in the switcher starts the same flow. Pending invitations also appear in the
account settings.

Invitation links (`/invites/{token}`) preview without a login and offer
sign-up first, with the address filled in and the token sent along so the API
skips the verification email; the auth form keeps `next` across the
login/sign-up links so a new user lands back on the invitation.

## Styling: Tailwind CSS and shadcn/ui

Tailwind CSS v4 runs through `@tailwindcss/postcss`; there is no
`tailwind.config.*`, everything lives in `src/app/globals.css`. It imports
`tailwindcss`, `tw-animate-css`, and `shadcn/tailwind.css`, declares the `dark`
variant as `.dark` on an ancestor, and defines the theme: the zinc color tokens
as `oklch()` variables on `:root` and `.dark`, mapped to Tailwind colors in
`@theme inline`, plus the radius scale. Use the semantic utilities
(`bg-background`, `text-muted-foreground`, `border-border`) over raw palette
colors so a theme change stays a one-file edit.

shadcn/ui was initialized from the preset at
<https://ui.shadcn.com/create?preset=bcivVNEe>: the `base-nova` style on
[Base UI](https://base-ui.com) primitives (`@base-ui/react`, not Radix), zinc
base color, Geist font, Lucide icons, small radius, pointer cursor on buttons.
`components.json` records those choices; `baseColor` cannot be changed after
init, the rest can. Add components with:

```sh
cd apps/web && pnpm dlx shadcn@latest add card dialog
```

Components land in `src/components/ui/` as plain source, so edit them like any
other file; `shadcn add --overwrite` resets one to the registry version. Import
`cn` from `@/lib/utils` to merge class names. The `shadcn` package is a
devDependency only because `globals.css` imports its `tailwind.css`; nothing
from it ships at runtime.

The Geist font is loaded in `layout.tsx` with `next/font/google` and exposed as
`--font-sans` on `<html>`, which `globals.css` maps to `font-sans`. Dark mode is
class-based: add `dark` to `<html>` (a theme switcher such as `next-themes` does
this) rather than relying on `prefers-color-scheme`.

## Calling the API

The browser never sees `API_URL`. Every request goes through
`src/app/api/[...path]/route.ts`, a Route Handler that forwards the method,
path, query, body, `Cookie`, and `Set-Cookie` between the browser and the API,
and passes the visitor's address along as `X-Forwarded-For` for the API's
rate limits. The address is read from the one request header
`CLIENT_IP_HEADER` names (`cf-connecting-ip` on Cloudflare, `x-real-ip`
behind Nginx, `x-forwarded-for` on Railway, Render, or Fly; for the last, the
final entry, which is the one the nearest proxy appended). Only the header
the host overwrites on every request is safe: the proxy cannot tell which
platform is in front of it, so guessing from whatever arrives would let a
visitor forge one of the others and dodge the per-address limits. With the
variable unset (local `next dev`), no address is sent and the API limits on
this server's address; an unknown value fails at startup in
`src/instrumentation.ts`.
The API's login response sets its `__Host-session` cookie for the Next.js
origin; the browser sends it back on the next `/api/...` call by itself, and
Server Components read it with `cookies()` and forward it through
`getSessionApi()`. Because the FastAPI collection routes end in a slash,
`skipTrailingSlashRedirect` is on so `/api/contacts/` is not redirected first.

Two clients, one set of types from `@alloy/api-client`:

```tsx
// Server Components: the caller's session, read from cookies()
const api = await getSessionApi();
const user = await requireUser(); // redirects to /login on 401

// Client Components: same-origin, cookie attached by the browser
import { browserApi } from "@/lib/api/client";
```

`unwrap()` turns a non-2xx result into an `ApiError` with the API's `detail`
as the message and, for a 422, per-field messages in `fields`.

### Server Components first

Pages are Server Components. The static parts (headers, buttons, layout) go
into the prerendered shell; anything that reads the session cookie or the URL
sits behind `<Suspense>` and streams, as Cache Components requires. Where the
page is read-only, that is the whole story: the dashboard fetches with the
session client and renders, no client bundle involved.

Where the page mutates or filters, a Client Component takes over from the
prefetched data, following the TanStack Query "advanced SSR" guide:

```tsx
// Server Component: prefetch into a per-request QueryClient, hand over the cache
const queryClient = getQueryClient();
await queryClient.prefetchQuery(contactListQuery(api, filters));
return (
  <HydrationBoundary state={dehydrate(queryClient)}>
    <ContactsTable initialFilters={filters} timeZone={timeZone} />
  </HydrationBoundary>
);

// Client Component: same key, same data, no second request
const { data } = useSuspenseQuery(contactListQuery(browserApi, filters));
```

Query definitions in each feature's `queries.ts` take the client as a
parameter so both sides build identical keys. Writes are plain functions in
the feature's `mutations.ts` (`createContact(ws, body)`,
`uploadAttachment(ws, parent, file, onProgress)`), so a component hands one
to `useMutation` and keeps only the toast and the navigation; the HTTP paths
live in one place per feature. After a CRM write, `invalidateCrm()` drops
every CRM query: the entities reference each other (a task embeds its
contact, completing one logs an activity), so a broad invalidation is simpler
than encoding those rules.

List filters live in the URL. A filter change updates the address bar with
`history.replaceState` (no server round trip) and the previous rows stay
visible through `useDeferredValue` while the next query loads; a real
navigation (back/forward) remounts the table with the new URL, and the server
prefetches whatever the URL says.

### Forms: Zod + TanStack Form + shadcn Field

`src/components/shared/form` binds TanStack Form to the shadcn `Field` components
with `createFormHook`, so a form is:

```tsx
const form = useAppForm({
  defaultValues: { name: "", email: "" },
  validationLogic: revalidateLogic(),        // quiet until submit, then live
  validators: { onDynamic: contactSchema },  // a Zod schema, no adapter
  onSubmit: async ({ value }) => mutation.mutateAsync(contactSchema.parse(value)),
});

<form.AppField name="email">{(field) => <field.TextField label="Email" type="email" />}</form.AppField>
<form.AppForm><form.SubmitButton>Save</form.SubmitButton></form.AppForm>
```

The Zod schemas in each feature's `schemas.ts` (built from the field helpers
in `src/lib/validation.ts`) take what inputs hold (strings) and produce the
API's request body: `""` becomes `null`, which a PATCH treats as
"clear this field"; datetime-local values become ISO instants in the user's
zone. Errors from the API land in a form-level `<FormError>`.

### Tables: TanStack Table v9

`src/components/shared/data-table.tsx` registers only sorting and pagination with
`tableFeatures()` (v9 is tree-shakeable) and exports a column helper typed
with those features. Both are the API's job: every list answers with a page
and a `total`, the table holds one page (50 rows) in manual mode, and a
header or pager click asks the owner for another. `useListState` keeps the
page and sort; the list pages put them in the URL next to the filters
(`?page=3&sort=company&order=desc`), so a link opens the same view and the
server prefetches the same page. Changing a filter goes back to page 1.

Lists that show everything at once (the activity feed, attachments, the task
card on a detail page) ask for the API's largest page, 500 rows, and say
"Showing 500 of N" when there was more.

The contact and company pickers in forms are a searchable combobox
(`src/components/entity-combobox.tsx`, on shadcn's Base UI combobox). The
API does the matching: each pause in typing fetches the first 20 matches by
name, the popup says how many more there were, and a value the form already
holds (an edit, or `?company_id=` on the new-contact page) shows its name
from the record or from a fetch of its own. `ComboboxField` in
`src/components/shared/form/fields.tsx` binds it to a form field whose value is the
id, or `""` for none.

### Time zones

"Today" depends on where the user is. `<TimeZoneSync>` writes the browser's
zone to a `tz` cookie on first visit and refreshes; the server reads it for the
API's `tz` parameter and passes it to every component that formats a date, so
server and client render the same text. Until the cookie exists, UTC.

## React Compiler

`reactCompiler` is on. Write plain React and let the compiler memoize; use
`useMemo`/`useCallback` only where you need precise control, such as a stable
value for an effect dependency. Opt a component out with `"use no memo"` if the
compiler mishandles it.

## Generated files

`next dev`, `next build`, and `vp run typegen` write `next-env.d.ts` and
`.next/types/` (route types for `typedRoutes`, `PageProps`, `LayoutProps`).
Both are gitignored, as the Next.js docs ask; `tsconfig.json` includes them when
present and `vp check` passes without them.
