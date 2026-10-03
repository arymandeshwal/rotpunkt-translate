import type { GlossaryCategory } from "@/api/client";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

// Same colours the translation preview uses to highlight these kinds of terms.
export const CATEGORY_STYLES: Record<GlossaryCategory, { label: string; className: string }> = {
  kitchen_term: { label: "Kitchen term", className: "bg-sky-100 text-sky-800 border-sky-200" },
  general: { label: "General", className: "bg-emerald-100 text-emerald-800 border-emerald-200" },
  product_name: { label: "Product name", className: "bg-white text-stone-700 border-stone-300" },
};

export function CategoryBadge({ category }: { category: GlossaryCategory }) {
  const style = CATEGORY_STYLES[category];
  return (
    <Badge variant="outline" className={cn(style.className)}>
      {style.label}
    </Badge>
  );
}
