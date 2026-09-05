"use strict";
const $ = (selector) => document.querySelector(selector);
let data, nodesById, selected = "Spider-Man", view = "main", mode = "in", scale = "log", points = [];
const canvas = $("#network-map");
const ctx = canvas.getContext("2d");
const colors = {main:"#93bcac", island:"#d7c779", isolate:"#b9a7d9"};

function press(attribute, value) {
  document.querySelectorAll("[" + attribute + "]").forEach(b => b.setAttribute("aria-pressed", String(b.getAttribute(attribute) === value)));
}
function choose(id) {
  const node = nodesById.get(id);
  if (!node) return;
  selected = id; view = node.component;
  press("data-view", view);
  $("#character").value = id;
  $("#node-name").textContent = node.name;
  $("#node-in").textContent = node.in;
  $("#node-out").textContent = node.out;
  $("#node-degree").textContent = node.degree;
  $("#wiki-link").href = node.url;
  $("#node-summary").textContent = node.component === "isolate"
    ? "No recorded links in either direction within this 303-page roster."
    : node.in + " other pages link to this character; this page links to " + node.out + " others.";
  $("#component-note").textContent = ({
    main:"The main component contains 277 characters. Highlighted lines connect the selected page to its neighbors; faint lines show the rest.",
    island:"This separate nine-character component has no links to the main component. The circular order is alphabetical, not a distance measurement.",
    isolate:"All 17 pages remain visible because we loaded the complete roster before the edges. No recorded edge reaches any of them."
  })[view];
  drawMap();
}
function drawMap() {
  if (!data) return;
  const width = canvas.clientWidth, height = canvas.clientHeight, ratio = window.devicePixelRatio || 1;
  canvas.width = width * ratio; canvas.height = height * ratio;
  ctx.setTransform(ratio,0,0,ratio,0,0); ctx.clearRect(0,0,width,height);
  const visible = data.nodes.filter(n => n.component === view).sort((a,b) => a.name.localeCompare(b.name));
  const lookup = new Map(), neighbors = new Set();
  data.edges.forEach(([a,b]) => {if (a===selected) neighbors.add(b); if (b===selected) neighbors.add(a);});
  const xs = visible.map(n=>n.x), ys = visible.map(n=>n.y);
  const minX=Math.min(...xs),maxX=Math.max(...xs),minY=Math.min(...ys),maxY=Math.max(...ys);
  points = visible.map((n,i)=>{
    let x,y;
    if (view==="main") {
      x=35+(n.x-minX)/(maxX-minX)*(width-70);
      y=35+(n.y-minY)/(maxY-minY)*(height-115);
    } else if (view==="island") {
      const angle=i/visible.length*Math.PI*2-Math.PI/2;
      x=width/2+Math.cos(angle)*Math.max(65,width/2-95);
      y=(height-65)/2+Math.sin(angle)*Math.max(75,(height-65)/2-65);
    } else {
      const cols=width<500?3:4, rows=Math.ceil(visible.length/cols);
      x=(i%cols+.5)*width/cols; y=35+(Math.floor(i/cols)+.5)*(height-125)/rows;
    }
    const p={...n,x,y,r:view==="main"?2.3+Math.sqrt(n.in)*.78:7+Math.sqrt(n.in)*.8};
    lookup.set(n.id,p);return p;
  });
  const pairs=new Set();
  const edges=data.edges.filter(([a,b])=>{
    if (!lookup.has(a)||!lookup.has(b)) return false;
    const key=[a,b].sort().join("|");
    if(pairs.has(key))return false;pairs.add(key);return true;
  });
  for(const highlighted of [false,true]) {
    ctx.beginPath();
    edges.forEach(([a,b])=>{
      if ((a===selected||b===selected)!==highlighted) return;
      const p=lookup.get(a),q=lookup.get(b);ctx.moveTo(p.x,p.y);ctx.lineTo(q.x,q.y);
    });
    ctx.strokeStyle=highlighted?"rgba(249,137,95,.65)":view==="main"?"rgba(152,192,172,.12)":"rgba(184,202,177,.4)";
    ctx.lineWidth=highlighted?1.2:.7;ctx.stroke();
  }
  for(const p of points) {
    ctx.beginPath();ctx.arc(p.x,p.y,p.r,0,Math.PI*2);
    ctx.fillStyle=p.id===selected?"#ff8459":neighbors.has(p.id)?"#d8e7c8":colors[view];ctx.fill();
    if(p.id===selected){ctx.beginPath();ctx.arc(p.x,p.y,p.r+5,0,Math.PI*2);ctx.strokeStyle="#ff8459";ctx.lineWidth=1;ctx.stroke();}
  }
  const labels = view==="main"?points.filter(p=>p.id===selected||p.in>=50):points;
  labels.forEach(p=>{
    const text=p.name.replace(/\s*\([^)]*\)/g,"");
    ctx.font=(p.id===selected?"600 ":"")+(view==="isolate"?"11":"12")+"px system-ui";
    ctx.fillStyle=p.id===selected?"#ffc4aa":"#d8e5d9";ctx.textAlign="center";
    const half=ctx.measureText(text).width/2+5;
    ctx.fillText(text,Math.max(half,Math.min(width-half,p.x)),Math.min(height-60,p.y+p.r+17));
  });
}
canvas.addEventListener("click",event=>{
  const r=canvas.getBoundingClientRect(),x=event.clientX-r.left,y=event.clientY-r.top;
  const near=points.map(p=>({p,d:Math.hypot(p.x-x,p.y-y)})).sort((a,b)=>a.d-b.d)[0];
  if(near&&near.d<Math.max(near.p.r+7,12))choose(near.p.id);
});
function svgElement(name,attrs={},text) {
  const el=document.createElementNS("http://www.w3.org/2000/svg",name);
  Object.entries(attrs).forEach(([k,v])=>el.setAttribute(k,v));
  if(text!==undefined)el.textContent=text;return el;
}
function drawChart(){
  if(!data)return;
  const series=data.distributions[mode],log=scale==="log",showBins=$("#binning").checked;
  const width=960,height=390,left=75,right=35,top=45,bottom=65;
  const raw=series.raw.filter(p=>!log||p.p>0),bins=series.binned.filter(p=>!log||p.p>0);
  const xmax=Math.max(...series.raw.map(p=>p.u));
  const ymax=Math.max(...series.raw.map(p=>p.p))*1.18;
  const positive=[...raw,...bins].filter(p=>p.p>0).map(p=>p.p);
  const ymin=log?Math.min(...positive)*.65:0;
  const fx=x=>left+(log?Math.log10(x)/Math.log10(xmax):(x-1)/(xmax-1))*(width-left-right);
  const fy=y=>height-bottom-(log?(Math.log10(y)-Math.log10(ymin))/(Math.log10(ymax)-Math.log10(ymin)):y/ymax)*(height-top-bottom);
  const svg=svgElement("svg",{viewBox:"0 0 "+width+" "+height,role:"img","aria-labelledby":"chart-title chart-desc"});
  svg.append(svgElement("title",{id:"chart-title"},(mode==="in"?"In":"Out")+"-degree distribution, "+(log?"log–log":"linear")+" axes"));
  svg.append(svgElement("desc",{id:"chart-desc"},"Horizontal position is k + 1. Green points show raw probabilities; red points optionally show mixed bin density. All 303 nodes, including isolates, enter the denominator."));
  const xTicks=log?[1,2,4,8,16,32,64,100].filter(v=>v<=xmax):[1,...Array.from({length:5},(_,i)=>Math.round(xmax/5*(i+1)))];
  const yTicks=log?[.0001,.001,.01,.1,1].filter(v=>v>=ymin&&v<=ymax):Array.from({length:5},(_,i)=>ymax*i/4);
  for(const y of yTicks){
    svg.append(svgElement("line",{x1:left,x2:width-right,y1:fy(y),y2:fy(y),stroke:"#c8d1c4","stroke-width":1}));
    svg.append(svgElement("text",{x:left-12,y:fy(y)+4,"text-anchor":"end",fill:"#526556","font-size":13},log?String(y):y.toFixed(2)));
  }
  for(const x of xTicks){
    svg.append(svgElement("line",{x1:fx(x),x2:fx(x),y1:top,y2:height-bottom,stroke:"#d4dbcf","stroke-width":1}));
    svg.append(svgElement("text",{x:fx(x),y:height-bottom+25,"text-anchor":"middle",fill:"#526556","font-size":13},x));
  }
  raw.forEach(p=>{
    const circle=svgElement("circle",{cx:fx(p.u),cy:fy(p.p),r:3.8,fill:"#176f61",opacity:.65});
    circle.append(svgElement("title",{},"k="+(p.u-1)+": "+p.count+" pages; P(k)="+p.p.toPrecision(4)));svg.append(circle);
  });
  if(showBins){
    svg.append(svgElement("polyline",{points:bins.map(p=>fx(p.u)+","+fy(p.p)).join(" "),fill:"none",stroke:"#d34a27","stroke-width":2}));
    bins.forEach(p=>{
      const circle=svgElement("circle",{cx:fx(p.u),cy:fy(p.p),r:4.5,fill:"#d34a27",stroke:"#e8ede5","stroke-width":1.3});
      circle.append(svgElement("title",{},"k="+(p.lo-1)+"…"+(p.hi-2)+": "+p.count+" pages; density="+p.p.toPrecision(4)));svg.append(circle);
    });
  }
  svg.append(svgElement("text",{x:width/2,y:height-10,"text-anchor":"middle",fill:"#314d40","font-size":15},"k + 1 (degree zero included)"));
  svg.append(svgElement("text",{transform:"translate(18 "+height/2+") rotate(-90)","text-anchor":"middle",fill:"#314d40","font-size":14},"Probability per unit degree"));
  svg.append(svgElement("text",{x:left,y:22,fill:"#176f61","font-size":14},"● Raw P(k)"));
  if(showBins)svg.append(svgElement("text",{x:left+120,y:22,fill:"#d34a27","font-size":14},"● Mixed bins"));
  $("#degree-chart").replaceChildren(svg);
  $("#chart-reading").textContent=mode==="in"
    ? (log?"The incoming tail reaches k = 106. Binning exposes its sparse shape, but visual resemblance alone cannot establish a power law.":"Most probability is concentrated at small degrees. The small dots far to the right are easy to miss on linear axes.")
    : (log?"Outgoing links stop at k = 28. The shorter tail is consistent with limits on how much one article links to the roster.":"A different editorial pattern: a page creates outgoing links, while many other pages can contribute incoming links.");
}
document.querySelectorAll("[data-view]").forEach(b=>b.addEventListener("click",()=>{
  if(!data)return;
  const component=b.dataset.view;
  const node=data.nodes.find(n=>n.component===component&&(component!=="main"||n.id==="Spider-Man"));
  choose(node.id);
}));
document.querySelectorAll("[data-degree]").forEach(b=>b.addEventListener("click",()=>{mode=b.dataset.degree;press("data-degree",mode);drawChart();}));
document.querySelectorAll("[data-scale]").forEach(b=>b.addEventListener("click",()=>{scale=b.dataset.scale;press("data-scale",scale);drawChart();}));
$("#binning").addEventListener("change",drawChart);
$("#character").addEventListener("change",e=>choose(e.target.value));
new ResizeObserver(drawMap).observe(canvas.parentElement);
fetch("data/week1.json").then(r=>{if(!r.ok)throw Error("Snapshot returned "+r.status);return r.json();}).then(result=>{
  data=result;nodesById=new Map(data.nodes.map(n=>[n.id,n]));
  data.nodes.slice().sort((a,b)=>a.name.localeCompare(b.name)).forEach(n=>{
    const option=document.createElement("option");option.value=n.id;option.textContent=n.name;$("#character").append(option);
  });
  $("#stranded-list").replaceChildren(...data.stats.stranded.map(id=>{const li=document.createElement("li");li.textContent=nodesById.get(id).name;return li;}));
  choose(selected);drawChart();
}).catch(error=>{
  $("#load-error").hidden=false;
  $("#load-error").textContent="The interactive data could not load. Please reload the page, or use the downloadable TSVs and figure below.";
  $("#node-summary").textContent="Interactive data unavailable. The article and tables remain readable.";
  console.error(error);
});

