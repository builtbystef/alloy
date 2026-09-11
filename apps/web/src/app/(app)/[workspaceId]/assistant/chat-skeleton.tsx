import { Skeleton } from "@/components/ui/skeleton";

export function ChatSkeleton() {
  return (
    <div className="flex h-full flex-col justify-end gap-4 p-4">
      <Skeleton className="h-16 w-2/3" />
      <Skeleton className="ml-auto h-10 w-1/3" />
      <Skeleton className="h-24 w-full" />
    </div>
  );
}
