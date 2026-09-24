# OpenRouter key check 2026-09-24

Verdict: WORKS

Key file exists, key endpoint returned HTTP 200, models list fetched,
and exactly 1 chat completion call returned HTTP 200 with usage fields.
No key material is in this file.

## 1. Key file

- Path: ~/.config/openrouter/key
- Exists: yes
- Byte count (wc -c): 73
- Starts with required 6-char prefix: yes
- Permissions (stat -f %Lp): 600

## 2. Key status (GET /api/v1/key)

- HTTP status: 200
- limit: null
- limit_remaining: null
- usage: 0
- is_free_tier: false
- Not a 401, so not a BAD-KEY case.
- Other fields from the endpoint are omitted on purpose.

## 3a. Models with glm in the id (21 total)

Prices are USD per million tokens (list price x 1e6). Context = context_length.

| model id | prompt $/M | completion $/M | context |
|---|---|---|---|
| z-ai/glm-4.5 | 0.6000 | 2.2000 | 131072 |
| z-ai/glm-4.5-air | 0.1300 | 0.8500 | 131072 |
| z-ai/glm-4.5v | 0.6000 | 1.8000 | 65536 |
| z-ai/glm-4.6 | 0.4300 | 1.7500 | 204800 |
| z-ai/glm-4.6v | 0.3000 | 0.9000 | 131072 |
| z-ai/glm-4.7 | 0.4000 | 1.7500 | 204800 |
| z-ai/glm-4.7-flash | 0.0605 | 0.4000 | 200000 |
| z-ai/glm-5 | 0.6000 | 1.9200 | 204800 |
| z-ai/glm-5-turbo | 1.2000 | 4.0000 | 202752 |
| z-ai/glm-5.1 | 0.9660 | 3.0360 | 204800 |
| z-ai/glm-5.2 | 0.6496 | 2.0416 | 1048576 |
| z-ai/glm-5.2:free | 0.0000 | 0.0000 | 32768 |
| z-ai/glm-5.3 | 1.4000 | 4.4000 | 1310720 |
| z-ai/glm-5.3-flash | 0.0450 | 0.6000 | 1310720 |
| z-ai/glm-5.3-flash:batch | 0.0600 | 0.2000 | 1048576 |
| z-ai/glm-5.3-flashx | 0.3700 | 1.2500 | 1048576 |
| z-ai/glm-5.3-prime | 2.8000 | 8.8000 | 1000000 |
| z-ai/glm-5.3:batch | 0.4500 | 2.0000 | 1048576 |
| z-ai/glm-5v-turbo | 1.2000 | 4.0000 | 202752 |
| ~z-ai/glm-flash-latest | 0.0450 | 0.1400 | 1310720 |
| ~z-ai/glm-latest | 0.5614 | 1.7644 | 1310720 |

Count with glm in id: 21. Paid with glm in id: 20. Free (0/0): 1.

## 3b. 12 cheapest paid pure-text models, context >= 32000, by prompt+completion

Definition used: paid means prompt+completion price > 0;
pure-text means architecture modality exactly text-to-text;
ranked by prompt+completion list price. Prices USD per million tokens.

| # | model id | prompt $/M | completion $/M | sum $/M | context |
|---|---|---|---|---|---|
| 1 | mistralai/mistral-nemo | 0.0190 | 0.0300 | 0.0490 | 131072 |
| 2 | inclusionai/ling-3.0-flash | 0.0210 | 0.0630 | 0.0840 | 262144 |
| 3 | openai/gpt-oss-20b | 0.0180 | 0.0900 | 0.1080 | 131072 |
| 4 | ibm-granite/granite-4.0-h-micro | 0.0170 | 0.1120 | 0.1290 | 131000 |
| 5 | mistralai/mistral-small-24b-instruct-2501 | 0.0500 | 0.0800 | 0.1300 | 32768 |
| 6 | meta-llama/llama-3.1-8b-instruct | 0.0500 | 0.0800 | 0.1300 | 131072 |
| 7 | openai/gpt-oss-20b:batch | 0.0240 | 0.1120 | 0.1360 | 131072 |
| 8 | openai/gpt-oss-120b:batch | 0.0296 | 0.1360 | 0.1656 | 131072 |
| 9 | amazon/nova-micro-v1 | 0.0350 | 0.1400 | 0.1750 | 128000 |
| 10 | poolside/laguna-xs-2.1 | 0.0600 | 0.1200 | 0.1800 | 262144 |
| 11 | inference-net/schematron-v2-turbo | 0.0300 | 0.1500 | 0.1800 | 128000 |
| 12 | cohere/command-r7b-12-2024 | 0.0375 | 0.1500 | 0.1875 | 128000 |

Models endpoint total: 458. Paid pure-text candidates with context >= 32000: 129.

## 4. One tiny chat call (exactly 1 call made)

- Model id: z-ai/glm-5.3-flash
- Why this model: highest version number (5.3) among 3a ids with both glm and flash in the name.
- Request: max_tokens 5, messages [{"role":"user","content":"Reply with the single word ok."}]
- HTTP status: 200
- Reply text: empty (message content null; reasoning field contained partial text only)
- finish_reason: length
- usage: prompt_tokens 19, completion_tokens 5, total_tokens 24
- cost: 0.00000273 (upstream prompt 0.00000133, completions 0.00000140)
- Calls made in this step: 1. No retries. No model called in step 3.

## Notes and deviations

- The brief named a rules file under /private/tmp that did not exist at run time; the run followed the rules pasted in the task text instead (additive only, no key exposure, 1 call only).
- The key endpoint label field was discarded and is not quoted here, to keep key material out.
- The chat reply did not contain the word ok; with max_tokens 5 the run hit length with 5 reasoning tokens and null content. The call still proves the key works (HTTP 200 + usage/cost recorded).
- No TEST-ONLY panel was used. No model was tuned. Network calls: 3 total (1 key GET, 1 models GET, 1 chat POST).
