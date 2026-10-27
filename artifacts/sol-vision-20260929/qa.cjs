// Same geometry checks as kit/eli5, plus all requested sizes/themes.
const {chromium}=require('playwright');
const fs=require('fs');
const path=require('path');
const {pathToFileURL}=require('url');
(async()=>{
 const dir=__dirname;
 const executablePath='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
 const browser=await chromium.launch({executablePath,headless:true});
 const results=[];
 for(const width of [400,720,1200]) for(const theme of ['light','dark']){
  const page=await browser.newPage({viewport:{width,height:900},colorScheme:theme});
  const external=[];page.on('request',r=>{if(/^https?:/.test(r.url()))external.push(r.url())});
  await page.goto(pathToFileURL(path.join(dir,'vision.html')).href);
  await page.emulateMedia({reducedMotion:'reduce'});
  await page.waitForTimeout(150);
  const geometry=await page.evaluate(()=>{
   const problems=[];
   document.querySelectorAll('svg').forEach((svg,index)=>{
    const v=svg.viewBox.baseVal, labels=[...svg.querySelectorAll('text')];
    labels.forEach(t=>{const b=t.getBBox();if(b.x< -1||b.x+b.width>v.width+1||b.y< -1||b.y+b.height>v.height+1)problems.push(`OUT ${index}: ${t.textContent}`)});
    for(let a=0;a<labels.length;a++)for(let b=a+1;b<labels.length;b++){
     const A=labels[a].getBBox(),B=labels[b].getBBox();
     if(A.x<B.x+B.width-1&&B.x<A.x+A.width-1&&A.y<B.y+B.height-1&&B.y<A.y+A.height-1)problems.push(`OVL ${index}: ${labels[a].textContent} | ${labels[b].textContent}`);
    }
   });
   return {problems,scrollWidth:document.documentElement.scrollWidth,cardCount:document.querySelectorAll('.card').length,svgCount:document.querySelectorAll('svg').length};
  });
  const screenshot=`vision-${width}-${theme}.png`;
  await page.screenshot({path:path.join(dir,screenshot),fullPage:true});
  if(width===1200&&theme==='light')await page.screenshot({path:path.join(dir,'vision-desktop-preview.png')});
  if(width===400&&theme==='light')await page.screenshot({path:path.join(dir,'vision-mobile-preview.png')});
  results.push({width,theme,...geometry,externalRequests:external,screenshot});
  await page.close();
 }
 await browser.close();
 const passed=results.every(x=>x.problems.length===0&&x.scrollWidth===x.width&&x.externalRequests.length===0&&x.cardCount===8&&x.svgCount===8);
 fs.writeFileSync(path.join(dir,'qa-results.json'),JSON.stringify({passed,browser:executablePath,method:'kit-equivalent SVG bounding-box/overlap checks + scroll width + zero remote requests',results},null,2)+'\n');
 console.log(JSON.stringify({passed,results}));process.exitCode=passed?0:1;
})().catch(e=>{console.error(e.message);process.exitCode=1});
