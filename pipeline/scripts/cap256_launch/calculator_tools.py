"""Mechanical literal references and bounded exact integer calculator calls.

No semantic operation, role, or unit is inferred from question text. These
functions never read labels, execute generated code, or call a model.
"""
import re


INTEGER_LITERAL = re.compile(r"(?<![\w.])[+-]?\d+(?!\w|(?:\.\d))")
MAX_LITERALS = 8
MAX_PRIOR_RESULTS = 3
MAX_ABSOLUTE_INTEGER = 1_000_000
MAX_CALLS = 4


class RegistryError(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def _require(condition, code):
    if not condition:
        raise RegistryError(code)


def _integer(value):
    return type(value) is int and abs(value) <= MAX_ABSOLUTE_INTEGER


def _span(span):
    return (isinstance(span, (list, tuple)) and len(span) == 2 and
            all(type(v) is int for v in span) and 0 <= span[0] < span[1])


def build_registry(question, tokenizer):
    """Return literal entries using offsets in the unmodified original string.

    Raises RegistryError with a stable code if registry construction is invalid.
    Decimal fragments and digits embedded in words are not integer literals.
    Sentence punctuation after an integer is allowed.
    """
    _require(isinstance(question, str), "INVALID_QUESTION")
    matches = []
    for match in INTEGER_LITERAL.finditer(question):
        _require(len(matches) < MAX_LITERALS, "TOO_MANY_LITERALS")
        text = match.group()
        significant = text.lstrip("+-").lstrip("0") or "0"
        _require(len(significant) <= 7, "LITERAL_OUT_OF_RANGE")
        value = int(significant) * (-1 if text.startswith("-") else 1)
        _require(_integer(value), "LITERAL_OUT_OF_RANGE")
        matches.append((match, value))
    try:
        encoding = tokenizer(question, add_special_tokens=False, return_offsets_mapping=True)
        ids, offsets = encoding["input_ids"], encoding["offset_mapping"]
    except (KeyError, TypeError, ValueError, NotImplementedError, AttributeError) as error:
        raise RegistryError("TOKENIZER_OFFSETS_UNAVAILABLE") from error
    _require(isinstance(ids, (list, tuple)) and isinstance(offsets, (list, tuple)) and
             len(ids) == len(offsets) and all(type(i) is int and i >= 0 for i in ids),
             "INVALID_TOKENIZER_ENCODING")
    previous_start, previous_end = -1, -1
    covered = bytearray(len(question))
    for offset in offsets:
        _require(_span(offset) and offset[1] <= len(question), "INVALID_SOURCE_OFFSET")
        start, end = offset
        _require(start >= previous_start and end >= previous_end, "NONPREFIX_SOURCE_OFFSETS")
        previous_start, previous_end = start, end
        covered[start:end] = b"\x01" * (end - start)
    _require(all(covered[i] or character.isspace() for i, character in enumerate(question)),
             "INCOMPLETE_SOURCE_OFFSETS")
    result = []
    for index, (match, value) in enumerate(matches):
        start, end = match.span()
        overlapping = [i for i, (left, right) in enumerate(offsets) if left < end and right > start]
        _require(overlapping, "LITERAL_TOKEN_OVERLAP_MISSING")
        _require(all(covered[i] for i in range(start, end)), "LITERAL_SOURCE_COVERAGE_MISSING")
        result.append({"id": "literal:%d" % index, "index": index, "value": value,
                       "char_span": [start, end], "token_indices": overlapping,
                       "source": "literal", "status": "OK"})
    return result


def _validate_registry(registry, call_index):
    _require(isinstance(registry, (list, tuple)), "INVALID_REGISTRY")
    _require(len(registry) <= MAX_LITERALS + MAX_PRIOR_RESULTS, "TOO_MANY_CANDIDATES")
    literals, results, by_id = 0, 0, {}
    last_literal_end, last_result_call = -1, 0
    literal_spans = set()
    result_phase = False
    for index, entry in enumerate(registry):
        _require(isinstance(entry, dict) and entry.get("status") == "OK", "REFERENCE_NOT_OK")
        _require(entry.get("index") == index and type(entry.get("index")) is int, "INVALID_REFERENCE_INDEX")
        row_id = entry.get("id")
        _require(isinstance(row_id, str) and row_id and row_id not in by_id, "INVALID_REFERENCE_ID")
        _require(_integer(entry.get("value")), "REFERENCE_VALUE_OUT_OF_RANGE")
        if entry.get("source") == "literal":
            _require(not result_phase, "NONPREFIX_LITERAL_REGISTRY")
            span, token_indices = entry.get("char_span"), entry.get("token_indices")
            _require(_span(span) and span[0] >= last_literal_end, "INVALID_LITERAL_SOURCE_SPAN")
            _require(isinstance(token_indices, (list, tuple)) and token_indices and
                     all(type(i) is int and i >= 0 for i in token_indices) and
                     list(token_indices) == sorted(set(token_indices)), "INVALID_LITERAL_TOKEN_INDICES")
            last_literal_end = span[1]
            literal_spans.add(tuple(span))
            literals += 1
            _require(literals <= MAX_LITERALS, "TOO_MANY_LITERALS")
        elif entry.get("source") == "result":
            result_phase = True
            origin_call = entry.get("source_call_index")
            _require(type(origin_call) is int and 1 <= origin_call < call_index, "FUTURE_RESULT_REFERENCE")
            _require(origin_call > last_result_call, "NONPREFIX_RESULT_REGISTRY")
            _require(row_id == "result:%d" % origin_call, "INVALID_RESULT_ID")
            spans = entry.get("origin_char_spans")
            _require(isinstance(spans, (list, tuple)) and spans and all(_span(s) for s in spans),
                     "INVALID_RESULT_ORIGINS")
            _require(all(tuple(s) in literal_spans for s in spans), "UNAVAILABLE_RESULT_ORIGINS")
            last_result_call = origin_call
            results += 1
            _require(results <= MAX_PRIOR_RESULTS, "TOO_MANY_PRIOR_RESULTS")
        else:
            raise RegistryError("INVALID_REFERENCE_SOURCE")
        by_id[row_id] = entry
    return by_id


def execute_integer_call(action, ordered_references, candidate_registry, call_index=None):
    """Return an OK/NONE/ERROR trace; malformed calls return stable error codes.

    References are zero-based registry indices or exact registry IDs. Calls are
    one-based (1..4). Runtime must qualify the numeric output token before it
    appends result to the next candidate registry; that qualification is separate.
    """
    trace = {"status": "ERROR", "action": action if isinstance(action, str) else None,
             "ordered_references": [r if isinstance(r, (str, int)) else None for r in ordered_references]
             if isinstance(ordered_references, (list, tuple)) else [],
             "call_index": call_index if type(call_index) is int else None, "result": None}
    try:
        _require(isinstance(action, str) and action in ("NONE", "ADD", "SUB", "SUBTRACT"), "INVALID_ACTION")
        canonical_action = "SUB" if action == "SUBTRACT" else action
        trace["action"] = canonical_action
        _require(isinstance(ordered_references, (list, tuple)), "INVALID_REFERENCES")
        if call_index is None:
            _require(isinstance(candidate_registry, (list, tuple)), "INVALID_REGISTRY")
            prior_calls = [e.get("source_call_index", 0) for e in candidate_registry if isinstance(e, dict) and e.get("source") == "result"]
            _require(all(type(c) is int for c in prior_calls), "INVALID_CALL_INDEX")
            call_index = max(prior_calls, default=0) + 1
        _require(type(call_index) is int and 1 <= call_index <= MAX_CALLS, "INVALID_CALL_INDEX")
        trace["call_index"] = call_index
        by_id = _validate_registry(candidate_registry, call_index)
        if canonical_action == "NONE":
            _require(len(ordered_references) == 0, "NONE_REQUIRES_ZERO_REFERENCES")
            trace["status"] = "NONE"
            return trace
        _require(len(ordered_references) == 2, "BINARY_REQUIRES_TWO_REFERENCES")
        selected = []
        for reference in ordered_references:
            if type(reference) is int:
                _require(0 <= reference < len(candidate_registry), "REFERENCE_UNAVAILABLE")
                selected.append(candidate_registry[reference])
            elif isinstance(reference, str):
                _require(reference in by_id, "REFERENCE_UNAVAILABLE")
                selected.append(by_id[reference])
            else:
                raise RegistryError("INVALID_REFERENCE_TYPE")
        _require(selected[0]["id"] != selected[1]["id"], "DUPLICATE_REFERENCE")
        values = [entry["value"] for entry in selected]
        value = values[0] + values[1] if canonical_action == "ADD" else values[0] - values[1]
        trace["operand_values"] = values
        _require(_integer(value), "RESULT_OUT_OF_RANGE")
        origin_spans = []
        for entry in selected:
            spans = [entry["char_span"]] if entry["source"] == "literal" else entry["origin_char_spans"]
            for span in spans:
                if list(span) not in origin_spans:
                    origin_spans.append(list(span))
        trace["resolved_references"] = [entry["id"] for entry in selected]
        trace["result"] = {"id": "result:%d" % call_index, "index": len(candidate_registry),
                           "value": value, "source": "result", "status": "OK",
                           "source_call_index": call_index, "origin_char_spans": origin_spans,
                           "operand_references": trace["resolved_references"]}
        trace["status"] = "OK"
        return trace
    except RegistryError as error:
        trace["error_code"] = error.code
        return trace
    except (TypeError, ValueError, KeyError, IndexError, OverflowError):
        trace["error_code"] = "MALFORMED_CALL"
        return trace
