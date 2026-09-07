"use client";

import type { ContactRead, ContactStatus } from "@alloy/api-client";
import { useSuspenseQuery } from "@tanstack/react-query";
import { SearchIcon } from "lucide-react";
import { useState } from "react";

import { DataTable } from "@/components/data-table";
import { Input } from "@/components/ui/input";
import { NativeSelect, NativeSelectOption } from "@/components/ui/native-select";
import { browserApi } from "@/lib/api-browser";
import { contactStatusLabels } from "@/lib/labels";
import { contactListQuery } from "@/lib/queries";
import { contactStatuses, parseContactSearch, type ContactSearch } from "@/lib/schemas";
import { useDebouncedValue } from "@/lib/use-debounced-value";
import { useUrlFilters } from "@/lib/use-url-filters";
import { cn } from "@/lib/utils";
import { useCan, useWorkspace } from "@/lib/workspace";

import { contactColumns } from "./contact-columns";
import { useDeleteContact } from "./use-delete-contact";

export function ContactsTable({
  initialFilters,
  timeZone,
}: {
  initialFilters: ContactSearch;
  timeZone: string;
}) {
  const [search, setSearch] = useState(initialFilters.q ?? "");
  const [status, setStatus] = useState<ContactStatus | "">(initialFilters.status ?? "");
  const q = useDebouncedValue(search.trim(), 300);
  const { deferred, isStale } = useUrlFilters(
    { ...initialFilters, q: q || undefined, status: status || undefined },
    parseContactSearch,
  );

  const { id: workspaceId, paths } = useWorkspace();
  const canWrite = useCan("crm:write");
  const { data: contacts } = useSuspenseQuery(contactListQuery(browserApi, workspaceId, deferred));
  const { confirmDelete, dialog } = useDeleteContact();

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center gap-2">
        <div className="relative w-full max-w-xs">
          <SearchIcon className="pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            type="search"
            placeholder="Search name, email, phone, company"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            className="pl-8"
            aria-label="Search contacts"
          />
        </div>
        <NativeSelect
          value={status}
          onChange={(event) => setStatus(event.target.value as ContactStatus | "")}
          aria-label="Filter by status"
        >
          <NativeSelectOption value="">All statuses</NativeSelectOption>
          {contactStatuses.map((value) => (
            <NativeSelectOption key={value} value={value}>
              {contactStatusLabels[value]}
            </NativeSelectOption>
          ))}
        </NativeSelect>
        <span className="ml-auto text-sm text-muted-foreground">
          {contacts.length} {contacts.length === 1 ? "contact" : "contacts"}
        </span>
      </div>
      <DataTable<ContactRead>
        columns={contactColumns({ timeZone, paths, onDelete: canWrite ? confirmDelete : null })}
        data={contacts}
        initialSorting={[{ id: "name", desc: false }]}
        emptyMessage={
          deferred.q || deferred.status
            ? "No contacts match these filters."
            : "No contacts yet. Add your first one."
        }
        className={cn(isStale && "opacity-60 transition-opacity")}
      />
      {dialog}
    </div>
  );
}
