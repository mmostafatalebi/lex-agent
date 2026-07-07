import { Loader2 } from "lucide-react";

export function AnalysisProgress({ message }: { message: string }) {
  return (
    <div
      className="flex flex-col items-center justify-center gap-4 py-24 text-center"
      data-testid="analysis-progress"
    >
      <Loader2 className="h-10 w-10 animate-spin text-primary" />
      <p className="text-lg font-medium">{message}</p>
      <p className="klabel">This can take a minute while the model works.</p>
    </div>
  );
}
