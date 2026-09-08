"use client";

import type { ImportKind } from "@alloy/api-client";
import { FileUpIcon, Loader2Icon, XIcon } from "lucide-react";
import { useId, useRef, useState, type DragEvent } from "react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { NativeSelect, NativeSelectOption } from "@/components/ui/native-select";
import { IMPORT_MAX_BYTES, formatBytes } from "@/lib/bytes";
import { importKindLabels } from "@/lib/labels";
import { importKinds } from "@/lib/schemas";
import { cn } from "@/lib/utils";

import { useImportUpload } from "./use-import-upload";

/** The columns `crm/importing.py` reads; anything else in the file is ignored. */
const columns: Record<ImportKind, string> = {
  contacts: "name, email, phone, job_title, status, company",
  companies: "name, website, industry, notes",
};

export function ImportCard({ initialKind }: { initialKind: ImportKind }) {
  const [kind, setKind] = useState<ImportKind>(initialKind);
  const [file, setFile] = useState<File | null>(null);
  const [dragging, setDragging] = useState(false);
  const input = useRef<HTMLInputElement>(null);
  const kindId = useId();
  const { start, fraction } = useImportUpload();
  const busy = fraction !== null;

  const choose = (files: FileList | null) => {
    const chosen = files?.[0];
    if (chosen) setFile(chosen);
  };

  const submit = () => {
    if (!file || busy) return;
    start(kind, file);
    setFile(null);
  };

  return (
    <Card
      className={cn(dragging && "ring-2 ring-ring/50")}
      onDragOver={(event: DragEvent) => {
        if (busy) return;
        event.preventDefault();
        setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={(event: DragEvent) => {
        event.preventDefault();
        setDragging(false);
        if (!busy) choose(event.dataTransfer.files);
      }}
    >
      <CardHeader>
        <CardTitle>Import a CSV</CardTitle>
        <CardDescription>
          UTF-8 with a header row, up to {formatBytes(IMPORT_MAX_BYTES)}. Column names are matched
          case-insensitively; the header must include <code>name</code>.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <div className="grid gap-4 sm:grid-cols-[auto_1fr] sm:items-end">
          <div className="flex flex-col gap-2">
            <Label htmlFor={kindId}>What the rows are</Label>
            <NativeSelect
              id={kindId}
              value={kind}
              disabled={busy}
              onChange={(event) => setKind(event.target.value as ImportKind)}
            >
              {importKinds.map((value) => (
                <NativeSelectOption key={value} value={value}>
                  {importKindLabels[value]}
                </NativeSelectOption>
              ))}
            </NativeSelect>
          </div>
          <div className="flex flex-col gap-2">
            <span className="text-sm leading-none font-medium">File</span>
            <input
              ref={input}
              type="file"
              accept=".csv,text/csv"
              className="sr-only"
              aria-label="Choose a CSV file"
              onChange={(event) => {
                choose(event.target.files);
                event.target.value = "";
              }}
            />
            <div className="flex h-8 min-w-0 items-center gap-2">
              <Button
                type="button"
                variant="outline"
                size="sm"
                disabled={busy}
                onClick={() => input.current?.click()}
              >
                <FileUpIcon /> {file ? "Change file" : "Choose file"}
              </Button>
              {file ? (
                <>
                  <span className="truncate text-sm">{file.name}</span>
                  <span className="shrink-0 text-xs text-muted-foreground">
                    {formatBytes(file.size)}
                  </span>
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon-xs"
                    aria-label="Remove the chosen file"
                    disabled={busy}
                    onClick={() => setFile(null)}
                  >
                    <XIcon />
                  </Button>
                </>
              ) : (
                <span className="truncate text-sm text-muted-foreground">
                  or drop one on this card
                </span>
              )}
            </div>
          </div>
        </div>
        <p className="text-sm text-muted-foreground">
          Columns for {importKindLabels[kind].toLowerCase()}: <code>{columns[kind]}</code>.
          {kind === "contacts"
            ? " A company is linked by name and created when it is new."
            : " Names are matched case-insensitively."}
        </p>
      </CardContent>
      <CardFooter className="gap-3">
        <Button type="button" disabled={!file || busy} onClick={submit}>
          {busy && <Loader2Icon className="animate-spin" />}
          {busy
            ? fraction < 1
              ? `Uploading ${Math.round(fraction * 100)}%`
              : "Starting…"
            : "Start import"}
        </Button>
        {busy && (
          <progress
            className="h-1 flex-1 overflow-hidden rounded-full [&::-webkit-progress-bar]:bg-muted [&::-webkit-progress-value]:bg-primary [&::-moz-progress-bar]:bg-primary"
            value={fraction}
            max={1}
            aria-label="Upload progress"
          />
        )}
      </CardFooter>
    </Card>
  );
}
