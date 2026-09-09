"use client";

import type { CompanyRead } from "@alloy/api-client";
import { useSuspenseQuery } from "@tanstack/react-query";
import { SearchIcon } from "lucide-react";
import { useState } from "react";

import { DataTable } from "@/components/data-table";
import { Input } from "@/components/ui/input";
import { browserApi } from "@/lib/api-browser";
import { companyListQuery, paged } from "@/lib/queries";
import { parseCompanySearch, type CompanySearch } from "@/lib/schemas";
import { useDebouncedValue } from "@/lib/use-debounced-value";
import { useListState } from "@/lib/use-list-state";
import { useUrlFilters } from "@/lib/use-url-filters";
import { cn } from "@/lib/utils";
import { useCan, useWorkspace } from "@/lib/workspace";

import { companyColumns } from "./company-columns";
import { useDeleteCompany } from "./use-delete-company";

export function CompaniesTable({
  initialFilters,
  timeZone,
}: {
  initialFilters: CompanySearch;
  timeZone: string;
}) {
  const [search, setSearch] = useState(initialFilters.q ?? "");
  const q = useDebouncedValue(search.trim(), 300);
  const list = useListState({
    filterKey: q,
    initial: initialFilters,
    defaultSort: { sort: "name", order: "asc" },
  });
  const { deferred, isStale } = useUrlFilters(
    { q: q || undefined, ...list.search },
    parseCompanySearch,
  );

  const { id: workspaceId, paths } = useWorkspace();
  const canWrite = useCan("crm:write");
  const { data: companies } = useSuspenseQuery(
    companyListQuery(browserApi, workspaceId, paged(deferred)),
  );
  const { confirmDelete, dialog } = useDeleteCompany();

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center gap-2">
        <div className="relative w-full max-w-xs">
          <SearchIcon className="pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            type="search"
            placeholder="Search name, website, industry"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            className="pl-8"
            aria-label="Search companies"
          />
        </div>
        <span className="ml-auto text-sm text-muted-foreground">
          {companies.total} {companies.total === 1 ? "company" : "companies"}
        </span>
      </div>
      <DataTable<CompanyRead>
        columns={companyColumns({ timeZone, paths, onDelete: canWrite ? confirmDelete : null })}
        data={companies.items}
        total={companies.total}
        page={list.page}
        onPageChange={list.setPage}
        sorting={list.sorting}
        onSortingChange={list.setSorting}
        emptyMessage={
          deferred.q ? "No companies match this search." : "No companies yet. Add your first one."
        }
        className={cn(isStale && "opacity-60 transition-opacity")}
      />
      {dialog}
    </div>
  );
}
