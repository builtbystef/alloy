"use client";

import type { Permission, WorkspaceRead } from "@alloy/api-client";
import { createContext, Suspense, use, type ReactNode } from "react";

import { workspacePaths, type WorkspacePaths } from "./routes";

/**
 * The current workspace, for Client Components. The layout passes the promise
 * from `requireWorkspace()` without awaiting it, so the static shell stays
 * static; each consumer suspends on its own, inside the page's <Suspense>.
 */
const WorkspaceContext = createContext<Promise<WorkspaceRead> | null>(null);

export function WorkspaceProvider({
  workspace,
  children,
}: {
  workspace: Promise<WorkspaceRead>;
  children: ReactNode;
}) {
  return <WorkspaceContext value={workspace}>{children}</WorkspaceContext>;
}

export function useWorkspace(): WorkspaceRead & { paths: WorkspacePaths } {
  const promise = use(WorkspaceContext);
  if (promise === null) throw new Error("useWorkspace() needs a <WorkspaceProvider> above it.");
  const workspace = use(promise);
  return { ...workspace, paths: workspacePaths(workspace.id) };
}

export function useCan(permission: Permission): boolean {
  return useWorkspace().permissions.includes(permission);
}

/**
 * Renders `children` only when the caller's role has `permission`. The API is
 * the real check; this only keeps buttons the request would reject out of view.
 */
export function Can({
  permission,
  children,
  fallback = null,
}: {
  permission: Permission;
  children: ReactNode;
  fallback?: ReactNode;
}) {
  return (
    <Suspense fallback={fallback}>
      <CanContent permission={permission} fallback={fallback}>
        {children}
      </CanContent>
    </Suspense>
  );
}

function CanContent({
  permission,
  children,
  fallback,
}: {
  permission: Permission;
  children: ReactNode;
  fallback: ReactNode;
}) {
  return useCan(permission) ? children : fallback;
}
