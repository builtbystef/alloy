"use client";

import { useSuspenseQuery } from "@tanstack/react-query";
import { BuildingIcon, MailIcon, PencilIcon, PhoneIcon, Trash2Icon } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Detail } from "@/components/shared/detail-list";
import { PageHeader } from "@/components/shared/layout/page-header";
import { ContactStatusBadge } from "@/features/crm/contacts/components/contact-status-badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { browserApi } from "@/lib/api/client";
import { formatDateTime, formatRelativeDays } from "@/lib/formatting/dates";
import { contactQuery } from "@/features/crm/contacts/queries";
import { useCan, useWorkspace } from "@/features/workspaces/workspace-provider";

import { AttachmentsCard } from "@/features/crm/attachments/components/attachments-card";
import { TaskList } from "@/features/crm/tasks/components/task-list";
import { useDeleteContact } from "@/features/crm/contacts/hooks/use-delete-contact";
import { ActivityFeed } from "./activity-feed";

export function ContactDetail({ id, timeZone }: { id: string; timeZone: string }) {
  const router = useRouter();
  const { id: workspaceId, paths } = useWorkspace();
  const canWrite = useCan("crm:write");
  const { data: contact } = useSuspenseQuery(contactQuery(browserApi, workspaceId, id));
  const { confirmDelete, dialog } = useDeleteContact({
    onDeleted: () => router.push(paths.contacts),
  });

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
              <Link href={paths.company(contact.company.id)} className="hover:underline">
                {contact.company.name}
              </Link>
            )}
          </>
        }
      >
        {canWrite && (
          <>
            <Button
              variant="outline"
              nativeButton={false}
              render={<Link href={paths.contactEdit(contact.id)} />}
            >
              <PencilIcon /> Edit
            </Button>
            <Button variant="destructive" onClick={() => confirmDelete(contact)}>
              <Trash2Icon /> Delete
            </Button>
          </>
        )}
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
                    <Link href={paths.company(contact.company.id)} className="hover:underline">
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
                <Detail label="Added">
                  {formatDateTime(contact.created_at, timeZone)}
                  {contact.created_by && (
                    <span className="text-muted-foreground"> by {contact.created_by.email}</span>
                  )}
                </Detail>
              </dl>
            </CardContent>
          </Card>
          <TaskList timeZone={timeZone} contact={contact} />
        </div>
        <div className="flex flex-col gap-6 lg:col-span-2">
          <ActivityFeed contactId={contact.id} timeZone={timeZone} />
          <AttachmentsCard parent={{ contactId: contact.id }} timeZone={timeZone} />
        </div>
      </div>
      {dialog}
    </>
  );
}
