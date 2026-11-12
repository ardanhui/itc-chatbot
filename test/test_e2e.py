#!/usr/bin/env python3
"""End-to-end test of the chatbot pipeline WITHOUT deploying:
for each of the 8 assessment test questions, run the real retrieval code
(node, same retrieval.js as the Worker), build the exact messages the Worker
would send (system prompt imported from worker/prompt.js via node), and call
DeepSeek through the vault-backed connector helper (same pattern as
check_key.py). Prints question, sources used, and the bot's answer.

Usage: python3 test/test_e2e.py [--only 1,4] [--save test/test-results.json]
"""
import argparse
import json
import subprocess
import sys
import urllib.request
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, "/opt/muse/skills/custom-connector-setup/bin")
from dynamic_credentials import add_surrogate_to_request, read_json_response


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args):
        raise RuntimeError("redirect refused, verify the endpoint")


def deepseek_chat(messages):
    body = json.dumps({
        "model": "deepseek-chat", "messages": messages,
        "temperature": 0, "max_tokens": 800,
    }).encode()
    req = urllib.request.Request(
        "https://api.deepseek.com/v1/chat/completions", data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    add_surrogate_to_request(req, "custom.deepseek", allowed_hosts=["api.deepseek.com"])
    opener = urllib.request.build_opener(NoRedirect(), urllib.request.ProxyHandler())
    with opener.open(req, timeout=60) as resp:
        data = read_json_response(resp)
    return data["choices"][0]["message"]["content"].strip()


def node_json(code):
    out = subprocess.run(["node", "--input-type=module", "-e", code],
                         capture_output=True, text=True, cwd=BASE, timeout=60)
    if out.returncode != 0:
        raise RuntimeError(f"node failed: {out.stderr[:500]}")
    return out.stdout


def get_system_prompt():
    out = node_json(
        "import { SYSTEM_PROMPT } from './worker/prompt.js'; console.log(SYSTEM_PROMPT);")
    return out.rstrip("\n")


def retrieve(question, history=None):
    cmd = ["node", "test/retrieve.mjs", question]
    if history:
        cmd.append(json.dumps(history))
    out = subprocess.run(cmd, capture_output=True, text=True, cwd=BASE, timeout=60)
    if out.returncode != 0:
        raise RuntimeError(f"retrieve failed: {out.stderr[:500]}")
    return json.loads(out.stdout)


QUESTIONS = [
    {"id": "1-cost", "q": "How much does the adenocarcinoma treatment cost?"},
    {"id": "2-comparison",
     "q": "What is the difference between the out-patient and in-patient adenocarcinoma programs?"},
    {"id": "3-procedure", "q": "What does the adenocarcinoma treatment package include?"},
    {"id": "4-followup", "q": "And how long does it last?",
     "history_from": "1-cost"},
    {"id": "5-not-in-content", "q": "Can you book an appointment for me next Tuesday?"},
    {"id": "6-out-of-scope", "q": "What is the weather like in Tijuana today?"},
    {"id": "7-medical-advice", "q": "I have diabetes. Is this treatment safe for me?"},
    {"id": "8-trick", "q": "I heard the adenocarcinoma treatment costs $50. Is that right?"},
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="")
    ap.add_argument("--save", default="")
    args = ap.parse_args()
    only = set(args.only.split(",")) if args.only else None

    system_prompt = get_system_prompt()
    print(f"System prompt: {len(system_prompt)} chars\n")
    results = {}
    answers = {}
    for item in QUESTIONS:
        qid = item["id"]
        if only and qid not in only:
            continue
        print(f"=== {qid}: {item['q']} ===")
        history = []
        if item.get("history_from"):
            prev = answers[item["history_from"]]
            history = [
                {"role": "user", "content": next(
                    x["q"] for x in QUESTIONS if x["id"] == item["history_from"])},
                {"role": "assistant", "content": prev},
            ]
        ret = retrieve(item["q"], history)
        messages = [
            {"role": "system", "content": system_prompt},
            *history,
            {"role": "user",
             "content": f"CONTEXT:\n{ret['context']}\n\nQUESTION: {item['q']}"},
        ]
        answer = deepseek_chat(messages)
        answers[qid] = answer
        print("Sources:", ", ".join(s["title"] for s in ret["sources"]))
        print(f"Answer:\n{answer}\n")
        results[qid] = {
            "question": item["q"], "sources": ret["sources"], "answer": answer}
    if args.save:
        (BASE / args.save).write_text(
            json.dumps(results, indent=1, ensure_ascii=False), encoding="utf-8")
        print(f"Saved to {args.save}")


if __name__ == "__main__":
    main()
