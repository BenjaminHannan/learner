# source me: force real Anthropic endpoint + Ben's key
unset ANTHROPIC_BASE_URL
export ANTHROPIC_API_KEY="$LEARNER_ANTHROPIC_API_KEY"
export ANTHROPIC_API_BASE=https://api.anthropic.com
export NO_PROXY="${NO_PROXY},api.anthropic.com"
