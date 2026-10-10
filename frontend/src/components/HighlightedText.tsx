import { Popover, PopoverContent, PopoverTrigger } from "./ui/popover";
import { Info, Replace } from "lucide-react";
import { Button } from "./ui/button";
import { cn } from "../lib/utils";

export type Annotation = {
  start: number;
  end: number;
  type: "glossary" | "dnt" | "kitchen_trade_term" | "ambiguous_term" | "faulty_term";
  text: string;
  preferred_target?: string;
};

interface HighlightedTextProps {
  text: string;
  annotations: Annotation[];
  onReplaceTerm?: (newText: string) => void;
}

const TYPE_STYLES = {
  glossary: "bg-green-100 text-green-900 border-green-200 border-b-2 font-medium",
  dnt: "bg-gray-100 text-gray-900 border-gray-200 border-b-2 font-mono text-[0.9em]",
  kitchen_trade_term: "bg-blue-100 text-blue-900 border-blue-200 border-b-2 font-medium",
  ambiguous_term: "bg-orange-100 text-orange-900 border-orange-200 border-b-2 font-medium",
  faulty_term: "bg-red-100 text-red-900 border-red-200 border-b-2 font-medium",
};

const TYPE_LABELS = {
  glossary: "Glossary Match",
  dnt: "Do Not Translate",
  kitchen_trade_term: "Trade Term (AI)",
  ambiguous_term: "Ambiguous (AI)",
  faulty_term: "Faulty / OCR Error",
};

export function HighlightedText({ text, annotations, onReplaceTerm }: HighlightedTextProps) {
  if (!annotations || annotations.length === 0) {
    return <span>{text}</span>;
  }

  // Ensure annotations are sorted by start index
  const sorted = [...annotations].sort((a, b) => a.start - b.start);
  
  const elements = [];
  let currentIndex = 0;

  for (let i = 0; i < sorted.length; i++) {
    const ann = sorted[i];
    if (!ann) continue;

    // Safety check against bad bounds or unsorted overlaps
    if (ann.start < currentIndex) continue;

    // Add unannotated text before this annotation
    if (ann.start > currentIndex) {
      elements.push(<span key={`text-${currentIndex}`}>{text.substring(currentIndex, ann.start)}</span>);
    }

    // Add the annotated text
    const markedText = text.substring(ann.start, ann.end);
    const styleClass = TYPE_STYLES[ann.type] || "bg-yellow-100 text-yellow-900";
    const label = TYPE_LABELS[ann.type] || "Match";

    elements.push(
      <Popover key={`mark-${i}`}>
        <PopoverTrigger asChild>
          <mark className={cn("cursor-pointer bg-transparent rounded-sm px-0.5 mx-0.5", styleClass)}>
            {markedText}
          </mark>
        </PopoverTrigger>
        <PopoverContent className="w-auto p-3 flex flex-col gap-3 text-sm shadow-md">
          <div className="flex items-start space-x-2">
            <Info className="w-4 h-4 text-muted-foreground mt-0.5" />
            <div>
              <p className="font-semibold">{label}</p>
              {ann.type === "glossary" && (
                <p className="text-muted-foreground text-xs">Standardized kitchen term.</p>
              )}
              {ann.type === "dnt" && (
                <p className="text-muted-foreground text-xs">Protected brand or product name.</p>
              )}
              {ann.type === "kitchen_trade_term" && (
                <p className="text-muted-foreground text-xs">Industry jargon identified by AI.</p>
              )}
              {ann.type === "ambiguous_term" && (
                <p className="text-muted-foreground text-xs">Meaning depends on kitchen context. Please review.</p>
              )}
            </div>
          </div>
          {onReplaceTerm && ann.preferred_target && ann.preferred_target.toLowerCase() !== markedText.toLowerCase() && (
            <div className="border-t pt-2 mt-1">
              <p className="text-xs text-muted-foreground mb-2">
                Preferred translation: <span className="font-semibold text-foreground">{ann.preferred_target}</span>
              </p>
              <Button 
                size="sm" 
                variant="secondary" 
                className="w-full text-xs h-7"
                onClick={() => {
                  const newFullText = text.substring(0, ann.start) + ann.preferred_target + text.substring(ann.end);
                  onReplaceTerm(newFullText);
                }}
              >
                <Replace className="w-3 h-3 mr-2" />
                Replace
              </Button>
            </div>
          )}
        </PopoverContent>
      </Popover>
    );

    currentIndex = ann.end;
  }

  // Add remaining unannotated text
  if (currentIndex < text.length) {
    elements.push(<span key={`text-${currentIndex}`}>{text.substring(currentIndex)}</span>);
  }

  return <span className="leading-relaxed">{elements}</span>;
}