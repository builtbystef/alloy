"use client";

import { useParams, usePathname } from "next/navigation";

/**
 * The title of the current page, shown in the shell header. It is derived from
 * the URL, which is only known at request time, so it streams in behind a
 * <Suspense> while the rest of the shell is prerendered.
 */
export function PageTitle() {
  const pathname = usePathname();
  const { workspaceId } = useParams<{ workspaceId: string }>();
  const title = titleFor(pathname, workspaceId);
  return title ? <h1 className="truncate text-sm font-medium">{title}</h1> : null;
}

export function titleFor(pathname: string, workspaceId: string | undefined): string | null {
  const base = `/${workspaceId}`;
  if (!workspaceId || (pathname !== base && !pathname.startsWith(`${base}/`))) return null;
  const segments = pathname.slice(base.length).split("/").filter(Boolean);
  const [section, id, action] = segments;
  switch (section) {
    case undefined:
      return "Dashboard";
    case "contacts":
      if (!id) return "Contacts";
      if (id === "new") return "New contact";
      return action === "edit" ? "Edit contact" : "Contact";
    case "companies":
      if (!id) return "Companies";
      if (id === "new") return "New company";
      return action === "edit" ? "Edit company" : "Company";
    case "tasks":
      return "Tasks";
    case "assistant":
      return "Assistant";
    case "imports":
      return "Imports";
    case "settings":
      return "Workspace settings";
    case "account":
      return "Settings";
    default:
      return null;
  }
}
