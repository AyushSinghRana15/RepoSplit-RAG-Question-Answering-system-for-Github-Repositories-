"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Folder,
  FolderOpen,
  FileCode,
  ChevronRight,
  ChevronDown,
  Loader2,
  AlertCircle,
  Search,
  X,
  Braces,
  FunctionSquare,
} from "lucide-react";

interface FunctionInfo {
  name: string;
  type: string;
  start_line: number;
  end_line: number;
  docstring: string | null;
  is_async?: boolean;
}

interface RepoData {
  files: Record<string, FunctionInfo[]>;
  total_files: number;
}

interface TreeNode {
  name: string;
  path: string;
  type: "folder" | "file";
  children: TreeNode[];
}

function buildTree(filePaths: string[]): TreeNode[] {
  const root: TreeNode[] = [];

  for (const fp of filePaths) {
    const parts = fp.split("/");
    let current = root;

    for (let i = 0; i < parts.length; i++) {
      const part = parts[i];
      const isFile = i === parts.length - 1;
      const existing = current.find((n) => n.name === part && n.type === (isFile ? "file" : "folder"));

      if (existing) {
        current = existing.children;
      } else {
        const node: TreeNode = {
          name: part,
          path: parts.slice(0, i + 1).join("/"),
          type: isFile ? "file" : "folder",
          children: [],
        };
        current.push(node);
        current = node.children;
      }
    }
  }

  const sortNodes = (nodes: TreeNode[]) => {
    nodes.sort((a, b) => {
      if (a.type !== b.type) return a.type === "folder" ? -1 : 1;
      return a.name.localeCompare(b.name);
    });
    for (const n of nodes) {
      if (n.children.length > 0) sortNodes(n.children);
    }
  };
  sortNodes(root);

  return root;
}

function FolderNode({
  node,
  depth,
  onFileSelect,
  selectedFile,
  initiallyOpen,
}: {
  node: TreeNode;
  depth: number;
  onFileSelect: (path: string) => void;
  selectedFile: string | null;
  initiallyOpen: boolean;
}) {
  const [open, setOpen] = useState(initiallyOpen);

  useEffect(() => {
    if (initiallyOpen) setOpen(true);
  }, [initiallyOpen]);

  if (node.type === "file") {
    return (
      <button
        onClick={() => onFileSelect(node.path)}
        className={`group flex w-full items-center gap-2 rounded-lg px-3 py-1.5 text-left text-xs transition-all duration-150 ${
          selectedFile === node.path
            ? "shadow-sm"
            : "hover:opacity-80"
        }`}
        style={{
          background: selectedFile === node.path ? "var(--bg-secondary)" : "transparent",
          color: selectedFile === node.path ? "var(--text-primary)" : "var(--text-secondary)",
          borderLeft: selectedFile === node.path ? "2px solid #8b5cf6" : "2px solid transparent",
          paddingLeft: `${depth * 16 + 16}px`,
        }}
      >
        <FileCode className="h-3.5 w-3.5 shrink-0" style={{ color: selectedFile === node.path ? "#8b5cf6" : "var(--text-muted)" }} />
        <span className="truncate font-mono">{node.name}</span>
      </button>
    );
  }

  return (
    <div>
      <button
        onClick={() => setOpen(!open)}
        className="group flex w-full items-center gap-2 rounded-lg px-3 py-1.5 text-left text-xs transition-all duration-150 hover:opacity-80"
        style={{
          color: "var(--text-secondary)",
          paddingLeft: `${depth * 16 + 8}px`,
        }}
      >
        {open ? (
          <ChevronDown className="h-3 w-3 shrink-0 transition-transform" style={{ color: "var(--text-muted)" }} />
        ) : (
          <ChevronRight className="h-3 w-3 shrink-0 transition-transform" style={{ color: "var(--text-muted)" }} />
        )}
        {open ? (
          <FolderOpen className="h-3.5 w-3.5 shrink-0 text-[#ca8a04]" />
        ) : (
          <Folder className="h-3.5 w-3.5 shrink-0 text-[#ca8a04]" />
        )}
        <span className="truncate font-mono" style={{ color: "var(--text-primary)" }}>
          {node.name}
        </span>
        <span className="ml-auto text-[10px]" style={{ color: "var(--text-muted)" }}>
          {node.children.filter((c) => c.type === "file").length}
        </span>
      </button>
      <div
        className={`overflow-hidden transition-all duration-200 ease-in-out ${
          open ? "max-h-[9999px] opacity-100" : "max-h-0 opacity-0"
        }`}
      >
        {node.children.map((child) => (
          <FolderNode
            key={child.path}
            node={child}
            depth={depth + 1}
            onFileSelect={onFileSelect}
            selectedFile={selectedFile}
            initiallyOpen={false}
          />
        ))}
      </div>
    </div>
  );
}

function FileDetails({
  path,
  functions,
  onClose,
}: {
  path: string;
  functions: FunctionInfo[];
  onClose: () => void;
}) {
  const classes = functions.filter((f) => f.type === "class");
  const funcs = functions.filter((f) => f.type === "function");

  return (
    <div
      className="rounded-xl border p-5"
      style={{ background: "var(--bg-card)", borderColor: "var(--border-subtle)" }}
    >
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2 min-w-0">
          <FileCode className="h-4 w-4 shrink-0 text-[#8b5cf6]" />
          <span className="truncate text-sm font-mono font-semibold" style={{ color: "var(--text-primary)" }}>
            {path}
          </span>
        </div>
        <button
          onClick={onClose}
          className="ml-2 flex h-6 w-6 shrink-0 items-center justify-center rounded-full transition-colors hover:opacity-80"
          style={{ color: "var(--text-muted)" }}
        >
          <X className="h-3.5 w-3.5" />
        </button>
      </div>

      {functions.length === 0 ? (
        <p className="text-xs" style={{ color: "var(--text-muted)" }}>
          No functions or classes found in this file.
        </p>
      ) : (
        <div className="space-y-3">
          {classes.length > 0 && (
            <div>
              <h4 className="mb-2 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>
                <Braces className="h-3 w-3" />
                Classes ({classes.length})
              </h4>
              <div className="space-y-2">
                {classes.map((fn) => (
                  <FunctionCard key={`class-${fn.name}`} fn={fn} />
                ))}
              </div>
            </div>
          )}

          {funcs.length > 0 && (
            <div>
              <h4 className="mb-2 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>
                <FunctionSquare className="h-3 w-3" />
                Functions ({funcs.length})
              </h4>
              <div className="space-y-2">
                {funcs.map((fn) => (
                  <FunctionCard key={`func-${fn.name}`} fn={fn} />
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function FunctionCard({ fn }: { fn: FunctionInfo }) {
  const [expanded, setExpanded] = useState(false);

  const colorMap: Record<string, string> = {
    function: "#3b82f6",
    class: "#8b5cf6",
  };

  return (
    <div
      className="rounded-lg border p-3 text-xs transition-all duration-200"
      style={{
        borderColor: "var(--border-subtle)",
        background: "var(--bg-secondary)",
      }}
    >
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex w-full items-center gap-2 text-left"
      >
        <div
          className="flex h-5 w-5 shrink-0 items-center justify-center rounded text-[10px] font-bold"
          style={{ background: `${colorMap[fn.type] || "#3b82f6"}20`, color: colorMap[fn.type] || "#3b82f6" }}
        >
          {fn.type === "class" ? "C" : "f"}
        </div>
        <div className="min-w-0 flex-1">
          <span className="font-mono font-semibold" style={{ color: "var(--text-primary)" }}>
            {fn.is_async ? "async " : ""}{fn.name}
          </span>
          <span className="ml-2" style={{ color: "var(--text-muted)" }}>
            L{fn.start_line}-{fn.end_line}
          </span>
        </div>
        {fn.docstring && (
          <ChevronDown
            className={`h-3 w-3 shrink-0 transition-transform duration-200 ${
              expanded ? "rotate-0" : "-rotate-90"
            }`}
            style={{ color: "var(--text-muted)" }}
          />
        )}
      </button>

      {fn.docstring && expanded && (
        <div className="mt-2 overflow-hidden transition-all duration-200">
          <div
            className="rounded-md p-2.5 text-xs leading-relaxed"
            style={{ background: "var(--bg-primary)" }}
          >
            <p style={{ color: "var(--text-secondary)" }}>{fn.docstring}</p>
          </div>
        </div>
      )}
    </div>
  );
}

interface RepoMapProps {
  visible: boolean;
  onClose: () => void;
}

export function RepoMap({ visible, onClose }: RepoMapProps) {
  const [data, setData] = useState<RepoData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");

  const fetchStructure = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/ingest/repo-structure");
      if (!res.ok) {
        const err = await res.json().catch(() => ({ error: "Failed to fetch" }));
        throw new Error(err.error || err.detail || `HTTP ${res.status}`);
      }
      const result = await res.json();
      setData(result);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (visible) {
      fetchStructure();
    }
  }, [visible, fetchStructure]);

  useEffect(() => {
    setSelectedFile(null);
  }, [data]);

  if (!visible) return null;

  const tree = data ? buildTree(Object.keys(data.files)) : [];

  const filteredTree = searchQuery
    ? buildTree(
        Object.keys(data?.files || {}).filter((fp) =>
          fp.toLowerCase().includes(searchQuery.toLowerCase())
        )
      )
    : tree;

  const selectedFunctions = selectedFile && data?.files[selectedFile]
    ? data.files[selectedFile]
    : null;

  return (
    <div
      className="mb-6 w-full overflow-hidden rounded-xl border shadow-lg"
      style={{
        borderColor: "var(--border-subtle)",
        background: "var(--bg-card)",
      }}
    >
      <div className="h-1 bg-gradient-to-r from-[#8b5cf6] via-[#3b82f6] to-transparent" />

      <div className="p-5">
        <div className="mb-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Braces className="h-4 w-4 text-[#8b5cf6]" />
            <span className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>
              Repository Map
            </span>
            {data && (
              <span className="rounded-full px-2 py-0.5 text-[10px] font-medium" style={{ background: "var(--bg-secondary)", color: "var(--text-muted)" }}>
                {data.total_files} files
              </span>
            )}
          </div>
          <button
            onClick={onClose}
            className="flex h-7 w-7 items-center justify-center rounded-full transition-colors hover:opacity-80"
            style={{ color: "var(--text-muted)" }}
          >
            <X className="h-3.5 w-3.5" />
          </button>
        </div>

        <div className="relative mb-3">
          <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2" style={{ color: "var(--text-muted)" }} />
          <input
            type="text"
            placeholder="Search files..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full rounded-lg py-2 pl-8 pr-3 text-xs outline-none transition-all"
            style={{
              background: "var(--bg-secondary)",
              border: "1px solid var(--border-subtle)",
              color: "var(--text-primary)",
            }}
          />
        </div>

        {loading && (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-5 w-5 animate-spin" style={{ color: "var(--text-muted)" }} />
            <span className="ml-2 text-sm" style={{ color: "var(--text-muted)" }}>
              Loading repository structure...
            </span>
          </div>
        )}

        {error && (
          <div className="flex items-center gap-2 rounded-lg px-3 py-2 text-xs" style={{ background: "rgba(239,68,68,0.1)", color: "#ef4444" }}>
            <AlertCircle className="h-3.5 w-3.5 shrink-0" />
            {error}
          </div>
        )}

        {!loading && !error && data && (
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <div
              className="max-h-[500px] overflow-y-auto rounded-xl border p-2"
              style={{ borderColor: "var(--border-subtle)", background: "var(--bg-primary)" }}
            >
              {filteredTree.length === 0 ? (
                <p className="py-4 text-center text-xs" style={{ color: "var(--text-muted)" }}>
                  {searchQuery ? "No files match your search." : "No files found in repository."}
                </p>
              ) : (
                filteredTree.map((node) => (
                  <FolderNode
                    key={node.path}
                    node={node}
                    depth={0}
                    onFileSelect={setSelectedFile}
                    selectedFile={selectedFile}
                    initiallyOpen={true}
                  />
                ))
              )}
            </div>

            <div className="max-h-[500px] overflow-y-auto">
              {selectedFunctions ? (
                <FileDetails
                  path={selectedFile!}
                  functions={selectedFunctions}
                  onClose={() => setSelectedFile(null)}
                />
              ) : (
                <div className="flex h-full min-h-[200px] flex-col items-center justify-center rounded-xl border" style={{ borderColor: "var(--border-subtle)" }}>
                  <FileCode className="mb-2 h-8 w-8" style={{ color: "var(--text-muted)" }} />
                  <p className="text-xs" style={{ color: "var(--text-muted)" }}>
                    Click a file to view its functions
                  </p>
                </div>
              )}
            </div>
          </div>
        )}

        {!loading && !error && !data && (
          <div className="flex items-center justify-center py-8">
            <p className="text-xs" style={{ color: "var(--text-muted)" }}>
              Ingest a repository to view its structure.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
