# @alloy/web

The Next.js front end for `apps/api`.

```sh
vp run dev:web      # from the repo root, http://localhost:3000
vp run dev:api      # the API it talks to, in another terminal
```

```text
apps/web/
├── next.config.ts        # cacheComponents, typedRoutes, reactCompiler
├── postcss.config.mjs    # @tailwindcss/postcss
├── components.json       # shadcn/ui: style, base color, aliases
├── tsconfig.json         # extends tsconfig/browser.json with what Next.js needs
├── .env.example          # API_URL, copy to .env.local
└── src/
    ├── app/
    │   ├── layout.tsx    # root layout, loads the Geist font
    │   ├── page.tsx      # /, static shell with <ApiStatus> behind <Suspense>
    │   ├── api-status.tsx
    │   └── globals.css   # Tailwind import, shadcn theme tokens
    ├── components/ui/    # shadcn/ui components, owned by this repo
    └── lib/
        ├── api.ts        # the @alloy/api-client instance, baseUrl from API_URL
        ├── api.test.ts
        └── utils.ts      # cn(), re-exported from the cn package
```

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
