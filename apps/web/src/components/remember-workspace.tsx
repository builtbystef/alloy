"use client";

import { useEffect } from "react";

import { WORKSPACE_COOKIE } from "@/lib/workspace-shared";

/** Writes the open workspace to a cookie so `/` returns to it next time. */
export function RememberWorkspace({ workspaceId }: { workspaceId: string }) {
  useEffect(() => {
    const oneYear = 60 * 60 * 24 * 365;
    document.cookie = `${WORKSPACE_COOKIE}=${workspaceId}; Path=/; Max-Age=${oneYear}; SameSite=Lax`;
  }, [workspaceId]);
  return null;
}
