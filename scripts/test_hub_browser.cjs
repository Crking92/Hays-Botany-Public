"use strict";
const assert=require("node:assert/strict");
const fs=require("node:fs");
const {chromium}=require("playwright");

const URL="https://crking92.github.io/Hays-Botany-Public/";
const results=[];
async function check(name,fn){
  try{await fn();results.push({test:name,result:"PASS"});console.log("PASS",name)}
  catch(error){console.error("FAIL",name,error);throw error}
}
async function load(page,url=URL){
  await page.goto(url,{waitUntil:"domcontentloaded",timeout:45000});
  await page.waitForFunction(()=>document.querySelector("#speciesCount")?.textContent?.includes("1,191"),null,{timeout:45000});
  await page.locator(".result").first().waitFor();
}
async function run(){
  const browser=await chromium.launch({headless:true});
  try{
    for(const width of [320,390,768,1280]){
      const page=await browser.newPage({viewport:{width,height:844},deviceScaleFactor:1});
      await check("initial site + no horizontal overflow at "+width,async()=>{
        await load(page);
        const size=await page.evaluate(()=>({
          visible:document.documentElement.clientWidth,
          content:document.documentElement.scrollWidth,
          count:document.querySelectorAll("#collectionsGrid .collectioncard").length,
          familyCount:document.querySelectorAll("#familiesGrid .familycard").length
        }));
        assert.equal(size.count,10);
        assert.equal(size.familyCount,146);
        assert(size.content<=size.visible+2,JSON.stringify(size));
      });
      if(width===390){
        await check("common-name search leads to correct Fabaceae deep link",async()=>{
          await page.locator("#searchInput").fill("leadplant");
          await page.waitForFunction(()=>document.querySelector("#resultSummary")?.textContent?.includes("matching species"));
          const link=page.locator("#results a.result[href*='amorpha-canescens']").first();
          assert(await link.count()>0);
          assert.match(await link.getAttribute("href"),/Hays-Botany-Fabaceae\/site\/\?species=amorpha-canescens/);
          assert.match(await link.textContent(),/Leadplant/i);
        });
        await check("common-name grass search retains original website fallback",async()=>{
          await page.locator("#searchInput").fill("little bluestem");
          const link=page.locator("#results a.result[href*='schizachyrium-scoparium']").first();
          assert(await link.count()>0);
          const href=await link.getAttribute("href");
          assert(href.startsWith("https://crking92.github.io/Hays-County-Botany/"),href);
        });
        await check("family button and browser Back restore previous search",async()=>{
          await page.locator("#searchInput").fill("");
          await page.locator("#familyFilter").fill("Fabaceae");
          const card=page.locator("#familiesGrid .familycard").first();
          assert.equal(await page.locator("#familiesGrid .familycard").count(),1);
          await card.click();
          assert.equal(await page.locator("#searchInput").inputValue(),"Fabaceae");
          assert.equal(new URL(page.url()).searchParams.get("family"),"Fabaceae");
          await page.goBack({waitUntil:"domcontentloaded"});
          await page.waitForFunction(()=>document.querySelector("#searchInput")?.value==="");
          assert.equal(await page.locator("#searchInput").inputValue(),"");
        });
        await check("direct hub species link selects the target species",async()=>{
          await load(page,URL+"?species=achillea-millefolium");
          assert.equal(await page.locator("#searchInput").inputValue(),"achillea-millefolium");
          const target=page.locator("#results a.result[href*='achillea-millefolium']").first();
          assert(await target.count()>0);
          assert.match(await target.getAttribute("href"),/Hays-Botany-Asteraceae\/site\/\?species=achillea-millefolium/);
        });
        fs.mkdirSync("test-artifacts",{recursive:true});
        await page.screenshot({path:"test-artifacts/hub-mobile-390.png"});
      }
      if(width===1280){
        await check("desktop scientific-name lookup",async()=>{
          await page.locator("#searchInput").fill("Amorpha canescens");
          assert(await page.locator("#results a.result[href*='amorpha-canescens']").count()>0);
          fs.mkdirSync("test-artifacts",{recursive:true});
          await page.screenshot({path:"test-artifacts/hub-desktop-1280.png"});
        });
      }
      await page.close();
    }
    console.log(JSON.stringify({status:"PASS",tests:results.length,results},null,2));
  }finally{await browser.close()}
}
run().catch(e=>{console.error(e);process.exitCode=1});
