import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from PIL import Image, ImageDraw

SCRIPT=Path(__file__).resolve().parents[1]/'src/night-learn/coordinate-image.py'

class CoordinateImageTests(unittest.TestCase):
    def test_video_cursor_measurement_and_ten_pixel_limit(self):
        with tempfile.TemporaryDirectory() as folder:
            folder=Path(folder)
            before=folder/'before.png'; Image.new('RGB',(200,120),'white').save(before)
            for offset,passed in [(2,True),(14,False)]:
                after=folder/f'after-{offset}.png'; image=Image.new('RGB',(200,120),'white')
                ImageDraw.Draw(image).polygon([(50+offset,40),(50+offset,49),(56+offset,46)],fill='black'); image.save(after)
                result=subprocess.run([sys.executable,str(SCRIPT),'measure',str(before),str(after),'50','40'],capture_output=True,text=True)
                self.assertEqual(result.returncode,0,result.stderr)
                measured=json.loads(result.stdout);self.assertEqual(measured['passed'],passed);self.assertEqual(measured['errorPx'],offset)
            unchanged=subprocess.run([sys.executable,str(SCRIPT),'measure',str(before),str(before),'50','40'],capture_output=True,text=True)
            self.assertNotEqual(unchanged.returncode,0)

if __name__=='__main__': unittest.main()
