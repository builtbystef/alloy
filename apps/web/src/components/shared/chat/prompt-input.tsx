"use client";

import type { ChatStatus, FileUIPart } from "ai";
import {
  CornerDownLeftIcon,
  ImageIcon,
  Loader2Icon,
  PaperclipIcon,
  PlusIcon,
  SquareIcon,
  XIcon,
} from "lucide-react";
import {
  Children,
  createContext,
  Fragment,
  use,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ChangeEventHandler,
  type ClipboardEventHandler,
  type ComponentProps,
  type FormEvent,
  type FormEventHandler,
  type HTMLAttributes,
  type KeyboardEventHandler,
  type PropsWithChildren,
  type ReactNode,
  type RefObject,
} from "react";

import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { HoverCard, HoverCardContent, HoverCardTrigger } from "@/components/ui/hover-card";
import {
  InputGroup,
  InputGroupAddon,
  InputGroupButton,
  InputGroupTextarea,
} from "@/components/ui/input-group";
import { cn } from "@/lib/utils";

// ============================================================================
// Attachments
// ============================================================================

/**
 * A file waiting in the prompt. `url` is a blob URL for previews. The upload
 * fields are filled in by whoever handles `onFilesAdded`: `uploadId` once the
 * API knows the file, `progress` (0..1) while the bytes move, `error` if it failed.
 */
export type PromptAttachment = FileUIPart & {
  id: string;
  size?: number;
  uploadId?: string;
  progress?: number;
  error?: string;
};

export type AttachmentsContext = {
  files: PromptAttachment[];
  add: (files: File[] | FileList) => void;
  remove: (id: string) => void;
  update: (id: string, patch: Partial<PromptAttachment>) => void;
  clear: () => void;
  openFileDialog: () => void;
  fileInputRef: RefObject<HTMLInputElement | null>;
};

export type TextInputContext = {
  value: string;
  setInput: (v: string) => void;
  clear: () => void;
};

export type PromptInputControllerProps = {
  textInput: TextInputContext;
  attachments: AttachmentsContext;
  /** INTERNAL: lets PromptInput register its hidden file input. */
  __registerFileInput: (ref: RefObject<HTMLInputElement | null>, open: () => void) => void;
};

const PromptInputController = createContext<PromptInputControllerProps | null>(null);
const ProviderAttachmentsContext = createContext<AttachmentsContext | null>(null);

export const usePromptInputController = () => {
  const ctx = use(PromptInputController);
  if (!ctx) {
    throw new Error(
      "Wrap your component inside <PromptInputProvider> to use usePromptInputController().",
    );
  }
  return ctx;
};

const useOptionalPromptInputController = () => use(PromptInputController);

export type AddedFile = { id: string; file: File };

/** What an upload handler may do to the attachments it was handed. */
export type AttachmentControls = Pick<AttachmentsContext, "update" | "remove">;

export type PromptInputProviderProps = PropsWithChildren<{
  initialInput?: string;
  /** Called with each batch of files the user added, so they can start uploading. */
  onFilesAdded?: (files: AddedFile[], controls: AttachmentControls) => void;
  /** Called when the user removes an attachment before sending, so its upload can be discarded. */
  onFileRemoved?: (file: PromptAttachment) => void;
  /** Largest file accepted, in bytes. Bigger ones are reported through `onError`. */
  maxFileSize?: number;
  onError?: (error: { code: "max_file_size"; message: string; file: File }) => void;
}>;

function toAttachment(file: File, id: string): PromptAttachment {
  return {
    id,
    type: "file",
    url: URL.createObjectURL(file),
    mediaType: file.type || "application/octet-stream",
    filename: file.name,
    size: file.size,
  };
}

/** Lifts the prompt's text and attachments out of PromptInput, so the chat can drive uploads. */
export function PromptInputProvider({
  initialInput = "",
  onFilesAdded,
  onFileRemoved,
  maxFileSize,
  onError,
  children,
}: PromptInputProviderProps) {
  const [textInput, setTextInput] = useState(initialInput);
  const clearInput = useCallback(() => setTextInput(""), []);

  const [attachmentFiles, setAttachmentFiles] = useState<PromptAttachment[]>([]);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const openRef = useRef<() => void>(() => {});

  const attachmentsRef = useRef(attachmentFiles);
  attachmentsRef.current = attachmentFiles;
  const onFileRemovedRef = useRef(onFileRemoved);
  onFileRemovedRef.current = onFileRemoved;
  const remove = useCallback((id: string) => {
    const found = attachmentsRef.current.find((f) => f.id === id);
    if (!found) return;
    if (found.url) URL.revokeObjectURL(found.url);
    onFileRemovedRef.current?.(found);
    setAttachmentFiles((prev) => prev.filter((f) => f.id !== id));
  }, []);

  const update = useCallback((id: string, patch: Partial<PromptAttachment>) => {
    setAttachmentFiles((prev) => prev.map((f) => (f.id === id ? { ...f, ...patch } : f)));
  }, []);

  const add = useCallback(
    (files: File[] | FileList) => {
      const added: AddedFile[] = [];
      for (const file of Array.from(files)) {
        if (maxFileSize !== undefined && file.size > maxFileSize) {
          onError?.({ code: "max_file_size", message: `${file.name} is too big.`, file });
          continue;
        }
        added.push({ id: crypto.randomUUID(), file });
      }
      if (added.length === 0) return;
      setAttachmentFiles((prev) =>
        prev.concat(added.map(({ id, file }) => toAttachment(file, id))),
      );
      onFilesAdded?.(added, { update, remove });
    },
    [maxFileSize, onError, onFilesAdded, update, remove],
  );

  const clear = useCallback(() => {
    setAttachmentFiles((prev) => {
      for (const f of prev) if (f.url) URL.revokeObjectURL(f.url);
      return [];
    });
  }, []);

  useEffect(
    () => () => {
      for (const f of attachmentsRef.current) if (f.url) URL.revokeObjectURL(f.url);
    },
    [],
  );

  const openFileDialog = useCallback(() => openRef.current?.(), []);

  const attachments = useMemo<AttachmentsContext>(
    () => ({ files: attachmentFiles, add, remove, update, clear, openFileDialog, fileInputRef }),
    [attachmentFiles, add, remove, update, clear, openFileDialog],
  );

  const __registerFileInput = useCallback(
    (ref: RefObject<HTMLInputElement | null>, open: () => void) => {
      fileInputRef.current = ref.current;
      openRef.current = open;
    },
    [],
  );

  const controller = useMemo<PromptInputControllerProps>(
    () => ({
      textInput: { value: textInput, setInput: setTextInput, clear: clearInput },
      attachments,
      __registerFileInput,
    }),
    [textInput, clearInput, attachments, __registerFileInput],
  );

  return (
    <PromptInputController value={controller}>
      <ProviderAttachmentsContext value={attachments}>{children}</ProviderAttachmentsContext>
    </PromptInputController>
  );
}

const LocalAttachmentsContext = createContext<AttachmentsContext | null>(null);

export const usePromptInputAttachments = () => {
  const provider = use(ProviderAttachmentsContext);
  const local = use(LocalAttachmentsContext);
  const context = provider ?? local;
  if (!context) {
    throw new Error(
      "usePromptInputAttachments must be used within a PromptInput or PromptInputProvider",
    );
  }
  return context;
};

export type PromptInputAttachmentProps = HTMLAttributes<HTMLDivElement> & {
  data: PromptAttachment;
  className?: string;
};

export function PromptInputAttachment({ data, className, ...props }: PromptInputAttachmentProps) {
  const attachments = usePromptInputAttachments();
  const filename = data.filename || "";
  const isImage = Boolean(data.mediaType?.startsWith("image/") && data.url);
  const attachmentLabel = filename || (isImage ? "Image" : "Attachment");
  const uploading = data.uploadId === undefined && !data.error;

  return (
    <PromptInputHoverCard>
      <HoverCardTrigger
        render={
          <div
            className={cn(
              "group relative flex h-8 cursor-pointer items-center gap-1.5 rounded-md border border-border px-1.5 text-sm font-medium transition-all select-none hover:bg-accent hover:text-accent-foreground dark:hover:bg-accent/50",
              data.error && "border-destructive text-destructive",
              className,
            )}
            data-uploading={uploading || undefined}
            {...props}
          />
        }
      >
        <div className="relative size-5 shrink-0">
          <div className="absolute inset-0 flex size-5 items-center justify-center overflow-hidden rounded bg-background transition-opacity group-hover:opacity-0">
            {uploading ? (
              <Loader2Icon className="size-3 animate-spin text-muted-foreground" />
            ) : isImage ? (
              // eslint-disable-next-line @next/next/no-img-element -- a local blob URL
              <img
                alt={filename || "attachment"}
                className="size-5 object-cover"
                height={20}
                src={data.url}
                width={20}
              />
            ) : (
              <div className="flex size-5 items-center justify-center text-muted-foreground">
                <PaperclipIcon className="size-3" />
              </div>
            )}
          </div>
          <Button
            aria-label={`Remove ${attachmentLabel}`}
            className="absolute inset-0 size-5 cursor-pointer rounded p-0 opacity-0 transition-opacity group-hover:pointer-events-auto group-hover:opacity-100 [&>svg]:size-2.5"
            onClick={(e) => {
              e.stopPropagation();
              attachments.remove(data.id);
            }}
            type="button"
            variant="ghost"
          >
            <XIcon />
            <span className="sr-only">Remove</span>
          </Button>
        </div>
        <span className="flex-1 truncate">{attachmentLabel}</span>
        {uploading && data.progress !== undefined && (
          <span className="text-xs text-muted-foreground tabular-nums">
            {Math.round(data.progress * 100)}%
          </span>
        )}
      </HoverCardTrigger>
      <PromptInputHoverCardContent className="w-auto p-2">
        <div className="w-auto space-y-3">
          {isImage && (
            <div className="flex max-h-96 w-96 items-center justify-center overflow-hidden rounded-md border">
              {/* eslint-disable-next-line @next/next/no-img-element -- a local blob URL */}
              <img
                alt={filename || "attachment preview"}
                className="max-h-full max-w-full object-contain"
                height={384}
                src={data.url}
                width={448}
              />
            </div>
          )}
          <div className="min-w-0 flex-1 space-y-1 px-0.5">
            <h4 className="truncate text-sm leading-none font-semibold">{attachmentLabel}</h4>
            {data.mediaType && (
              <p className="truncate font-mono text-xs text-muted-foreground">{data.mediaType}</p>
            )}
            {data.error && <p className="text-xs text-destructive">{data.error}</p>}
          </div>
        </div>
      </PromptInputHoverCardContent>
    </PromptInputHoverCard>
  );
}

export type PromptInputAttachmentsProps = Omit<HTMLAttributes<HTMLDivElement>, "children"> & {
  children: (attachment: PromptAttachment) => ReactNode;
};

export function PromptInputAttachments({
  children,
  className,
  ...props
}: PromptInputAttachmentsProps) {
  const attachments = usePromptInputAttachments();
  if (!attachments.files.length) return null;

  return (
    <div className={cn("flex w-full flex-wrap items-center gap-2 p-3", className)} {...props}>
      {attachments.files.map((file) => (
        <Fragment key={file.id}>{children(file)}</Fragment>
      ))}
    </div>
  );
}

export type PromptInputActionAddAttachmentsProps = ComponentProps<typeof DropdownMenuItem> & {
  label?: string;
};

export const PromptInputActionAddAttachments = ({
  label = "Add photos or files",
  ...props
}: PromptInputActionAddAttachmentsProps) => {
  const attachments = usePromptInputAttachments();
  return (
    <DropdownMenuItem {...props} onClick={() => attachments.openFileDialog()}>
      <ImageIcon className="mr-2 size-4" /> {label}
    </DropdownMenuItem>
  );
};

// ============================================================================
// The input
// ============================================================================

export type PromptInputMessage = {
  text: string;
  files: PromptAttachment[];
};

export type PromptInputProps = Omit<HTMLAttributes<HTMLFormElement>, "onSubmit" | "onError"> & {
  accept?: string;
  multiple?: boolean;
  /** Accept drops anywhere on the document, not only on the form. */
  globalDrop?: boolean;
  maxFiles?: number;
  maxFileSize?: number;
  onError?: (err: { code: "max_files" | "max_file_size" | "accept"; message: string }) => void;
  onSubmit: (
    message: PromptInputMessage,
    event: FormEvent<HTMLFormElement>,
  ) => void | Promise<void>;
};

export const PromptInput = ({
  className,
  accept,
  multiple,
  globalDrop,
  maxFiles,
  maxFileSize,
  onError,
  onSubmit,
  children,
  ...props
}: PromptInputProps) => {
  const controller = useOptionalPromptInputController();
  const usingProvider = controller !== null;

  const inputRef = useRef<HTMLInputElement | null>(null);
  const formRef = useRef<HTMLFormElement | null>(null);

  // Local attachments, used only without a provider.
  const [items, setItems] = useState<PromptAttachment[]>([]);
  const files = usingProvider ? controller.attachments.files : items;
  const filesRef = useRef(files);
  filesRef.current = files;

  const openFileDialogLocal = useCallback(() => inputRef.current?.click(), []);

  const matchesAccept = useCallback(
    (f: File) => {
      if (!accept || accept.trim() === "") return true;
      return accept
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean)
        .some((pattern) =>
          pattern.endsWith("/*") ? f.type.startsWith(pattern.slice(0, -1)) : f.type === pattern,
        );
    },
    [accept],
  );

  const addLocal = useCallback(
    (fileList: File[] | FileList) => {
      const incoming = Array.from(fileList);
      const accepted = incoming.filter(matchesAccept);
      if (incoming.length && accepted.length === 0) {
        onError?.({ code: "accept", message: "No files match the accepted types." });
        return;
      }
      const sized = accepted.filter((f) => (maxFileSize ? f.size <= maxFileSize : true));
      if (accepted.length > 0 && sized.length === 0) {
        onError?.({ code: "max_file_size", message: "All files exceed the maximum size." });
        return;
      }
      setItems((prev) => {
        const capacity =
          typeof maxFiles === "number" ? Math.max(0, maxFiles - prev.length) : undefined;
        const capped = typeof capacity === "number" ? sized.slice(0, capacity) : sized;
        if (typeof capacity === "number" && sized.length > capacity) {
          onError?.({ code: "max_files", message: "Too many files. Some were not added." });
        }
        return prev.concat(capped.map((file) => toAttachment(file, crypto.randomUUID())));
      });
    },
    [matchesAccept, maxFiles, maxFileSize, onError],
  );

  const removeLocal = useCallback(
    (id: string) =>
      setItems((prev) => {
        const found = prev.find((file) => file.id === id);
        if (found?.url) URL.revokeObjectURL(found.url);
        return prev.filter((file) => file.id !== id);
      }),
    [],
  );

  const updateLocal = useCallback(
    (id: string, patch: Partial<PromptAttachment>) =>
      setItems((prev) => prev.map((f) => (f.id === id ? { ...f, ...patch } : f))),
    [],
  );

  const clearLocal = useCallback(
    () =>
      setItems((prev) => {
        for (const file of prev) if (file.url) URL.revokeObjectURL(file.url);
        return [];
      }),
    [],
  );

  const add = usingProvider ? controller.attachments.add : addLocal;
  const remove = usingProvider ? controller.attachments.remove : removeLocal;
  const update = usingProvider ? controller.attachments.update : updateLocal;
  const clear = usingProvider ? controller.attachments.clear : clearLocal;
  const openFileDialog = usingProvider
    ? controller.attachments.openFileDialog
    : openFileDialogLocal;

  useEffect(() => {
    if (!usingProvider) return;
    controller.__registerFileInput(inputRef, () => inputRef.current?.click());
  }, [usingProvider, controller]);

  // Drops on the form (or the whole document when `globalDrop` is set).
  useEffect(() => {
    const target: HTMLElement | Document | null = globalDrop ? document : formRef.current;
    if (!target) return;
    const onDragOver = (e: Event) => {
      const event = e as DragEvent;
      if (event.dataTransfer?.types?.includes("Files")) event.preventDefault();
    };
    const onDrop = (e: Event) => {
      const event = e as DragEvent;
      if (event.dataTransfer?.types?.includes("Files")) event.preventDefault();
      if (event.dataTransfer?.files && event.dataTransfer.files.length > 0)
        add(event.dataTransfer.files);
    };
    target.addEventListener("dragover", onDragOver);
    target.addEventListener("drop", onDrop);
    return () => {
      target.removeEventListener("dragover", onDragOver);
      target.removeEventListener("drop", onDrop);
    };
  }, [add, globalDrop]);

  useEffect(
    () => () => {
      if (!usingProvider) for (const f of filesRef.current) if (f.url) URL.revokeObjectURL(f.url);
    },
    [usingProvider],
  );

  const handleChange: ChangeEventHandler<HTMLInputElement> = (event) => {
    if (event.currentTarget.files) add(event.currentTarget.files);
    // So the same file can be picked again after being removed.
    event.currentTarget.value = "";
  };

  const ctx = useMemo<AttachmentsContext>(
    () => ({ files, add, remove, update, clear, openFileDialog, fileInputRef: inputRef }),
    [files, add, remove, update, clear, openFileDialog],
  );

  const handleSubmit: FormEventHandler<HTMLFormElement> = (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    const text = usingProvider
      ? controller.textInput.value
      : ((new FormData(form).get("message") as string | null) ?? "");
    if (!usingProvider) form.reset();

    const finish = () => {
      clear();
      if (usingProvider) controller.textInput.clear();
    };
    try {
      const result = onSubmit({ text, files }, event);
      if (result instanceof Promise) {
        result.then(finish).catch(() => {
          // Keep the draft so the user can retry.
        });
      } else {
        finish();
      }
    } catch {
      // Keep the draft so the user can retry.
    }
  };

  const inner = (
    <>
      <input
        accept={accept}
        aria-label="Upload files"
        className="hidden"
        multiple={multiple}
        onChange={handleChange}
        ref={inputRef}
        title="Upload files"
        type="file"
      />
      <form className={cn("w-full", className)} onSubmit={handleSubmit} ref={formRef} {...props}>
        <InputGroup className="overflow-hidden">{children}</InputGroup>
      </form>
    </>
  );

  return usingProvider ? (
    inner
  ) : (
    <LocalAttachmentsContext value={ctx}>{inner}</LocalAttachmentsContext>
  );
};

export type PromptInputBodyProps = HTMLAttributes<HTMLDivElement>;

export const PromptInputBody = ({ className, ...props }: PromptInputBodyProps) => (
  <div className={cn("contents", className)} {...props} />
);

export type PromptInputTextareaProps = ComponentProps<typeof InputGroupTextarea>;

export const PromptInputTextarea = ({
  onChange,
  className,
  placeholder = "What would you like to know?",
  ...props
}: PromptInputTextareaProps) => {
  const controller = useOptionalPromptInputController();
  const attachments = usePromptInputAttachments();
  const [isComposing, setIsComposing] = useState(false);

  const handleKeyDown: KeyboardEventHandler<HTMLTextAreaElement> = (e) => {
    if (e.key === "Enter") {
      if (isComposing || e.nativeEvent.isComposing || e.shiftKey) return;
      e.preventDefault();
      const form = e.currentTarget.form;
      const submitButton = form?.querySelector<HTMLButtonElement>('button[type="submit"]');
      if (submitButton?.disabled) return;
      form?.requestSubmit();
    }
    if (e.key === "Backspace" && e.currentTarget.value === "" && attachments.files.length > 0) {
      e.preventDefault();
      const last = attachments.files.at(-1);
      if (last) attachments.remove(last.id);
    }
  };

  const handlePaste: ClipboardEventHandler<HTMLTextAreaElement> = (event) => {
    const items = event.clipboardData?.items;
    if (!items) return;
    const files: File[] = [];
    for (const item of items) {
      if (item.kind === "file") {
        const file = item.getAsFile();
        if (file) files.push(file);
      }
    }
    if (files.length > 0) {
      event.preventDefault();
      attachments.add(files);
    }
  };

  const controlledProps = controller
    ? {
        value: controller.textInput.value,
        onChange: (e: React.ChangeEvent<HTMLTextAreaElement>) => {
          controller.textInput.setInput(e.currentTarget.value);
          onChange?.(e);
        },
      }
    : { onChange };

  return (
    <InputGroupTextarea
      className={cn("field-sizing-content max-h-48 min-h-16", className)}
      name="message"
      onCompositionEnd={() => setIsComposing(false)}
      onCompositionStart={() => setIsComposing(true)}
      onKeyDown={handleKeyDown}
      onPaste={handlePaste}
      placeholder={placeholder}
      {...props}
      {...controlledProps}
    />
  );
};

export type PromptInputHeaderProps = Omit<ComponentProps<typeof InputGroupAddon>, "align">;

export const PromptInputHeader = ({ className, ...props }: PromptInputHeaderProps) => (
  <InputGroupAddon
    align="block-end"
    className={cn("order-first flex-wrap gap-1", className)}
    {...props}
  />
);

export type PromptInputFooterProps = Omit<ComponentProps<typeof InputGroupAddon>, "align">;

export const PromptInputFooter = ({ className, ...props }: PromptInputFooterProps) => (
  <InputGroupAddon
    align="block-end"
    className={cn("justify-between gap-1", className)}
    {...props}
  />
);

export type PromptInputToolsProps = HTMLAttributes<HTMLDivElement>;

export const PromptInputTools = ({ className, ...props }: PromptInputToolsProps) => (
  <div className={cn("flex items-center gap-1", className)} {...props} />
);

export type PromptInputButtonProps = ComponentProps<typeof InputGroupButton>;

export const PromptInputButton = ({
  variant = "ghost",
  className,
  size,
  ...props
}: PromptInputButtonProps) => {
  const newSize = size ?? (Children.count(props.children) > 1 ? "sm" : "icon-sm");
  return (
    <InputGroupButton
      className={cn(className)}
      size={newSize}
      type="button"
      variant={variant}
      {...props}
    />
  );
};

export type PromptInputActionMenuProps = ComponentProps<typeof DropdownMenu>;
export const PromptInputActionMenu = (props: PromptInputActionMenuProps) => (
  <DropdownMenu {...props} />
);

export type PromptInputActionMenuTriggerProps = PromptInputButtonProps;

export const PromptInputActionMenuTrigger = ({
  className,
  children,
  ...props
}: PromptInputActionMenuTriggerProps) => (
  <DropdownMenuTrigger render={<PromptInputButton className={className} {...props} />}>
    {children ?? <PlusIcon className="size-4" />}
  </DropdownMenuTrigger>
);

export type PromptInputActionMenuContentProps = ComponentProps<typeof DropdownMenuContent>;
export const PromptInputActionMenuContent = ({
  className,
  ...props
}: PromptInputActionMenuContentProps) => (
  <DropdownMenuContent align="start" className={cn(className)} {...props} />
);

export type PromptInputActionMenuItemProps = ComponentProps<typeof DropdownMenuItem>;
export const PromptInputActionMenuItem = ({
  className,
  ...props
}: PromptInputActionMenuItemProps) => <DropdownMenuItem className={cn(className)} {...props} />;

export type PromptInputSubmitProps = ComponentProps<typeof InputGroupButton> & {
  status?: ChatStatus;
};

/** Send, or Stop while a reply streams. */
export const PromptInputSubmit = ({
  className,
  variant = "default",
  size = "icon-sm",
  status,
  children,
  ...props
}: PromptInputSubmitProps) => {
  let Icon = <CornerDownLeftIcon className="size-4" />;
  if (status === "submitted") Icon = <Loader2Icon className="size-4 animate-spin" />;
  else if (status === "streaming") Icon = <SquareIcon className="size-4" />;
  else if (status === "error") Icon = <XIcon className="size-4" />;

  return (
    <InputGroupButton
      aria-label={status === "streaming" ? "Stop" : "Send"}
      className={cn(className)}
      size={size}
      type="submit"
      variant={variant}
      {...props}
    >
      {children ?? Icon}
    </InputGroupButton>
  );
};

export type PromptInputHoverCardProps = ComponentProps<typeof HoverCard>;
export const PromptInputHoverCard = (props: PromptInputHoverCardProps) => <HoverCard {...props} />;

export type PromptInputHoverCardContentProps = ComponentProps<typeof HoverCardContent>;
export const PromptInputHoverCardContent = ({
  align = "start",
  ...props
}: PromptInputHoverCardContentProps) => <HoverCardContent align={align} {...props} />;
