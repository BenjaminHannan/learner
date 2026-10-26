"""Run in the tau2 venv: write {domain}.json with the tool schemas and the normal agent system prompt exactly as tau2's LLMAgent builds them."""
import json, sys
from tau2.agent.llm_agent import AGENT_INSTRUCTION, SYSTEM_PROMPT
from tau2.registry import registry

out = sys.argv[1]
for dom in sys.argv[2:]:
    env = registry.get_env_constructor(dom)()
    pol = env.get_policy()
    json.dump({"policy": pol, "tools": [t.openai_schema for t in env.get_tools()],
               "system": SYSTEM_PROMPT.format(domain_policy=pol, agent_instruction=AGENT_INSTRUCTION)},
              open(f"{out}/env_{dom}.json", "w"))
    print(dom, "tools:", len(env.get_tools()), "policy chars:", len(pol))
