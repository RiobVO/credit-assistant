// Lifecycle черновика формы досье. Save идёт на переход между шагами
// (вызов saveDraft из page.tsx), не on-input. POST для нового draft,
// PUT для существующего; PUT-404 (TTL истёк / удалён) → fallback POST.
//
// На mount при `initialDraftId !== null` грузим payload и через
// `form.reset()` наполняем форму. 404 / битый id → state{draftId=null},
// форма остаётся в defaults — caller чистит URL.

"use client";

import { useMutation } from "@tanstack/react-query";
import { useCallback, useEffect, useRef, useState } from "react";
import type { UseFormReturn } from "react-hook-form";

import { ApiError, createDraft, getDraft, updateDraft } from "@/lib/api";

import type { FormValues } from "../schema";

export type UseFormDraftResult = {
  draftId: string | null;
  savedAt: Date | null;
  isSaving: boolean;
  saveError: unknown;
  isLoading: boolean;
  loadFailed: boolean;
  saveDraft: (values: FormValues) => void;
  resetDraft: () => void;
};

type Args = {
  form: UseFormReturn<FormValues>;
  initialDraftId: string | null;
};

export function useFormDraft({ form, initialDraftId }: Args): UseFormDraftResult {
  const [draftId, setDraftId] = useState<string | null>(initialDraftId);
  const [savedAt, setSavedAt] = useState<Date | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(initialDraftId !== null);
  const [loadFailed, setLoadFailed] = useState<boolean>(false);

  // Защита от двойного mount-load в React 18 strict mode.
  const loadedRef = useRef<string | null>(null);

  const mutation = useMutation({
    mutationFn: async (values: FormValues): Promise<string> => {
      const payload = values as unknown as Record<string, unknown>;
      if (draftId === null) {
        const created = await createDraft(payload);
        return created.draft_id;
      }
      try {
        const updated = await updateDraft(draftId, payload);
        return updated.draft_id;
      } catch (err) {
        // TTL истёк / draft удалён — создаём новый.
        if (err instanceof ApiError && err.status === 404) {
          const created = await createDraft(payload);
          return created.draft_id;
        }
        throw err;
      }
    },
    onSuccess: (newDraftId) => {
      setDraftId(newDraftId);
      setSavedAt(new Date());
    },
  });

  useEffect(() => {
    if (initialDraftId === null) return;
    if (loadedRef.current === initialDraftId) return;
    loadedRef.current = initialDraftId;

    let cancelled = false;
    setIsLoading(true);
    setLoadFailed(false);

    getDraft(initialDraftId)
      .then((res) => {
        if (cancelled) return;
        // Payload — raw FormValues. Если структура изменится несовместимо,
        // reset поднимет zod-ошибки только при попытке submit; для нас это OK.
        form.reset(res.payload as unknown as FormValues);
        setDraftId(res.draft_id);
      })
      .catch((err) => {
        if (cancelled) return;
        if (err instanceof ApiError && err.status === 404) {
          setLoadFailed(true);
          setDraftId(null);
        } else {
          // Сетевые / 500 — тоже считаем failed, но без чистки URL.
          setLoadFailed(true);
        }
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [initialDraftId, form]);

  const saveDraft = useCallback(
    (values: FormValues) => {
      mutation.mutate(values);
    },
    [mutation],
  );

  const resetDraft = useCallback(() => {
    setDraftId(null);
    setSavedAt(null);
    setLoadFailed(false);
    mutation.reset();
  }, [mutation]);

  return {
    draftId,
    savedAt,
    isSaving: mutation.isPending,
    saveError: mutation.isError ? mutation.error : null,
    isLoading,
    loadFailed,
    saveDraft,
    resetDraft,
  };
}
