"""Conservative typed quantities for strict-4. No eval, model, or NLP backend."""
from decimal import Decimal, InvalidOperation
import re

_NUMBER = r'[+-]?(?:\d+(?:\.\d+)?|\.\d+)'
_SMALL = dict(zip('zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen'.split(), range(20)))
_TENS = dict(zip('twenty thirty forty fifty sixty seventy eighty ninety'.split(), range(20, 100, 10)))
_UNITS = {'minute': 'minute', 'minutes': 'minute', 'min': 'minute', 'hour': 'hour', 'hours': 'hour', 'hr': 'hour',
          'c': 'celsius', '°c': 'celsius', 'celsius': 'celsius', 'degree celsius': 'celsius', 'degrees celsius': 'celsius',
          'f': 'fahrenheit', '°f': 'fahrenheit', 'fahrenheit': 'fahrenheit', 'degree fahrenheit': 'fahrenheit', 'degrees fahrenheit': 'fahrenheit',
          'sheet': 'sheet', 'sheets': 'sheet', 'bead': 'bead', 'beads': 'bead', 'day': 'day', 'days': 'day',
          'month': 'month', 'months': 'month', 'side': 'side', 'sides': 'side', 'leg': 'leg', 'legs': 'leg',
          'square centimetre': 'cm2', 'square centimetres': 'cm2', 'square centimeter': 'cm2', 'square centimeters': 'cm2', 'cm²': 'cm2', 'cm2': 'cm2'}


def number(text):
    text = text.strip().lower().replace('−', '-')
    if re.fullmatch(_NUMBER, text):
        try: return Decimal(text)
        except InvalidOperation: return None
    sign = 1
    if text.startswith('minus '): sign, text = -1, text[6:]
    elif text.startswith('-'): sign, text = -1, text[1:]
    elif text.startswith('+'): text = text[1:]
    if text.startswith(('-', '+', 'minus ')): return None
    words = text.replace('-', ' ').split()
    if not words: return None
    if len(words) == 1:
        if words[0] == 'hundred': return Decimal(100 * sign)
        value = _SMALL.get(words[0], _TENS.get(words[0]))
        return Decimal(value * sign) if value is not None else None
    if len(words) == 2 and words[0] in _TENS and words[1] in _SMALL and 0 < _SMALL[words[1]] < 10:
        return Decimal(sign * (_TENS[words[0]] + _SMALL[words[1]]))
    if len(words) == 2 and words[0] in _SMALL and 0 < _SMALL[words[0]] < 10 and words[1] == 'hundred':
        return Decimal(sign * _SMALL[words[0]] * 100)
    return None


def unwrap(text, *, parentheses=False):
    text = text.strip()
    pairs = (('**', '**'), ('__', '__'), ('`', '`')) + ((('(', ')'),) if parentheses else ())
    # Numeric text can nest ordinary presentation wrappers. Every iteration
    # shrinks the text; classification and parsing must see the same contents.
    for _ in range(len(text) if parentheses else 3):
        pair = next(((left, right) for left, right in pairs if text.startswith(left)), None)
        if pair is None: return text
        left, right = pair
        if len(text) < len(left) + len(right) or not text.endswith(right): return None
        text = text[len(left):-len(right)].strip()
    return text


def clean(text):
    value = unwrap(text, parentheses=True)
    return (value if value is not None else text).replace('−', '-').replace('×', '*').replace('÷', '/').strip()


def unit_identity(text):
    text = text.strip()
    if not text: return None
    if text.lower() in _UNITS: return _UNITS[text.lower()]
    # Fraction/decimal grammar is not an arbitrary unit. Match whole words:
    # the legitimate unit 'points' must not match the forbidden token 'point'.
    grammar = set(_SMALL) | set(_TENS) | {'hundred', 'thousand', 'point', 'decimal', 'half', 'halves', 'quarter', 'quarters', 'over', 'and', 'minus', 'negative', 'positive', 'to'}
    if set(re.findall(r'[a-z]+', text.lower())) & grammar: return None
    # Unknown declared units are exact literals; GB and Gb must not collapse.
    if re.fullmatch(r'[A-Za-zµ°²³]+(?: +[A-Za-zµ°²³]+)*', text): return 'literal:' + text
    return None


def split_quantity(text):
    text = clean(text).rstrip('.!').strip()
    literal = re.fullmatch('(' + _NUMBER + r')\s*(.*)', text)
    if literal:
        value, suffix = number(literal[1]), literal[2]
        if not suffix: return value, None
        unit = unit_identity(suffix)
        return (value, unit) if unit is not None else None
    parts = text.split()
    for stop in range(min(len(parts), 4), 0, -1):
        value = number(' '.join(parts[:stop]))
        if value is None: continue
        suffix = ' '.join(parts[stop:])
        if not suffix: return value, None
        unit = unit_identity(suffix)
        if unit is not None: return value, unit
    return None


def expected_unit(question):
    q = question.lower()
    if 'celsius' in q or re.search(r'°c\b', q): return 'celsius'
    if 'fahrenheit' in q or re.search(r'°f\b', q): return 'fahrenheit'
    if 'square centimet' in q: return 'cm2'
    for word in ('minute', 'hour', 'sheet', 'bead', 'day', 'month', 'side', 'leg'):
        if re.search(r'\b' + word + r's?\b', q): return word
    return None


def quantity(text, wanted_unit, allow_bare=True):
    parsed = split_quantity(text)
    if parsed is None: return None
    value, unit = parsed
    return value if (unit is None and allow_bare) or (unit is not None and unit == wanted_unit) else None


def numeric_answer(raw_line, question, accepted, head_contains):
    cleaned_gold = [clean(answer) for answer in accepted]
    parsed_gold = [split_quantity(answer) for answer in cleaned_gold]
    values = {item[0] for item in parsed_gold if item is not None}
    if not values:
        # Unsupported numeric gold is not a name; never erase its sign/units
        # through the generic whole-phrase fallback.
        # Bounded fraction vocabulary classifies unsupported gold; it does not
        # calculate fractions. Literal names such as 'Quarter' fail closed too.
        fractions = {'half', 'halves', 'quarter', 'quarters'} | {word + plural for word in ('third', 'fourth', 'fifth', 'sixth', 'seventh', 'eighth', 'ninth', 'tenth') for plural in ('', 's')}
        fraction_prefix = '|'.join(sorted(fractions, key=len, reverse=True))
        prefixes = '|'.join(sorted(set(_SMALL) | set(_TENS) | fractions | {'hundred', 'thousand', 'minus', 'negative', 'positive'}, key=len, reverse=True))
        def numeric_looking(answer):
            # Classification only: presentation punctuation may hide the first
            # value from the parser, but must never route it to phrase matching.
            # No stripped text is parsed or used to authorize a numeric hit.
            prefix = re.sub(r'^[\W_]+', '', answer.strip())
            return bool(prefix and (prefix[0].isnumeric() or re.match(r'(?:(?:' + prefixes + r')\b|(?:a|an)\b[\W_]+(?:' + fraction_prefix + r')\b)', prefix, re.I)))
        return False if any(numeric_looking(answer) for answer in cleaned_gold) else None
    allow_bare = any(item is not None and item[1] is None for item in parsed_gold)
    units = {item[1] for item in parsed_gold if item is not None and item[1] is not None}
    unit = expected_unit(question) or (next(iter(units)) if len(units) == 1 else None)
    if len(units) > 1 or (units and unit not in units): return False
    line = clean(raw_line)
    line = re.sub(r'^(?:the answer is|answer\s*:|it is|there are|there remain)\s*', '', line, flags=re.I)
    value = quantity(line, unit, allow_bare)
    if value is not None:
        return value in values and head_contains(line)
    # Celsius/Fahrenheit pair: both quantities and conversion must agree.
    pair = re.fullmatch('(' + _NUMBER + r')\s*°?([cCfF])\s*\(\s*(' + _NUMBER + r')\s*°?([cCfF])\s*\)[.!]?', line)
    if pair:
        a, b = number(pair[1]), number(pair[3]); first, second = pair[2].lower(), pair[4].lower()
        valid = first != second and (a * 9 / 5 + 32 == b if first == 'c' else (a - 32) * 5 / 9 == b)
        return bool(valid and (unit is None or _UNITS[first] == unit) and a in values and head_contains(pair[1]))
    # A complete equation is validated independently, not by answer-token search.
    eq = re.fullmatch('(' + _NUMBER + r')\s*([+*/-])\s*(' + _NUMBER + r')\s*=\s*(.+)', line)
    percent = re.fullmatch('(' + _NUMBER + r')\s*%\s+of\s+(' + _NUMBER + r')\s+(?:is|=)\s*(.+)', line, re.I)
    if eq or percent:
        match = eq or percent
        a, b = number(match[1]), number(match[3] if eq else match[2])
        operand_values = {abs(number(x)) for x in re.findall(_NUMBER, question)}
        if abs(a) not in operand_values or abs(b) not in operand_values: return False
        result_text = match[4] if eq else match[3]
        result = quantity(result_text, unit, allow_bare)
        try:
            computed = a * b / 100 if percent else {'+': lambda: a + b, '-': lambda: a - b, '*': lambda: a * b, '/': lambda: a / b}[match[2]]()
        except (ArithmeticError, InvalidOperation): return False
        return result in values and computed == result and head_contains(result_text)
    # Narrow validated clock-duration frame, still within the first 12 words.
    clock = re.fullmatch(r'The time from (\d{2}:\d{2}) to (\d{2}:\d{2}) is (.+)', line, re.I)
    if clock and unit == 'minute' and all(value in question for value in clock.group(1, 2)):
        def minutes(value):
            hour, minute = map(int, value.split(':'))
            return hour * 60 + minute if hour < 24 and minute < 60 else None
        begin, end = minutes(clock[1]), minutes(clock[2]); result = quantity(clock[3], unit, allow_bare)
        return begin is not None and end is not None and end >= begin and result in values and end - begin == result and head_contains(clock[3])
    return False
