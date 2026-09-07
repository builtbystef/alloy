# @alloy/web

The Next.js front end for `apps/api`.

```sh
vp run dev:web      # from the repo root, http://localhost:3000
vp run dev:api      # the API it talks to, in another terminal
```

```text
apps/web/
├── next.config.ts        # cacheComponents, typedRoutes, reactCompiler
├── tsconfig.json         # extends tsconfig/browser.json with what Next.js needs
├── .env.example          # API_URL, copy to .env.local
└── src/
    ├── app/
    │   ├── layout.tsx    # root layout, required
    │   ├── page.tsx      # /, static shell with <ApiStatus> behind <Suspense>
    │   ├── api-status.tsx
    │   └── globals.css
    └── lib/
        ├── api.ts        # the @alloy/api-client instance, baseUrl from API_URL
        └── api.test.ts
```

## Calling the API

`src/lib/api.ts` exports `api`, a client from `@alloy/api-client` typed against
the FastAPI OpenAPI schema. Use it in Server Components, Route Handlers, and
Server Actions:

```tsx
import { api } from "@/lib/api";

async function ApiStatus() {
  const { data } = await api.GET("/health/"); // data: { status: string } | undefined
  return <p>{data?.status}</p>;
}
```

`API_URL` is read on the server and not prefixed `NEXT_PUBLIC_`, so it is never
inlined into the browser bundle; one build can be pointed at different APIs per
environment. The browser only talks to Next.js.

With `cacheComponents` on, every route prerenders a static shell. A component
that reads uncached data (like `ApiStatus`) must sit inside `<Suspense>` so its
fallback ships in the shell and the data streams in at request time, or use the
`"use cache"` directive with a `cacheLife` to be included in the shell. The dev
overlay flags a component that does neither.

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
