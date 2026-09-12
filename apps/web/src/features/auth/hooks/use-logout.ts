"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import type { Route } from "next";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { logout } from "@/features/auth/mutations";
import { errorMessage } from "@/lib/api/errors";

/**
 * End the session and go to the login page (or `to`). Cached queries belong
 * to the account, so they are dropped; the refresh lets Server Components
 * see the cleared cookie.
 */
export function useLogout({
  to = "/login",
  onError = (error) => toast.error(errorMessage(error)),
}: {
  to?: Route;
  onError?: (error: Error) => void;
} = {}) {
  const router = useRouter();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: logout,
    onSuccess: () => {
      queryClient.clear();
      router.push(to);
      router.refresh();
    },
    onError,
  });
}
