"use strict";
const $ = selector => document.querySelector(selector);
const labels = {not_started:"待运行",model_finished:"模型结束",model_incomplete:"模型未完成",budget_exhausted:"预算停止",output_truncated:"输出截断",paused_error:"异常暂停",requesting:"等待响应",running:"运行中",executing_tool:"调用工具",rendering:"渲染中",retry_wait:"等待重试",completed:"全部结束",finished:"已结束"};
const names = {"gpt-6-astra":"GPT-6 Astra","gpt-5.6-sol":"GPT-5.6 Sol","claude-sonnet-5":"Claude Sonnet 5","kimi-k3":"Kimi K3"};
let data = null, selectedModel = null, selectedTask = null, selectedRender = null, selectedFrame = 0, view = "video", busy = false, playing = null;
let detailSignature = "";
const runMap = new Map();
function el(tag,text,cls){const node=document.createElement(tag);if(text!=null)node.textContent=text;if(cls)node.className=cls;return node}
function tone(status){if(["model_finished","completed"].includes(status))return "good";if(["budget_exhausted","output_truncated","model_incomplete","retry_wait"].includes(status))return "warn";if(status==="paused_error")return "bad";return "idle"}
function statusText(status){return labels[status]||status||"待运行"}
function displayName(model){return names[model]||model}
function address(path){return path.split("/").map(encodeURIComponent).join("/")}
function link(text,path){const a=el("a",text);a.href=address(path);a.target="_blank";a.rel="noopener";return a}
function addLinks(target,items){target.replaceChildren();for(const [text,path]of items){if(path)target.append(link(text,path))}}
function timeText(value){if(!value)return "—";const date=new Date(value);return Number.isNaN(date.getTime())?String(value):date.toLocaleString("zh-CN",{hour12:false})}
function currentRun(){return runMap.get(selectedModel+"/"+selectedTask)}
function stopPlayback(){if(playing)clearInterval(playing);playing=null}
function button(text,cls){const b=el("button",text,cls);b.type="button";return b}

function select(model,task,scroll=false){
  if(!data.models.some(item=>item.alias===model)||!data.tasks.some(item=>item.id===task))return;
  const changed=selectedModel!==model||selectedTask!==task;
  selectedModel=model;selectedTask=task;
  if(changed){selectedRender=null;selectedFrame=0;detailSignature="";stopPlayback()}
  history.replaceState(null,"","#"+new URLSearchParams({model,task}));
  drawNavigation();drawDetail();drawOverview();
  if(scroll)$("#detail").scrollIntoView({behavior:"smooth",block:"start"});
}

function drawHeader(){
  const summary=data.summary,state=data.state,current=state.current;
  $("#metric-completed").replaceChildren(document.createTextNode(summary.completed),el("span"," / "+summary.total,"denominator"));
  $("#metric-requests").textContent=summary.requests.toLocaleString();
  $("#metric-renders").replaceChildren(document.createTextNode(summary.videos_ready||0),el("span"," / "+summary.started,"denominator"));
  const recording=data.video_recording||{};
  $("#video-progress").textContent=recording.status==="recording"?"正在录制 "+recording.current:"连续渲染 · 30 fps";
  $("#metric-current").textContent=current?.task_id||(state.status==="completed"?"全部结束":"尚未开始");
  $("#metric-model").textContent=current?displayName(current.model):"等待实验队列";
  const notice=$("#notice");notice.replaceChildren();notice.className="notice";
  if(state.status==="paused_error"){
    notice.classList.add("error");notice.append(el("strong","队列已暂停"));
    const description=(current?`${displayName(current.model)} / ${current.task_id} · `:"")+(/401/.test(current?.error||state.error||"")?"API 认证失败（HTTP 401）":current?.stop_reason==="local_error"?"宿主运行错误":"请求或运行异常");
    notice.append(el("span",description),el("span",`已结束 ${summary.completed}/${summary.total} 题 · ${timeText(state.updated)}`));
  }else if(current?.status==="retry_wait"){
    notice.classList.add("stale");
    notice.append(el("strong","HTTP 错误 · 等待重试"),el("span",`${displayName(current.model)} / ${current.task_id} · 下次尝试 ${timeText(current.retry_at*1000)}`),el("span","五分钟后自动继续，保留当前进度。"));
  }else if(state.status==="completed"){
    notice.append(el("strong","实验队列已结束"),el("span",`${summary.completed}/${summary.total} 题 · 具体结束原因见下方任务。`));
  }else{
    notice.append(el("strong",statusText(state.status)),el("span",current?`${displayName(current.model)} / ${current.task_id} · ${statusText(current.status)}`:"等待启动串行队列"),el("span","GPT → Claude → Kimi · 每次执行一个任务"));
  }
  if(Date.now()-new Date(data.generated_at).getTime()>45000){notice.classList.add("stale");notice.append(el("span","展示数据暂未更新，请检查本地展示服务。"))}
  $("#updated").textContent="数据更新于 "+timeText(data.generated_at);
}

function drawNavigation(){
  const models=$("#models");models.replaceChildren();
  for(const model of data.models){
    const b=button(null,"model-tab"+(model.alias===selectedModel?" active":""));b.dataset.model=model.alias;b.setAttribute("aria-pressed",String(model.alias===selectedModel));
    b.append(el("span",displayName(model.name),"model-name"));
    const line=el("span",null,"model-progress");line.append(el("span",model.started?"已结束 "+model.completed+" / "+model.total:"等待前序模型"),el("span",String(Math.round(model.completed/model.total*100))+"%"));b.append(line);
    const progress=el("div",null,"progress-track"),bar=el("i");bar.style.width=(model.completed/model.total*100)+"%";progress.append(bar);b.append(progress);models.append(b);
  }
  const groups=$("#tasks");groups.replaceChildren();
  for(const group of data.groups){
    const box=el("section",null,"task-group"),heading=el("div",null,"task-group-heading");heading.append(el("span",group.id,"group-num"),el("span",group.title));box.append(heading,el("p",group.algorithm));
    const levels=el("div",null,"level-buttons");
    for(const task of data.tasks.filter(item=>item.group===group.id)){
      const run=runMap.get(selectedModel+"/"+task.id),b=button(null,"level-button"+(task.id===selectedTask?" active":""));b.dataset.task=task.id;b.title=task.title;b.setAttribute("aria-pressed",String(task.id===selectedTask));b.setAttribute("aria-label",`${task.id} ${task.title} ${statusText(run.status)}`);
      b.append(el("strong","L"+task.level),el("small",statusText(run.status),tone(run.status)));levels.append(b);
    }
    box.append(levels);groups.append(box);
  }
}

function drawDetail(){
  const run=currentRun(),task=data.tasks.find(item=>item.id===selectedTask),model=data.models.find(item=>item.alias===selectedModel);
  if(!run||!task)return;
  const signature=JSON.stringify(run);
  if(signature===detailSignature)return;
  detailSignature=signature;
  $("#task-id").textContent=task.id+" · "+displayName(model.name);
  $("#task-title").textContent=task.title;
  $("#task-status").textContent=statusText(run.status);$("#task-status").className="badge "+tone(run.status);
  const stats=$("#task-stats");stats.replaceChildren();
  for(const [label,value] of [["请求",`${run.requests} / ${data.limits.requests}`],["render",`${run.render_calls} / ${data.limits.render_calls}`],["计划自评",`${run.plan.status||"未制定"}`]]){
    const span=el("span",label+" ");span.append(el("b",value));stats.append(span);
  }
  if(run.updated)stats.append(el("span","更新 "+timeText(run.updated)));
  $("#task-error").hidden=!run.error;$("#task-error").textContent=run.error||"";
  const selectBox=$("#render-select");selectBox.replaceChildren();
  if(!run.renders.some(item=>item.id===selectedRender)){
    selectedRender=([...run.renders].reverse().find(item=>item.ok&&item.images.length)||run.renders.at(-1))?.id||null;selectedFrame=0;
  }
  for(const render of [...run.renders].reverse()){
    const option=el("option",`第 ${render.index} 次 · ${render.ok===true?"运行成功":render.ok===false?"执行失败":"进行中"} · ${render.images.length} 帧`);option.value=render.id;selectBox.append(option);
  }
  if(!run.renders.length){const option=el("option","暂无渲染");option.value="";selectBox.append(option)}
  selectBox.value=selectedRender||"";selectBox.disabled=!run.renders.length;
  drawVideo();drawRender();drawPlan();setView(view);
}

function drawRender(){
  const run=currentRun(),render=run.renders.find(item=>item.id===selectedRender),stage=$("#image-stage"),frames=$("#frames"),caption=$("#render-caption"),errors=$("#render-errors");
  stage.replaceChildren();frames.replaceChildren();caption.replaceChildren();errors.replaceChildren();
  $("#original-image").hidden=true;$("#camera-details").hidden=!render;
  if(!render){stopPlayback();stage.append(el("div",run.status==="not_started"?"本任务尚未执行。完成渲染后会在此显示。":"本任务尚未产生渲染记录。","empty-state"));$("#render-links").replaceChildren();return}
  selectedFrame=Math.min(selectedFrame,Math.max(0,render.images.length-1));
  const picture=render.images[selectedFrame];
  if(picture){
    const img=el("img");img.src=address(picture.path);img.alt=`${selectedTask} ${displayName(data.models.find(m=>m.alias===selectedModel).name)} 第 ${render.index} 次渲染，第 ${picture.frame} 帧`;
    img.addEventListener("error",()=>stage.replaceChildren(el("div","截图暂时无法读取，请刷新或查看渲染日志。","empty-state")),{once:true});stage.append(img);
    $("#original-image").href=address(picture.path);$("#original-image").hidden=false;
  }else{stopPlayback();stage.append(el("div",render.ok===false?"本次渲染未生成可用截图，请查看下方错误与日志。":"正在等待截图文件。","empty-state"))}
  if(render.images.length>1){const play=button(playing?"Ⅱ 暂停":"▶ 播放帧","play");play.id="play-frames";frames.append(play)}
  render.images.forEach((item,index)=>{const b=button("帧 "+item.frame,index===selectedFrame?"active":"");b.dataset.frame=String(index);b.setAttribute("aria-pressed",String(index===selectedFrame));frames.append(b)});
  const scope=render.scene_kind==="candidate_preview"?"隔离预览":"本题目标场景";
  caption.append(el("span",`第 ${render.index} 次渲染 · ${scope}`+(picture?` · ${picture.width} × ${picture.height} · t = ${Number(picture.elapsed_s||0).toFixed(2)} s`:"")));
  caption.append(el("br"),el("span",render.matches_current_files?"与当前候选文件一致。":"当前候选文件与本次渲染版本不同。",render.matches_current_files?"":"warning"));
  if(render.ok===false)caption.append(el("span"," 本次执行失败，图像未作为成功渲染回传。","warning"));
  if(render.id!==run.renders.at(-1)?.id)caption.append(el("span",` 正在查看历史记录，最新为第 ${run.renders.length} 次。`,"warning"));
  addLinks($("#render-links"),[["渲染日志",render.links["godot.log"]],["导入日志",render.links["import.log"]],["数值输出",render.links["samples.json"]],["运行记录",render.links["result.json"]],["文件快照",render.links["files.json"]]]);
  $("#camera-json").textContent=JSON.stringify({request:render.request,captured_camera:picture?.camera||null},null,2);
  if(render.errors.length){const details=el("details");details.open=true;details.append(el("summary",`执行错误 · ${render.errors.length} 条`),el("pre",render.errors.join("\n"),"render-error"));errors.append(details)}
  if(render.warnings.length){const details=el("details");details.append(el("summary",`运行警告 · ${render.warnings.length} 条`),el("pre",render.warnings.join("\n")));errors.append(details)}
}

function format(value){if(value==null||value==="")return "—";return typeof value==="string"?value:JSON.stringify(value,null,2)}
function drawPlan(){
  const run=currentRun(),target=$("#plan-content");target.replaceChildren();
  const steps=Array.isArray(run.plan.steps)?run.plan.steps:[];
  if(!steps.length)target.append(el("div","尚未保存子任务计划。","empty-state"));
  else{
    target.append(el("p",`计划状态：${run.plan.status||"—"} · 当前子任务：${run.plan.active_step||"无"}。以下状态为模型自评。`,"muted"));
    for(const step of steps){
      const details=el("details",null,"plan-step"),summary=el("summary");summary.append(el("span",`${step.id} · ${step.goal}`),el("span",step.status));details.append(summary);
      const dl=el("dl");for(const [key,label]of [["expected","预期"],["counterexample","反例"],["observations","观察记录"],["summary","结论"],["limitations","限制"]]){dl.append(el("dt",label),el("dd",format(step[key])))}details.append(dl);target.append(details);
    }
  }
  const final=$("#final-content");final.replaceChildren();if(run.final_text){final.append(el("h3","模型最终说明（自评）"),el("pre",run.final_text))}
}

function setView(next){view=next;if(next!=="render")stopPlayback();const player=$("#final-video");if(player&&next!=="video")player.pause();for(const name of ["video","render","prompt","trajectory","plan","files"]){$("#"+name+"-view").hidden=name!==next;const b=document.querySelector(`[data-view="${name}"]`);b.classList.toggle("active",name===next);b.setAttribute("aria-pressed",String(name===next))}window.caseInspector?.show(next)}
function drawOverview(){
  const head=$("#overview-head"),body=$("#overview-body");head.replaceChildren();body.replaceChildren();const row=el("tr");row.append(el("th","任务"));for(const model of data.models)row.append(el("th",displayName(model.name)));head.append(row);
  for(const task of data.tasks){
    const tr=el("tr"),title=el("td",task.id);title.append(el("small",task.title));tr.append(title);
    for(const model of data.models){
      const run=runMap.get(model.alias+"/"+task.id),td=el("td"),b=button(null,"matrix-button"+(model.alias===selectedModel&&task.id===selectedTask?" active":""));b.dataset.model=model.alias;b.dataset.task=task.id;b.dataset.jump="true";
      b.append(el("i",null,"dot "+tone(run.status)),el("span",statusText(run.status),tone(run.status)),el("span",run.requests?run.requests+" 请求":"—","count"));td.append(b);tr.append(td);
    }
    body.append(tr);
  }
}

async function refresh(){
  if(busy)return;busy=true;$("#refresh").disabled=true;
  try{
    const response=await fetch("runtime/dashboard.json",{cache:"no-store"});if(!response.ok)throw new Error("HTTP "+response.status);
    data=await response.json();runMap.clear();for(const run of data.runs)runMap.set(run.alias+"/"+run.task_id,run);
    if(!selectedModel){const hash=new URLSearchParams(location.hash.slice(1)),ready=data.runs.find(run=>run.terminal&&run.video?.status==="ready"&&run.video.matches_current_files);selectedModel=hash.get("model")||ready?.alias||data.state.current?.alias||data.models[0].alias;selectedTask=hash.get("task")||ready?.task_id||data.state.current?.task_id||data.tasks[0].id}
    if(!data.models.some(m=>m.alias===selectedModel))selectedModel=data.models[0].alias;
    if(!data.tasks.some(t=>t.id===selectedTask))selectedTask=data.tasks[0].id;
    drawHeader();drawNavigation();drawDetail();drawOverview();
  }catch(error){const notice=$("#notice");notice.className="notice error";notice.replaceChildren(el("strong","展示数据读取失败"),el("span",location.protocol==="file:"?"请通过 http://127.0.0.1:8771/index.html 打开页面。":`请检查本地展示服务。${error.message}`));}
  finally{busy=false;$("#refresh").disabled=false}
}

document.addEventListener("click",event=>{
  const b=event.target.closest("button");if(!b)return;
  if(b.id==="refresh"){refresh();return}
  if(b.dataset.model||b.dataset.task){select(b.dataset.model||selectedModel,b.dataset.task||selectedTask,b.dataset.jump==="true");return}
  if(b.dataset.view){setView(b.dataset.view);if(b.dataset.view==="video")$("#final-video")?.play().catch(()=>{});return}
  if(b.dataset.frame){stopPlayback();selectedFrame=Number(b.dataset.frame);drawRender();return}
  if(b.id==="play-frames"){
    if(playing)stopPlayback();else playing=setInterval(()=>{const render=currentRun().renders.find(item=>item.id===selectedRender);if(!render?.images.length){stopPlayback();return}selectedFrame=(selectedFrame+1)%render.images.length;drawRender()},850);
    drawRender();
  }
});
$("#render-select").addEventListener("change",event=>{stopPlayback();selectedRender=event.target.value;selectedFrame=0;drawRender()});
window.addEventListener("hashchange",()=>{if(!data)return;const hash=new URLSearchParams(location.hash.slice(1));select(hash.get("model"),hash.get("task"))});
setInterval(()=>{if($("#auto-refresh").checked&&!document.hidden)refresh()},15000);
document.addEventListener("visibilitychange",()=>{if(document.hidden)stopPlayback();else if($("#auto-refresh").checked)refresh()});
refresh();

function drawVideo(){
  const run=currentRun(),video=run.video||{},stage=$("#video-stage"),caption=$("#video-caption"),errorBox=$("#video-errors");
  caption.replaceChildren();errorBox.replaceChildren();
  $("#video-kind").textContent=run.terminal?"最终候选视频":"当前候选预览 · 任务未结束";
  const ready=video.status==="ready"&&video.video&&video.matches_current_files;
  if(ready){
    const path=address(video.video),existing=$("#final-video");
    if(!existing||existing.getAttribute("src")!==path){
      const player=el("video");player.id="final-video";player.controls=true;player.loop=true;player.muted=true;player.autoplay=true;player.playsInline=true;player.preload="metadata";
      player.src=path;if(video.poster)player.poster=address(video.poster);player.playbackRate=Number($("#video-speed").value);
      player.setAttribute("aria-label",selectedTask+" 连续效果视频");
      player.addEventListener("error",()=>errorBox.replaceChildren(el("p","视频无法读取，请使用下载链接或检查展示服务。","render-error")));
      stage.replaceChildren(player);
    }
    caption.append(el("span",`${video.resolution[0]} × ${video.resolution[1]} · ${video.fps} fps · ${video.duration_seconds.toFixed(2)} 秒 · ${video.frame_count} 帧`));
    caption.append(el("br"),el("span",video.request.orbit?"相机小幅环绕观察；固定算法输入保持不变。":"按固定输入完整推进时间过程；循环播放，支持慢放和全屏。"));
    if(!run.terminal)caption.append(el("br"),el("span","任务尚未结束，此视频仅代表当前保存的候选。","warning"));
    addLinks($("#video-links"),[["下载 MP4",video.video],["录制记录",video.metadata_link],["GPU 日志",video.directory+"/godot.log"]]);
    const download=$("#video-links a");if(download)download.download=selectedModel+"_"+selectedTask+".mp4";
  }else{
    const states={recording:"正在连续录制完整时间过程…",encoding:"正在编码 MP4 视频…",failed:"当前候选录制失败，请查看下方日志。",queued:"等待 GPU 空闲后录制…"};
    const message=run.status==="not_started"?"本任务尚未执行，完成后会自动录制效果视频。":video.status==="ready"&&!video.matches_current_files?"候选文件已更新，正在等待重新录制最新视频。":states[video.status]||"等待录制最终候选视频…";
    if(!stage.querySelector(".empty-state")||stage.textContent!==message)stage.replaceChildren(el("div",message,"empty-state"));
    caption.append(el("span","录制使用各模型实际保存的实现，完成后会自动显示。"));
    addLinks($("#video-links"),[["录制记录",video.metadata_link]]);
    if(video.errors?.length)errorBox.append(el("pre",video.errors.join("\n"),"render-error"));
  }
  $("#video-speed").disabled=!ready;
}
$("#video-speed").addEventListener("change",event=>{const player=$("#final-video");if(player)player.playbackRate=Number(event.target.value)});
