"use client";

import type { AttachmentRead } from "@alloy/api-client";
import { useSuspenseQuery } from "@tanstack/react-query";
import {
  DownloadIcon,
  FileIcon,
  FileTextIcon,
  ImageIcon,
  Loader2Icon,
  Trash2Icon,
  UploadIcon,
} from "lucide-react";
import { useRef, useState, type DragEvent, type ReactNode } from "react";

import { TruncatedNote } from "@/components/truncated-note";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardAction,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { browserApi } from "@/lib/api-browser";
import { ATTACHMENT_MAX_BYTES, formatBytes } from "@/lib/bytes";
import { formatDateTime, formatRelativeDays } from "@/lib/dates";
import { attachmentDownloadHref, attachmentsQuery, type AttachmentParent } from "@/lib/queries";
import { cn } from "@/lib/utils";
import { useCan, useWorkspace } from "@/lib/workspace";

import { useAttachmentMutations } from "./use-attachment-mutations";

function fileIcon(contentType: string): ReactNode {
  if (contentType.startsWith("image/")) return <ImageIcon />;
  if (contentType === "application/pdf" || contentType.startsWith("text/")) return <FileTextIcon />;
  return <FileIcon />;
}

export function AttachmentsCard({
  parent,
  timeZone,
}: {
  parent: AttachmentParent;
  timeZone: string;
}) {
  const { id: workspaceId } = useWorkspace();
  const canWrite = useCan("crm:write");
  const { data: attachments } = useSuspenseQuery(attachmentsQuery(browserApi, workspaceId, parent));
  const { upload, uploads, confirmDelete, dialog } = useAttachmentMutations(parent);
  const input = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);

  const onDrop = (event: DragEvent) => {
    event.preventDefault();
    setDragging(false);
    if (canWrite) upload(event.dataTransfer.files);
  };

  return (
    <Card
      className={cn(dragging && "ring-2 ring-ring/50")}
      onDragOver={(event) => {
        if (!canWrite) return;
        event.preventDefault();
        setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={onDrop}
    >
      <CardHeader>
        <CardTitle>Attachments</CardTitle>
        <CardDescription>
          Contracts, proposals, photos. Up to {formatBytes(ATTACHMENT_MAX_BYTES)} each.
        </CardDescription>
        {canWrite && (
          <CardAction>
            <input
              ref={input}
              type="file"
              multiple
              className="sr-only"
              aria-label="Choose files to attach"
              onChange={(event) => {
                if (event.target.files) upload(event.target.files);
                event.target.value = "";
              }}
            />
            <Button variant="outline" size="sm" onClick={() => input.current?.click()}>
              <UploadIcon /> Upload
            </Button>
          </CardAction>
        )}
      </CardHeader>
      <CardContent>
        {attachments.items.length === 0 && uploads.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            {canWrite ? "No files yet. Drop one here or use Upload." : "No files yet."}
          </p>
        ) : (
          <ul className="flex flex-col gap-1">
            {uploads.map((item) => (
              <li key={item.id} className="flex items-center gap-3 rounded-md py-1.5">
                <span className="flex size-7 shrink-0 items-center justify-center rounded-md bg-muted text-muted-foreground [&_svg]:size-3.5">
                  <Loader2Icon className="animate-spin" />
                </span>
                <div className="flex min-w-0 flex-1 flex-col gap-1">
                  <span className="truncate text-sm">{item.filename}</span>
                  <progress
                    className="h-1 w-full overflow-hidden rounded-full [&::-webkit-progress-bar]:bg-muted [&::-webkit-progress-value]:bg-primary [&::-moz-progress-bar]:bg-primary"
                    value={item.fraction}
                    max={1}
                    aria-label={`Uploading ${item.filename}`}
                  />
                </div>
                <span className="text-xs text-muted-foreground tabular-nums">
                  {item.fraction < 1 ? `${Math.round(item.fraction * 100)}%` : "Saving…"}
                </span>
              </li>
            ))}
            {attachments.items.map((attachment) => (
              <AttachmentRow
                key={attachment.id}
                attachment={attachment}
                timeZone={timeZone}
                href={attachmentDownloadHref(workspaceId, attachment.id)}
                onDelete={canWrite ? () => confirmDelete(attachment) : null}
              />
            ))}
          </ul>
        )}
        <TruncatedNote shown={attachments.items.length} total={attachments.total} noun="files" />
      </CardContent>
      {dialog}
    </Card>
  );
}

function AttachmentRow({
  attachment,
  timeZone,
  href,
  onDelete,
}: {
  attachment: AttachmentRead;
  timeZone: string;
  href: string;
  onDelete: (() => void) | null;
}) {
  const uploader = attachment.uploaded_by?.email;
  return (
    <li className="group flex items-center gap-3 rounded-md py-1.5">
      <span className="flex size-7 shrink-0 items-center justify-center rounded-md bg-muted text-muted-foreground [&_svg]:size-3.5">
        {fileIcon(attachment.content_type)}
      </span>
      <div className="flex min-w-0 flex-1 flex-col">
        <a href={href} className="truncate text-sm font-medium hover:underline" download>
          {attachment.filename}
        </a>
        <span className="truncate text-xs text-muted-foreground">
          {formatBytes(attachment.size)}
          {" · "}
          <span title={formatDateTime(attachment.uploaded_at, timeZone)}>
            {formatRelativeDays(attachment.uploaded_at, timeZone)}
          </span>
          {uploader && ` by ${uploader}`}
        </span>
      </div>
      <Button
        variant="ghost"
        size="icon-xs"
        nativeButton={false}
        render={<a href={href} download />}
        aria-label={`Download ${attachment.filename}`}
      >
        <DownloadIcon />
      </Button>
      {onDelete && (
        <Button
          variant="ghost"
          size="icon-xs"
          className="text-destructive opacity-0 group-hover:opacity-100 focus-visible:opacity-100"
          onClick={onDelete}
          aria-label={`Delete ${attachment.filename}`}
        >
          <Trash2Icon />
        </Button>
      )}
    </li>
  );
}
