"use client";

import { ArrowDownIcon } from "lucide-react";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  type ComponentProps,
  type ReactNode,
  type RefObject,
} from "react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

/** Distance from the bottom, in px, still counted as "at the bottom". */
const BOTTOM_THRESHOLD = 24;

type StickToBottomContextValue = {
  isAtBottom: boolean;
  scrollToBottom: () => void;
  contentRef: RefObject<HTMLDivElement | null>;
};

const StickToBottomContext = createContext<StickToBottomContextValue | null>(null);

const useStickToBottomContext = () => {
  const context = useContext(StickToBottomContext);
  if (!context) throw new Error("Conversation components must be used inside <Conversation>");
  return context;
};

/** Share of the remaining distance covered each frame; ~250ms ease-out at 60fps. */
const EASE = 0.25;

const prefersReducedMotion = () =>
  typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

/**
 * Keeps a scroll container pinned to its bottom while content grows, and lets
 * go as soon as the user scrolls up. Re-pins when they scroll back down or
 * call `scrollToBottom`. Movement is a short ease-out that re-targets every
 * frame, so it glides after streamed text instead of jumping.
 */
const useStickToBottom = () => {
  const scrollRef = useRef<HTMLDivElement>(null);
  const contentRef = useRef<HTMLDivElement>(null);
  const pinnedRef = useRef(true);
  const lastScrollTopRef = useRef(0);
  const frameRef = useRef<number | null>(null);
  const [isAtBottom, setIsAtBottom] = useState(true);

  const stopAnimation = useCallback(() => {
    if (frameRef.current !== null) cancelAnimationFrame(frameRef.current);
    frameRef.current = null;
  }, []);

  const scrollToBottom = useCallback(() => {
    const el = scrollRef.current;
    if (!el) return;
    pinnedRef.current = true;
    if (frameRef.current !== null) return; // already gliding; it re-targets itself
    if (prefersReducedMotion()) {
      el.scrollTop = el.scrollHeight;
      return;
    }
    const step = () => {
      const target = el.scrollHeight - el.clientHeight;
      const remaining = target - el.scrollTop;
      if (remaining <= 0.5) {
        el.scrollTop = target;
        frameRef.current = null;
        return;
      }
      el.scrollTop += Math.max(remaining * EASE, Math.min(remaining, 1));
      frameRef.current = requestAnimationFrame(step);
    };
    frameRef.current = requestAnimationFrame(step);
  }, []);

  useEffect(() => stopAnimation, [stopAnimation]);

  // Follow new content while pinned.
  useEffect(() => {
    const content = contentRef.current;
    if (!content) return;
    const observer = new ResizeObserver(() => {
      if (pinnedRef.current) scrollToBottom();
    });
    observer.observe(content);
    return () => {
      observer.disconnect();
    };
  }, [scrollToBottom]);

  const onScroll = useCallback(() => {
    const el = scrollRef.current;
    if (!el) return;
    const distance = el.scrollHeight - el.scrollTop - el.clientHeight;
    const atBottom = distance <= BOTTOM_THRESHOLD;
    // Only a scroll *up* unpins, so our own glide (which passes through
    // "not at bottom" positions) does not cancel itself.
    if (atBottom) {
      pinnedRef.current = true;
    } else if (el.scrollTop < lastScrollTopRef.current) {
      pinnedRef.current = false;
      stopAnimation();
    }
    lastScrollTopRef.current = el.scrollTop;
    setIsAtBottom(atBottom);
  }, [stopAnimation]);

  return { scrollRef, contentRef, isAtBottom, scrollToBottom, onScroll };
};

export type ConversationProps = ComponentProps<"div">;

export const Conversation = ({ className, children, ...props }: ConversationProps) => {
  const { scrollRef, contentRef, isAtBottom, scrollToBottom, onScroll } = useStickToBottom();

  return (
    <StickToBottomContext.Provider value={{ isAtBottom, scrollToBottom, contentRef }}>
      <div className={cn("relative flex-1 overflow-y-hidden", className)} {...props}>
        <div ref={scrollRef} onScroll={onScroll} className="size-full overflow-y-auto" role="log">
          {children}
        </div>
      </div>
    </StickToBottomContext.Provider>
  );
};

export type ConversationContentProps = ComponentProps<"div">;

export const ConversationContent = ({ className, ...props }: ConversationContentProps) => {
  const { contentRef } = useStickToBottomContext();
  return <div ref={contentRef} className={cn("flex flex-col gap-8 p-4", className)} {...props} />;
};

export type ConversationEmptyStateProps = ComponentProps<"div"> & {
  title?: string;
  description?: string;
  icon?: ReactNode;
};

export const ConversationEmptyState = ({
  className,
  title = "No messages yet",
  description = "Start a conversation to see messages here",
  icon,
  children,
  ...props
}: ConversationEmptyStateProps) => (
  <div
    className={cn(
      "flex size-full flex-col items-center justify-center gap-3 p-8 text-center",
      className,
    )}
    {...props}
  >
    {children ?? (
      <>
        {icon && <div className="text-muted-foreground">{icon}</div>}
        <div className="space-y-1">
          <h3 className="text-sm font-medium">{title}</h3>
          {description && <p className="text-sm text-muted-foreground">{description}</p>}
        </div>
      </>
    )}
  </div>
);

export type ConversationScrollButtonProps = ComponentProps<typeof Button>;

export const ConversationScrollButton = ({
  className,
  ...props
}: ConversationScrollButtonProps) => {
  const { isAtBottom, scrollToBottom } = useStickToBottomContext();

  if (isAtBottom) return null;

  return (
    <Button
      className={cn("absolute bottom-4 left-1/2 -translate-x-1/2 rounded-full", className)}
      onClick={() => {
        scrollToBottom();
      }}
      size="icon"
      type="button"
      variant="outline"
      aria-label="Scroll to bottom"
      {...props}
    >
      <ArrowDownIcon className="size-4" />
    </Button>
  );
};
