/**
 * Every app page lives under `/{workspaceId}`. These helpers build those hrefs
 * in one place, typed as template literals so `typedRoutes` can check them.
 */
export function workspacePaths(workspaceId: string) {
  const base = `/${workspaceId}` as const;
  return {
    home: base,
    contacts: `${base}/contacts` as const,
    contact: (id: string) => `${base}/contacts/${id}` as const,
    contactEdit: (id: string) => `${base}/contacts/${id}/edit` as const,
    contactNew: `${base}/contacts/new` as const,
    companies: `${base}/companies` as const,
    company: (id: string) => `${base}/companies/${id}` as const,
    companyEdit: (id: string) => `${base}/companies/${id}/edit` as const,
    companyNew: `${base}/companies/new` as const,
    tasks: `${base}/tasks` as const,
    task: (id: string) => `${base}/tasks/${id}` as const,
    taskEdit: (id: string) => `${base}/tasks/${id}/edit` as const,
    taskNew: `${base}/tasks/new` as const,
    assistant: `${base}/assistant` as const,
    assistantChat: (id: string) => `${base}/assistant/${id}` as const,
    imports: `${base}/imports` as const,
    onboarding: `${base}/onboarding` as const,
    settings: `${base}/settings` as const,
    members: `${base}/settings/members` as const,
    account: `${base}/account` as const,
  };
}

export type WorkspacePaths = ReturnType<typeof workspacePaths>;

/** `/invites/{token}`, as opposed to the `/invites` list. */
export function isInviteLink(pathname: string): boolean {
  return pathname.startsWith("/invites/") && pathname.length > "/invites/".length;
}

/**
 * A `?next=` value as a path on this site, or "/" when it is anything else.
 * "//evil.com" and "/\evil.com" are protocol-relative URLs to a browser, so a
 * leading slash alone is not enough.
 */
export function safeNextPath(next: string | null | undefined): string {
  if (!next || !next.startsWith("/") || next.startsWith("//") || next.startsWith("/\\")) {
    return "/";
  }
  return next;
}
