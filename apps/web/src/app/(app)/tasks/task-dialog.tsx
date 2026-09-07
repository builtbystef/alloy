"use client";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

import { TaskForm, type TaskFormProps } from "./task-form";

export function TaskDialog({
  open,
  onOpenChange,
  ...formProps
}: Omit<TaskFormProps, "onSaved" | "onCancel"> & {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>{formProps.task ? "Edit task" : "New task"}</DialogTitle>
          <DialogDescription>
            {formProps.task
              ? "Marking a task done logs an activity on its contact."
              : "Link it to a contact or company to see it on their page."}
          </DialogDescription>
        </DialogHeader>
        {open && (
          <TaskForm
            {...formProps}
            onSaved={() => onOpenChange(false)}
            onCancel={() => onOpenChange(false)}
          />
        )}
      </DialogContent>
    </Dialog>
  );
}
