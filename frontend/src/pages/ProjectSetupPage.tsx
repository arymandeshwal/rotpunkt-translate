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
import { useProject, useUpdateProjectLanguage } from "../hooks/useProjects";

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

  // Initialize with 'de' but update once data loads
  const [sourceLang, setSourceLang] = useState<LanguageCode>("de");
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
    updateMutation.mutate(
      { id: project.id, sourceLanguage: sourceLang },
      {
        onSuccess: () => {
          toast.success("Project setup complete");
          // Redirect to a placeholder for the actual translation view
          navigate("/"); 
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
        <p className="text-muted-foreground">Confirm the document's source language.</p>
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
        <div className="space-y-2">
          <label className="text-sm font-medium leading-none">
            Detected Source Language
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
          <p className="text-[0.8rem] text-muted-foreground">
            Segments in other languages will be marked as "do not translate".
            Currently, {skippedCount} out of {doc?.segments?.length || 0} segments will be skipped.
          </p>
        </div>

        <Button 
          onClick={handleConfirm} 
          disabled={updateMutation.isPending}
          className="w-full"
        >
          {updateMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
          Confirm & Continue
        </Button>
      </div>
    </div>
  );
}