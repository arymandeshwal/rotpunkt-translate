import { useProject, useRetranslateSegment } from "../hooks/useProjects";
import { useParams } from "react-router";
import { Loader2, RefreshCw } from "lucide-react";
import { HighlightedText, type Annotation } from "../components/HighlightedText";
import { Button } from "../components/ui/button";
import { toast } from "sonner";

export function ProjectEditorPage() {
  const { id } = useParams<{ id: string }>();

  // Poll every 3 seconds if status is "translating", otherwise stop polling
  const { data: project, isLoading, error } = useProject(id!, 3000);
  const retranslateMutation = useRetranslateSegment();

  if (isLoading || !project) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 text-destructive">
        Failed to load project details. It may have been deleted.
      </div>
    );
  }

  const isTranslating = project.status === "translating";
  const doc = project.documents?.[0];

  if (!doc) {
    return <div>No documents found for this project.</div>;
  }

  // Find the target language by checking the translations dictionary of the first translatable segment
  const translatableSegment = doc.segments.find(s => s.is_translatable && Object.keys(s.translations || {}).length > 0);
  const targetLanguage = translatableSegment ? Object.keys(translatableSegment.translations || {})[0] : null;

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">{project.name}</h1>
          <p className="text-muted-foreground">
            Status: <span className="font-semibold uppercase">{project.status}</span>
          </p>
        </div>
      </div>

      {isTranslating ? (
        <div className="flex flex-col items-center justify-center space-y-4 rounded-xl border bg-card p-12 text-center shadow">
          <Loader2 className="h-10 w-10 animate-spin text-primary" />
          <h2 className="text-xl font-semibold">Translating document...</h2>
          <p className="text-muted-foreground">This may take a minute or two depending on the size of the file.</p>
        </div>
      ) : (
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4 rounded-t-xl border-b bg-muted p-4 font-semibold">
            <div>Source ({doc.source_language?.toUpperCase() || "DE"})</div>
            <div>Target ({targetLanguage?.toUpperCase() || "EN"})</div>
          </div>
          
          <div className="divide-y rounded-xl border bg-card shadow">
            {doc.segments.map((segment) => {
              const translation = targetLanguage ? (segment.translations as Record<string, string>)?.[targetLanguage] : null;
              const annotations = targetLanguage ? (segment.annotations as Record<string, Annotation[]>)?.[targetLanguage] || [] : [];
              
              return (
                <div key={segment.id} className="grid grid-cols-2 gap-4 p-4 hover:bg-muted/50 transition-colors group">
                  <div className="text-sm">
                    {segment.text}
                  </div>
                  <div className="text-sm flex items-start justify-between gap-4">
                    <div className="flex-1">
                      {!segment.is_translatable ? (
                        <span className="text-muted-foreground italic">Skipped (Not in source language)</span>
                      ) : translation ? (
                        <HighlightedText text={translation} annotations={annotations} />
                      ) : (
                        <span className="text-muted-foreground italic">No translation available</span>
                      )}
                    </div>
                    {segment.is_translatable && targetLanguage && (
                      <Button
                        variant="ghost"
                        size="icon"
                        className="opacity-0 group-hover:opacity-100 transition-opacity h-8 w-8 text-muted-foreground hover:text-primary"
                        disabled={retranslateMutation.isPending && retranslateMutation.variables?.segmentId === segment.id}
                        onClick={() => {
                          retranslateMutation.mutate(
                            { projectId: project.id, segmentId: segment.id, targetLanguage },
                            {
                              onError: (err) => {
                                toast.error("Retranslation failed", { description: err.message });
                              }
                            }
                          );
                        }}
                        title="Re-translate segment"
                      >
                        <RefreshCw className={`h-4 w-4 ${retranslateMutation.isPending && retranslateMutation.variables?.segmentId === segment.id ? 'animate-spin text-primary' : ''}`} />
                        <span className="sr-only">Re-translate segment</span>
                      </Button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}