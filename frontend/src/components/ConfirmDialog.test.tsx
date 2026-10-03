import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";

import { ConfirmDialog } from "./ConfirmDialog";

function Harness({ onConfirm }: { onConfirm: () => void }) {
  const [open, setOpen] = useState(true);
  return (
    <>
      <span>{open ? "open" : "closed"}</span>
      <ConfirmDialog
        open={open}
        onOpenChange={setOpen}
        title="Delete entry?"
        description="Hochschrank will be removed from the glossary."
        confirmLabel="Delete"
        destructive
        onConfirm={onConfirm}
      />
    </>
  );
}

describe("ConfirmDialog", () => {
  it("shows the title and description", () => {
    render(<Harness onConfirm={vi.fn()} />);

    expect(screen.getByRole("alertdialog", { name: "Delete entry?" })).toBeInTheDocument();
    expect(screen.getByText("Hochschrank will be removed from the glossary.")).toBeInTheDocument();
  });

  it("calls onConfirm and closes when confirmed", async () => {
    const onConfirm = vi.fn();
    render(<Harness onConfirm={onConfirm} />);

    await userEvent.click(screen.getByRole("button", { name: "Delete" }));

    expect(onConfirm).toHaveBeenCalledOnce();
    expect(screen.getByText("closed")).toBeInTheDocument();
  });

  it.each([
    ["the cancel button", async () => userEvent.click(screen.getByRole("button", { name: "Cancel" }))],
    ["Escape", async () => userEvent.keyboard("{Escape}")],
  ])("closes without confirming via %s", async (_, dismiss) => {
    const onConfirm = vi.fn();
    render(<Harness onConfirm={onConfirm} />);

    await dismiss();

    expect(onConfirm).not.toHaveBeenCalled();
    expect(screen.getByText("closed")).toBeInTheDocument();
  });
});
