"""Patch tau2's LLMAgent so env SKILLSLEEP_HINT (a reviewer critique) is appended to the system prompt. No env var = unchanged prompt."""
import sys
p = sys.argv[1] + "/src/tau2/agent/llm_agent.py"
s = open(p).read()
if "SKILLSLEEP_HINT" in s:
    print("hint patch already applied"); sys.exit(0)
old = """        return SYSTEM_PROMPT.format(
            domain_policy=self.domain_policy, agent_instruction=AGENT_INSTRUCTION
        )

    def get_init_state("""
new = """        import os  # PATCHED (skillsleep): retry hint
        prompt = SYSTEM_PROMPT.format(
            domain_policy=self.domain_policy, agent_instruction=AGENT_INSTRUCTION
        )
        hint = os.environ.get("SKILLSLEEP_HINT")
        if hint:
            prompt += "\\n<reviewer_notes>\\nA reviewer read an earlier failed attempt at a request like this one:\\n" + hint + "\\n</reviewer_notes>"
        return prompt

    def get_init_state("""
assert s.count(old) == 1, "llm_agent.py system_prompt not found"
open(p, "w").write(s.replace(old, new)); print("hint patch applied")
