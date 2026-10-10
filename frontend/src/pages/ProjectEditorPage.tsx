import { useProject, useRetranslateSegment, useEditSegment } from "../hooks/useProjects";
import { useParams } from "react-router";
import { Loader2, RefreshCw, AlertTriangle, Check, X, Pencil } from "lucide-react";
import { HighlightedText, type Annotation } from "../components/HighlightedText";
import { Button } from "../components/ui/button";
import { toast } from "sonner";
import { useState } from "react";
import { Textarea } from "../components/ui/textarea";

export function ProjectEditorPage() {
  const { id } = useParams<{ id: string }>();

  // Poll every 3 seconds if status is "translating", otherwise stop polling
  const { data: project, isLoading, error } = useProject(id!, 3000);
  const retranslateMutation = useRetranslateSegment();
  const editMutation = useEditSegment();
  
  const [editingSegmentId, setEditingSegmentId] = useState<string | null>(null);
  const [draftText, setDraftText] = useState<string>("");

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
              const issues = targetLanguage ? (segment.issues as Record<string, {type: string; message: string; term?: string; expected?: string}[]>)?.[targetLanguage] || [] : [];
              
              const isEditing = editingSegmentId === segment.id;

              return (
                <div key={segment.id} className={`grid grid-cols-2 gap-4 p-4 transition-colors group ${isEditing ? 'bg-muted/30 shadow-sm' : 'hover:bg-muted/50'}`}>
                  <div className="text-sm">
                    {segment.text}
                  </div>
                  <div className="text-sm flex items-start justify-between gap-4">
                    <div className="flex-1 flex flex-col gap-2">
                      {!segment.is_translatable ? (
                        <span className="text-muted-foreground italic">Skipped (Not in source language)</span>
                      ) : isEditing ? (
                        <div className="flex flex-col gap-2 relative">
                          <Textarea
                            className="min-h-[100px] text-sm leading-relaxed pr-24 resize-none"
                            value={draftText}
                            onChange={(e) => setDraftText(e.target.value)}
                            autoFocus
                          />
                          <div className="absolute bottom-2 right-2 flex gap-1">
                            <Button 
                              size="sm" 
                              variant="outline" 
                              className="h-7 px-2"
                              onClick={() => {
                                setEditingSegmentId(null);
                                setDraftText("");
                              }}
                            >
                              <X className="h-3.5 w-3.5" />
                            </Button>
                            <Button 
                              size="sm" 
                              className="h-7 px-2"
                              disabled={editMutation.isPending && editMutation.variables?.segmentId === segment.id}
                              onClick={() => {
                                if (!targetLanguage) return;
                                editMutation.mutate(
                                  { projectId: project.id, segmentId: segment.id, targetLanguage, newText: draftText },
                                  {
                                    onSuccess: () => {
                                      setEditingSegmentId(null);
                                      setDraftText("");
                                    },
                                    onError: (err) => {
                                      toast.error("Failed to save edit", { description: err.message });
                                    }
                                  }
                                );
                              }}
                            >
                              {editMutation.isPending && editMutation.variables?.segmentId === segment.id ? (
                                <Loader2 className="h-3.5 w-3.5 animate-spin" />
                              ) : (
                                <Check className="h-3.5 w-3.5" />
                              )}
                            </Button>
                          </div>
                        </div>
                      ) : translation !== null ? (
                        <>
                          <div 
                            className="cursor-text hover:bg-muted/50 p-1 -m-1 rounded transition-colors group/text relative min-h-6"
                            onClick={() => {
                              setDraftText(translation);
                              setEditingSegmentId(segment.id);
                            }}
                          >
                            {translation ? (
                              <HighlightedText text={translation} annotations={annotations} />
                            ) : (
                              <span className="text-muted-foreground italic">&lt;Empty translation&gt;</span>
                            )}
                            <div className="absolute right-2 top-2 opacity-0 group-hover/text:opacity-100 transition-opacity bg-background border shadow-sm rounded p-1 text-muted-foreground pointer-events-none">
                              <Pencil className="h-3.5 w-3.5" />
                            </div>
                          </div>
                          {issues.length > 0 && (
                            <div className="flex flex-col gap-1 mt-2">
                              {issues.map((issue, idx) => (
                                <div key={idx} className="flex items-start gap-2 text-xs font-medium text-amber-600 bg-amber-50 dark:text-amber-400 dark:bg-amber-950/30 p-2 rounded-md border border-amber-200 dark:border-amber-900/50">
                                  <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5" />
                                  <span>{issue.message}</span>
                                </div>
                              ))}
                            </div>
                          )}
                        </>
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