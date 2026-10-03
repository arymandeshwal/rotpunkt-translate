import { useQuery } from "@tanstack/react-query";

import { getHealth } from "../api/client";

export function HealthBadge() {
  const { data, isPending, isError } = useQuery({
    queryKey: ["health"],
    queryFn: getHealth,
    refetchInterval: 30_000,
    retry: false,
  });

  const [label, dot] = isPending
    ? ["Checking…", "bg-stone-300"]
    : isError
      ? ["API offline", "bg-red-500"]
      : data.status === "ok"
        ? ["All systems online", "bg-emerald-500"]
        : ["Database unavailable", "bg-amber-500"];

  return (
    <span role="status" className="inline-flex items-center gap-2 text-xs text-stone-500">
      <span aria-hidden className={`h-2 w-2 rounded-full ${dot}`} />
      {label}
    </span>
  );
}
