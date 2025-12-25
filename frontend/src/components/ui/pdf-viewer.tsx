import React, { useEffect, useMemo, useState } from "react";

export interface PdfViewerLabels {
  loading?: string;
  empty?: string;
  download?: string;
  fullscreen?: string;
  close?: string;
}

export interface PdfViewerClassNames {
  backdrop?: string;
  container?: string;
  iframe?: string;
  header?: string;
  body?: string;
  actions?: string;
}

export interface PdfViewerProps {
  isOpen: boolean;
  blob: Blob | null;
  filename: string;
  onClose: () => void;
  isLoading?: boolean;
  /**
   * Optional override to handle downloads (DIP).
   * Receives the created object URL and filename.
   */
  onDownload?: (objectUrl: string, filename: string) => void;
  /**
   * Optional override to handle opening in new tab/fullscreen (DIP).
   */
  onOpenExternal?: (objectUrl: string) => void;
  labels?: PdfViewerLabels;
  className?: PdfViewerClassNames;
}

const useObjectUrl = (blob: Blob | null) => {
  const [objectUrl, setObjectUrl] = useState<string | null>(null);

  useEffect(() => {
    if (!blob) {
      setObjectUrl(null);
      return;
    }
    const url = URL.createObjectURL(blob);
    setObjectUrl(url);
    return () => {
      URL.revokeObjectURL(url);
      setObjectUrl(null);
    };
  }, [blob]);

  return objectUrl;
};

export const PdfViewer: React.FC<PdfViewerProps> = ({
  isOpen,
  blob,
  filename,
  onClose,
  isLoading = false,
  onDownload,
  onOpenExternal,
  labels,
  className,
}) => {
  const objectUrl = useObjectUrl(blob);

  const effectiveFilename = useMemo(
    () => filename?.trim() || "document.pdf",
    [filename]
  );

  const handleDownload = () => {
    if (!objectUrl) return;
    if (onDownload) {
      onDownload(objectUrl, effectiveFilename);
      return;
    }
    const link = document.createElement("a");
    link.href = objectUrl;
    link.download = effectiveFilename;
    link.rel = "noopener";
    link.click();
  };

  const handleOpenExternal = () => {
    if (!objectUrl) return;
    if (onOpenExternal) {
      onOpenExternal(objectUrl);
      return;
    }
    window.open(objectUrl, "_blank", "noopener,noreferrer");
  };

  if (!isOpen) return null;

  const t: Required<PdfViewerLabels> = {
    loading: labels?.loading ?? "PDF wird geladen …",
    empty: labels?.empty ?? "Keine PDF verfügbar.",
    download: labels?.download ?? "Download",
    fullscreen: labels?.fullscreen ?? "Vollbild",
    close: labels?.close ?? "Schließen",
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={effectiveFilename}
      className={
        className?.backdrop ??
        "fixed inset-0 z-50 flex items-center justify-center bg-black/70"
      }
    >
      <div
        className={
          className?.container ??
          "relative flex h-[85vh] w-[90vw] max-w-6xl flex-col overflow-hidden rounded-lg bg-white shadow-xl"
        }
      >
        <header
          className={
            className?.header ??
            "flex items-center justify-between border-b px-4 py-3"
          }
        >
          <div className="flex items-center gap-2">
            <span className="font-semibold text-gray-800">
              {effectiveFilename}
            </span>
            {isLoading && (
              <span className="text-xs text-gray-500">{t.loading}</span>
            )}
          </div>
          <div
            className={
              className?.actions ?? "flex items-center gap-2"
            }
          >
            <button
              type="button"
              onClick={handleOpenExternal}
              className="rounded border px-3 py-1 text-sm hover:bg-gray-50"
              disabled={!objectUrl || isLoading}
            >
              {t.fullscreen}
            </button>
            <button
              type="button"
              onClick={handleDownload}
              className="rounded border px-3 py-1 text-sm hover:bg-gray-50"
              disabled={!objectUrl || isLoading}
            >
              {t.download}
            </button>
            <button
              type="button"
              onClick={onClose}
              className="rounded border px-3 py-1 text-sm hover:bg-gray-50"
            >
              {t.close}
            </button>
          </div>
        </header>

        <div
          className={
            className?.body ?? "relative flex-1 bg-gray-100"
          }
        >
          {isLoading && (
            <div className="absolute inset-0 z-10 flex items-center justify-center bg-white/70">
              <span className="text-sm text-gray-600">{t.loading}</span>
            </div>
          )}

          {objectUrl ? (
            <iframe
              title="PDF Vorschau"
              src={objectUrl}
              className={className?.iframe ?? "h-full w-full"}
              loading="lazy"
            />
          ) : (
            <div className="flex h-full items-center justify-center text-sm text-gray-600">
              {t.empty}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default PdfViewer;