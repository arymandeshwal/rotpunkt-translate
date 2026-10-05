import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";
import type { components, paths } from "../api/schema";

type ProjectResponse = components["schemas"]["ProjectResponse"];
type UploadBody = paths["/api/projects"]["post"]["requestBody"]["content"]["multipart/form-data"];

export function useUploadProject() {
  return useMutation({
    mutationFn: async (file: File) => {
      // openapi-fetch natively supports passing a FormData body
      const formData = new FormData();
      formData.append("file", file);

      const { data, error } = await api.POST("/api/projects", {
        body: formData as unknown as UploadBody,
      });

      if (error) {
        throw new Error((error as { detail?: string }).detail || "Upload failed");
      }
      return data as ProjectResponse;
    },
  });
}

export function useProject(id: string) {
  return useQuery({
    queryKey: ["projects", id],
    queryFn: async () => {
      const { data, error } = await api.GET("/api/projects/{project_id}", {
        params: { path: { project_id: id } },
      });
      if (error) throw error;
      return data as ProjectResponse;
    },
    enabled: !!id,
  });
}

export function useUpdateProjectLanguage() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      id,
      sourceLanguage,
    }: {
      id: string;
      sourceLanguage: components["schemas"]["ProjectUpdateRequest"]["source_language"];
    }) => {
      const { data, error } = await api.PATCH("/api/projects/{project_id}", {
        params: { path: { project_id: id } },
        body: { source_language: sourceLanguage },
      });
      if (error) throw error;
      return data as ProjectResponse;
    },
    onSuccess: (data, variables) => {
      queryClient.setQueryData(["projects", variables.id], data);
    },
  });
}