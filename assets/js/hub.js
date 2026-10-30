"use strict";
/* Family links use only explicitly verified destinations; Poaceae keeps the\n   original learner fallback. This does not change botanical source ownership. */
const state = {species:[],families:[],collections:[],source:null,shown:24,currentResults:[]};
const $ = id => document.getElementById(id);
function el(tag,className,text){
  const node=document.createElement(tag);
  if(className)node.className=className;
  if(text!==undefined&&text!==null)node.textContent=String(text);
  return node;
}
function token(s){return String(s||"").toLowerCase().normalize("NFKD").replace(/[^a-z0-9 ]+/g," ").replace(/\s+/g," ").trim();}
function legacyLink(id){
  return (state.source?.canonical_site||"https://crking92.github.io/Hays-County-Botany/")+"?species="+encodeURIComponent(id);
}
async function getJSON(path){
  const res=await fetch(path,{cache:"no-store"});
  if(!res.ok)throw new Error("Could not load "+path+" ("+res.status+")");
  return res.json();
}
function familyRoute(sp){
  const c=state.collections.find(g=>g.families.includes(sp.family));
  if(["LIVE_TEXT_ONLY_PREVIEW","LIVE_VERIFIED_CC_GALLERY"].includes(c?.status) && /^https:\/\/crking92\.github\.io\/Hays-Botany-[A-Za-z-]+\/site\/$/.test(c.live_url||"")){
    return {href:c.live_url+"?species="+encodeURIComponent(sp.id),label:c.status==="LIVE_VERIFIED_CC_GALLERY"?"Family learner · verified source-credited photographs":"Family field-ID text learner · photographs pending",family:true};
  }
  return {href:legacyLink(sp.id),label:sp.family==="Poaceae"?"Original grass learner · photo fallback":"Original learner · family route unavailable",family:false};
}
function addSpeciesLink(sp){
  const route=familyRoute(sp);
  const link=el("a","result");link.href=route.href;
  link.target="_blank";link.rel="noopener noreferrer";
  link.setAttribute("aria-label","Open "+sp.search_label+" in "+(route.family?"the verified family field-ID learner":"the original grass learner"));
  link.append(el("span","tag",sp.family));
  const science=sp.scientific_name||sp.search_label||sp.id.replaceAll("-"," ");
  const common=sp.common_name||"";
  link.append(el("strong","",common||science));
  if(common)link.append(el("em","scientific",science));
  link.append(el("small","",sp.id+" · "+sp.genus));
  link.append(el("small","",route.label));
  return link;
}
function rankedSpecies(query){
  const words=token(query).split(" ").filter(Boolean);
  if(!words.length)return state.species.slice(0,24);
  return state.species.filter(sp=>words.every(w=>sp._search.includes(w))).sort((a,b)=>{
    const aFirst=a._common.startsWith(words[0])?0:a._label.startsWith(words[0])?1:2;
    const bFirst=b._common.startsWith(words[0])?0:b._label.startsWith(words[0])?1:2;
    return aFirst-bFirst||a.family.localeCompare(b.family)||a.id.localeCompare(b.id);
  });
}
function renderResults(reset=true){
  if(reset)state.shown=24;
  const query=$("searchInput").value.trim();
  state.currentResults=rankedSpecies(query);
  const count=state.currentResults.length;
  $("resultSummary").textContent=query?count.toLocaleString()+" matching species — available family lessons open directly; grass links use the original learner":"Showing a few indexed species. Search by common name, scientific name, genus, family, or ID.";
  const wrap=$("results");wrap.replaceChildren();
  const frag=document.createDocumentFragment();
  state.currentResults.slice(0,state.shown).forEach(sp=>frag.append(addSpeciesLink(sp)));
  if(!count)frag.append(el("p","muted","No species found in this staging index. Try a genus, family or stable ID."));
  wrap.append(frag);
  $("moreResults").hidden=state.shown>=count;
}
function renderFamilies(){
  const query=token($("familyFilter").value);
  const wrap=$("familiesGrid");wrap.replaceChildren();
  const frag=document.createDocumentFragment();
  const chosen=state.families.filter(f=>token(f.name+" "+(f.common_name||"")).includes(query));
  for(const f of chosen){
    const btn=el("button","familycard");btn.type="button";
    btn.append(el("strong","",f.name));
    if(f.common_name)btn.append(el("span","",f.common_name));
    btn.append(el("small","",f.species_count+" indexed species"));
    btn.append(el("em","",""));
    btn.lastChild.textContent="See species ↗";
    btn.addEventListener("click",()=>{
      const url=new URL(location.href);
      url.searchParams.delete("species");url.searchParams.delete("q");
      url.searchParams.set("family",f.name);url.hash="species";
      history.pushState({family:f.name},"",url);
      $("searchInput").value=f.name;
      renderResults(true);
      document.getElementById("species").scrollIntoView({behavior:"smooth",block:"start"});
      $("searchInput").focus({preventScroll:true});
    });
    frag.append(btn);
  }
  if(!chosen.length)frag.append(el("p","muted","No family found."));
  wrap.append(frag);
}
function prettyCollectionName(id){
  const titles={"Hays-Botany-Poaceae":"Grasses · Poaceae","Hays-Botany-Asteraceae":"Sunflowers · Asteraceae","Hays-Botany-Fabaceae":"Legumes · Fabaceae","Hays-Botany-Monocots-Aquatics":"Monocots & aquatics","Hays-Botany-Lamiales":"Lamiales","Hays-Botany-Asterid-Allies":"Asterid allies","Hays-Botany-Cacti-Buttercups":"Cacti & buttercups","Hays-Botany-Spurges-Mallows":"Spurges & mallows","Hays-Botany-Trees-Shrubs":"Trees & shrubs","Hays-Botany-Mixed-Families":"Mixed families"};
  return titles[id]||id.replace("Hays-Botany-","").replaceAll("-"," ");
}
function renderCollections(){
  const target=$("collectionsGrid");target.replaceChildren();const frag=document.createDocumentFragment();
  for(const group of state.collections){
    const card=el("article","collectioncard");
    const live=["LIVE_TEXT_ONLY_PREVIEW","LIVE_VERIFIED_CC_GALLERY"].includes(group.status);
    const grassReview=group.id==="Hays-Botany-Poaceae" && group.status==="LIVE_REVIEW_ONLY_NOT_ROUTED";
    const label=group.status==="LIVE_VERIFIED_CC_GALLERY"?"Live field-ID learner · "+group.photos_deployed_in_this_collection+" verified photographs":live?"Live field-ID text learner · photo review pending":grassReview?"Live grass review · "+group.review_published_photo_files+" source photo files / "+group.review_visible_photo_panels+" panels · original fallback active":"Grass learner in preparation · original site available";
    card.append(el("span","status",label));
    card.append(el("h3","",prettyCollectionName(group.id)));
    card.append(el("p","",group.families.length+" "+(group.families.length===1?"family":"families")+" · "+group.installed_species_baseline+" source species"));
    const sample=group.families.slice(0,5).join(", ");
    card.append(el("small","",sample+(group.families.length>5?" and "+(group.families.length-5)+" more":"")));
    const links=el("div","links"),sourceLink=el("a","button secondary","View source repository");
    sourceLink.href=group.github_url;sourceLink.target="_blank";sourceLink.rel="noopener noreferrer";
    if(live){
      const go=el("a","button","Open family learner");
      go.href=group.live_url;go.target="_blank";go.rel="noopener noreferrer";links.append(go);
    }else{
      const old=el("a","button","Open original grass learner");
      old.href=state.source.canonical_site+"?species=schizachyrium-scoparium";old.target="_blank";old.rel="noopener noreferrer";links.append(old);
      if(grassReview){
        const review=el("a","button secondary","Try dedicated grass learner");
        review.href=group.review_url;review.target="_blank";review.rel="noopener noreferrer";links.append(review);
      }
    }
    links.append(sourceLink);card.append(links);frag.append(card);
  }
  target.append(frag);
}
function showFailure(e){
  $("resultSummary").textContent="The hub index could not load. The original Visual Learner is still available.";
  const p=el("p","muted",e.message);$("results").replaceChildren(p);
  $("familiesGrid").replaceChildren(el("p","muted","Family index unavailable."));
  $("collectionsGrid").replaceChildren(el("p","muted","Collection index unavailable."));
}
async function start(){
  try {
    const [index,hub]=await Promise.all([getJSON("./data/species-index.json"),getJSON("./data/collections.json")]);
    if(index.status!=="STAGING_READ_ONLY_SOURCE_SNAPSHOT"||!["NINE_VERIFIED_FAMILY_TEXT_SITES_GRASSES_LEGACY_FALLBACK","NINE_VERIFIED_FAMILY_PHOTO_GALLERIES_GRASSES_LEGACY_FALLBACK"].includes(hub.status)||!Array.isArray(index.records)||!Array.isArray(hub.collections)||!Array.isArray(hub.families))throw Error("Hub data schema or staging-only routing status was not recognized.");
    if(index.records.length!==index.source_count||hub.collections.length!==10)throw Error("Indexed data counts did not match the saved baseline.");
    state.source=hub;
    state.species=index.records.map(x=>({...x,
      _label:token(x.scientific_name||x.search_label),
      _common:token(x.common_name),
      _search:token([x.id,x.genus,x.family,x.search_label,x.scientific_name,x.common_name].join(" "))
    }));
    state.families=hub.families;
    state.collections=hub.collections;
    $("speciesCount").textContent=state.species.length.toLocaleString();
    $("familyCount").textContent=state.families.length.toLocaleString();
    $("collectionCount").textContent=state.collections.length.toLocaleString();
    $("sourceStamp").textContent="Read-only snapshot from "+index.canonical_source_repository+" · source manifest blob "+index.source_manifest_blob_sha.slice(0,12)+" · generated "+index.generated_at+".";
    renderFamilies();renderCollections();restoreSearchFromURL();
    refreshPublishedFamilyCatalog();
  }catch(e){showFailure(e)}
}
async function refreshPublishedFamilyCatalog(){
  // Public-site indexes, not source staging, are the only approved expansion
  // authority. The preserved original 1,191-record hub snapshot is the fallback.
  const collections=state.collections.filter(c=>
    ["LIVE_TEXT_ONLY_PREVIEW","LIVE_VERIFIED_CC_GALLERY"].includes(c.status) &&
    /^https:\/\/crking92\.github\.io\/Hays-Botany-[A-Za-z-]+\/site\/$/.test(c.live_url||""));
  const responses=await Promise.allSettled(collections.map(async c=>{
    const data=await getJSON(c.live_url+"data/collection-index.json");
    if(!Array.isArray(data.entries))throw Error("Bad family index");
    return {collection:c,entries:data.entries};
  }));
  const known=new Set(state.species.map(s=>s.id));
  let discovered=0;
  for(const result of responses){
    if(result.status!=="fulfilled")continue;
    const {collection,entries}=result.value;
    for(const r of entries){
      const id=String(r.id||"");
      const family=String(r.family||"");
      if(!/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(id)||
         !collection.families.includes(family)||known.has(id))continue;
      const name=String(r.scientific_name||"").trim();
      if(!name)continue;
      const genus=String(r.genus||name.split(" ")[0]).trim();
      const common=String(r.common_name||"").trim();
      if(!genus)continue;
      const item={id,family,genus,search_label:name,scientific_name:name,
        common_name:common,metadata_source:collection.id+":published-site",
        _label:token(name),_common:token(common),
        _search:token([id,family,genus,name,common].join(" "))};
      state.species.push(item);
      known.add(id);
      discovered++;
      const fam=state.families.find(f=>f.name===family);
      if(fam)fam.species_count++;
    }
  }
  if(discovered){
    state.species.sort((a,b)=>a.family.localeCompare(b.family)||a.id.localeCompare(b.id));
    $("speciesCount").textContent=state.species.length.toLocaleString();
    $("sourceStamp").textContent+=" "+discovered+" additional published family species discovered automatically; the historical source snapshot remains unchanged.";
    renderResults(true);
    renderFamilies();
  }
}
function restoreSearchFromURL(){
  const params=new URLSearchParams(location.search);
  const id=params.get("species");
  const exact=id&&state.species.find(sp=>sp.id===id);
  $("searchInput").value=exact?exact.id:(params.get("family")||params.get("q")||"");
  renderResults(true);
  if(exact){
    const target=document.getElementById("species");
    if(target)target.scrollIntoView({block:"start"});
  }
}
function updateSearchURL(){
  const url=new URL(location.href);
  url.searchParams.delete("species");url.searchParams.delete("family");
  const q=$("searchInput").value.trim();
  if(q)url.searchParams.set("q",q);else url.searchParams.delete("q");
  history.replaceState({q},"",url);
}
$("searchInput").addEventListener("input",()=>{updateSearchURL();renderResults(true)});
$("clearSearch").addEventListener("click",()=>{
  $("searchInput").value="";updateSearchURL();renderResults(true);$("searchInput").focus();
});
window.addEventListener("popstate",()=>{if(state.species.length)restoreSearchFromURL()});
$("moreResults").addEventListener("click",()=>{state.shown+=48;renderResults(false)});
$("familyFilter").addEventListener("input",renderFamilies);
start();
