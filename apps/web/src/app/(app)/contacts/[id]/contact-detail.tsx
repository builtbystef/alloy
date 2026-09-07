"use client";

import { useSuspenseQuery } from "@tanstack/react-query";
import { BuildingIcon, MailIcon, PencilIcon, PhoneIcon, Trash2Icon } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import type { ReactNode } from "react";

import { PageHeader } from "@/components/page-header";
import { ContactStatusBadge } from "@/components/status-badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { browserApi } from "@/lib/api-browser";
import { formatDateTime, formatRelativeDays } from "@/lib/dates";
import { contactQuery } from "@/lib/queries";

import { TaskList } from "../../tasks/task-list";
import { useDeleteContact } from "../use-delete-contact";
import { ActivityFeed } from "./activity-feed";

export function ContactDetail({ id, timeZone }: { id: string; timeZone: string }) {
  const router = useRouter();
  const { data: contact } = useSuspenseQuery(contactQuery(browserApi, id));
  const { confirmDelete, dialog } = useDeleteContact({ onDeleted: () => router.push("/contacts") });

  return (
    <>
      <PageHeader
        title={
          <span className="flex flex-wrap items-center gap-3">
            {contact.name}
            <ContactStatusBadge status={contact.status} />
          </span>
        }
        description={
          <>
            {contact.job_title}
            {contact.job_title && contact.company && " at "}
            {contact.company && (
              <Link href={`/companies/${contact.company.id}`} className="hover:underline">
                {contact.company.name}
              </Link>
            )}
          </>
        }
      >
        <Button
          variant="outline"
          nativeButton={false}
          render={<Link href={`/contacts/${contact.id}/edit`} />}
        >
          <PencilIcon /> Edit
        </Button>
        <Button variant="destructive" onClick={() => confirmDelete(contact)}>
          <Trash2Icon /> Delete
        </Button>
      </PageHeader>

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="flex flex-col gap-6">
          <Card>
            <CardHeader>
              <CardTitle>Details</CardTitle>
            </CardHeader>
            <CardContent>
              <dl className="flex flex-col gap-3 text-sm">
                <Detail icon={<MailIcon />} label="Email">
                  {contact.email ? (
                    <a href={`mailto:${contact.email}`} className="hover:underline">
                      {contact.email}
                    </a>
                  ) : null}
                </Detail>
                <Detail icon={<PhoneIcon />} label="Phone">
                  {contact.phone ? (
                    <a href={`tel:${contact.phone}`} className="hover:underline">
                      {contact.phone}
                    </a>
                  ) : null}
                </Detail>
                <Detail icon={<BuildingIcon />} label="Company">
                  {contact.company ? (
                    <Link href={`/companies/${contact.company.id}`} className="hover:underline">
                      {contact.company.name}
                    </Link>
                  ) : null}
                </Detail>
                <Detail label="Last contacted">
                  {contact.last_contacted_at ? (
                    <span title={formatDateTime(contact.last_contacted_at, timeZone)}>
                      {formatRelativeDays(contact.last_contacted_at, timeZone)}
                    </span>
                  ) : null}
                </Detail>
                <Detail label="Added">{formatDateTime(contact.created_at, timeZone)}</Detail>
              </dl>
            </CardContent>
          </Card>
          <TaskList timeZone={timeZone} contact={contact} />
        </div>
        <div className="lg:col-span-2">
          <ActivityFeed contactId={contact.id} timeZone={timeZone} />
        </div>
      </div>
      {dialog}
    </>
  );
}

function Detail({
  icon,
  label,
  children,
}: {
  icon?: ReactNode;
  label: string;
  children: ReactNode;
}) {
  return (
    <div className="grid grid-cols-[7rem_1fr] items-start gap-2">
      <dt className="flex items-center gap-1.5 text-muted-foreground [&_svg]:size-3.5">
        {icon}
        {label}
      </dt>
      <dd className="min-w-0 break-words">
        {children || <span className="text-muted-foreground">–</span>}
      </dd>
    </div>
  );
}
