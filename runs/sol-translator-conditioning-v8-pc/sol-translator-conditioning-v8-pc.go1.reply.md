Traceback (most recent call last):
  File "<stdin>", line 15, in <module>
  File "C:\Users\benja\sol-translator-conditioning-v8\scripts\sol_translator_conditioning_audit_v8.py", line 35, in coverage
    rows,_=human_rows(a.corpus);rows=[x for x in rows if x['split']=='train']
  File "C:\Users\benja\sol-translator-conditioning-v8\scripts\sol_translator_grounding_v6.py", line 20, in human_rows
    corpus=Path(corpus);reg=json.loads((corpus/'registry.json').read_text());rows=json.loads((corpus/'pairs.json').read_text())
  File "C:\Users\benja\AppData\Local\Programs\Python\Python310\lib\pathlib.py", line 1135, in read_text
    return f.read()
  File "C:\Users\benja\AppData\Local\Programs\Python\Python310\lib\encodings\cp1252.py", line 23, in decode
    return codecs.charmap_decode(input,self.errors,decoding_table)[0]
UnicodeDecodeError: 'charmap' codec can't decode byte 0x90 in position 247472: character maps to <undefined>
rc=1
