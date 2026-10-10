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

export function useProject(id: string, refetchInterval?: number | false) {
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
    refetchInterval,
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

export function useTranslateProject() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      id,
      targetLanguage,
    }: {
      id: string;
      targetLanguage: components["schemas"]["TranslateRequest"]["target_language"];
    }) => {
      const { data, error } = await api.POST("/api/projects/{project_id}/translate", {
        params: { path: { project_id: id } },
        body: { target_language: targetLanguage },
      });
      if (error) throw error;
      return data;
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ["projects", variables.id] });
    },
  });
}

export function useEditSegment() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      projectId,
      segmentId,
      targetLanguage,
      newText,
    }: {
      projectId: string;
      segmentId: string;
      targetLanguage: components["schemas"]["SegmentEditRequest"]["target_language"];
      newText: string;
    }) => {
      const { data, error } = await api.PATCH(
        "/api/projects/{project_id}/segments/{segment_id}",
        {
          params: { path: { project_id: projectId, segment_id: segmentId } },
          body: { target_language: targetLanguage, new_text: newText },
        }
      );
      if (error) throw error;
      return data;
    },
    onSuccess: (newSegment, variables) => {
      queryClient.setQueryData(
        ["projects", variables.projectId],
        (oldData: ProjectResponse | undefined) => {
          if (!oldData || !oldData.documents || oldData.documents.length === 0) return oldData;
          
          const newDocs = [...oldData.documents];
          const newSegments = newDocs[0].segments.map((seg) => 
            seg.id === variables.segmentId ? newSegment : seg
          );
          
          newDocs[0] = { ...newDocs[0]!, segments: newSegments };
          return { ...oldData, documents: newDocs };
        }
      );
    },
  });
}

export function useRetranslateSegment() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      projectId,
      segmentId,
      targetLanguage,
    }: {
      projectId: string;
      segmentId: string;
      targetLanguage: components["schemas"]["TranslateRequest"]["target_language"];
    }) => {
      const { data, error } = await api.POST(
        "/api/projects/{project_id}/segments/{segment_id}/retranslate",
        {
          params: { path: { project_id: projectId, segment_id: segmentId } },
          body: { target_language: targetLanguage },
        }
      );
      if (error) throw error;
      return data;
    },
    onSuccess: (newSegment, variables) => {
      // Optimistically update the cache for the specific segment
      queryClient.setQueryData(
        ["projects", variables.projectId],
        (oldData: ProjectResponse | undefined) => {
          if (!oldData || !oldData.documents || oldData.documents.length === 0) return oldData;
          
          const newDocs = [...oldData.documents];
          const newSegments = newDocs[0].segments.map((seg) => 
            seg.id === variables.segmentId ? newSegment : seg
          );
          
          newDocs[0] = { ...newDocs[0]!, segments: newSegments };
          return { ...oldData, documents: newDocs };
        }
      );
    },
  });
}

export function useAddSegmentComment() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      projectId,
      segmentId,
      text,
    }: {
      projectId: string;
      segmentId: string;
      text: string;
    }) => {
      const { data, error } = await api.POST(
        "/api/projects/{project_id}/segments/{segment_id}/comments",
        {
          params: { path: { project_id: projectId, segment_id: segmentId } },
          body: { text },
        }
      );
      if (error) throw error;
      return data;
    },
    onSuccess: (newComment, variables) => {
      queryClient.setQueryData(
        ["projects", variables.projectId],
        (oldData: ProjectResponse | undefined) => {
          if (!oldData || !oldData.documents || oldData.documents.length === 0) return oldData;
          
          const newDocs = [...oldData.documents];
          const newSegments = newDocs[0].segments.map((seg) => {
            if (seg.id === variables.segmentId) {
              return { ...seg, comments: [...(seg.comments || []), newComment] };
            }
            return seg;
          });
          
          newDocs[0] = { ...newDocs[0]!, segments: newSegments };
          return { ...oldData, documents: newDocs };
        }
      );
    },
  });
}

export function useDeleteSegmentComment() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      projectId,
      segmentId,
      commentId,
    }: {
      projectId: string;
      segmentId: string;
      commentId: string;
    }) => {
      const { error } = await api.DELETE(
        "/api/projects/{project_id}/segments/{segment_id}/comments/{comment_id}",
        {
          params: { path: { project_id: projectId, segment_id: segmentId, comment_id: commentId } },
        }
      );
      if (error) throw error;
      return commentId;
    },
    onSuccess: (deletedCommentId, variables) => {
      queryClient.setQueryData(
        ["projects", variables.projectId],
        (oldData: ProjectResponse | undefined) => {
          if (!oldData || !oldData.documents || oldData.documents.length === 0) return oldData;
          
          const newDocs = [...oldData.documents];
          const newSegments = newDocs[0].segments.map((seg) => {
            if (seg.id === variables.segmentId) {
              return { 
                ...seg, 
                comments: (seg.comments || []).filter(c => c.id !== deletedCommentId) 
              };
            }
            return seg;
          });
          
          newDocs[0] = { ...newDocs[0]!, segments: newSegments };
          return { ...oldData, documents: newDocs };
        }
      );
    },
  });
}
export function useApproveProject() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: string) => {
      const { data, error } = await api.POST("/api/projects/{project_id}/approve", {
        params: { path: { project_id: id } },
      });
      if (error) throw error;
      return data;
    },
    onSuccess: (data, variables) => {
      queryClient.setQueryData(["projects", variables], data);
    },
  });
}
