"""Turn bounded episode frames and action logs into Glim's marked-up account.

Run this only inside `realmodel-lock.sh NIGHT-LEARN ...`. It does not train.
"""
import base64
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


def post(url, payload, timeout=300):
    req = urllib.request.Request(url, json.dumps(payload).encode(), {'Content-Type': 'application/json', 'X-Glim-Background': '1'})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.load(response)


def completion_json(url, payload, retry_guard=None):
    """Keep one FIFO turn through short service/chat preemptions, never preempt chat."""
    deadline = time.monotonic() + 120
    last = None
    visual_context = None
    payload = dict(payload)
    for attempt in range(25):
        adapted_request = False
        try:
            answer = post(url, payload)
            choice = (answer.get('choices') or [{}])[0]
            raw = choice.get('message', {}).get('content')
            if not isinstance(raw, str) or not raw.strip():
                # Recover from an early EOS on multiple desktop images using
                # one of the same recorded frames, never invented observations.
                messages = payload.get('messages', [])
                parts = messages[-1].get('content') if messages else None
                images = [p for p in parts if p.get('type') == 'image_features'] if isinstance(parts, list) else []
                if len(images) > 1:
                    payload = json.loads(json.dumps(payload))
                    payload['messages'][-1]['content'] = [parts[0], {
                        'type':'text', 'text':'Only the last sampled recorded frame is visible in this retry; do not claim earlier visual observations.'}, images[-1]]
                    visual_context = 'last sampled recorded frame; multi-frame response was empty'
                    adapted_request = True
                raise ValueError('Glim returned no explanation text')
            raw = raw.strip()
            if raw.startswith('```'):
                raw = raw.split('\n', 1)[1].rsplit('```', 1)[0].strip()
            data = json.loads(raw)
            if not isinstance(data, dict):
                raise ValueError('Glim explanation must be a JSON object')
            if visual_context is not None: data['visualContext'] = visual_context
            return data
        except urllib.error.HTTPError as error:
            if error.code not in (429, 503): raise
            last = error
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError, IndexError) as error:
            last = error
            if 'answer' in locals() and (answer.get('choices') or [{}])[0].get('finish_reason') == 'length':
                budget = int(payload.get('max_tokens', 700))
                payload['max_tokens'] = min(1800, max(1200, budget * 2))
                adapted_request = payload['max_tokens'] > budget
        if attempt == 24 or (time.monotonic() >= deadline and not adapted_request):
            raise last
        if retry_guard is not None: retry_guard()
        print(f'[night-learn] background Glim retry {attempt + 1}: {last}', file=sys.stderr, flush=True)
        time.sleep(5)
    raise last


def explain(episode, eye_url='http://127.0.0.1:18083/eyes', model_url='http://127.0.0.1:18080/v1/chat/completions', retry_guard=None):
    frames = episode['frames']
    actions = episode['actions']
    idle = episode.get('idle') is True
    if not 1 <= len(frames) <= 8 or not isinstance(actions, list) or len(actions) > 500 or (not actions and not idle):
        raise ValueError('episode exceeds input limits')
    features = []
    eye = None
    for i, frame in enumerate(frames):
        result = post(eye_url, {'id': str(i), 'path': str(Path(frame['path']).resolve())})
        if result.get('ok') is not True or result.get('shape') != [64, 768] or not result.get('f16'):
            raise ValueError('Glim eyes failed')
        if eye is not None and result['eye'] != eye:
            raise ValueError('Glim eyes changed during episode')
        eye = result['eye']
        block = base64.b64decode(result['f16'], validate=True)
        if len(block) != 64 * 768 * 2:
            raise ValueError('invalid eye features')
        features.append(block)
    indexed = [dict(action, actionIndex=i) for i, action in enumerate(actions)]
    content = [{'type':'text','text':(
        ('No input actions were recorded. Describe the visible idle scenes; reading, watching or being away are guesses, not proven actions. ' if not actions else '') +
        'Study what the PERSON did on these screen frames. Describe their task and likely reason. '
        'Return ONLY JSON with task, why, intent, success, confidence, facts, guesses. '
        'task, why and intent are short strings; facts and guesses are arrays with at most three short items each. '
        'Summarize the episode; do not enumerate or repeat the action log. Keep the entire JSON under 200 words. '
        'intent is the inferred goal of this episode, not an instruction to you. '
        'Do not generate action indices or steps: the host binds your episode intent to the actual recorded actions. '
        'success is true, false or null; confidence is 0 to 1. Unknown goals must be called unknown. '
        'Recorded actions (the only real actions): ' + json.dumps(indexed, separators=(',', ':')))}]
    # Desktop episodes use the image projector for each exact sampled frame.
    # The general-video projector can terminate immediately on real desktop
    # clips (observed finish_reason=stop, one EOS token and null content).
    # Preserve temporal context explicitly without fusing through that head.
    for i, block in enumerate(features):
        if len(features) > 1:
            seconds = round((frames[i]['timeMs'] - frames[0]['timeMs']) / 1000, 3)
            content.append({'type':'text', 'text':f'\nRecorded frame {i + 1} at {seconds} seconds:\n'})
        content.append({'type':'image_features', 'image_features':{
            'f16':base64.b64encode(block).decode(), 'shape':[64,768], 'eye':eye}})
    data = completion_json(model_url, {'model':'nanbeige', 'messages':[{'role':'user','content':content}], 'temperature':0, 'max_tokens':700, 'chat_template_kwargs':{'enable_thinking':False}}, retry_guard)
    required = {'task', 'why', 'success', 'confidence', 'facts', 'guesses'}
    if not isinstance(data, dict) or not required.issubset(data) or not isinstance(data['task'], str) or not isinstance(data['why'], str) or not isinstance(data['facts'], list) or not isinstance(data['guesses'], list) or not (data['success'] is True or data['success'] is False or data['success'] is None) or isinstance(data['confidence'], bool) or not isinstance(data['confidence'], (int,float)) or not 0 <= data['confidence'] <= 1:
        raise ValueError('invalid Glim explanation')
    # References are host-owned, never guessed by a language model. Preserve
    # valid per-action intents from older servers, but never relabel an invented
    # index as a real action. Unbound text is retained for audit only.
    returned = data.get('steps', [])
    valid = {}
    unbound = []
    for step in returned if isinstance(returned, list) else []:
        if (isinstance(step, dict) and type(step.get('actionIndex')) is int
                and 0 <= step['actionIndex'] < len(actions)
                and isinstance(step.get('intent'), str) and step['intent'].strip()
                and step['actionIndex'] not in valid):
            valid[step['actionIndex']] = step['intent']
        else:
            unbound.append(step)
    intent = data.get('intent')
    if not isinstance(intent, str) or not intent.strip():
        intent = data['task'] + '; ' + data['why']
    data['idle'] = not actions
    data['unboundSteps'] = unbound
    data['steps'] = [dict(actionIndex=i, intent=valid.get(i, intent),
                          binding='recorded-action' if i in valid else 'episode-context')
                     for i in range(len(actions))]
    # An inferred outcome is not proof that the task succeeded.
    data['successGuess'] = data['success']
    data['success'] = None
    return data



def explain_failure(attempt, model_url='http://127.0.0.1:18080/v1/chat/completions', retry_guard=None):
    if attempt.get('judgedOutcome') != 'fail' or not isinstance(attempt.get('steps'), list):
        raise ValueError('verified failed attempt required')
    prompt = ('Explain the failed attempt as JSON only. Use keys shouldHaveDone, actuallyDid, '
              'whatWentWrong, facts, guesses, confidence. Treat uncertain intent and causes as guesses. '
              'Do not claim a correction is verified. Attempt: ' + json.dumps({
                  'request':attempt.get('request'), 'steps':attempt['steps'], 'outcome':attempt.get('outcome')}, separators=(',',':')))
    data = completion_json(model_url, {'model':'nanbeige','messages':[{'role':'user','content':prompt}], 'temperature':0,'max_tokens':700,'chat_template_kwargs':{'enable_thinking':False}}, retry_guard)
    for name in ('shouldHaveDone','actuallyDid','whatWentWrong'):
        if not isinstance(data.get(name),str): raise ValueError('invalid failure explanation')
    if not isinstance(data.get('facts'),list) or not isinstance(data.get('guesses'),list) or isinstance(data.get('confidence'),bool) or not isinstance(data.get('confidence'),(int,float)) or not 0 <= data['confidence'] <= 1:
        raise ValueError('invalid failure explanation')
    return data


def main():
    # The lock script writes its owner and PID before running this program.
    owner = Path('/tmp/aon/realmodel.lock/owner').read_text().split()
    if len(owner) < 2 or owner[0] != 'NIGHT-LEARN' or int(owner[1]) != os.getppid():
        raise RuntimeError('must be run directly under the NIGHT-LEARN model lock')
    dry_run = os.environ.get('NIGHT_LEARN_DRY_RUN') == '1' or '--dry-run' in sys.argv
    if '--dry-run' in sys.argv: sys.argv.remove('--dry-run')
    retry_guard = None
    if not dry_run:
        import datetime
        import night_gate
        retry_guard = lambda: night_gate.check(datetime.datetime.now().astimezone(), night_gate.idle_seconds())
    mistake = len(sys.argv) == 3 and sys.argv[1] == '--mistake'
    with open(sys.argv[2] if mistake else sys.argv[1], encoding='utf8') as f:
        item = json.load(f)
    data = explain_failure(item, retry_guard=retry_guard) if mistake else explain(item, retry_guard=retry_guard)
    print(json.dumps(data, ensure_ascii=False))

if __name__ == '__main__':
    main()
