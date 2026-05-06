import { useEffect, useRef, useState } from "react";

import { IconClose, IconPaperclip } from "@/components/ui/action-icons";
import { InlineSpinner } from "@/components/ui/InlineSpinner";
import { toast } from "@/lib/toast";

type Props = {
  onSend: (text: string, files: File[]) => Promise<void>;
  disabled?: boolean;
  placeholder?: string;
};

type PendingAttachment = { id: string; file: File; previewUrl: string };

const MAX_CHARS = 2000;
const MAX_ATTACHMENTS = 4;
const MAX_BYTES = 5 * 1024 * 1024;
const ALLOWED_MIMES = ["image/jpeg", "image/png", "image/webp"] as const;

function isAllowedMime(mime: string): mime is (typeof ALLOWED_MIMES)[number] {
  return (ALLOWED_MIMES as readonly string[]).includes(mime);
}

export function ComposerBar({
  onSend,
  disabled = false,
  placeholder = "Descreva o post que você quer criar…",
}: Props) {
  const [text, setText] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [attachments, setAttachments] = useState<PendingAttachment[]>([]);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const attachmentsRef = useRef(attachments);
  attachmentsRef.current = attachments;

  const charCount = text.length;
  const canSend = text.trim().length > 0 && !disabled && !submitting;
  const attachBlocked =
    disabled || submitting || attachments.length >= MAX_ATTACHMENTS;

  useEffect(() => {
    return () => {
      attachmentsRef.current.forEach((a) => URL.revokeObjectURL(a.previewUrl));
    };
  }, []);

  function autoResize() {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 120) + "px";
  }

  function handleChange(e: React.ChangeEvent<HTMLTextAreaElement>) {
    if (e.target.value.length > MAX_CHARS) return;
    setText(e.target.value);
    autoResize();
  }

  function handleFiles(e: React.ChangeEvent<HTMLInputElement>) {
    const list = Array.from(e.target.files || []);
    const input = e.target;
    input.value = "";
    if (!list?.length) return;

    let tooLarge = 0;
    let badMime = 0;
    let overLimit = 0;
    const accepted: PendingAttachment[] = [];

    setAttachments((prev) => {
      let slots = MAX_ATTACHMENTS - prev.length;
      for (const file of list) {
        if (slots <= 0) {
          overLimit += 1;
          continue;
        }
        if (!isAllowedMime(file.type)) {
          badMime += 1;
          continue;
        }
        if (file.size > MAX_BYTES) {
          tooLarge += 1;
          continue;
        }
        accepted.push({
          id: crypto.randomUUID(),
          file,
          previewUrl: URL.createObjectURL(file),
        });
        slots -= 1;
      }
      if (accepted.length === 0) return prev;
      return [...prev, ...accepted];
    });

    const rejected = tooLarge + badMime + overLimit;
    if (rejected > 0) {
      const parts: string[] = [];
      if (tooLarge > 0) {
        parts.push(
          `${tooLarge} ${tooLarge === 1 ? "muito grande" : "muito grandes"}`,
        );
      }
      if (badMime > 0) {
        parts.push(
          `${badMime} ${badMime === 1 ? "formato inválido" : "formatos inválidos"}`,
        );
      }
      if (overLimit > 0) {
        parts.push(
          `${overLimit} ${overLimit === 1 ? "excedeu o limite de anexos" : "excederam o limite de anexos"}`,
        );
      }
      toast.error(
        `${rejected} ${rejected === 1 ? "arquivo rejeitado" : "arquivos rejeitados"}: ${parts.join(", ")}`,
      );
    }
  }

  function removeAttachment(id: string) {
    setAttachments((prev) => {
      const found = prev.find((a) => a.id === id);
      if (found) URL.revokeObjectURL(found.previewUrl);
      return prev.filter((a) => a.id !== id);
    });
  }

  async function handleSend() {
    const trimmed = text.trim();
    if (!trimmed || submitting || disabled) return;
    const snapshot = attachments;
    const files = snapshot.map((a) => a.file);
    setSubmitting(true);
    try {
      await onSend(trimmed, files);
      snapshot.forEach((a) => URL.revokeObjectURL(a.previewUrl));
      setAttachments([]);
      setText("");
      if (textareaRef.current) {
        textareaRef.current.style.height = "auto";
      }
    } catch {
      // Parent surfaces errors (e.g. toast); keep draft
    } finally {
      setSubmitting(false);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  return (
    <div className="min-h-[var(--app-bottom-shelf-min-height)] shrink-0 border-t border-[var(--color-border-subtle)] bg-[var(--color-bg-surface)] px-4 py-3">
      <div className="mx-auto max-w-3xl">
        <div className="flex flex-col gap-2 rounded-[var(--radius-lg)] border border-[var(--color-border-subtle)] bg-[var(--color-bg-app)] px-3 py-2 shadow-[var(--shadow-composer)] focus-within:ring-2 focus-within:ring-[var(--color-focus-ring)]">
          {attachments.length > 0 && (
            <div className="flex flex-wrap gap-2 pb-1">
              {attachments.map((a) => (
                <div key={a.id} className="relative h-16 w-16 shrink-0">
                  <img
                    src={a.previewUrl}
                    alt=""
                    className="h-16 w-16 rounded-[var(--radius-sm)] object-cover"
                  />
                  <button
                    type="button"
                    onClick={() => removeAttachment(a.id)}
                    aria-label="Remover anexo"
                    className="absolute -right-1 -top-1 flex h-5 w-5 items-center justify-center rounded-full bg-[var(--color-text-primary)] text-white shadow hover:opacity-90"
                  >
                    <IconClose size={12} className="text-white" />
                  </button>
                </div>
              ))}
            </div>
          )}
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              disabled={attachBlocked}
              aria-label="Anexar imagens"
              className="flex h-8 w-8 shrink-0 items-center justify-center rounded-[var(--radius-md)] text-[var(--color-text-muted)] hover:bg-[var(--color-bg-muted)] hover:text-[var(--color-text-primary)] disabled:cursor-not-allowed disabled:opacity-40"
            >
              <IconPaperclip size={18} />
            </button>
            <input
              ref={fileInputRef}
              type="file"
              hidden
              multiple
              accept="image/jpeg,image/png,image/webp"
              onChange={handleFiles}
            />
            <textarea
              ref={textareaRef}
              value={text}
              onChange={handleChange}
              onKeyDown={handleKeyDown}
              disabled={disabled || submitting}
              placeholder={placeholder}
              rows={1}
              aria-label="Mensagem"
              className="flex-1 resize-none bg-transparent py-2 text-sm leading-snug text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)] outline-none disabled:cursor-not-allowed disabled:opacity-60"
              style={{ maxHeight: 120 }}
            />
            <div className="flex shrink-0 items-center gap-2">
              <span
                className={[
                  "text-xs tabular-nums",
                  charCount > MAX_CHARS * 0.9
                    ? "text-amber-500"
                    : "text-[var(--color-text-muted)]",
                ].join(" ")}
              >
                {charCount}/{MAX_CHARS}
              </span>
              <button
                type="button"
                onClick={handleSend}
                disabled={!canSend}
                aria-label="Enviar"
                className="flex h-8 w-8 items-center justify-center rounded-[var(--radius-md)] bg-[var(--color-brand-primary)] text-white transition-opacity hover:bg-[var(--color-brand-primary-hover)] disabled:cursor-not-allowed disabled:opacity-40"
              >
                {submitting ? (
                  <InlineSpinner size={16} ariaHidden className="text-white" />
                ) : (
                  <IconSend />
                )}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function IconSend() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path
        d="M22 2L11 13M22 2L15 22l-4-9-9-4 20-7z"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
