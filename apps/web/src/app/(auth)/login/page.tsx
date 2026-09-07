import type { Metadata } from "next";
import { Suspense } from "react";

import { AuthForm } from "../auth-form";

export const metadata: Metadata = { title: "Log in" };

export default function LoginPage() {
  return (
    // useSearchParams() in the form reads the `next` parameter at request time.
    <Suspense>
      <AuthForm mode="login" />
    </Suspense>
  );
}
