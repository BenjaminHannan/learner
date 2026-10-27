#!/bin/bash
# when agent 15 exits without tables, launch the corrected 15b
while pgrep -f "queue/15-relation-alias" > /dev/null || pgrep -f "15-relation-alias.md" >/dev/null; do sleep 15; done
if [ ! -f /Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27/data/open/wikidata-props/alias_table.json ]; then /private/tmp/claude-502/-Users-ben-hannan-Desktop-projects-beautiful-model--claude-worktrees-card-experiment-handoff-7c5b27/76c622f5-1395-42cc-b432-71b65f256cf4/scratchpad/mimo/resume.sh /private/tmp/claude-502/-Users-ben-hannan-Desktop-projects-beautiful-model--claude-worktrees-card-experiment-handoff-7c5b27/76c622f5-1395-42cc-b432-71b65f256cf4/scratchpad/mimo/queue/15b-relation-alias.md; fi
