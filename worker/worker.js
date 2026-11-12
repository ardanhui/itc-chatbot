// worker.js — Cloudflare Worker for the ITC / PlacidWay knowledge chatbot.
// Endpoints:
//   POST /api/chat  { message, history? } -> { answer, sources }
//   POST /api/lead  { name, email, message? } -> { ok, stored }
//   GET  /api/health -> { ok, chunks, model }
// Secrets: DEEPSEEK_API_KEY (wrangler secret put DEEPSEEK_API_KEY)
// Optional bindings: LEADS_KV (lead capture), LOG_KV (unanswered questions)
// Optional var: ALLOWED_ORIGIN (defaults to *, restrict to the Pages domain)
import kbData from "./kb.json";
import { buildIndex, search, formatContext, sourceList, expandQuery } from "./retrieval.js";
import { SYSTEM_PROMPT } from "./prompt.js";

const MODEL = "deepseek-chat";
const MAX_HISTORY = 6; // last 6 messages (3 turns) for follow-ups
const TOP_K = 7;

let INDEX = null;
function getIndex() {
  if (!INDEX) INDEX = buildIndex(kbData.chunks);
  return INDEX;
}

const UNANSWERED_RE = /i don'?t know|not listed|isn'?t listed|not provided|no information on/i;

function corsHeaders(env, req) {
  const origin = req.headers.get("Origin") || "";
  const allowed = env.ALLOWED_ORIGIN || "*";
  return {
    "Access-Control-Allow-Origin": allowed === "*" ? "*" : origin === allowed ? origin : allowed,
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Max-Age": "86400",
  };
}

function jsonResponse(env, req, body, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json", ...corsHeaders(env, req) },
  });
}

async function handleChat(env, req, ctx) {
  let body;
  try {
    body = await req.json();
  } catch {
    return jsonResponse(env, req, { error: "Invalid JSON body." }, 400);
  }
  const message = (body.message || "").toString().trim();
  if (!message) return jsonResponse(env, req, { error: "message is required." }, 400);
  if (message.length > 2000) {
    return jsonResponse(env, req, { error: "message is too long (max 2000 characters)." }, 400);
  }
  const history = Array.isArray(body.history)
    ? body.history
        .filter((m) => m && (m.role === "user" || m.role === "assistant") && typeof m.content === "string")
        .slice(-MAX_HISTORY)
        .map((m) => ({ role: m.role, content: m.content.slice(0, 2000) }))
    : [];

  if (!env.DEEPSEEK_API_KEY) {
    return jsonResponse(env, req, { error: "Chat is not configured (missing API key)." }, 500);
  }

  const results = search(getIndex(), expandQuery(history, message), TOP_K);
  const context = formatContext(results);
  const messages = [
    { role: "system", content: SYSTEM_PROMPT },
    ...history,
    {
      role: "user",
      content: `CONTEXT:\n${context}\n\nQUESTION: ${message}`,
    },
  ];

  let resp;
  try {
    resp = await fetch("https://api.deepseek.com/v1/chat/completions", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${env.DEEPSEEK_API_KEY}`,
      },
      body: JSON.stringify({ model: MODEL, messages, temperature: 0, max_tokens: 800 }),
    });
  } catch (e) {
    return jsonResponse(env, req, { error: "Could not reach the language model. Please try again." }, 502);
  }
  if (!resp.ok) {
    return jsonResponse(env, req, { error: "The language model returned an error. Please try again." }, 502);
  }
  const data = await resp.json();
  const answer = (data.choices?.[0]?.message?.content || "").trim();
  if (!answer) {
    return jsonResponse(env, req, { error: "Empty answer from the language model. Please try again." }, 502);
  }

  // Nice-to-have: log unanswered questions for content-gap review.
  if (UNANSWERED_RE.test(answer) && env.LOG_KV) {
    const key = `unanswered:${Date.now()}:${Math.random().toString(36).slice(2, 8)}`;
    ctx.waitUntil(
      env.LOG_KV.put(key, JSON.stringify({ question: message, answer: answer.slice(0, 500), at: new Date().toISOString() }))
    );
  }

  return jsonResponse(env, req, { answer, sources: sourceList(results) });
}

async function handleLead(env, req) {
  let body;
  try {
    body = await req.json();
  } catch {
    return jsonResponse(env, req, { error: "Invalid JSON body." }, 400);
  }
  const name = (body.name || "").toString().trim();
  const email = (body.email || "").toString().trim();
  const message = (body.message || "").toString().trim().slice(0, 1000);
  if (!name || name.length > 100) {
    return jsonResponse(env, req, { error: "Please provide your name." }, 400);
  }
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
    return jsonResponse(env, req, { error: "Please provide a valid email address." }, 400);
  }
  let stored = false;
  if (env.LEADS_KV) {
    const key = `lead:${Date.now()}:${Math.random().toString(36).slice(2, 8)}`;
    await env.LEADS_KV.put(
      key,
      JSON.stringify({ name, email, message, at: new Date().toISOString() })
    );
    stored = true;
  }
  return jsonResponse(env, req, {
    ok: true,
    stored,
    message: "Thank you. PlacidWay will contact you about a free quote.",
  });
}

export default {
  async fetch(req, env, ctx) {
    const url = new URL(req.url);
    if (req.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: corsHeaders(env, req) });
    }
    if (url.pathname === "/api/health" && req.method === "GET") {
      return jsonResponse(env, req, {
        ok: true,
        chunks: kbData.chunks.length,
        sources: kbData.sources.length,
        model: MODEL,
      });
    }
    if (url.pathname === "/api/chat" && req.method === "POST") {
      return handleChat(env, req, ctx);
    }
    if (url.pathname === "/api/lead" && req.method === "POST") {
      return handleLead(env, req);
    }
    return jsonResponse(env, req, { error: "Not found." }, 404);
  },
};
