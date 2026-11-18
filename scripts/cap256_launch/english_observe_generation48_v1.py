"""G3: English-scoped native generation observer, output cap 1..48 tokens incl. EOS.

Source copy of sol_cloud_capability256_v1.observe_generation (lines 276-337).
The ONLY differences are the function name and the cap guard (32 -> 48); the
native call, argument/option checks, raw ID typing, EOS rules and strip parity
are identical (checked line-by-line by test_english_pilot_observer48_v1.py).
decoder.generate itself is unchanged and already permits 1..128.
Stdlib only.
"""
ENGLISH_OUTPUT_CAP = 48


def observe_generation48(decoder, packet, max_tokens=48):
    """Observe the SAME native generate result before the existing EOS strip.

    This supplies no extra generation argument, target, text, or forward call.
    The original instance/class method arrangement is restored even on failure.
    """
    if type(max_tokens) is not int or not 1 <= max_tokens <= ENGLISH_OUTPUT_CAP:
        raise ValueError('strict integer English observed-generation cap1..48')
    lm = decoder.lm
    original = lm.generate
    had_instance_method = 'generate' in vars(lm)
    original_instance_method = vars(lm).get('generate')
    calls = []
    def observed(*args, **kwargs):
        record = {'argument_keys': sorted(kwargs), 'positional_argument_count': len(args),
                  'options': {key: kwargs.get(key) for key in ('max_new_tokens', 'do_sample',
                      'use_cache', 'bos_token_id', 'eos_token_id', 'pad_token_id')}}
        calls.append(record)
        result = original(*args, **kwargs)
        record['raw_ids'] = result.tolist()
        return result
    lm.generate = observed
    error = None
    returned = None
    try:
        returned = decoder.generate(packet,max_tokens=max_tokens)
    except Exception as caught:
        error = {'error_type':type(caught).__name__,'error':str(caught)}
    finally:
        if had_instance_method: lm.generate = original_instance_method
        else: delattr(lm,'generate')
    raw = calls[0].get('raw_ids') if len(calls)==1 else None
    allowed = ['attention_mask','bos_token_id','do_sample','eos_token_id','inputs_embeds',
               'max_new_tokens','pad_token_id','use_cache']
    call_valid = (len(calls)==1 and calls[0]['argument_keys']==allowed
                  and calls[0]['positional_argument_count']==0
                  and calls[0]['options'] == {'max_new_tokens': max_tokens, 'do_sample': False,
                      'use_cache': True, 'bos_token_id': decoder.bos_id,
                      'eos_token_id': decoder.eos_id, 'pad_token_id': decoder.eos_id})
    typed = (type(raw) is list and len(raw)==1 and type(raw[0]) is list
             and all(type(token) is int and token>=0 for token in raw[0]))
    full = raw[0] if typed else None
    eos_positions = [i for i,token in enumerate(full) if token==decoder.eos_id] if typed else []
    if not call_valid or error: reason='invalid_native_generation_call'
    elif not typed: reason='invalid_or_multiple_output_sequences'
    elif len(full)>max_tokens: reason='invalid_generation_extent'
    elif len(eos_positions)>1: reason='invalid_multiple_EOS'
    elif eos_positions and eos_positions[-1]!=len(full)-1: reason='invalid_tokens_after_EOS'
    elif eos_positions: reason='observed_EOS'
    elif len(full)==max_tokens: reason='max_new_tokens_without_EOS'
    else: reason='terminated_without_observed_EOS'
    expected_strip = full[:eos_positions[0]] if eos_positions else full
    stripped_equal = typed and returned==[expected_strip]
    if not stripped_equal and reason=='observed_EOS': reason='invalid_native_stripped_output_parity'
    return {'MODEL_raw_generate_ids':raw,'MODEL_generated_ids_with_observed_EOS':full,
            'MODEL_native_decoder_return':returned,'native_generate_call_count':len(calls),
            'native_call_contract_valid':call_valid,'raw_output_single_typed_sequence':typed,
            'native_generation_options':calls[0]['options'] if len(calls)==1 else None,
            'EOS_positions':eos_positions,'observed_EOS':bool(eos_positions),
            'termination_reason':reason,'native_stripped_output_equal':stripped_equal,
            'generation_error':error,'same_generation_call_no_rescore':True}


def observation_valid(observed):
    """One successful, contract-valid native call with a typed single sequence."""
    return (observed.get('native_generate_call_count') == 1
            and observed.get('native_call_contract_valid') is True
            and observed.get('generation_error') is None
            and observed.get('raw_output_single_typed_sequence') is True
            and not str(observed.get('termination_reason', '')).startswith('invalid'))
