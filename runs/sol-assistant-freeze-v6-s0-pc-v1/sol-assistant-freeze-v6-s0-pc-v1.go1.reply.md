Traceback (most recent call last):
  File "C:\Users\benja\sol-translator-human-v6\scripts\sol_assistant_freeze.py", line 44, in <module>
    p=argparse.ArgumentParser();p.add_argument('--run',required=True);p.add_argument('--seed',type=int,choices=(0,1),required=True);p.add_argument('--stdout',required=True);p.add_argument('--model',required=True);p.add_argument('--out',required=True);a=p.parse_args();freeze(a.run,a.seed,a.stdout,a.model,a.out)
  File "C:\Users\benja\sol-translator-human-v6\scripts\sol_assistant_freeze.py", line 22, in freeze
    for line in log.read_text().splitlines():
  File "C:\Users\benja\AppData\Local\Programs\Python\Python310\lib\pathlib.py", line 1135, in read_text
    return f.read()
  File "C:\Users\benja\AppData\Local\Programs\Python\Python310\lib\encodings\cp1252.py", line 23, in decode
    return codecs.charmap_decode(input,self.errors,decoding_table)[0]
UnicodeDecodeError: 'charmap' codec can't decode byte 0x8d in position 585: character maps to <undefined>
rc=1
