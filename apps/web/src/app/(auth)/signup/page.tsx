import type { Metadata } from "next";
import { Suspense } from "react";

import { AuthForm } from "@/features/auth/components/auth-form";

export const metadata: Metadata = { title: "Sign up" };

export default function SignupPage() {
  return (
    <Suspense>
      <AuthForm mode="signup" />
    </Suspense>
  );
}
