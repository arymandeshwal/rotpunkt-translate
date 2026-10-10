import { useProject, useRetranslateSegment, useEditSegment } from "../hooks/useProjects";
import { useParams } from "react-router";
import { Loader2, RefreshCw, AlertTriangle, Check, X, Pencil } from "lucide-react";
import { HighlightedText, type Annotation } from "../components/HighlightedText";
import { Button } from "../components/ui/button";
import { toast } from "sonner";
import { useState } from "react";
import { Textarea } from "../components/ui/textarea";

import { Popover, PopoverContent, PopoverTrigger } from "../components/ui/popover";
import { Label } from "../components/ui/label";
import { MessageSquare } from "lucide-react";
import { CommentsPanel } from "../components/CommentsPanel";
import { Input } from "../components/ui/input";
import { useCreateEntry } from "../hooks/useGlossary";

function GlossaryQuickAddForm({
  sourceText,
  sourceLang,
  targetLang,
  onClose
}: {
  sourceText: string;
  sourceLang: components["schemas"]["LanguageCode"];
  targetLang: components["schemas"]["LanguageCode"];
  onClose: () => void;
}) {
  const createMutation = useCreateEntry();
  const [sourceTerm, setSourceTerm] = useState(sourceText);
  const [targetTerm, setTargetTerm] = useState("");

  const handleSave = () => {
    if (!sourceTerm.trim() || !targetTerm.trim()) {
      toast.error("Both terms are required");
      return;
    }
    createMutation.mutate(
      {
        category: "General",
        description: null,
        is_dnt: false,
        is_case_sensitive: false,
        terms: [
          { language: sourceLang, text: sourceTerm.trim() },
          { language: targetLang, text: targetTerm.trim() },
        ],
      },
      {
        onSuccess: () => {
          toast.success(`Added "${sourceTerm}" to glossary`);
          onClose();
        },
        onError: (err) => toast.error("Failed to add to glossary", { description: err.message }),
      }
    );
  };

  return (
    <div className="grid gap-3 p-1">
      <div className="space-y-1.5">
        <h4 className="font-medium leading-none">Add to Glossary</h4>
        <p className="text-xs text-muted-foreground">Instantly creates a new dictionary rule.</p>
      </div>
      <div className="grid gap-2">
        <div className="grid grid-cols-4 items-center gap-2">
          <Label className="text-right text-xs uppercase">{sourceLang}</Label>
          <Input 
            value={sourceTerm} 
            onChange={(e) => setSourceTerm(e.target.value)} 
            className="col-span-3 h-8 text-xs" 
          />
        </div>
        <div className="grid grid-cols-4 items-center gap-2">
          <Label className="text-right text-xs uppercase">{targetLang}</Label>
          <Input 
            value={targetTerm} 
            onChange={(e) => setTargetTerm(e.target.value)} 
            className="col-span-3 h-8 text-xs" 
            autoFocus 
            onKeyDown={(e) => {
              if (e.key === 'Enter') handleSave();
            }}
          />
        </div>
      </div>
      <div className="flex justify-end gap-2 mt-1">
        <Button variant="ghost" size="sm" className="h-7 text-xs" onClick={onClose}>Cancel</Button>
        <Button size="sm" className="h-7 text-xs" onClick={handleSave} disabled={createMutation.isPending}>
          {createMutation.isPending && <Loader2 className="mr-1 h-3 w-3 animate-spin" />}
          Save
        </Button>
      </div>
    </div>
  );
}

export function ProjectEditorPage() {
  const { id } = useParams<{ id: string }>();

  // Poll every 3 seconds if status is "translating", otherwise stop polling
  const { data: project, isLoading, error } = useProject(id!, 3000);
  const retranslateMutation = useRetranslateSegment();
  const editMutation = useEditSegment();
  
  const [editingSegmentId, setEditingSegmentId] = useState<string | null>(null);
  const [draftText, setDraftText] = useState<string>("");
  const [openComments, setOpenComments] = useState<Record<string, boolean>>({});

  const toggleComments = (segmentId: string) => {
    setOpenComments(prev => ({ ...prev, [segmentId]: !prev[segmentId] }));
  };

  const [glossaryPopState, setGlossaryPopState] = useState<{
    segmentId: string | null;
    sourceText: string;
    sourceLang: components["schemas"]["LanguageCode"];
    targetLang: components["schemas"]["LanguageCode"];
  }>({
    segmentId: null,
    sourceText: "",
    sourceLang: "de",
    targetLang: "en"
  });

  const handleDoubleClick = (e: React.MouseEvent, segmentId: string, lang: "source" | "target") => {
    if (editingSegmentId || (e.target as HTMLElement).tagName === 'TEXTAREA') return;
    
    const selection = window.getSelection();
    const text = selection?.toString().trim();
    if (text && text.length > 0) {
      setGlossaryPopState({
        segmentId,
        sourceText: text,
        sourceLang: lang === "source" ? ((doc?.source_language as components["schemas"]["LanguageCode"]) || "de") : ((targetLanguage as components["schemas"]["LanguageCode"]) || "en"),
        targetLang: lang === "source" ? ((targetLanguage as components["schemas"]["LanguageCode"]) || "en") : ((doc?.source_language as components["schemas"]["LanguageCode"]) || "de"),
      });
      selection?.removeAllRanges();
    }
  };

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
                <div key={`wrapper-${segment.id}`} className="relative">
                  {/* Floating Action Button / Popover anchor attached OUTSIDE the layout flow */}
                  <div className="absolute left-[-16px] top-1/2 -translate-y-1/2 -translate-x-full">
                    <Popover 
                      key={`popover-${segment.id}`} 
                      open={glossaryPopState.segmentId === segment.id} 
                      onOpenChange={(open) => { if (!open) setGlossaryPopState(prev => ({ ...prev, segmentId: null })) }}
                    >
                      <PopoverTrigger asChild>
                        <div className="w-1 h-1 pointer-events-none" />
                      </PopoverTrigger>
                      <PopoverContent side="left" align="center" sideOffset={16} collisionPadding={8} className="w-80 max-w-[95vw] p-0 overflow-hidden shadow-lg border-primary/20 z-50">
                        <GlossaryQuickAddForm 
                          sourceText={glossaryPopState.sourceText}
                          sourceLang={glossaryPopState.sourceLang}
                          targetLang={glossaryPopState.targetLang}
                          onClose={() => setGlossaryPopState(prev => ({ ...prev, segmentId: null }))}
                        />
                      </PopoverContent>
                    </Popover>
                  </div>

                  <div className={`grid grid-cols-2 gap-4 p-4 transition-colors relative ${isEditing ? 'bg-muted/30 shadow-sm' : 'hover:bg-muted/50'}`}>
                      <div 
                        className="text-sm selection:bg-primary/20"
                        onDoubleClick={(e) => handleDoubleClick(e, segment.id, "source")}
                      >
                        {segment.text}
                      </div>
                      <div 
                        className="text-sm flex items-start justify-between gap-4 selection:bg-primary/20"
                        onDoubleClick={(e) => handleDoubleClick(e, segment.id, "target")}
                      >
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
                            onClick={(e) => {
                              // Don't trigger edit mode if they clicked a highlight popover trigger
                              if ((e.target as HTMLElement).closest('mark') || (e.target as HTMLElement).closest('[data-radix-popper-content-wrapper]')) {
                                return;
                              }
                              setDraftText(translation);
                              setEditingSegmentId(segment.id);
                            }}
                          >
                            {translation ? (
                              <HighlightedText 
                                text={translation} 
                                annotations={annotations} 
                                onReplaceTerm={targetLanguage ? (newText) => {
                                  editMutation.mutate(
                                    { projectId: project.id, segmentId: segment.id, targetLanguage, newText },
                                    {
                                      onError: (err) => {
                                        toast.error("Failed to replace term", { description: err.message });
                                      }
                                    }
                                  );
                                } : undefined}
                              />
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
                    
                    <div className="absolute right-2 top-2 flex flex-col gap-1">
                      {segment.is_translatable && targetLanguage && (
                        <Button
                          variant="ghost"
                          size="icon"
                          className="opacity-0 group-hover:opacity-100 transition-opacity h-8 w-8 text-muted-foreground hover:text-primary bg-background/50 backdrop-blur-sm border shadow-sm"
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
                      
                      <Button
                        variant="ghost"
                        size="icon"
                        className={`h-8 w-8 transition-opacity bg-background/50 backdrop-blur-sm border shadow-sm ${openComments[segment.id] || (segment.comments && segment.comments.length > 0) ? 'opacity-100 text-primary' : 'opacity-0 group-hover:opacity-100 text-muted-foreground hover:text-primary'}`}
                        onClick={() => toggleComments(segment.id)}
                        title="Comments"
                      >
                        <div className="relative">
                          <MessageSquare className="h-4 w-4" />
                          {segment.comments && segment.comments.length > 0 && (
                            <span className="absolute -top-1.5 -right-1.5 flex h-4 w-4 items-center justify-center rounded-full bg-primary text-[9px] font-bold text-primary-foreground border-2 border-background shadow-sm">
                              {segment.comments.length}
                            </span>
                          )}
                        </div>
                        <span className="sr-only">Comments</span>
                      </Button>
                    </div>
                  </div>
                  </div>

                  {openComments[segment.id] && (
                    <CommentsPanel 
                      projectId={project.id} 
                      segmentId={segment.id} 
                      comments={segment.comments || []} 
                    />
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}