import os,json,urllib.request as R
Q=(-11,-10,-9,-1,1,9,10,11)
D={'P':(-10,-20,-11,-9),'N':(-21,-19,-12,-8,8,12,19,21),'B':(-11,-9,9,11),'R':(-10,1,10,-1),'Q':Q,'K':Q}
S='BBBBPUKPACFF@DCE>BAD>AAA=B??BBBBBBBB[[YUOPNLGEDCDCBACCABDCCCBBBB*5=;8<LG;KGKADEJ@CDD?ADC>:@B3?:=:=@>>A>B??CC@BEE?BDE<?AA?A?A>;?@>C6=DFEDAGFGACEGADDFBDDDCDDB=B@?@?@AAAC@BABBBCDCABDE@BCC@@@B?A?AGHGIFGJKAEFG?@CF=>@B<>@@<@?A?@BDDCEDDDDDCCCCCBDBAAAAABACABABABBB>BFD?<AB@@CC>>@@A>AA@B@B=ADBB?ACAEEF@EGH?CCIBEEH?FEI@>DC?@AC=>?<9ED@FB?AAEB@@?@>;B><@@?;BCA9@GD:7=??@DDDCDEDAEFF?BDE>@CD:=?@9<>@'
V=(82,94,0,10,337,281,1,32,365,297,1,33,477,512,2,50,1025,936,4,95,20000,20000,0,900)
P,PW,MV={},{},{}
for n,k in enumerate('PNBRQK'):m0,e0,w0,v0=V[n*4:n*4+4];PW[k]=w0;MV[k]=v0;a,b=S[n*64:n*64+32],S[n*64+32:n*64+64];P[k]=(0j,)*20+tuple(0j if c%9<1 else(ord(a[r*4+min(c-1,8-c)])-66)*7+m0+((ord(b[r*4+min(c-1,8-c)])-66)*7+e0)*1j for r in range(8)for c in range(10))+(0j,)*20
I='         \n'*2+' rnbqkbnr\n pppppppp\n'+' ........\n'*4+' PPPPPPPP\n RNBQKBNR\n'+'         \n'*2
ps=lambda s:(10-int(s[1]))*10+ord(s[0])-96
ms=lambda m,f:''.join(chr(x%10+96)+str(10-x//10)for x in(119-m[0]if f else m[0],119-m[1]if f else m[1]))+m[2].lower()
def chk(b):
 k=b.find('K')
 if k<0 or b[k-11]=='p'or b[k-9]=='p'or'n'in(b[k-21],b[k-19],b[k-12],b[k-8],b[k+8],b[k+12],b[k+19],b[k+21]):return 1
 for d in(-11,-9,9,11):
  j=k+d;q=b[j]
  if q=='k':return 1
  while q=='.':j+=d;q=b[j]
  if q=='b'or q=='q':return 1
 for d in(-10,1,10,-1):
  j=k+d;q=b[j]
  if q=='k':return 1
  while q=='.':j+=d;q=b[j]
  if q=='r'or q=='q':return 1
 return 0
def gen(o):
 b,_,_,w,_,e,k=o
 for i,p in enumerate(b):
  if'A'<=p<='Z':
   for d in D[p]:
    j=i+d
    while 1:
     q=b[j]
     if q<'+'or'A'<=q<='Z':break
     if p=='P':
      if d in(-10,-20)and q!='.'or d==-20 and(i<81 or b[i-10]!='.')or d in(-11,-9)and q=='.'and j not in(e,k,k-1,k+1):break
      if 21<=j<=28:
       for r in'QRBN':yield(i,j,r)
       break
     yield(i,j,'')
     if p in'PNK'or q>'`':break
     if i==91 and b[j+1]=='K'and w&1:yield(j+1,j-1,'')
     if i==98 and b[j-1]=='K'and w&2:yield(j-1,j+1,'')
     j+=d
def dv(b,m,e,k):
 i,j,r=m;p,q=b[i],b[j];v=P[r or p][j]-P[p][i]
 if q>'`':v+=P[q.upper()][119-j]
 if abs(j-k)<2:v+=2e4+2e4j
 if p=='K'and abs(i-j)==2:v+=P['R'][(i+j)//2]-P['R'][91 if j<i else 98]
 elif p=='P'and j==e:v+=P['P'][109-j]
 return v
def mv(o,m):
 b,sc,ph,w,c,e,k=o;i,j,r=m;p,q=b[i],b[j];u=v=0;L=list(b);L[j]=r or p;L[i]='.';w&=(i!=91)|2*(i!=98);c&=(j!=28)|2*(j!=21)
 if p=='K':
  w=0
  if abs(j-i)==2:v=(i+j)//2;L[91 if j<i else 98]='.';L[v]='R'
 elif p=='P':
  if j-i==-20:u=i-10
  elif j==e:L[j+10]='.'
 return(''.join(L)[::-1].swapcase(),-(sc+dv(b,m,e,k)),ph-(PW[q.upper()]if q>'`'else 0)+(PW[r]if r else 0),c,w,119-u if u else 0,119-v if v else 0)
def ev(o):
 b,sc,ph=o[0],o[1],o[2];p=ph if ph<24 else 24;bp=(b.count('B')>1)-(b.count('b')>1)
 return int((sc.real+36*bp)*p+(sc.imag+46*bp)*(24-p))//24+12
TT,H,KL,RP={},{},{},{};N=ST=0;LIM=130000
def ab(o,a,b,d,y,nl=1):
 global N,ST
 if ST or o[1].real<-15e3:return 0 if ST else y-30000
 bd=o[0]
 if y and RP.get(bd):return 0
 N+=1
 if N>=LIM:ST=1;return 0
 pv=b-a>1;s0=ev(o);kp=o[6];ck=0
 if d>=0:
  ck=chk(bd)
  if ck and y<20:d+=1
 if d<1:
  if s0>=b:return b
  if s0>a:a=s0
  cs=[]
  for m in gen(o):
   q=bd[m[1]]
   if q>'`'or m[2]or abs(m[1]-kp)<2:
    if q=='k'or abs(m[1]-kp)<2:return 30000-y
    g=(MV[q.upper()]*10 if q>'`'else 0)+(900 if m[2]=='Q'else 300 if m[2]else 0)
    if s0+g+150>=a:cs.append((g-MV[bd[m[0]]],m))
  cs.sort(key=lambda x:x[0],reverse=1)
  for _,m in cs:
   sc=-ab(mv(o,m),-b,-a,-1,y+1,0)
   if ST or sc>=b:return a if ST else b
   if sc>a:a=sc
  return a
 tk=(bd,o[3],o[4],o[5]);te=TT.get(tk);tm=te[3]if te else 0
 if te and te[0]>=d and y and not pv:
  tv=te[2]-y*((te[2]>25000)-(te[2]<-25000))
  if te[1]<1 or te[1]==1 and tv>=b or te[1]>1 and tv<=a:return tv
 if not pv and not ck and y and d<3 and b<25000 and s0-150*d>=b:return s0
 if nl and not pv and not ck and d>2 and y and s0>=b and o[2]and-ab((bd[::-1].swapcase(),-o[1],o[2],o[4],o[3],0,0),-b,-b+1,d-3-(d>5),y+1,0)>=b and not ST:return b
 ks=KL.get(y,(0,0));raw=[]
 for m in gen(o):
  q=bd[m[1]]
  if q=='k'or abs(m[1]-kp)<2:return 30000-y
  if m==tm:pr=1e6
  elif q>'`'or m[2]:pr=5e5+(MV[q.upper()]*16 if q>'`'else 0)+(900 if m[2]=='Q'else 0)-MV[bd[m[0]]]
  elif m==ks[0]:pr=4e5
  elif m==ks[1]:pr=39e4
  else:pr=H.get((bd[m[0]],m[1]),0)+(P[bd[m[0]]][m[1]]-P[bd[m[0]]][m[0]]).real
  raw.append((pr,m))
 raw.sort(key=lambda x:x[0],reverse=1)
 oa,best,bm,lg=a,-99999,0,0;RP[bd]=RP.get(bd,0)+1
 for x,(_,m)in enumerate(sorted(raw,reverse=1)):
  np=mv(o,m)
  if np[1].real<-15e3:best=30000-y;break
  cp=bd[m[1]]>'`'or m[2]
  if not pv and not ck and d==1 and lg and not cp and a>-25000 and s0+185<=a:continue
  rd=(2 if d>5 and x>8 else(1 if d>2 and x>3 else 0))if lg and not cp and not ck else 0
  sc=-ab(np,-b,-a,d-1,y+1,1)if not lg else-ab(np,-a-1,-a,d-1-rd,y+1,1)
  if lg and not ST and sc>a and rd:sc=-ab(np,-a-1,-a,d-1,y+1,1)
  if lg and not ST and a<sc<b:sc=-ab(np,-b,-a,d-1,y+1,1)
  if ST:break
  lg+=sc>-28000
  if sc>best:best,bm=sc,m
  if sc>a:
   a=sc
   if a>=b:
    if not cp:
     if m!=ks[0]:KL[y]=(m,ks[0])
     hk=(bd[m[0]],m[1]);H[hk]=min(200000,H.get(hk,0)+d*d)
    break
 RP[bd]-=1
 if ST:return 0
 if best<-25000 and not ck:best=0
 len(TT)>200000 and TT.clear()
 TT[tk]=(d,(best>=b)+2*(best<=oa),best+y*((best>25000)-(best<-25000)),bm)
 return best
def leg_m(o,f,leg=None):
 ls=set(leg)if leg is not None else 0
 return[m for m in gen(o)if(ms(m,f)in ls if ls else all(np[0][z[1]]!='k'and abs(z[1]-np[6])>1 for np in(mv(o,m),)for z in gen(np)))]
def think(o,f,leg=None,lim=130000):
 global N,ST,LIM
 cs=leg_m(o,f,leg)
 if len(cs)<2:return cs[0]if cs else 0
 N=ST=0;LIM=lim;KL.clear();len(H)>4096 and H.clear();bm=cs[0]
 for d in range(1,22):
  od=sorted(cs,key=lambda m:(m==bm,dv(o[0],m,o[5],o[6]).real),reverse=1)
  best,cur,a=-99999,bm,-35000
  for x,m in enumerate(od):
   np=mv(o,m);sc=-ab(np,-35000,-a,d-1,1,1)if not x else-ab(np,-a-1,-a,d-1,1,1)
   if x and not ST and a<sc<35000:sc=-ab(np,-35000,-a,d-1,1,1)
   if ST:break
   if sc>best:best,cur=sc,m;a=max(a,sc)
  if ST:
   if best>28000:bm=cur
   break
  bm=cur
  if abs(best)>28000:break
 return bm
def main():
 u=os.environ.get('MAKEFUN_ENV_URL')
 if not u:return
 post=lambda p,o:json.loads(R.urlopen(R.Request(u+p,json.dumps(o).encode(),{'Content-Type':'application/json'}),timeout=9).read())
 while 1:
  g=post('/game',{})
  if g.get('status')=='done':break
  o=(I,0j,24,3,3,0,0);f=p=0;RP.clear();TT.clear();H.clear()
  while g.get('status')=='your_move':
   for s in g.get('moves',[])[p:]:
    i,j=ps(s[:2]),ps(s[2:4])
    if f:i,j=119-i,119-j
    RP[o[0]]=RP.get(o[0],0)+1;o=mv(o,(i,j,s[4:].upper()));f^=1;p+=1
   m=think(o,f,g.get('legal_moves'),130000);g=post('/move',{'game':g['game'],'move':ms(m,f)})
if __name__=='__main__':main()