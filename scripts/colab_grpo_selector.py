"""EXP-009 (runs on a Colab GPU): GRPO fine-tuning of a small LLM as a budgeted memory selector.

Input  /content/llm_selector/{train,test}.jsonl  (from scripts/llm_selector_data.py)
Output /content/out/exp009_llm.json, /content/out/exp009_llm_preds.jsonl, /content/out/adapter/

The model sees a question, a read budget and K numbered candidate memories with token counts, and
replies with candidate ids in priority order. Ids are packed in that order until the budget is full;
reward = gold-evidence recall of the packed set (+ a small format term). The untrained base model is
evaluated with the same prompt first, so the effect of RL is measured directly.
"""

import argparse
import json
import random
import re
import time
from pathlib import Path

import torch
from datasets import Dataset
from peft import LoraConfig
from transformers import AutoModelForCausalLM, AutoTokenizer
from trl import GRPOConfig, GRPOTrainer

DATA = Path("/content/llm_selector")
OUT = Path("/content/out")

SYSTEM = ("You select memories for a question-answering assistant that can only read a limited number of "
          "tokens. Pick the memories that contain the evidence needed to answer the question, most useful "
          "first, and stay within the token budget. Reply with memory ids only, comma-separated, e.g. 4, 1, 17.")


def prompt_of(r):
    lines = [f"[{i + 1}] ({n} tok) {t}" for i, (t, n) in enumerate(zip(r["texts"], r["ntok"]))]
    user = (f"Question: {r['question']}\nToken budget: {r['budget']}\n\nMemories:\n" + "\n".join(lines) +
            "\n\nIds of the memories to give the assistant, most useful first:")
    return [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}]


def parse_ids(text, k):
    out = []
    for m in re.findall(r"\d+", text):
        i = int(m) - 1
        if 0 <= i < k and i not in out:
            out.append(i)
    return out


def packed_recall(ids, ntok, cover, n_ev, budget):
    used, got = 0, set()
    for i in ids:
        if used + ntok[i] > budget:
            break  # prefix packing, as for every other method
        used += ntok[i]
        got.update(cover[i])
    return len(got) / n_ev


def reward_fn(prompts, completions, ntok, cover, n_evidence, budget, **_):
    out = []
    for c, nt, cv, ne, b in zip(completions, ntok, cover, n_evidence, budget):
        text = c[0]["content"] if isinstance(c, list) else c
        ids = parse_ids(text, len(nt))
        r = packed_recall(ids, nt, cv, ne, b) if ids else 0.0
        out.append(r - (0.2 if not ids else 0.0))
    return out


@torch.no_grad()
def evaluate(model, tok, rows, bs, max_new):
    model.eval()
    tok.padding_side = "left"
    preds = []
    for s in range(0, len(rows), bs):
        batch = rows[s:s + bs]
        texts = [tok.apply_chat_template(prompt_of(r), tokenize=False, add_generation_prompt=True) for r in batch]
        enc = tok(texts, return_tensors="pt", padding=True).to(model.device)
        gen = model.generate(**enc, max_new_tokens=max_new, do_sample=False, pad_token_id=tok.pad_token_id)
        for r, g in zip(batch, gen[:, enc["input_ids"].shape[1]:]):
            text = tok.decode(g, skip_special_tokens=True)
            ids = parse_ids(text, len(r["ntok"]))
            preds.append(dict(qid=r["qid"], budget=r["budget"], text=text, ids=ids,
                              recall=packed_recall(ids, r["ntok"], r["cover"], r["n_evidence"], r["budget"])))
        print(f"  eval {min(s + bs, len(rows))}/{len(rows)}", flush=True)
    return preds


def summarise(preds):
    res = {}
    for b in sorted({p["budget"] for p in preds}):
        ps = [p for p in preds if p["budget"] == b]
        res[str(b)] = dict(recall=sum(p["recall"] for p in ps) / len(ps),
                           parse_fail=sum(not p["ids"] for p in ps) / len(ps),
                           mean_ids=sum(len(p["ids"]) for p in ps) / len(ps))
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="Qwen/Qwen2.5-1.5B-Instruct")
    ap.add_argument("--steps", type=int, default=400)
    ap.add_argument("--gens", type=int, default=8)
    ap.add_argument("--prompts_per_step", type=int, default=4)
    ap.add_argument("--lr", type=float, default=2e-5)
    ap.add_argument("--max_new", type=int, default=48)
    ap.add_argument("--eval_bs", type=int, default=16)
    ap.add_argument("--limit_test", type=int, default=0)
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    random.seed(0)
    torch.manual_seed(0)

    train = [json.loads(l) for l in open(DATA / "train.jsonl")]
    test = [json.loads(l) for l in open(DATA / "test.jsonl")]
    if args.limit_test:
        test = test[:args.limit_test]
    bf16 = torch.cuda.is_bf16_supported()
    dtype = torch.bfloat16 if bf16 else torch.float16
    print(f"GPU {torch.cuda.get_device_name(0)}  bf16={bf16}  train={len(train)} test={len(test)}", flush=True)

    tok = AutoTokenizer.from_pretrained(args.model)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    model = AutoModelForCausalLM.from_pretrained(args.model, torch_dtype=dtype, device_map="cuda")

    t0 = time.time()
    base_preds = evaluate(model, tok, test, args.eval_bs, args.max_new)
    base_eval_s = time.time() - t0
    base = summarise(base_preds)
    print("base model:", json.dumps(base), flush=True)

    ds = Dataset.from_list([dict(prompt=prompt_of(r), ntok=r["ntok"], cover=r["cover"], n_evidence=r["n_evidence"],
                                 budget=r["budget"]) for r in train]).shuffle(seed=0)
    cfg = GRPOConfig(
        output_dir=str(OUT / "ckpt"), max_steps=args.steps, learning_rate=args.lr,
        per_device_train_batch_size=args.gens * args.prompts_per_step // 2, gradient_accumulation_steps=2,
        num_generations=args.gens, max_completion_length=args.max_new, temperature=1.0,
        logging_steps=10, save_strategy="no", report_to="none", bf16=bf16, fp16=not bf16,
        gradient_checkpointing=True, seed=0,
    )
    for k, v in dict(max_prompt_length=2048, beta=0.0).items():
        if hasattr(cfg, k):
            setattr(cfg, k, v)
    trainer = GRPOTrainer(model=model, reward_funcs=[reward_fn], args=cfg, train_dataset=ds, processing_class=tok,
                          peft_config=LoraConfig(r=16, lora_alpha=32, lora_dropout=0.0, task_type="CAUSAL_LM",
                                                 target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                                                                 "gate_proj", "up_proj", "down_proj"]))
    t0 = time.time()
    trainer.train()
    train_s = time.time() - t0
    trainer.model.save_pretrained(str(OUT / "adapter"))
    log = [h for h in trainer.state.log_history if "reward" in h or "rewards/reward_fn/mean" in h]

    t0 = time.time()
    rl_preds = evaluate(trainer.model, tok, test, args.eval_bs, args.max_new)
    rl_eval_s = time.time() - t0
    rl = summarise(rl_preds)
    print("GRPO model:", json.dumps(rl), flush=True)

    with open(OUT / "exp009_llm_preds.jsonl", "w") as f:
        for tag, ps in [("base", base_preds), ("grpo", rl_preds)]:
            for p in ps:
                f.write(json.dumps(dict(p, model=tag)) + "\n")
    json.dump(dict(model=args.model, gpu=torch.cuda.get_device_name(0), steps=args.steps, gens=args.gens,
                   prompts_per_step=args.prompts_per_step, lr=args.lr, lora_r=16, train_seconds=train_s,
                   eval_ms_per_query=dict(base=1000 * base_eval_s / len(test), grpo=1000 * rl_eval_s / len(test)),
                   base=base, grpo=rl, train_log=log), open(OUT / "exp009_llm.json", "w"), indent=2)
    print("saved /content/out/exp009_llm.json", flush=True)


if __name__ == "__main__":
    main()
