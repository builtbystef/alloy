import { Skeleton } from "@/components/ui/skeleton";

export function ChatSkeleton() {
  return (
    <div className="mx-auto flex h-full w-full max-w-3xl flex-col justify-end gap-6 px-4 py-6 md:px-6">
      <Skeleton className="ml-auto h-10 w-1/3 rounded-2xl" />
      <div className="flex flex-col gap-2">
        <Skeleton className="h-4 w-11/12" />
        <Skeleton className="h-4 w-4/5" />
        <Skeleton className="h-4 w-2/3" />
      </div>
      <Skeleton className="mt-4 h-24 w-full rounded-2xl" />
    </div>
  );
}
