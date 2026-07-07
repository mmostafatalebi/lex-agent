import { Skeleton } from "@/components/ui/skeleton";

export default function Loading() {
  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-4">
      <Skeleton className="mx-auto h-10 w-3/4" />
      <Skeleton className="mx-auto h-6 w-full" />
      <Skeleton className="h-48 w-full" />
    </div>
  );
}
