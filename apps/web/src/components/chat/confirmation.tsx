"use client";

import type { ToolUIPart } from "ai";
import { createContext, use, type ComponentProps, type ReactNode } from "react";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

/** The `approval` field of a tool part, in any state that has one. */
export type ToolUIPartApproval =
  | {
      id: string;
      approved?: boolean | undefined;
      reason?: string | undefined;
    }
  | undefined;

type ConfirmationContextValue = {
  approval: ToolUIPartApproval;
  state: ToolUIPart["state"];
};

const ConfirmationContext = createContext<ConfirmationContextValue | null>(null);

const useConfirmation = () => {
  const context = use(ConfirmationContext);
  if (!context) throw new Error("Confirmation components must be used within Confirmation");
  return context;
};

export type ConfirmationProps = ComponentProps<typeof Alert> & {
  approval?: ToolUIPartApproval;
  state: ToolUIPart["state"];
};

/** Renders only once the call is waiting for, or has received, a decision. */
export const Confirmation = ({ className, approval, state, ...props }: ConfirmationProps) => {
  if (!approval || state === "input-streaming" || state === "input-available") return null;

  return (
    <ConfirmationContext value={{ approval, state }}>
      <Alert className={cn("flex flex-col gap-2", className)} {...props} />
    </ConfirmationContext>
  );
};

export type ConfirmationTitleProps = ComponentProps<typeof AlertDescription>;

export const ConfirmationTitle = ({ className, ...props }: ConfirmationTitleProps) => (
  <AlertDescription className={cn("inline", className)} {...props} />
);

export const ConfirmationRequest = ({ children }: { children?: ReactNode }) => {
  const { state } = useConfirmation();
  if (state !== "approval-requested") return null;
  return children;
};

const responded = (state: ToolUIPart["state"]) =>
  state === "approval-responded" || state === "output-denied" || state === "output-available";

export const ConfirmationAccepted = ({ children }: { children?: ReactNode }) => {
  const { approval, state } = useConfirmation();
  if (!approval?.approved || !responded(state)) return null;
  return children;
};

export const ConfirmationRejected = ({ children }: { children?: ReactNode }) => {
  const { approval, state } = useConfirmation();
  if (approval?.approved !== false || !responded(state)) return null;
  return children;
};

export type ConfirmationActionsProps = ComponentProps<"div">;

export const ConfirmationActions = ({ className, ...props }: ConfirmationActionsProps) => {
  const { state } = useConfirmation();
  if (state !== "approval-requested") return null;
  return (
    <div className={cn("flex items-center justify-end gap-2 self-end", className)} {...props} />
  );
};

export type ConfirmationActionProps = ComponentProps<typeof Button>;

export const ConfirmationAction = (props: ConfirmationActionProps) => (
  <Button className="h-8 px-3 text-sm" type="button" {...props} />
);
