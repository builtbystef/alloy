"use client";

import type { DynamicToolUIPart, ToolUIPart } from "ai";
import {
  CheckCircleIcon,
  ChevronDownIcon,
  CircleIcon,
  ClockIcon,
  WrenchIcon,
  XCircleIcon,
} from "lucide-react";
import { isValidElement, type ComponentProps, type ReactNode } from "react";

import { Badge } from "@/components/ui/badge";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { cn } from "@/lib/utils";

export type ToolState = ToolUIPart["state"];

export type ToolProps = ComponentProps<typeof Collapsible>;

export const Tool = ({ className, ...props }: ToolProps) => (
  <Collapsible
    className={cn("not-prose group/tool mb-4 w-full rounded-md border", className)}
    {...props}
  />
);

export type ToolHeaderProps = {
  title?: string;
  type: ToolUIPart["type"] | DynamicToolUIPart["type"];
  state: ToolState;
  className?: string;
};

const labels: Record<ToolState, string> = {
  "input-streaming": "Pending",
  "input-available": "Running",
  "approval-requested": "Awaiting approval",
  "approval-responded": "Responded",
  "output-available": "Completed",
  "output-error": "Error",
  "output-denied": "Denied",
};

const icons: Record<ToolState, ReactNode> = {
  "input-streaming": <CircleIcon className="size-4" />,
  "input-available": <ClockIcon className="size-4 animate-pulse" />,
  "approval-requested": <ClockIcon className="size-4 text-yellow-600" />,
  "approval-responded": <CheckCircleIcon className="size-4 text-blue-600" />,
  "output-available": <CheckCircleIcon className="size-4 text-green-600" />,
  "output-error": <XCircleIcon className="size-4 text-red-600" />,
  "output-denied": <XCircleIcon className="size-4 text-orange-600" />,
};

export const ToolStatusBadge = ({ state }: { state: ToolState }) => (
  <Badge className="gap-1.5 rounded-full text-xs" variant="secondary" data-state={state}>
    {icons[state]}
    {labels[state]}
  </Badge>
);

export const ToolHeader = ({ className, title, type, state, ...props }: ToolHeaderProps) => (
  <CollapsibleTrigger
    className={cn("flex w-full items-center justify-between gap-4 p-3 text-left", className)}
    {...props}
  >
    <div className="flex items-center gap-2">
      <WrenchIcon className="size-4 text-muted-foreground" />
      <span className="text-sm font-medium">{title ?? type.split("-").slice(1).join("-")}</span>
      <ToolStatusBadge state={state} />
    </div>
    <ChevronDownIcon className="size-4 text-muted-foreground transition-transform group-data-open/tool:rotate-180" />
  </CollapsibleTrigger>
);

export type ToolContentProps = ComponentProps<typeof CollapsibleContent>;

export const ToolContent = ({ className, ...props }: ToolContentProps) => (
  <CollapsibleContent
    className={cn(
      "text-popover-foreground outline-none data-open:animate-in data-open:slide-in-from-top-2 data-closed:animate-out data-closed:fade-out-0 data-closed:slide-out-to-top-2",
      className,
    )}
    {...props}
  />
);

const JsonBlock = ({ value }: { value: unknown }) => (
  <pre className="overflow-x-auto p-3 font-mono text-xs whitespace-pre-wrap">
    {typeof value === "string" ? value : JSON.stringify(value, null, 2)}
  </pre>
);

export type ToolInputProps = ComponentProps<"div"> & {
  input: ToolUIPart["input"];
};

export const ToolInput = ({ className, input, ...props }: ToolInputProps) => (
  <div className={cn("space-y-2 overflow-hidden p-4", className)} {...props}>
    <h4 className="text-xs font-medium tracking-wide text-muted-foreground uppercase">
      Parameters
    </h4>
    <div className="rounded-md bg-muted/50">
      <JsonBlock value={input} />
    </div>
  </div>
);

export type ToolOutputProps = ComponentProps<"div"> & {
  output: ToolUIPart["output"];
  errorText: ToolUIPart["errorText"];
};

export const ToolOutput = ({ className, output, errorText, ...props }: ToolOutputProps) => {
  if (!(output || errorText)) return null;

  let rendered: ReactNode;
  if (isValidElement(output)) rendered = output;
  else if (output !== undefined && output !== null) rendered = <JsonBlock value={output} />;

  return (
    <div className={cn("space-y-2 p-4", className)} {...props}>
      <h4 className="text-xs font-medium tracking-wide text-muted-foreground uppercase">
        {errorText ? "Error" : "Result"}
      </h4>
      <div
        className={cn(
          "overflow-x-auto rounded-md text-xs [&_table]:w-full",
          errorText ? "bg-destructive/10 text-destructive" : "bg-muted/50 text-foreground",
        )}
      >
        {errorText && <div className="p-3 whitespace-pre-wrap">{errorText}</div>}
        {rendered}
      </div>
    </div>
  );
};
