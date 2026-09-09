# @alloy/web

The Next.js front end for `apps/api`.

```sh
vp run dev:web      # from the repo root, http://localhost:3000
vp run dev:api      # the API it talks to, in another terminal
```

```text
apps/web/
├── next.config.ts        # cacheComponents, typedRoutes, reactCompiler, skipTrailingSlashRedirect
├── postcss.config.mjs    # @tailwindcss/postcss
├── components.json       # shadcn/ui: style, base color, aliases
├── tsconfig.json         # extends tsconfig/browser.json with what Next.js needs
├── .env.example          # API_URL, copy to .env.local
└── src/
    ├── proxy.ts          # no cookie → /login?next=…; cookie on /login → /
    ├── app/
    │   ├── layout.tsx    # root layout: Geist font, <Providers>
    │   ├── providers.tsx # QueryClientProvider, next-themes, sonner <Toaster>
    │   ├── globals.css   # Tailwind import, shadcn theme tokens
    │   ├── icon.svg, favicon.ico, apple-icon.png   # the logo, in the formats browsers ask for
    │   ├── api/[...path]/route.ts   # the proxy to the API; forwards the visitor's address
    │   ├── (auth)/       # centered layout with the logo; login and signup share auth-form.tsx; verify-email/, forgot-password/, reset-password/, confirm-email/ follow emailed links; invites/[token]/ accepts an invitation
    │   └── (app)/
    │       ├── page.tsx              # `/`: opens the last-used (cookie) or first workspace; offers to create one if none
    │       ├── workspace-form.tsx    # create a workspace (first sign-in and the switcher's dialog)
    │       └── [workspaceId]/        # app layout (sidebar: workspace switcher, nav, user menu; <WorkspaceProvider>), error.tsx, not-found.tsx
    │           ├── page.tsx          # dashboard (Server Component only)
    │           ├── contacts/         # page, contacts-table, contact-columns, contact-form, [id]/ (detail, activity feed), new/, [id]/edit/
    │           ├── companies/        # same shape as contacts
    │           ├── tasks/            # page, tasks-table, task-dialog + task-form, task-list (used on detail pages)
    │           ├── imports/          # CSV import card (kind, file, upload progress), history table polling while a job runs, details dialog
    │           ├── members/          # members table (roles, remove), invitations card (invite, revoke)
    │           ├── settings/         # rename, leave, delete the workspace
    │           └── account/          # change email or password, log out everywhere, delete the account
    ├── components/
    │   ├── ui/           # shadcn/ui components, owned by this repo
    │   ├── form/         # useAppForm + TextField, TextareaField, SelectField, DateTimeField, SubmitButton
    │   ├── data-table.tsx, confirm-dialog.tsx, page-header.tsx, status-badge.tsx, skeletons.tsx
    │   └── logo.tsx, time-zone-sync.tsx, remember-workspace.tsx
    └── lib/
        ├── api.ts        # createApi(): the @alloy/api-client instance, baseUrl from API_URL
        ├── session.ts    # server-only: getSessionApi(), getCurrentUser(), requireUser(), listWorkspaces(), requireWorkspace()
        ├── workspace.tsx # client: <WorkspaceProvider>, useWorkspace(), useCan(), <Can permission>
        ├── routes.ts     # workspacePaths(id): every href under /{workspaceId}
        ├── api-browser.ts# browserApi: the same client pointed at /api
        ├── api-error.ts  # ApiError, unwrap(), errorMessage()
        ├── queries.ts    # queryOptions() factories and keys; invalidateCrm()
        ├── query-client.ts
        ├── schemas.ts    # Zod: form schemas (input → request body) and URL search params
        ├── dates.ts      # ISO ⇄ datetime-local in a zone; relative days
        ├── time-zone.ts  # server-only: the zone from the `tz` cookie
        └── labels.ts, use-url-filters.ts, use-debounced-value.ts, utils.ts
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
`<RememberWorkspace>` writes on every visit, else the first. Invitation links
(`/invites/{token}`) preview without a login; the proxy sends logged-out
visitors to `/login?next=…`, and the auth form keeps `next` across the
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
rate limits (from `CF-Connecting-IP`, `X-Real-IP`, or the last entry of the
incoming `X-Forwarded-For`, whichever the platform in front sets).
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
import { browserApi } from "@/lib/api-browser";
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

Query definitions in `src/lib/queries.ts` take the client as a parameter so
both sides build identical keys. Mutations use `useMutation` and call
`invalidateCrm()`, which drops every CRM query: the entities reference each
other (a task embeds its contact, completing one logs an activity), so a
broad invalidation is simpler than encoding those rules.

List filters live in the URL. A filter change updates the address bar with
`history.replaceState` (no server round trip) and the previous rows stay
visible through `useDeferredValue` while the next query loads; a real
navigation (back/forward) remounts the table with the new URL, and the server
prefetches whatever the URL says.

### Forms: Zod + TanStack Form + shadcn Field

`src/components/form` binds TanStack Form to the shadcn `Field` components
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

The Zod schemas in `src/lib/schemas.ts` take what inputs hold (strings) and
produce the API's request body: `""` becomes `null`, which a PATCH treats as
"clear this field"; datetime-local values become ISO instants in the user's
zone. Errors from the API land in a form-level `<FormError>`.

### Tables: TanStack Table v9

`src/components/data-table.tsx` registers only sorting and pagination with
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
`src/components/form/fields.tsx` binds it to a form field whose value is the
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
