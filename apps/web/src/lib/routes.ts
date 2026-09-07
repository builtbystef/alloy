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
    members: `${base}/members` as const,
    settings: `${base}/settings` as const,
    account: `${base}/account` as const,
  };
}

export type WorkspacePaths = ReturnType<typeof workspacePaths>;
