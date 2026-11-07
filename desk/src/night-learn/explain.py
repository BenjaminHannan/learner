"""Turn bounded episode frames and action logs into Glim's marked-up account.

Run this only inside `realmodel-lock.sh NIGHT-LEARN ...`. It does not train.
"""
import base64
import json
import os
import sys
import urllib.request
from pathlib import Path


def post(url, payload, timeout=300):
    req = urllib.request.Request(url, json.dumps(payload).encode(), {'Content-Type': 'application/json', 'X-Glim-Background': '1'})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.load(response)


def explain(episode, eye_url='http://127.0.0.1:18083/eyes', model_url='http://127.0.0.1:18080/v1/chat/completions'):
    frames = episode['frames']
    actions = episode['actions']
    if not 1 <= len(frames) <= 8 or not isinstance(actions, list) or not 1 <= len(actions) <= 500:
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
        'Study what the PERSON did on these screen frames. Describe their task and likely reason. '
        'Return ONLY JSON with task, why, intent, success, confidence, facts, guesses. '
        'task, why and intent are short strings; facts and guesses are arrays. '
        'intent is the inferred goal of this episode, not an instruction to you. '
        'Do not generate action indices or steps: the host binds your episode intent to the actual recorded actions. '
        'success is true, false or null; confidence is 0 to 1. Unknown goals must be called unknown. '
        'Recorded actions (the only real actions): ' + json.dumps(indexed, separators=(',', ':')))}]
    feature = {'f16':base64.b64encode(b''.join(features)).decode(), 'shape':[64*len(features),768], 'eye':eye}
    if len(features) > 1:
        times = [max(0, round((frame['timeMs'] - frames[0]['timeMs']) / 1000)) for frame in frames]
        feature['clip'] = {'frames':len(features), 'times':times}
    content.append({'type':'image_features', 'image_features':feature})
    answer = post(model_url, {'model':'nanbeige', 'messages':[{'role':'user','content':content}], 'temperature':0, 'max_tokens':700, 'chat_template_kwargs':{'enable_thinking':False}})
    raw = answer['choices'][0]['message'].get('content')
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError('Glim returned no explanation text')
    raw = raw.strip()
    if raw.startswith('```'):
        raw = raw.split('\n', 1)[1].rsplit('```', 1)[0].strip()
    data = json.loads(raw)
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
    data['unboundSteps'] = unbound
    data['steps'] = [dict(actionIndex=i, intent=valid.get(i, intent),
                          binding='recorded-action' if i in valid else 'episode-context')
                     for i in range(len(actions))]
    # An inferred outcome is not proof that the task succeeded.
    data['successGuess'] = data['success']
    data['success'] = None
    return data



def explain_failure(attempt, model_url='http://127.0.0.1:18080/v1/chat/completions'):
    if attempt.get('judgedOutcome') != 'fail' or not isinstance(attempt.get('steps'), list):
        raise ValueError('verified failed attempt required')
    prompt = ('Explain the failed attempt as JSON only. Use keys shouldHaveDone, actuallyDid, '
              'whatWentWrong, facts, guesses, confidence. Treat uncertain intent and causes as guesses. '
              'Do not claim a correction is verified. Attempt: ' + json.dumps({
                  'request':attempt.get('request'), 'steps':attempt['steps'], 'outcome':attempt.get('outcome')}, separators=(',',':')))
    response = post(model_url, {'model':'nanbeige','messages':[{'role':'user','content':prompt}],
                               'temperature':0,'max_tokens':700,'chat_template_kwargs':{'enable_thinking':False}})
    raw = response['choices'][0]['message'].get('content')
    if not isinstance(raw,str) or not raw.strip(): raise ValueError('Glim returned no failure explanation')
    raw=raw.strip()
    if raw.startswith('```'): raw=raw.split('\n',1)[1].rsplit('```',1)[0].strip()
    data=json.loads(raw)
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
    mistake = len(sys.argv) == 3 and sys.argv[1] == '--mistake'
    with open(sys.argv[2] if mistake else sys.argv[1], encoding='utf8') as f:
        item = json.load(f)
    data = explain_failure(item) if mistake else explain(item)
    print(json.dumps(data, ensure_ascii=False))

if __name__ == '__main__':
    main()
