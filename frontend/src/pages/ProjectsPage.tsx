import { Loader2, UploadCloud } from "lucide-react";
import { useCallback, useState } from "react";
import { useNavigate } from "react-router";
import { toast } from "sonner";
import { useUploadProject } from "../hooks/useProjects";

export function ProjectsPage() {
  const navigate = useNavigate();
  const uploadMutation = useUploadProject();
  const [isDragging, setIsDragging] = useState(false);

  const handleFile = useCallback((file: File) => {
    if (file.type !== "application/pdf") {
      toast.error("Invalid file type", { description: "Please upload a PDF file." });
      return;
    }
    uploadMutation.mutate(file, {
      onSuccess: (data) => {
        toast.success("Project created", { description: `Parsed ${data.documents?.[0]?.pages?.length || 0} pages.` });
        navigate(`/projects/${data.id}/setup`);
      },
      onError: (error) => {
        toast.error("Upload failed", { description: error.message });
      },
    });
  }, [navigate, uploadMutation]);

  const onDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const onDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFile(e.dataTransfer.files[0]);
    }
  }, [handleFile]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Projects</h1>
        <p className="text-muted-foreground">Upload a kitchen document to start a new translation project.</p>
      </div>

      <div
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        onDrop={onDrop}
        className={`mt-8 flex flex-col items-center justify-center rounded-lg border-2 border-dashed p-12 transition-colors
          ${isDragging ? "border-primary bg-primary/10" : "border-border bg-card"}
          ${uploadMutation.isPending ? "pointer-events-none opacity-50" : ""}
        `}
      >
        {uploadMutation.isPending ? (
          <Loader2 className="mb-4 h-10 w-10 animate-spin text-primary" />
        ) : (
          <UploadCloud className={`mb-4 h-10 w-10 ${isDragging ? "text-primary" : "text-muted-foreground"}`} />
        )}
        
        <h3 className="mb-1 text-lg font-semibold">
          {uploadMutation.isPending ? "Parsing PDF..." : "Drag & drop your PDF here"}
        </h3>
        
        {!uploadMutation.isPending && (
          <>
            <p className="mb-4 text-sm text-muted-foreground">or click to browse from your computer</p>
            <input
              type="file"
              accept="application/pdf"
              className="hidden"
              id="file-upload"
              onChange={(e) => {
                if (e.target.files && e.target.files[0]) {
                  handleFile(e.target.files[0]);
                }
              }}
            />
            <label
              htmlFor="file-upload"
              className="cursor-pointer rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
            >
              Select File
            </label>
          </>
        )}
      </div>
    </div>
  );
}