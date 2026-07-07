import Link from "next/link";
import { FileQuestion } from "lucide-react";

import { buttonVariants } from "@/components/ui/button";

export default function NotFound() {
  return (
    <div
      className="mx-auto flex max-w-md flex-col items-center gap-4 py-24 text-center"
      data-testid="not-found"
    >
      <FileQuestion className="h-10 w-10 text-muted-foreground" />
      <h1 className="text-xl font-semibold">Analysis not found</h1>
      <p className="text-sm text-muted-foreground">
        We could not find that analysis. It may have expired or the link may be wrong.
      </p>
      <Link href="/" className={buttonVariants({ variant: "outline" })}>
        Start a new review
      </Link>
    </div>
  );
}
