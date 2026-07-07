import Link from "next/link";
import { ScaleIcon } from "lucide-react";

import { ThemeToggle } from "@/components/theme-toggle";

export function Nav() {
  return (
    <header className="border-b border-border">
      <div className="container flex h-16 items-center justify-between">
        <Link href="/" className="flex items-center gap-2">
          <ScaleIcon className="h-5 w-5 text-primary" />
          <span className="text-lg font-semibold tracking-tight">LexAgent</span>
        </Link>
        <ThemeToggle />
      </div>
    </header>
  );
}
