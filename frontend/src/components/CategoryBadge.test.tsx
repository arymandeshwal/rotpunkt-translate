import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { GlossaryCategory } from "@/api/client";

import { CategoryBadge } from "./CategoryBadge";

describe("CategoryBadge", () => {
  it.each<[GlossaryCategory, string, string]>([
    ["kitchen_term", "Kitchen term", "bg-sky-100"],
    ["general", "General", "bg-emerald-100"],
    ["product_name", "Product name", "bg-white"],
  ])("renders %s with its label and highlight colour", (category, label, colourClass) => {
    render(<CategoryBadge category={category} />);

    expect(screen.getByText(label)).toHaveClass(colourClass);
  });
});
