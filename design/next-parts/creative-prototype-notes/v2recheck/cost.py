# Run-time arithmetic. Forward rate from v2-check's own S5 figure (82k forwards in 30-60 min) = 22-44 ms.
lo,hi=30*60/82000,60*60/82000
f=lambda n:(n*lo/60,n*hi/60)
upd=lambda runs,a,b:(runs*512*a/60,runs*512*b/60)
S2=f(4*128*33); S3=f(1024*65); S4=tuple(x+y for x,y in zip(upd(9,1.0,1.3),f(3*128*33))); S5=f(10*256*33)
S6=tuple(x+y for x,y in zip(upd(7,0.41,1.3),f(7*256*33)))
extra5=tuple(x+y+z for x,y,z in zip(upd(6,1.0,1.3),f(2*128*33),f(6*256*33)))
for k,v in dict(S2=S2,S3=S3,S4=S4,S5=S5,S6=S6,extra_if_5_seeds=extra5).items(): print('%-17s %5.0f to %5.0f min'%(k,*v))
tot=[5+S2[0]+S3[0]+S4[0]+S5[0], 10+S2[1]+S3[1]+S4[1]+S5[1]]
print('S1..S5 total %.1f to %.1f h'%(tot[0]/60,tot[1]/60))
