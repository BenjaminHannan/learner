import sys, time
PACK = "/Users/ben-hannan/Desktop/projects/beautiful-model/.runtime/teacher/models/Ternary-Bonsai-2-27B-mlx-2bit"
sys.path.insert(0, PACK + "/runtime")
import mlx.core as mx
from vision_artifact import load_vl_model
from mlx_vlm import generate
t = time.time()
model, processor, config = load_vl_model(PACK)
print(f"LOAD_SECONDS={time.time()-t:.1f}")
tok = processor.tokenizer
request = ("Rewrite the sentence below in 8 different ways, using simple words a child knows. "
           "Keep the placeholders <A> and <PLACE> exactly as written and do not add any new facts. "
           "Output one sentence per line and nothing else.\n\nSentence: <A> walks to the <PLACE>.")
prompt = tok.apply_chat_template([{"role": "user", "content": request}], tokenize=False, add_generation_prompt=True, enable_thinking=False)
for run in range(2):
    t = time.time()
    result = generate(model, processor, prompt, image=None, max_tokens=160, temperature=0.7, verbose=False)
    wall = time.time() - t
    text = getattr(result, "text", result)
    print(f"RUN{run} wall={wall:.1f}s gen_tps={getattr(result,'generation_tps',None)} prompt_tps={getattr(result,'prompt_tps',None)} gen_tokens={getattr(result,'generation_tokens',None)} peak_mem_gb={getattr(result,'peak_memory',None)}")
print("OUTPUT:\n" + text)
