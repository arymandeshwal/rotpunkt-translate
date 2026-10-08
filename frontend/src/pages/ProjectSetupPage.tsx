import { Loader2 } from "lucide-react";
import { useState } from "react";
import { useNavigate, useParams } from "react-router";
import { toast } from "sonner";
import { Button } from "../components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../components/ui/select";
import { useProject, useUpdateProjectLanguage, useTranslateProject } from "../hooks/useProjects";

import type { components } from "../api/schema";

type LanguageCode = components["schemas"]["ProjectUpdateRequest"]["source_language"];

const LANGUAGES = [
  { code: "de", name: "German" },
  { code: "en", name: "English" },
  { code: "fr", name: "French" },
  { code: "nl", name: "Dutch" },
  { code: "da", name: "Danish" },
  { code: "nb", name: "Norwegian" },
  { code: "es", name: "Spanish" },
];

export function ProjectSetupPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  
  const { data: project, isLoading, error } = useProject(id!);
  const updateMutation = useUpdateProjectLanguage();
  const translateMutation = useTranslateProject();

  // Initialize with 'de' but update once data loads
  const [sourceLang, setSourceLang] = useState<LanguageCode>("de");
  const [targetLang, setTargetLang] = useState<LanguageCode>("en");
  const [isInitialized, setIsInitialized] = useState(false);

  if (project && !isInitialized) {
    setSourceLang((project.documents?.[0]?.source_language as LanguageCode) || "de");
    setIsInitialized(true);
  }

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error || !project) {
    return (
      <div className="p-4 text-destructive">
        Failed to load project details. It may have been deleted.
      </div>
    );
  }

  const doc = project.documents?.[0];

  const translatableCount = doc?.segments?.filter((s) => s.is_translatable).length || 0;
  const skippedCount = (doc?.segments?.length || 0) - translatableCount;

  const handleConfirm = () => {
    if (sourceLang === targetLang) {
      toast.error("Source and target languages cannot be the same");
      return;
    }

    updateMutation.mutate(
      { id: project.id, sourceLanguage: sourceLang },
      {
        onSuccess: () => {
          translateMutation.mutate(
            { id: project.id, targetLanguage: targetLang },
            {
              onSuccess: () => {
                toast.success("Translation started");
                navigate(`/projects/${project.id}`);
              },
              onError: (err) => {
                toast.error("Failed to start translation", { description: err.message });
              }
            }
          );
        },
        onError: (err) => {
          toast.error("Failed to update project", { description: err.message });
        },
      }
    );
  };

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Project Setup</h1>
        <p className="text-muted-foreground">Confirm languages to start translation.</p>
      </div>

      <div className="rounded-xl border bg-card text-card-foreground shadow">
        <div className="flex flex-col space-y-1.5 p-6">
          <h3 className="font-semibold leading-none tracking-tight">File Summary</h3>
          <p className="text-sm text-muted-foreground">{doc?.original_filename}</p>
        </div>
        <div className="p-6 pt-0">
          <dl className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <dt className="text-muted-foreground">Pages</dt>
              <dd className="font-medium">{doc?.pages?.length || 0}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Total Segments</dt>
              <dd className="font-medium">{doc?.segments?.length || 0}</dd>
            </div>
          </dl>
        </div>
      </div>

      <div className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-2">
            <label className="text-sm font-medium leading-none">
              Source Language
            </label>
            <Select value={sourceLang} onValueChange={(val) => setSourceLang(val as LanguageCode)}>
              <SelectTrigger className="w-full">
                <SelectValue placeholder="Select language" />
              </SelectTrigger>
              <SelectContent>
                {LANGUAGES.map((lang) => (
                  <SelectItem key={lang.code} value={lang.code}>
                    {lang.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium leading-none">
              Target Language
            </label>
            <Select value={targetLang} onValueChange={(val) => setTargetLang(val as LanguageCode)}>
              <SelectTrigger className="w-full">
                <SelectValue placeholder="Select language" />
              </SelectTrigger>
              <SelectContent>
                {LANGUAGES.map((lang) => (
                  <SelectItem key={lang.code} value={lang.code} disabled={lang.code === sourceLang}>
                    {lang.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        <p className="text-[0.8rem] text-muted-foreground">
          Segments in languages other than the Source Language will be marked as "do not translate".
          Currently, {skippedCount} out of {doc?.segments?.length || 0} segments will be skipped.
        </p>

        <Button 
          onClick={handleConfirm} 
          disabled={updateMutation.isPending || translateMutation.isPending}
          className="w-full"
        >
          {(updateMutation.isPending || translateMutation.isPending) && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
          Start Translation
        </Button>
      </div>
    </div>
  );
}