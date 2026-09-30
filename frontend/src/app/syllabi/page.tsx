"use client";

import React, { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useDropzone } from "react-dropzone";
import {
  AlertCircle,
  ArrowRight,
  BookOpen,
  CheckCircle2,
  Clock,
  FileText,
  Loader2,
  Plus,
  RefreshCw,
  Search,
  UploadCloud,
  X,
} from "lucide-react";
import { api, Syllabus } from "@/lib/api";

export default function SyllabiPage() {
  const [syllabi, setSyllabi] = useState<Syllabus[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [showUploader, setShowUploader] = useState(false);

  // Upload state
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [title, setTitle] = useState("");
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);

  // Active polling tracking
  const [processingId, setProcessingId] = useState<string | null>(null);
  const [processingStatus, setProcessingStatus] = useState<string>("processing");

  const refreshSyllabi = useCallback(async () => {
    try {
      const data = await api.listSyllabi();
      setSyllabi(data);
    } catch {
      // Ignored
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let isMounted = true;
    api.listSyllabi()
      .then((data) => {
        if (isMounted) {
          setSyllabi(data);
          setLoading(false);
        }
      })
      .catch(() => {
        if (isMounted) setLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, []);

  // Polling for processing syllabus
  useEffect(() => {
    if (!processingId) return;

    const interval = setInterval(async () => {
      try {
        const status = await api.getSyllabusStatus(processingId);
        setProcessingStatus(status.status);
        if (status.status === "ready" || status.status === "failed") {
          clearInterval(interval);
          setProcessingId(null);
          refreshSyllabi();
        }
      } catch {
        // Retry
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [processingId, refreshSyllabi]);

  const onDrop = useCallback((acceptedFiles: File[]) => {
    if (acceptedFiles.length > 0) {
      const file = acceptedFiles[0];
      setSelectedFile(file);
      setUploadError(null);
      // Clean title from filename
      const cleanTitle = file.name
        .replace(/\.[^/.]+$/, "")
        .replace(/[-_]/g, " ")
        .replace(/\b\w/g, (c) => c.toUpperCase());
      setTitle(cleanTitle);
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "application/pdf": [".pdf"],
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [
        ".docx",
      ],
      "application/msword": [".doc"],
    },
    maxFiles: 1,
    multiple: false,
  });

  const handleUploadSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile) {
      setUploadError("Please select a syllabus document first");
      return;
    }
    if (!title.trim()) {
      setUploadError("Please provide a course title");
      return;
    }

    setUploading(true);
    setUploadError(null);

    try {
      const result = await api.uploadSyllabus(selectedFile, title.trim());
      setProcessingId(result.id);
      setProcessingStatus(result.status);
      setSelectedFile(null);
      setTitle("");
      setShowUploader(false);
      await refreshSyllabi();
    } catch (err) {
      setUploadError(
        err instanceof Error ? err.message : "Failed to upload syllabus"
      );
    } finally {
      setUploading(false);
    }
  };

  const filteredSyllabi = syllabi.filter((s) => {
    const q = search.toLowerCase();
    return s.title.toLowerCase().includes(q) || s.filename.toLowerCase().includes(q);
  });

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 md:py-12 flex flex-col gap-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-[var(--border-subtle)] pb-6">
        <div>
          <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-[var(--color-brand-yellow)]">
            <BookOpen className="w-4 h-4" />
            <span>Academic Curriculum Ingestion</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-[var(--text-main)] tracking-tight mt-1">
            Course Syllabi Repository
          </h1>
          <p className="text-sm text-[var(--text-muted)] mt-1 max-w-2xl">
            Upload institutional syllabi in PDF or DOCX format to parse discrete competencies, examine evidence snippets, and run gap analyses.
          </p>
        </div>

        <button
          onClick={() => setShowUploader((prev) => !prev)}
          className="px-4 py-2.5 rounded-xl bg-[var(--color-primary)] text-[var(--color-primary-text)] font-semibold text-sm hover:opacity-90 transition flex items-center gap-2 cursor-pointer shadow-sm"
        >
          {showUploader ? (
            <>
              <X className="w-4 h-4" />
              <span>Close Uploader</span>
            </>
          ) : (
            <>
              <Plus className="w-4 h-4" />
              <span>Upload Syllabus</span>
            </>
          )}
        </button>
      </div>

      {/* Active Processing Card */}
      {processingId && (
        <div className="p-4 rounded-2xl bg-[var(--color-status-warning-bg)] border border-[var(--color-brand-yellow)] flex items-center justify-between gap-4 animate-pulse">
          <div className="flex items-center gap-3">
            <RefreshCw className="w-5 h-5 text-[var(--color-brand-yellow)] animate-spin" />
            <div>
              <p className="text-sm font-bold text-[var(--color-brand-navy)] dark:text-[var(--text-main)]">
                Processing Syllabus ({processingStatus})
              </p>
              <p className="text-xs text-[var(--text-muted)]">
                Extracting textual chunks, identifying skills, and mapping taxonomy...
              </p>
            </div>
          </div>
          <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-[var(--bg-surface)] text-[var(--color-brand-navy)]">
            In progress
          </span>
        </div>
      )}

      {/* Uploader Section */}
      {showUploader && (
        <div className="p-6 md:p-8 rounded-3xl bg-[var(--bg-surface)] border border-[var(--border-subtle)] shadow-md flex flex-col gap-6 transition-all">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-bold text-[var(--text-main)]">
              Upload New Course Syllabus
            </h2>
            <button
              onClick={() => setShowUploader(false)}
              className="p-1 rounded-lg hover:bg-[var(--bg-surface-elevated)] text-[var(--text-muted)] cursor-pointer"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {uploadError && (
            <div
              role="alert"
              className="p-3 rounded-xl bg-[var(--color-status-missing-bg)] border border-[var(--color-status-missing)] text-[var(--color-status-missing)] text-xs flex items-center gap-2"
            >
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{uploadError}</span>
            </div>
          )}

          <form onSubmit={handleUploadSubmit} className="flex flex-col gap-5">
            {/* Dropzone */}
            <div
              {...getRootProps()}
              className={`border-2 border-dashed rounded-2xl p-8 text-center cursor-pointer transition flex flex-col items-center justify-center gap-3 ${
                isDragActive
                  ? "border-[var(--color-brand-green)] bg-[var(--color-status-covered-bg)]/20"
                  : "border-[var(--border-subtle)] hover:border-[var(--border-strong)] bg-[var(--bg-page)]/50"
              }`}
            >
              <input {...getInputProps()} />
              <div className="w-12 h-12 rounded-2xl bg-[var(--bg-surface-elevated)] border border-[var(--border-subtle)] flex items-center justify-center text-[var(--color-brand-green)] dark:text-[var(--color-brand-aqua)]">
                <UploadCloud className="w-6 h-6" />
              </div>
              <div className="flex flex-col gap-1">
                <p className="text-sm font-semibold text-[var(--text-main)]">
                  {isDragActive
                    ? "Drop the syllabus document here"
                    : "Drag & drop your syllabus file here, or browse"}
                </p>
                <p className="text-xs text-[var(--text-muted)]">
                  Supports PDF (.pdf) or Word (.docx, .doc) up to 25MB
                </p>
              </div>
            </div>

            {/* Selected File Card */}
            {selectedFile && (
              <div className="p-3.5 rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface-elevated)] flex items-center justify-between gap-3">
                <div className="flex items-center gap-3">
                  <FileText className="w-5 h-5 text-[var(--color-brand-green)] dark:text-[var(--color-brand-aqua)]" />
                  <div>
                    <p className="text-xs font-semibold text-[var(--text-main)]">
                      {selectedFile.name}
                    </p>
                    <p className="text-[11px] text-[var(--text-muted)]">
                      {(selectedFile.size / 1024).toFixed(1)} KB
                    </p>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => {
                    setSelectedFile(null);
                    setTitle("");
                  }}
                  className="text-xs text-[var(--color-status-missing)] hover:underline cursor-pointer"
                >
                  Remove
                </button>
              </div>
            )}

            {/* Course Title Input */}
            <div className="flex flex-col gap-1.5">
              <label
                htmlFor="courseTitle"
                className="text-xs font-semibold text-[var(--text-main)]"
              >
                Official Course Title
              </label>
              <input
                id="courseTitle"
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="e.g. CS302: Cloud Architecture and Distributed Systems"
                required
                className="w-full px-3.5 py-2.5 text-sm rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-page)] text-[var(--text-main)] placeholder:text-[var(--text-muted)]/60 focus:outline-none focus:border-[var(--color-brand-green)] dark:focus:border-[var(--color-brand-aqua)] transition"
              />
            </div>

            {/* Action Buttons */}
            <div className="flex items-center justify-end gap-3 pt-2">
              <button
                type="button"
                onClick={() => {
                  setShowUploader(false);
                  setSelectedFile(null);
                  setTitle("");
                }}
                className="px-4 py-2.5 rounded-xl border border-[var(--border-subtle)] text-xs font-semibold hover:bg-[var(--bg-surface-elevated)] transition cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={uploading || !selectedFile}
                className="px-5 py-2.5 rounded-xl bg-[var(--color-primary)] text-[var(--color-primary-text)] text-xs font-semibold hover:opacity-90 transition flex items-center gap-2 cursor-pointer disabled:opacity-50 shadow-sm"
              >
                {uploading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Uploading...</span>
                  </>
                ) : (
                  <>
                    <UploadCloud className="w-4 h-4" />
                    <span>Process &amp; Extract Skills</span>
                  </>
                )}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Syllabi List & Search */}
      <div className="flex flex-col gap-4">
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
          <div className="relative flex-1 max-w-md">
            <Search className="w-4 h-4 text-[var(--text-muted)] absolute left-3 top-3 pointer-events-none" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search uploaded syllabi by title or filename..."
              className="w-full pl-9 pr-3 py-2 text-xs sm:text-sm rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] text-[var(--text-main)] placeholder:text-[var(--text-muted)]/60 focus:outline-none focus:border-[var(--color-brand-green)] dark:focus:border-[var(--color-brand-aqua)] transition"
            />
          </div>
          <span className="text-xs text-[var(--text-muted)] self-center sm:self-auto">
            Showing {filteredSyllabi.length} of {syllabi.length} syllabi
          </span>
        </div>

        {/* Syllabi Grid */}
        {loading ? (
          <div className="p-12 text-center text-sm text-[var(--text-muted)] flex flex-col items-center justify-center gap-3">
            <Loader2 className="w-6 h-6 animate-spin text-[var(--color-brand-yellow)]" />
            <span>Loading course syllabi...</span>
          </div>
        ) : filteredSyllabi.length === 0 ? (
          <div className="p-12 text-center rounded-3xl bg-[var(--bg-surface)] border border-[var(--border-subtle)] flex flex-col items-center justify-center gap-4">
            <div className="w-12 h-12 rounded-2xl bg-[var(--color-brand-pink)] text-[var(--color-brand-navy)] flex items-center justify-center">
              <BookOpen className="w-6 h-6" />
            </div>
            <div className="flex flex-col gap-1 max-w-sm">
              <h3 className="text-base font-bold text-[var(--text-main)]">
                No Syllabi Found
              </h3>
              <p className="text-xs text-[var(--text-muted)]">
                {search
                  ? "No courses matched your search query. Try clearing the filter."
                  : "No curriculum documents have been uploaded yet. Upload your first course syllabus to begin gap analysis."}
              </p>
            </div>
            {!search && (
              <button
                onClick={() => setShowUploader(true)}
                className="mt-2 px-4 py-2 rounded-xl bg-[var(--color-primary)] text-[var(--color-primary-text)] font-semibold text-xs hover:opacity-90 transition cursor-pointer"
              >
                Upload Course Syllabus
              </button>
            )}
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {filteredSyllabi.map((syllabus) => {
              const isReady = syllabus.status === "ready";
              const isProcessing =
                syllabus.status === "processing" || syllabus.status === "pending";
              const isFailed = syllabus.status === "failed";

              return (
                <div
                  key={syllabus.id}
                  className="p-6 rounded-2xl bg-[var(--bg-surface)] border border-[var(--border-subtle)] hover:border-[var(--border-strong)] transition-all flex flex-col justify-between gap-5 shadow-sm"
                >
                  <div className="flex flex-col gap-3">
                    <div className="flex items-start justify-between gap-2">
                      <span
                        className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full inline-flex items-center gap-1 ${
                          isReady
                            ? "bg-[var(--color-status-covered-bg)] text-[var(--color-status-covered)]"
                            : isProcessing
                            ? "bg-[var(--color-status-warning-bg)] text-[var(--color-brand-yellow)]"
                            : "bg-[var(--color-status-missing-bg)] text-[var(--color-status-missing)]"
                        }`}
                      >
                        {isReady && <CheckCircle2 className="w-3 h-3" />}
                        {isProcessing && (
                          <RefreshCw className="w-3 h-3 animate-spin" />
                        )}
                        {isFailed && <AlertCircle className="w-3 h-3" />}
                        <span>{syllabus.status}</span>
                      </span>

                      <div className="flex items-center gap-1 text-[11px] text-[var(--text-muted)]">
                        <Clock className="w-3 h-3" />
                        <span>
                          {syllabus.created_at
                            ? new Date(syllabus.created_at).toLocaleDateString()
                            : "Recent"}
                        </span>
                      </div>
                    </div>

                    <div>
                      <h3 className="text-base font-bold text-[var(--text-main)] line-clamp-2">
                        {syllabus.title}
                      </h3>
                      <p className="text-xs text-[var(--text-muted)] flex items-center gap-1.5 mt-1 font-mono">
                        <FileText className="w-3.5 h-3.5 shrink-0" />
                        <span className="truncate">{syllabus.filename}</span>
                      </p>
                    </div>

                    {syllabus.error_message && (
                      <p className="text-xs text-[var(--color-status-missing)] bg-[var(--color-status-missing-bg)] p-2 rounded-lg">
                        {syllabus.error_message}
                      </p>
                    )}
                  </div>

                  <div className="pt-4 border-t border-[var(--border-subtle)] flex items-center justify-between gap-2">
                    <Link
                      href={`/syllabi/${syllabus.id}`}
                      className="text-xs font-semibold text-[var(--text-main)] hover:text-[var(--color-brand-green)] dark:hover:text-[var(--color-brand-aqua)] transition flex items-center gap-1"
                    >
                      <span>View Skills</span>
                      <ArrowRight className="w-3.5 h-3.5" />
                    </Link>

                    {isReady && (
                      <Link
                        href={`/analysis?syllabus_id=${syllabus.id}`}
                        className="text-xs font-semibold px-3 py-1.5 rounded-lg bg-[var(--color-primary)] text-[var(--color-primary-text)] hover:opacity-90 transition shadow-sm"
                      >
                        Run Gap Analysis
                      </Link>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
