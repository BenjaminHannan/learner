"""Select a low-variance empty patch or measure cursor change in video pixels."""
import json,sys
import numpy as np
from PIL import Image

if sys.argv[1]=='spot':
    image=np.asarray(Image.open(sys.argv[2]).convert('RGB'),dtype=float)
    h,w,_=image.shape
    choices=[]
    for y in range(40,h-60,40):
        for x in range(40,w-60,40):
            patch=image[y-12:y+24,x-12:x+24]
            choices.append((float(patch.var(axis=(0,1)).mean()),x,y))
    v,x,y=min(choices)
    if v>20: raise ValueError('no empty stable patch')
    print(json.dumps(dict(x=x,y=y,variance=v)))
else:
    before=np.asarray(Image.open(sys.argv[2]).convert('RGB'),dtype=float)
    after=np.asarray(Image.open(sys.argv[3]).convert('RGB'),dtype=float)
    x,y=map(float,sys.argv[4:6]); ix,iy=round(x),round(y)
    delta=np.abs(after-before).mean(axis=2)
    # The selected patch was empty; a small, localized new shape is the cursor.
    y0,y1=max(0,iy-16),min(delta.shape[0],iy+32)
    x0,x1=max(0,ix-16),min(delta.shape[1],ix+32)
    yy,xx=np.where(delta[y0:y1,x0:x1]>35)
    if not 3<=len(xx)<=300: raise ValueError('cursor change not independently identifiable')
    px,py=float(xx.min()+x0),float(yy.min()+y0)
    error=float(np.hypot(px-x,py-y))
    print(json.dumps(dict(observed=dict(x=px,y=py),expected=dict(x=x,y=y),errorPx=error,changedPixels=len(xx),passed=error<=10)))
