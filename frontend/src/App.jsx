import React, { useState, useRef, useEffect, useCallback } from "react";
import axios from "axios";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { vscDarkPlus } from "react-syntax-highlighter/dist/esm/styles/prism";
import {
  GitBranch,
  Search,
  Zap,
  FileCode2,
  ChevronRight,
  CheckCircle2,
  XCircle,
  Loader2,
  Terminal,
  Sparkles,
  Copy,
  Check,
  ExternalLink,
  Hash,
  AlertCircle,
} from "lucide-react";
import "./index.css";
import "./App.css";

const API_BASE =
  process.env.REACT_APP_API_URL || "https://repomind-2588.onrender.com";

// ── Utilities ────────────────────────────────────────────────────
const uid = () => Math.random().toString(36).slice(2);
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

function extractCodeBlocks(text) {
  const parts = [];
  const regex = /```(\w+)?\n?([\s\S]*?)```/g;
  let last = 0;
  let match;
  while ((match = regex.exec(text)) !== null) {
    if (match.index > last)
      parts.push({ type: "text", content: text.slice(last, match.index) });
    parts.push({
      type: "code",
      content: match[2].trim(),
      lang: match[1] || "text",
    });
    last = match.index + match[0].length;
  }
  if (last < text.length)
    parts.push({ type: "text", content: text.slice(last) });
  return parts;
}

// ── CopyButton ───────────────────────────────────────────────────
function CopyButton({ text }) {
  const [copied, setCopied] = useState(false);
  const handle = async () => {
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };
  return (
    <button
      onClick={handle}
      style={{
        background: "none",
        border: "none",
        cursor: "pointer",
        color: copied ? "var(--green)" : "var(--text-muted)",
        display: "flex",
        alignItems: "center",
        gap: 4,
        fontSize: 11,
        fontFamily: "var(--font-mono)",
        transition: "color .2s",
      }}
    >
      {copied ? (
        <>
          <Check size={12} /> copied
        </>
      ) : (
        <>
          <Copy size={12} /> copy
        </>
      )}
    </button>
  );
}

// ── MessageBubble ────────────────────────────────────────────────
function MessageBubble({ msg }) {
  const cleanContent = msg.content.replace(/\[([^\]]+)\]\(http[^)]+\)/g, "$1");
  const parts =
    msg.type === "assistant" ? extractCodeBlocks(cleanContent) : null;

  if (msg.type === "system")
    return (
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 8,
          padding: "6px 12px",
          margin: "4px 0",
          background: "var(--bg-elevated)",
          border: "1px solid var(--border)",
          borderRadius: 6,
          fontSize: 12,
          color: "var(--text-muted)",
          fontFamily: "var(--font-mono)",
        }}
      >
        <Hash size={11} color="var(--accent)" />
        <span>{msg.content}</span>
      </div>
    );

  if (msg.type === "user")
    return (
      <div
        style={{ display: "flex", justifyContent: "flex-end", margin: "8px 0" }}
      >
        <div
          style={{
            background: "var(--accent-dim)",
            border: "1px solid var(--accent)",
            borderRadius: "12px 12px 2px 12px",
            padding: "10px 16px",
            maxWidth: "70%",
            color: "var(--text-primary)",
            fontSize: 13,
            lineHeight: 1.6,
          }}
        >
          {msg.content}
        </div>
      </div>
    );

  return (
    <div style={{ margin: "12px 0" }}>
      {/* Header */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 8,
          marginBottom: 8,
          color: "var(--accent)",
          fontSize: 12,
        }}
      >
        <Sparkles size={13} />
        <span style={{ fontFamily: "var(--font-display)", fontWeight: 600 }}>
          RepoMind
        </span>
        {msg.iterations && (
          <span
            style={{
              background: "var(--accent-dim)",
              color: "var(--accent)",
              padding: "1px 7px",
              borderRadius: 20,
              fontSize: 10,
              border: "1px solid var(--accent)",
            }}
          >
            {msg.iterations} tool calls
          </span>
        )}
      </div>

      {/* Loading state */}
      {msg.loading ? (
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 10,
            padding: "16px 20px",
            background: "var(--bg-elevated)",
            border: "1px solid var(--border)",
            borderRadius: 8,
            color: "var(--text-muted)",
          }}
        >
          <Loader2 size={14} className="spin" color="var(--accent)" />
          <span style={{ fontSize: 12 }}>Searching codebase...</span>
          <span
            style={{
              marginLeft: "auto",
              fontSize: 11,
              color: "var(--text-dim)",
            }}
          >
            this may take 30-60s
          </span>
        </div>
      ) : (
        <>
          {/* Content */}
          <div
            style={{
              background: "var(--bg-elevated)",
              border: "1px solid var(--border)",
              borderRadius: 8,
              overflow: "hidden",
            }}
          >
            {parts?.map((part, i) =>
              part.type === "code" ? (
                <div key={i} style={{ position: "relative" }}>
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      padding: "6px 12px",
                      background: "var(--bg-surface)",
                      borderBottom: "1px solid var(--border)",
                      fontSize: 11,
                      color: "var(--text-muted)",
                    }}
                  >
                    <div
                      style={{ display: "flex", alignItems: "center", gap: 6 }}
                    >
                      <FileCode2 size={11} color="var(--accent)" />
                      <span>{part.lang}</span>
                    </div>
                    <CopyButton text={part.content} />
                  </div>
                  <SyntaxHighlighter
                    language={part.lang}
                    style={vscDarkPlus}
                    customStyle={{
                      margin: 0,
                      padding: "14px 16px",
                      background: "#0d0f14",
                      fontSize: 12,
                      lineHeight: 1.7,
                    }}
                  >
                    {part.content}
                  </SyntaxHighlighter>
                </div>
              ) : (
                <div
                  key={i}
                  style={{
                    padding: "14px 18px",
                    fontSize: 13,
                    lineHeight: 1.8,
                    color: "var(--text-primary)",
                    whiteSpace: "pre-wrap",
                    wordBreak: "break-word",
                  }}
                >
                  {part.content.split("\n").map((line, j) => {
                    const isFileCite = line.match(/`src\/|`tests\//);
                    const isBullet = line.trim().startsWith("-");
                    const isHeader =
                      line.trim().endsWith(":") && line.trim().length < 60;
                    return (
                      <div
                        key={j}
                        style={{
                          color: isFileCite
                            ? "var(--cyan)"
                            : isHeader
                              ? "var(--amber)"
                              : isBullet
                                ? "var(--text-primary)"
                                : "var(--text-primary)",
                          fontWeight: isHeader ? 600 : 400,
                          marginLeft: isBullet ? 0 : 0,
                          marginBottom: line === "" ? 6 : 0,
                        }}
                      >
                        {line || "\u00A0"}
                      </div>
                    );
                  })}
                </div>
              ),
            )}
          </div>

          {/* Cited files */}
          {msg.citedFiles && msg.citedFiles.length > 0 && (
            <div
              style={{
                marginTop: 8,
                display: "flex",
                flexWrap: "wrap",
                gap: 6,
              }}
            >
              {msg.citedFiles.slice(0, 8).map((f, i) => (
                <span
                  key={i}
                  style={{
                    background: "var(--bg-elevated)",
                    border: "1px solid var(--border)",
                    borderRadius: 4,
                    padding: "2px 8px",
                    fontSize: 11,
                    color: "var(--text-muted)",
                    fontFamily: "var(--font-mono)",
                    display: "flex",
                    alignItems: "center",
                    gap: 4,
                  }}
                >
                  <FileCode2 size={10} color="var(--green)" />
                  {f.split("/").pop()}
                </span>
              ))}
              {msg.citedFiles.length > 8 && (
                <span
                  style={{
                    fontSize: 11,
                    color: "var(--text-dim)",
                    padding: "2px 6px",
                  }}
                >
                  +{msg.citedFiles.length - 8} more
                </span>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}

// ── IndexPanel ───────────────────────────────────────────────────
function IndexPanel({ onIndexed }) {
  const [url, setUrl] = useState("");
  const [status, setStatus] = useState("idle");
  const [progress, setProgress] = useState("");
  const [errorMsg, setErrorMsg] = useState("");

  const EXAMPLES = [
    "https://github.com/pallets/flask",
    "https://github.com/fastapi/fastapi",
    "https://github.com/tiangolo/sqlmodel",
  ];

  const handleIndex = async () => {
    if (!url.trim()) return;
    setStatus("indexing");
    setProgress("Cloning repository...");
    setErrorMsg("");

    try {
      await axios.post(`${API_BASE}/index`, { repo_url: url });

      const messages = [
        "Cloning repository...",
        "Walking file tree...",
        "Parsing with tree-sitter...",
        "Building BM25 index...",
        "Embedding chunks...",
        "Storing in Qdrant...",
        "Verifying...",
      ];

      let msgIdx = 0;
      const interval = setInterval(() => {
        if (msgIdx < messages.length - 1) {
          msgIdx++;
          setProgress(messages[msgIdx]);
        }
      }, 6000);

      while (true) {
        await sleep(4000);
        const { data } = await axios.get(
          `${API_BASE}/repos/${encodeURIComponent(url)}/status`,
        );
        if (data.status === "ready") {
          clearInterval(interval);
          setStatus("done");
          setProgress(`${data.summary?.chunks_stored || 0} chunks indexed`);
          onIndexed(url);
          break;
        }
        if (data.status === "failed") {
          clearInterval(interval);
          setStatus("error");
          setErrorMsg(data.summary?.error || "Indexing failed");
          break;
        }
      }
    } catch (e) {
      setStatus("error");
      setErrorMsg(e.message || "Network error");
    }
  };

  return (
    <div style={{ padding: "24px 0" }}>
      <div
        style={{
          fontSize: 11,
          color: "var(--accent)",
          fontFamily: "var(--font-mono)",
          marginBottom: 6,
          letterSpacing: 1,
        }}
      >
        $ repomind index
      </div>
      <div
        style={{
          display: "flex",
          gap: 8,
          alignItems: "stretch",
          marginBottom: 12,
        }}
      >
        <div style={{ position: "relative", flex: 1 }}>
          <GitBranch
            size={14}
            color="var(--text-muted)"
            style={{
              position: "absolute",
              left: 12,
              top: "50%",
              transform: "translateY(-50%)",
              pointerEvents: "none",
            }}
          />
          <input
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleIndex()}
            placeholder="https://github.com/owner/repo"
            disabled={status === "indexing"}
            style={{
              width: "100%",
              padding: "10px 12px 10px 36px",
              background: "var(--bg-elevated)",
              border: "1px solid var(--border-light)",
              borderRadius: 6,
              color: "var(--text-primary)",
              fontFamily: "var(--font-mono)",
              fontSize: 13,
              outline: "none",
              transition: "border-color .2s",
            }}
            onFocus={(e) => (e.target.style.borderColor = "var(--accent)")}
            onBlur={(e) => (e.target.style.borderColor = "var(--border-light)")}
          />
        </div>
        <button
          onClick={handleIndex}
          disabled={status === "indexing" || !url.trim()}
          style={{
            padding: "10px 20px",
            background:
              status === "indexing" ? "var(--bg-elevated)" : "var(--accent)",
            border: "1px solid var(--accent)",
            borderRadius: 6,
            color: "white",
            fontFamily: "var(--font-mono)",
            fontSize: 12,
            cursor: status === "indexing" ? "not-allowed" : "pointer",
            display: "flex",
            alignItems: "center",
            gap: 6,
            transition: "all .2s",
            whiteSpace: "nowrap",
            opacity: status === "indexing" ? 0.6 : 1,
          }}
        >
          {status === "indexing" ? (
            <>
              <Loader2 size={13} className="spin" /> Indexing
            </>
          ) : (
            <>
              <Zap size={13} /> Index
            </>
          )}
        </button>
      </div>

      {/* Status */}
      {status === "indexing" && (
        <div
          style={{
            padding: "10px 14px",
            background: "var(--accent-dim)",
            border: "1px solid var(--accent)",
            borderRadius: 6,
            fontSize: 12,
            color: "var(--accent)",
            display: "flex",
            alignItems: "center",
            gap: 8,
          }}
        >
          <Loader2 size={12} className="spin" />
          {progress}
        </div>
      )}
      {status === "done" && (
        <div
          style={{
            padding: "10px 14px",
            background: "var(--green-dim)",
            border: "1px solid var(--green)",
            borderRadius: 6,
            fontSize: 12,
            color: "var(--green)",
            display: "flex",
            alignItems: "center",
            gap: 8,
          }}
        >
          <CheckCircle2 size={12} />
          Ready — {progress}
        </div>
      )}
      {status === "error" && (
        <div
          style={{
            padding: "10px 14px",
            background: "var(--red-dim)",
            border: "1px solid var(--red)",
            borderRadius: 6,
            fontSize: 12,
            color: "var(--red)",
            display: "flex",
            alignItems: "center",
            gap: 8,
          }}
        >
          <XCircle size={12} />
          {errorMsg}
        </div>
      )}

      {/* Examples */}
      {status === "idle" && (
        <div style={{ marginTop: 14 }}>
          <div
            style={{ fontSize: 11, color: "var(--text-dim)", marginBottom: 6 }}
          >
            try an example:
          </div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
            {EXAMPLES.map((ex) => (
              <button
                key={ex}
                onClick={() => setUrl(ex)}
                style={{
                  background: "none",
                  border: "1px solid var(--border)",
                  borderRadius: 4,
                  padding: "3px 10px",
                  color: "var(--text-muted)",
                  fontSize: 11,
                  fontFamily: "var(--font-mono)",
                  cursor: "pointer",
                  transition: "all .15s",
                }}
                onMouseEnter={(e) => {
                  e.target.style.borderColor = "var(--accent)";
                  e.target.style.color = "var(--accent)";
                }}
                onMouseLeave={(e) => {
                  e.target.style.borderColor = "var(--border)";
                  e.target.style.color = "var(--text-muted)";
                }}
              >
                {ex.split("/").slice(-1)[0]}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ── Main App ─────────────────────────────────────────────────────
export default function App() {
  const [indexedRepo, setIndexedRepo] = useState("");
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [querying, setQuerying] = useState(false);
  const [view, setView] = useState("index");
  const bottomRef = useRef(null);
  const inputRef = useRef(null);

  const SUGGESTED = [
    "How does request context work?",
    "How does Blueprint registration work?",
    "What is the g object and how is it reset?",
    "How does Flask handle exceptions?",
    "How does the test client work?",
  ];

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleIndexed = useCallback((url) => {
    setIndexedRepo(url);
    setMessages([
      {
        id: uid(),
        type: "system",
        content: `indexed ${url.split("/").slice(-2).join("/")} — ${new Date().toLocaleTimeString()}`,
        timestamp: new Date(),
      },
    ]);
    setView("chat");
  }, []);

  const sendQuery = useCallback(
    async (q) => {
      if (!q.trim() || querying || !indexedRepo) return;
      const query = q.trim();
      setInput("");
      setQuerying(true);

      const userMsg = {
        id: uid(),
        type: "user",
        content: query,
        timestamp: new Date(),
      };
      const loadingMsg = {
        id: uid(),
        type: "assistant",
        content: "",
        timestamp: new Date(),
        loading: true,
      };

      setMessages((prev) => [...prev, userMsg, loadingMsg]);

      try {
        const { data } = await axios.post(`${API_BASE}/query`, {
          repo_url: indexedRepo,
          query,
        });

        setMessages((prev) =>
          prev.map((m) =>
            m.id === loadingMsg.id
              ? {
                  ...m,
                  loading: false,
                  content: data.answer,
                  citedFiles: data.cited_files,
                  iterations: data.iterations,
                }
              : m,
          ),
        );
      } catch (e) {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === loadingMsg.id
              ? {
                  ...m,
                  loading: false,
                  content: `Error: ${e.response?.data?.detail || e.message}`,
                }
              : m,
          ),
        );
      } finally {
        setQuerying(false);
        setTimeout(() => inputRef.current?.focus(), 100);
      }
    },
    [querying, indexedRepo],
  );

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        height: "100vh",
        overflow: "hidden",
      }}
    >
      {/* Header */}
      <header
        style={{
          borderBottom: "1px solid var(--border)",
          background: "var(--bg-surface)",
          padding: "0 24px",
          display: "flex",
          alignItems: "center",
          gap: 16,
          height: 52,
          flexShrink: 0,
          position: "relative",
        }}
      >
        {/* Logo */}
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <div
            style={{
              width: 28,
              height: 28,
              background: "linear-gradient(135deg, var(--accent), var(--cyan))",
              borderRadius: 6,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              flexShrink: 0,
              boxShadow: "0 0 12px var(--accent-glow)",
            }}
          >
            <Terminal size={14} color="white" />
          </div>
          <span
            style={{
              fontFamily: "var(--font-display)",
              fontWeight: 800,
              fontSize: 16,
              letterSpacing: "-0.5px",
              background: "linear-gradient(135deg, #e8eaf0, var(--accent))",
              WebkitBackgroundClip: "text",
              WebkitTextFillColor: "transparent",
            }}
          >
            RepoMind
          </span>
        </div>

        {/* Nav tabs */}
        <div style={{ display: "flex", gap: 2, marginLeft: 8 }}>
          {["index", "chat"].map((v) => (
            <button
              key={v}
              onClick={() => setView(v)}
              style={{
                background: view === v ? "var(--accent-dim)" : "none",
                border:
                  view === v
                    ? "1px solid var(--accent)"
                    : "1px solid transparent",
                borderRadius: 5,
                padding: "4px 12px",
                color: view === v ? "var(--accent)" : "var(--text-muted)",
                fontFamily: "var(--font-mono)",
                fontSize: 12,
                cursor: "pointer",
                transition: "all .15s",
              }}
            >
              {v === "index" ? "$ index" : "> query"}
            </button>
          ))}
        </div>

        {/* Repo badge */}
        {indexedRepo && (
          <div
            style={{
              marginLeft: "auto",
              display: "flex",
              alignItems: "center",
              gap: 6,
              background: "var(--green-dim)",
              border: "1px solid var(--green)",
              borderRadius: 5,
              padding: "3px 10px",
              fontSize: 11,
              color: "var(--green)",
            }}
          >
            <CheckCircle2 size={11} />
            {indexedRepo.split("/").slice(-2).join("/")}
          </div>
        )}

        {/* API link */}
        <a
          href={`${API_BASE}/docs`}
          target="_blank"
          rel="noreferrer"
          style={{
            marginLeft: indexedRepo ? 8 : "auto",
            display: "flex",
            alignItems: "center",
            gap: 4,
            color: "var(--text-dim)",
            fontSize: 11,
            textDecoration: "none",
            transition: "color .15s",
          }}
          onMouseEnter={(e) =>
            (e.currentTarget.style.color = "var(--text-muted)")
          }
          onMouseLeave={(e) =>
            (e.currentTarget.style.color = "var(--text-dim)")
          }
        >
          <ExternalLink size={11} />
          API docs
        </a>
      </header>

      {/* Main content */}
      <main
        style={{
          flex: 1,
          overflow: "hidden",
          display: "flex",
          flexDirection: "column",
        }}
      >
        {/* INDEX VIEW */}
        {view === "index" && (
          <div
            style={{
              flex: 1,
              overflowY: "auto",
              padding: "0 24px 24px",
              maxWidth: 720,
              margin: "0 auto",
              width: "100%",
            }}
          >
            {/* Hero */}
            <div style={{ padding: "48px 0 32px", textAlign: "center" }}>
              <div
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 8,
                  background: "var(--accent-dim)",
                  border: "1px solid var(--accent)",
                  borderRadius: 20,
                  padding: "4px 14px",
                  marginBottom: 24,
                  fontSize: 11,
                  color: "var(--accent)",
                }}
              >
                <Sparkles size={11} />
                Agentic RAG · Hybrid Search · RAGAS Evaluated
              </div>
              <h1
                style={{
                  fontFamily: "var(--font-display)",
                  fontWeight: 800,
                  fontSize: 42,
                  lineHeight: 1.1,
                  letterSpacing: "-1.5px",
                  marginBottom: 16,
                  background:
                    "linear-gradient(160deg, #e8eaf0 30%, var(--accent) 100%)",
                  WebkitBackgroundClip: "text",
                  WebkitTextFillColor: "transparent",
                }}
              >
                Ask anything about
                <br />
                any codebase
              </h1>
              <p
                style={{
                  color: "var(--text-muted)",
                  fontSize: 14,
                  lineHeight: 1.7,
                  maxWidth: 460,
                  margin: "0 auto 32px",
                }}
              >
                Paste a GitHub URL. RepoMind indexes the repo with AST-aware
                chunking, hybrid search, and a LangGraph agent that traces
                across files to answer your questions with citations.
              </p>
            </div>

            {/* Index form */}
            <div
              style={{
                background: "var(--bg-surface)",
                border: "1px solid var(--border)",
                borderRadius: 10,
                padding: "20px 24px",
              }}
            >
              <IndexPanel onIndexed={handleIndexed} />
            </div>

            {/* Feature grid */}
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "1fr 1fr",
                gap: 12,
                marginTop: 24,
              }}
            >
              {[
                {
                  icon: "⚡",
                  title: "AST-Aware Chunking",
                  desc: "tree-sitter parses code into functions and classes — never splits mid-expression",
                },
                {
                  icon: "🔍",
                  title: "Hybrid Search",
                  desc: "Dense embeddings + BM25 keywords merged with Reciprocal Rank Fusion",
                },
                {
                  icon: "🤖",
                  title: "Agentic Retrieval",
                  desc: "LangGraph agent decides what to search next — multi-hop across files",
                },
                {
                  icon: "📊",
                  title: "RAGAS Evaluated",
                  desc: "0.847 faithfulness on 15-question benchmark — grounded answers, not hallucinations",
                },
              ].map((f) => (
                <div
                  key={f.title}
                  style={{
                    background: "var(--bg-surface)",
                    border: "1px solid var(--border)",
                    borderRadius: 8,
                    padding: "16px 18px",
                    transition: "border-color .2s",
                  }}
                  onMouseEnter={(e) =>
                    (e.currentTarget.style.borderColor = "var(--border-light)")
                  }
                  onMouseLeave={(e) =>
                    (e.currentTarget.style.borderColor = "var(--border)")
                  }
                >
                  <div style={{ fontSize: 20, marginBottom: 8 }}>{f.icon}</div>
                  <div
                    style={{
                      fontFamily: "var(--font-display)",
                      fontWeight: 600,
                      fontSize: 13,
                      marginBottom: 4,
                      color: "var(--text-primary)",
                    }}
                  >
                    {f.title}
                  </div>
                  <div
                    style={{
                      fontSize: 12,
                      color: "var(--text-muted)",
                      lineHeight: 1.6,
                    }}
                  >
                    {f.desc}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* CHAT VIEW */}
        {view === "chat" && (
          <>
            {/* Messages */}
            <div
              style={{
                flex: 1,
                overflowY: "auto",
                padding: "16px 24px",
                maxWidth: 820,
                margin: "0 auto",
                width: "100%",
              }}
            >
              {messages.length === 0 ? (
                <div style={{ textAlign: "center", paddingTop: 60 }}>
                  <div style={{ fontSize: 32, marginBottom: 16 }}>💬</div>
                  <div
                    style={{
                      fontFamily: "var(--font-display)",
                      fontWeight: 600,
                      fontSize: 18,
                      color: "var(--text-primary)",
                      marginBottom: 8,
                    }}
                  >
                    Index a repo first
                  </div>
                  <div style={{ fontSize: 13, color: "var(--text-muted)" }}>
                    Go to the Index tab and paste a GitHub URL
                  </div>
                </div>
              ) : (
                <>
                  {messages.map((msg) => (
                    <MessageBubble key={msg.id} msg={msg} />
                  ))}

                  {/* Suggested questions — show after first answer */}
                  {messages.filter((m) => m.type === "assistant" && !m.loading)
                    .length === 1 && (
                    <div style={{ marginTop: 16 }}>
                      <div
                        style={{
                          fontSize: 11,
                          color: "var(--text-dim)",
                          marginBottom: 8,
                        }}
                      >
                        suggested questions:
                      </div>
                      <div
                        style={{ display: "flex", flexWrap: "wrap", gap: 6 }}
                      >
                        {SUGGESTED.map((s) => (
                          <button
                            key={s}
                            onClick={() => sendQuery(s)}
                            style={{
                              background: "var(--bg-elevated)",
                              border: "1px solid var(--border)",
                              borderRadius: 5,
                              padding: "5px 12px",
                              color: "var(--text-muted)",
                              fontSize: 12,
                              fontFamily: "var(--font-mono)",
                              cursor: "pointer",
                              transition: "all .15s",
                              textAlign: "left",
                            }}
                            onMouseEnter={(e) => {
                              e.currentTarget.style.borderColor =
                                "var(--accent)";
                              e.currentTarget.style.color = "var(--accent)";
                            }}
                            onMouseLeave={(e) => {
                              e.currentTarget.style.borderColor =
                                "var(--border)";
                              e.currentTarget.style.color = "var(--text-muted)";
                            }}
                          >
                            {s}
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                </>
              )}
              <div ref={bottomRef} />
            </div>

            {/* Input bar */}
            <div
              style={{
                borderTop: "1px solid var(--border)",
                background: "var(--bg-surface)",
                padding: "12px 24px",
                flexShrink: 0,
              }}
            >
              <div
                style={{
                  maxWidth: 820,
                  margin: "0 auto",
                  display: "flex",
                  gap: 10,
                  alignItems: "flex-end",
                }}
              >
                {!indexedRepo && (
                  <div
                    style={{
                      flex: 1,
                      padding: "10px 14px",
                      background: "var(--amber-dim)",
                      border: "1px solid var(--amber)",
                      borderRadius: 6,
                      fontSize: 12,
                      color: "var(--amber)",
                      display: "flex",
                      alignItems: "center",
                      gap: 8,
                    }}
                  >
                    <AlertCircle size={13} />
                    Index a repository first before querying
                  </div>
                )}
                {indexedRepo && (
                  <>
                    <div style={{ position: "relative", flex: 1 }}>
                      <textarea
                        ref={inputRef}
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === "Enter" && !e.shiftKey) {
                            e.preventDefault();
                            sendQuery(input);
                          }
                        }}
                        placeholder="Ask about the codebase... (Enter to send, Shift+Enter for newline)"
                        disabled={querying}
                        rows={1}
                        style={{
                          width: "100%",
                          padding: "10px 14px",
                          background: "var(--bg-elevated)",
                          border: "1px solid var(--border-light)",
                          borderRadius: 6,
                          color: "var(--text-primary)",
                          fontFamily: "var(--font-mono)",
                          fontSize: 13,
                          outline: "none",
                          resize: "none",
                          transition: "border-color .2s",
                          lineHeight: 1.6,
                        }}
                        onFocus={(e) =>
                          (e.target.style.borderColor = "var(--accent)")
                        }
                        onBlur={(e) =>
                          (e.target.style.borderColor = "var(--border-light)")
                        }
                      />
                    </div>
                    <button
                      onClick={() => sendQuery(input)}
                      disabled={querying || !input.trim()}
                      style={{
                        padding: "10px 16px",
                        background: querying
                          ? "var(--bg-elevated)"
                          : "var(--accent)",
                        border: "1px solid var(--accent)",
                        borderRadius: 6,
                        color: "white",
                        cursor: querying ? "not-allowed" : "pointer",
                        display: "flex",
                        alignItems: "center",
                        gap: 6,
                        fontFamily: "var(--font-mono)",
                        fontSize: 12,
                        transition: "all .2s",
                        flexShrink: 0,
                        opacity: querying ? 0.5 : 1,
                      }}
                    >
                      {querying ? (
                        <Loader2 size={14} className="spin" />
                      ) : (
                        <>
                          <Search size={13} />
                          <ChevronRight size={13} />
                        </>
                      )}
                    </button>
                  </>
                )}
              </div>
              <div
                style={{
                  maxWidth: 820,
                  margin: "6px auto 0",
                  fontSize: 10,
                  color: "var(--text-dim)",
                  display: "flex",
                  justifyContent: "space-between",
                }}
              >
                <span>⏎ send · ⇧⏎ newline</span>
                {indexedRepo && (
                  <span style={{ color: "var(--green)", opacity: 0.7 }}>
                    ● {indexedRepo.split("/").slice(-2).join("/")}
                  </span>
                )}
              </div>
            </div>
          </>
        )}
      </main>
    </div>
  );
}
