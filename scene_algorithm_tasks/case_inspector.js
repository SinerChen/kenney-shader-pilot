"use strict";
const inspectCache = new Map();
let inspectKey = "", inspectData = null, inspectFile = null, inspectFileMode = "diff", inspectPage = 0, inspectToken = 0;
const inspectPageSize = 20;
const eventLabels = {request:"模型请求",response:"模型响应",tool:"工具调用",api_error:"API 错误",budget_exhausted:"预算结束",local_error:"宿主错误"};
const fileLabels = {added:"新增",modified:"修改",unchanged:"未变更",deleted:"删除"};

async function inspectFetch(path){
  const response=await fetch(address(path),{cache:"no-store"});
  if(!response.ok)throw new Error("HTTP "+response.status);
  return response.json();
}
function inspectPre(text,cls){return el("pre",text==null?"二进制文件，请通过原文件链接查看。":text,cls||"inspect-code")}
function inspectSection(title,text,open=false){const d=el("details",null,"inspect-block");d.open=open;d.append(el("summary",title),inspectPre(text));return d}
function inspectRawLink(label,path){const a=link(label,path);a.download="";return a}
function inspectText(content){return typeof content==="string"?content:JSON.stringify(content,null,2)}

window.caseInspector={
  async show(next){
    if(!["prompt","trajectory","files"].includes(next))return;
    const run=currentRun(),key=run.alias+"/"+run.task_id+"/"+(run.case_details?.version||"");
    if(inspectKey===key&&inspectData){inspectDraw(next);return}
    const token=++inspectToken;
    const body=$("#"+next+"-body");body.replaceChildren(el("p","正在读取本案例记录…","muted"));
    try{
      if(!run.case_details?.path)throw new Error("展示索引正在更新，请稍后刷新");
      const value=inspectCache.get(key)||await inspectFetch(run.case_details.path);
      if(token!==inspectToken||currentRun().alias!==run.alias||currentRun().task_id!==run.task_id)return;
      inspectCache.set(key,value);
      const sameCase=inspectData?.alias===value.alias&&inspectData?.task_id===value.task_id;
      inspectKey=key;inspectData=value;
      if(!sameCase){inspectFile=null;inspectPage=0;$("#trace-search").value="";$("#trace-filter").value="all"}
      inspectDraw(view);
    }catch(error){if(token===inspectToken)body.replaceChildren(el("p","记录读取失败："+error.message,"render-error"))}
  }
};
function inspectDraw(next){
  if(!inspectData)return;
  if(next==="prompt")inspectPrompt();
  if(next==="trajectory")inspectTrace();
  if(next==="files")inspectFiles();
}

function inspectPrompt(){
  const box=$("#prompt-body");if(box.dataset.version===inspectKey)return;box.dataset.version=inspectKey;box.replaceChildren();
  const actual=inspectData.input_source==="actual";
  box.append(el("p",actual?"本案例实际发送的起始输入：P3 系统提示词、当前任务题面与工具定义。":"尚未调用模型。以下为已冻结的输入预览，实际调用记录将在运行后出现。",actual?"inspect-notice":"inspect-notice warning"));
  const source=el("div",null,"resource-links");source.append(link(actual?"实际 input.json":"冻结输入 JSON",inspectData.input_link));box.append(source);
  const messages=inspectData.input.messages||[];
  for(const [index,message] of messages.entries()){
    const title=message.role==="system"?"P3 · System":message.role==="user"?"当前任务 · User":message.role+" · "+(index+1);
    const block=inspectSection(title,inspectText(message.content),true),copy=button("复制内容","quiet");
    copy.addEventListener("click",async()=>{try{await navigator.clipboard.writeText(inspectText(message.content));copy.textContent="已复制"}catch{copy.textContent="请在下方选中文本复制"}});
    block.insertBefore(copy,block.querySelector("pre"));box.append(block);
  }
  box.append(inspectSection("工具定义 · read / write / render",JSON.stringify(inspectData.input.tools||[],null,2)));
}

function inspectFiltered(){
  const type=$("#trace-filter").value,query=$("#trace-search").value.trim().toLowerCase();
  return inspectData.events.filter(event=>{
    const category=type==="all"||(type==="model"&&event.type==="response")||(type==="request"&&event.type==="request")||(type==="error"&&(event.ok===false||event.type.includes("error")))||event.tool===type;
    return category&&(!query||[event.title,event.preview,event.text,event.path,JSON.stringify(event.error||"")].join(" ").toLowerCase().includes(query));
  });
}
function inspectTrace(){
  const box=$("#trajectory-body"),filtered=inspectFiltered();box.replaceChildren();
  const counts=inspectData.event_counts;
  $("#trace-summary").textContent=`${inspectData.events.length} 条事件 · ${counts.request||0} 次请求 · ${counts.response||0} 次响应 · ${counts.tool||0} 次工具调用`+(inspectData.partial_trace?" · 最后一条记录仍在写入":"");
  const links=$("#trace-links");links.replaceChildren();if(inspectData.trajectory)links.append(inspectRawLink("下载原始 trajectory.jsonl",inspectData.trajectory));
  if(!filtered.length){box.append(el("div",inspectData.events.length?"没有符合筛选条件的事件。":"本案例尚无调用轨迹。","empty-state"))}
  inspectPage=Math.min(inspectPage,Math.max(0,Math.ceil(filtered.length/inspectPageSize)-1));
  for(const event of filtered.slice(inspectPage*inspectPageSize,(inspectPage+1)*inspectPageSize)){
    const d=el("details",null,"trace-event");d.dataset.event=event.id;
    const head=el("summary"),top=el("div",null,"event-heading"),tag=el("span",eventLabels[event.type]||event.title,"event-tag");
    top.append(el("span","#"+event.id,"muted"),tag,el("strong",event.tool||event.preview.slice(0,90)||event.title));
    if(event.ok!=null)top.append(el("span",event.ok?"成功":"失败",event.ok?"good":"bad"));
    head.append(top,el("small",`请求 ${event.request_number||"—"} · ${timeText(event.time)}`,"muted"));d.append(head);
    d.addEventListener("toggle",()=>{if(d.open&&!d.dataset.loaded){d.dataset.loaded="true";inspectEvent(d,event)}});
    box.append(d);
  }
  $("#trace-page").textContent=`${filtered.length?inspectPage+1:0} / ${Math.ceil(filtered.length/inspectPageSize)} 页 · 筛选后 ${filtered.length} 条`;
  $("#trace-prev").disabled=inspectPage===0;$("#trace-next").disabled=(inspectPage+1)*inspectPageSize>=filtered.length;
}
async function inspectEvent(container,event){
  const workspace=inspectData.workspace;
  const content=el("div",null,"event-body");content.append(el("p","正在读取…","muted"));container.append(content);
  try{
    const raw=await inspectFetch(event.raw);content.replaceChildren();
    if(event.type==="tool"){
      let args=raw.call.arguments;try{if(typeof args==="string")args=JSON.parse(args)}catch{args={unparsed:args}}
      if(!args||typeof args!=="object")args={unparsed:args};
      const output=raw.result;
      const copy={...args};delete copy.content;
      content.append(inspectSection("调用参数",JSON.stringify(copy,null,2),true));
      if(typeof args?.content==="string")content.append(inspectSection("写入的完整内容",args.content,true));
      if(typeof output.content==="string")content.append(inspectSection("读取结果",output.content,true));
      const slim={...output};delete slim.content;
      if(slim.images)slim.images=slim.images.map(({data,...item})=>item);
      content.append(inspectSection("工具返回",JSON.stringify(slim,null,2),true));
      const images=el("div",null,"trace-images");
      const feedback=output.kind==="image"?[{...output,path:args.path}]:output.images||[];
      for(const item of feedback){
        const path=item.data?.$image_file?workspace.replace(/model_workspace\/$/,"")+item.data.$image_file:item.path?workspace+item.path:null;
        if(!path)continue;const a=link("",path),img=el("img");img.src=address(path);img.loading="lazy";img.alt="工具回传图像 · 帧 "+(item.frame||"");a.append(img,el("span","帧 "+(item.frame||"")));images.append(a);
      }
      content.append(images);
    }else if(event.type==="response"){
      content.append(inspectPre(event.text||"本条响应没有可展示的文本；可展开原始响应查看工具调用与状态。"));
      if(event.usage)content.append(inspectSection("用量与响应状态",JSON.stringify({usage:event.usage,status:event.response_status},null,2)));
    }else if(event.type==="request"){
      content.append(inspectSection("请求参数",JSON.stringify(event.metadata||{},null,2),true));
      content.append(el("p","完整请求体可在下方展开，包含当次提交的消息与工具定义。","muted"));
    }else content.append(inspectPre(JSON.stringify(raw,null,2)));
    const rawSection=el("details",null,"inspect-block raw-event");rawSection.append(el("summary","展开原始事件 JSON"));
    rawSection.addEventListener("toggle",()=>{if(rawSection.open&&!rawSection.querySelector("pre"))rawSection.append(inspectPre(JSON.stringify(raw,null,2)))});
    content.append(rawSection,inspectRawLink("下载此事件 JSON",event.raw));
  }catch(error){content.replaceChildren(el("p","事件读取失败："+error.message,"render-error"));delete container.dataset.loaded}
}

function inspectFiles(){
  const box=$("#files-body");if(box.dataset.version===inspectKey)return;box.dataset.version=inspectKey;box.replaceChildren();
  const counts=inspectData.change_counts;
  const origin=inspectData.parent_task?`本题开始时实际继承的 ${inspectData.parent_task} 文件快照`:"本题开始时的初始文件快照";
  box.append(el("p",inspectData.initial_source?`对比基准：${origin}。新增 ${counts.added||0} · 修改 ${counts.modified||0} · 未变更 ${counts.unchanged||0} · 删除 ${counts.deleted||0}。`:"任务尚未启动，尚无模型修改记录。","inspect-notice"));
  const grid=el("div",null,"file-inspector"),list=el("div",null,"inspect-file-list");list.id="files-content";
  const panel=el("div",null,"file-detail");panel.id="file-detail";
  for(const file of inspectData.files){
    const row=button(null,"inspect-file");row.dataset.file=file.name;
    row.append(el("strong",file.name),el("span",`${fileLabels[file.status]} · +${file.added_lines} −${file.removed_lines}`,file.status==="unchanged"?"muted":"good"));
    row.addEventListener("click",()=>inspectSelectFile(file.name));list.append(row);
  }
  grid.append(list,panel);box.append(grid);
  const links=el("div",null,"resource-links");links.id="run-links";
  const run=currentRun();addLinks(links,[["结束记录",run.links.result],["实时状态",run.links.status],["计划 JSON",run.links.plan],["S1 继承记录",run.links.inheritance],["原始调用轨迹",run.links.trajectory],["最终说明",run.links.final]]);
  for(const a of links.querySelectorAll("a"))if(a.textContent==="原始调用轨迹")a.download=`${selectedModel}_${selectedTask}_trajectory.jsonl`;
  box.append(el("h3","运行记录"),links);
  if(inspectData.files.length){inspectFile=inspectData.files.some(f=>f.name===inspectFile)?inspectFile:inspectData.files.find(f=>f.name==="main.gd")?.name||inspectData.files[0].name;inspectSelectFile(inspectFile)}
  else panel.append(el("div","尚无候选文件。","empty-state"));
}
async function inspectSelectFile(name){
  inspectFile=name;const key=inspectKey,file=inspectData.files.find(f=>f.name===name),panel=$("#file-detail");
  document.querySelectorAll(".inspect-file").forEach(b=>b.classList.toggle("active",b.dataset.file===name));
  panel.replaceChildren(el("p","正在读取文件…","muted"));
  try{
    const details=await inspectFetch(file.detail);
    if(key!==inspectKey||inspectFile!==name)return;
    panel.replaceChildren(el("h3","effect/"+name));
    const links=el("div",null,"resource-links");addLinks(links,[["当前文件",file.current],["起始文件",file.before]]);panel.append(links);
    const tabs=el("div",null,"code-tabs"),code=el("div");code.id="file-code";
    const draw=()=>{
      tabs.querySelectorAll("button").forEach(b=>b.classList.toggle("active",b.dataset.mode===inspectFileMode));code.replaceChildren();
      if(inspectFileMode==="diff"){
        if(details.binary)code.append(el("p","二进制文件，请下载原文件比较。","muted"));
        else if(!details.diff.length)code.append(el("p","与本题起始快照相同。","muted"));
        else{const pre=el("pre",null,"inspect-code diff-code");for(const line of details.diff)pre.append(el("span",line+"\n",line.startsWith("+")?"diff-add":line.startsWith("-")?"diff-remove":line.startsWith("@@")?"diff-range":""));code.append(pre)}
      }else code.append(inspectPre(inspectFileMode==="current"?details.current_text:details.before_text));
    };
    for(const [mode,label] of [["diff","修改差异"],["current","当前内容"],["before","起始内容"]]){const b=button(label);b.dataset.mode=mode;b.addEventListener("click",()=>{inspectFileMode=mode;draw()});tabs.append(b)}
    panel.append(tabs,code);draw();
    const history=el("div",null,"write-history");history.append(el("span",`成功写入 ${file.writes.length} 次：`,"muted"));
    for(const id of file.writes){const b=button("#"+id,"quiet");b.addEventListener("click",()=>inspectJump(id));history.append(b)}
    panel.append(history);
  }catch(error){if(key===inspectKey&&inspectFile===name)panel.replaceChildren(el("p","文件读取失败："+error.message,"render-error"))}
}
function inspectJump(id){
  $("#trace-filter").value="all";$("#trace-search").value="";
  inspectPage=Math.floor(inspectData.events.findIndex(event=>event.id===id)/inspectPageSize);
  setView("trajectory");const target=document.querySelector(`.trace-event[data-event="${id}"]`);
  if(target){target.open=true;target.scrollIntoView({behavior:"smooth",block:"center"})}
}
$("#trace-filter").addEventListener("change",()=>{inspectPage=0;inspectTrace()});
$("#trace-search").addEventListener("input",()=>{inspectPage=0;inspectTrace()});
$("#trace-prev").addEventListener("click",()=>{inspectPage--;inspectTrace()});
$("#trace-next").addEventListener("click",()=>{inspectPage++;inspectTrace()});
