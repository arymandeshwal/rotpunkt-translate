import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  api,
  unwrap,
  type GlossaryCategory,
  type GlossaryEntryCreate,
  type GlossaryEntryUpdate,
  type LanguageCode,
} from "@/api/client";

export type SortField = LanguageCode | "created_at" | "updated_at";

export interface GlossaryQuery {
  q?: string;
  category?: GlossaryCategory;
  doNotTranslate?: boolean;
  caseSensitive?: boolean;
  missing?: LanguageCode;
  sort: SortField;
  order: "asc" | "desc";
  page: number;
  pageSize: number;
}

const glossaryKey = ["glossary"] as const;

export function useLanguages() {
  return useQuery({
    queryKey: ["languages"],
    queryFn: async () => unwrap(await api.GET("/api/languages")),
    staleTime: Infinity,
  });
}

export function useGlossaryList(query: GlossaryQuery) {
  return useQuery({
    queryKey: [...glossaryKey, "list", query],
    queryFn: async () =>
      unwrap(
        await api.GET("/api/glossary", {
          params: {
            query: {
              q: query.q || undefined,
              category: query.category,
              do_not_translate: query.doNotTranslate,
              case_sensitive: query.caseSensitive,
              missing: query.missing,
              sort: query.sort,
              order: query.order,
              page: query.page,
              page_size: query.pageSize,
            },
          },
        }),
      ),
    // Keep showing the current page while the next one loads.
    placeholderData: keepPreviousData,
  });
}

function useInvalidateGlossary() {
  const queryClient = useQueryClient();
  return () => queryClient.invalidateQueries({ queryKey: glossaryKey });
}

export function useCreateEntry() {
  const invalidate = useInvalidateGlossary();
  return useMutation({
    mutationFn: async (body: GlossaryEntryCreate) =>
      unwrap(await api.POST("/api/glossary", { body })),
    onSuccess: invalidate,
  });
}

export function useUpdateEntry() {
  const invalidate = useInvalidateGlossary();
  return useMutation({
    mutationFn: async ({ id, body }: { id: number; body: GlossaryEntryUpdate }) =>
      unwrap(
        await api.PATCH("/api/glossary/{entry_id}", {
          params: { path: { entry_id: id } },
          body,
        }),
      ),
    onSuccess: invalidate,
  });
}

export function useDeleteEntry() {
  const invalidate = useInvalidateGlossary();
  return useMutation({
    mutationFn: async (id: number) => {
      const { error, response } = await api.DELETE("/api/glossary/{entry_id}", {
        params: { path: { entry_id: id } },
      });
      if (!response.ok) unwrap({ error, response });
    },
    onSuccess: invalidate,
  });
}
