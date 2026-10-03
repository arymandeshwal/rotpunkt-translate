import { ChevronLeftIcon, ChevronRightIcon } from "lucide-react";

import { Button } from "@/components/ui/button";

interface GlossaryPaginationProps {
  page: number;
  pageSize: number;
  total: number;
  onPageChange: (page: number) => void;
}

export function GlossaryPagination({ page, pageSize, total, onPageChange }: GlossaryPaginationProps) {
  const first = total === 0 ? 0 : (page - 1) * pageSize + 1;
  const last = Math.min(page * pageSize, total);
  const lastPage = Math.max(1, Math.ceil(total / pageSize));

  return (
    <div className="flex items-center justify-end gap-2 text-sm text-muted-foreground">
      <span>
        {first}–{last} of {total}
      </span>
      <Button
        variant="outline"
        size="icon-sm"
        aria-label="Previous page"
        disabled={page <= 1}
        onClick={() => onPageChange(page - 1)}
      >
        <ChevronLeftIcon />
      </Button>
      <Button
        variant="outline"
        size="icon-sm"
        aria-label="Next page"
        disabled={page >= lastPage}
        onClick={() => onPageChange(page + 1)}
      >
        <ChevronRightIcon />
      </Button>
    </div>
  );
}
