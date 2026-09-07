import type { ContactRead } from "@alloy/api-client";
import { AlertTriangleIcon, CalendarClockIcon, UsersIcon } from "lucide-react";
import type { Metadata } from "next";
import Link from "next/link";
import { Suspense, type ReactNode } from "react";

import { PageHeader } from "@/components/page-header";
import { ContactStatusBadge } from "@/components/status-badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { unwrap } from "@/lib/api-error";
import { formatRelativeDays } from "@/lib/dates";
import { requireUser, getSessionApi } from "@/lib/session";
import { getTimeZone } from "@/lib/time-zone";

export const metadata: Metadata = { title: "Dashboard" };

/**
 * Read-only, so a Server Component is all it takes: no client bundle, no
 * query cache. The data component sits behind <Suspense> because it reads
 * the session cookie.
 */
export default function DashboardPage() {
  return (
    <>
      <PageHeader title="Dashboard" description="What needs your attention today." />
      <Suspense fallback={<DashboardSkeleton />}>
        <DashboardContent />
      </Suspense>
    </>
  );
}

async function DashboardContent() {
  await requireUser();
  const [api, tz] = await Promise.all([getSessionApi(), getTimeZone()]);
  const dashboard = unwrap(await api.GET("/dashboard/", { params: { query: { tz } } }));

  return (
    <div className="flex flex-col gap-6">
      <div className="grid gap-4 sm:grid-cols-3">
        <StatCard
          title="Contacts"
          value={dashboard.total_contacts}
          icon={<UsersIcon />}
          href="/contacts"
        />
        <StatCard
          title="Due today"
          value={dashboard.tasks_due_today}
          icon={<CalendarClockIcon />}
          href="/tasks?due=today&status=open"
        />
        <StatCard
          title="Overdue"
          value={dashboard.overdue_tasks}
          icon={<AlertTriangleIcon />}
          href="/tasks?due=overdue&status=open"
          alert={dashboard.overdue_tasks > 0}
        />
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        <ContactList
          title="Recently contacted"
          description="Your most recent conversations."
          contacts={dashboard.recently_contacted}
          timeZone={tz}
          empty="Log a call, email, or meeting on a contact and it shows up here."
        />
        <ContactList
          title="Needs attention"
          description="Not contacted in the last 30 days, or ever."
          contacts={dashboard.not_recently_contacted}
          timeZone={tz}
          empty="Everyone has been contacted recently."
        />
      </div>
    </div>
  );
}

function StatCard({
  title,
  value,
  icon,
  href,
  alert = false,
}: {
  title: string;
  value: number;
  icon: ReactNode;
  href: "/contacts" | `/tasks?${string}`;
  alert?: boolean;
}) {
  return (
    <Link
      href={href}
      className="rounded-xl outline-none focus-visible:ring-3 focus-visible:ring-ring/50"
    >
      <Card className="h-full transition-colors hover:bg-muted/50">
        <CardHeader>
          <CardDescription className="flex items-center gap-2 [&_svg]:size-4">
            {icon}
            {title}
          </CardDescription>
          <CardTitle
            className={alert ? "text-3xl font-semibold text-destructive" : "text-3xl font-semibold"}
          >
            {value}
          </CardTitle>
        </CardHeader>
      </Card>
    </Link>
  );
}

function ContactList({
  title,
  description,
  contacts,
  timeZone,
  empty,
}: {
  title: string;
  description: string;
  contacts: ContactRead[];
  timeZone: string;
  empty: string;
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent>
        {contacts.length === 0 ? (
          <p className="text-sm text-muted-foreground">{empty}</p>
        ) : (
          <ul className="divide-y">
            {contacts.map((contact) => (
              <li
                key={contact.id}
                className="flex items-center justify-between gap-3 py-2 first:pt-0 last:pb-0"
              >
                <div className="min-w-0">
                  <Link href={`/contacts/${contact.id}`} className="font-medium hover:underline">
                    {contact.name}
                  </Link>
                  <p className="truncate text-sm text-muted-foreground">
                    {contact.company?.name ?? contact.email ?? "No company"}
                  </p>
                </div>
                <div className="flex shrink-0 items-center gap-2 text-sm text-muted-foreground">
                  <span>
                    {contact.last_contacted_at
                      ? formatRelativeDays(contact.last_contacted_at, timeZone)
                      : "Never contacted"}
                  </span>
                  <ContactStatusBadge status={contact.status} />
                </div>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}

function DashboardSkeleton() {
  return (
    <div className="flex flex-col gap-6">
      <div className="grid gap-4 sm:grid-cols-3">
        {Array.from({ length: 3 }, (_, i) => (
          <Skeleton key={i} className="h-28" />
        ))}
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        <Skeleton className="h-64" />
        <Skeleton className="h-64" />
      </div>
    </div>
  );
}
