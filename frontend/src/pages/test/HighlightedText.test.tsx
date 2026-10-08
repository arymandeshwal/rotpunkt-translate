import { render, screen } from "@testing-library/react";
import { HighlightedText, type Annotation } from "../../components/HighlightedText";

describe("HighlightedText", () => {
  it("renders plain text when no annotations exist", () => {
    render(<HighlightedText text="Hello world" annotations={[]} />);
    expect(screen.getByText("Hello world")).toBeInTheDocument();
  });

  it("renders annotated text correctly", () => {
    const annotations: Annotation[] = [
      { start: 6, end: 11, type: "glossary", text: "world" },
    ];
    render(<HighlightedText text="Hello world" annotations={annotations} />);
    
    expect(screen.getByText(/Hello/i)).toBeInTheDocument();
    
    const mark = screen.getByText("world");
    expect(mark.tagName.toLowerCase()).toBe("mark");
    expect(mark).toHaveClass("bg-green-100");
  });

  it("handles multiple annotations and overlapping logic safely", () => {
    const annotations: Annotation[] = [
      { start: 0, end: 5, type: "kitchen_trade_term", text: "Hello" },
      { start: 6, end: 11, type: "dnt", text: "world" },
    ];
    render(<HighlightedText text="Hello world" annotations={annotations} />);
    
    const mark1 = screen.getByText("Hello");
    expect(mark1).toHaveClass("bg-blue-100");
    
    const mark2 = screen.getByText("world");
    expect(mark2).toHaveClass("bg-gray-100");
  });
});
