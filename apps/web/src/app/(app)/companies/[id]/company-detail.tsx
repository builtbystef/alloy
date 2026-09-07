"use client";

import type { ContactRead } from "@alloy/api-client";
import { useSuspenseQuery } from "@tanstack/react-query";
import { ExternalLinkIcon, PencilIcon, PlusIcon, Trash2Icon } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { DataTable } from "@/components/data-table";
import { PageHeader } from "@/components/page-header";
import { Button } from "@/components/ui/button";
import { Card, CardAction, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { browserApi } from "@/lib/api-browser";
import { formatDateTime } from "@/lib/dates";
import { companyContactsQuery, companyQuery } from "@/lib/queries";

import { contactColumns } from "../../contacts/contact-columns";
import { useDeleteContact } from "../../contacts/use-delete-contact";
import { TaskList } from "../../tasks/task-list";
import { websiteLabel } from "../company-columns";
import { useDeleteCompany } from "../use-delete-company";

export function CompanyDetail({ id, timeZone }: { id: string; timeZone: string }) {
  const router = useRouter();
  const { data: company } = useSuspenseQuery(companyQuery(browserApi, id));
  const { data: contacts } = useSuspenseQuery(companyContactsQuery(browserApi, id));
  const deleteCompany = useDeleteCompany({ onDeleted: () => router.push("/companies") });
  const deleteContact = useDeleteContact();

  return (
    <>
      <PageHeader
        title={company.name}
        description={
          <span className="flex flex-wrap items-center gap-x-3">
            {company.industry}
            {company.website && (
              <a
                href={company.website}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1 hover:underline"
              >
                {websiteLabel(company.website)}
                <ExternalLinkIcon className="size-3" />
              </a>
            )}
            <span>Added {formatDateTime(company.created_at, timeZone)}</span>
          </span>
        }
      >
        <Button
          variant="outline"
          nativeButton={false}
          render={<Link href={`/companies/${company.id}/edit`} />}
        >
          <PencilIcon /> Edit
        </Button>
        <Button variant="destructive" onClick={() => deleteCompany.confirmDelete(company)}>
          <Trash2Icon /> Delete
        </Button>
      </PageHeader>

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="flex flex-col gap-6 lg:col-span-2">
          <Card>
            <CardHeader>
              <CardTitle>Contacts</CardTitle>
              <CardAction>
                <Button
                  variant="outline"
                  size="sm"
                  render={<Link href={`/contacts/new?company_id=${company.id}`} />}
                >
                  <PlusIcon /> Add contact
                </Button>
              </CardAction>
            </CardHeader>
            <CardContent>
              <DataTable<ContactRead>
                columns={contactColumns({
                  timeZone,
                  onDelete: deleteContact.confirmDelete,
                  showCompany: false,
                })}
                data={contacts}
                initialSorting={[{ id: "name", desc: false }]}
                emptyMessage="No contacts at this company yet."
              />
            </CardContent>
          </Card>
          {company.notes && (
            <Card>
              <CardHeader>
                <CardTitle>Notes</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm whitespace-pre-wrap">{company.notes}</p>
              </CardContent>
            </Card>
          )}
        </div>
        <TaskList timeZone={timeZone} company={company} />
      </div>
      {deleteCompany.dialog}
      {deleteContact.dialog}
    </>
  );
}
