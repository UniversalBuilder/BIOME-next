// Run against a fresh synthetic_fixture project. Does not save or delete project data.
const {chromium}=require(process.env.BIOME_PLAYWRIGHT || 'playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const target=process.argv[2];
if(!target)throw Error('Usage: node tools/check_interface.cjs http://127.0.0.1:PORT/ (synthetic fixture only)');
const origin=new URL(target).origin+'/';
const captures=path.resolve(__dirname,'../test-tmp/interface');fs.mkdirSync(captures,{recursive:true});
(async()=>{
const browser=await chromium.launch({headless:true,...(process.env.BIOME_CHROMIUM ? {executablePath:process.env.BIOME_CHROMIUM} : {})});
const page=await browser.newPage({viewport:{width:1440,height:1000}});const errors=[],requests=[];
page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>requests.push(r.url()));
await page.goto(origin);await page.locator('#metric-total').filter({hasText:'1'}).waitFor();await page.evaluate(()=>document.fonts.ready);
assert(await page.evaluate(()=>document.fonts.check('400 14px "Biome Sans"')));assert.equal(await page.locator('#open-help').count(),0);assert.equal(await page.locator('#help-view').count(),0);
await page.screenshot({path:path.join(captures,'biome-next-polished-projects.png'),fullPage:true});
await page.locator('#new-project').hover();await page.waitForTimeout(550);assert(await page.locator('#action-tooltip').isVisible());assert.match(await page.locator('#action-tooltip').textContent(),/formulaire de création/);assert.equal(await page.locator('#new-project').getAttribute('aria-describedby'),'action-tooltip');
await page.locator('#action-tooltip').hover();assert(await page.locator('#action-tooltip').isVisible());await page.keyboard.press('Escape');assert(!await page.locator('#action-tooltip').isVisible());
await page.locator('#context-help').click();assert(await page.locator('#page-help-dialog').isVisible());assert.equal(await page.locator('#page-help-title').textContent(),'Retrouver et commencer un projet');await page.screenshot({path:path.join(captures,'biome-next-polished-help.png')});await page.keyboard.press('Escape');assert(!await page.locator('#page-help-dialog').isVisible());assert.equal(await page.evaluate(()=>document.activeElement.id),'context-help');
await page.locator('#new-project').click();await page.locator('#new-title').fill('Brouillon conservé');await page.locator('#context-help').click();assert.equal(await page.locator('#page-help-title').textContent(),'Créer le dossier du projet');await page.locator('#page-help-close').click();assert.equal(await page.locator('#new-title').inputValue(),'Brouillon conservé');await page.locator('#cancel-project').click();
await page.locator('.project-link').hover();await page.waitForTimeout(550);assert.match(await page.locator('#action-tooltip').textContent(),/Ouvrir le cahier/);await page.locator('.project-link').click();await page.locator('#project-workspace').waitFor({state:'visible'});
await page.locator('#tab-files').click();await page.locator('#context-help').click();assert.equal(await page.locator('#page-help-title').textContent(),'Distinguer fichiers et données');await page.locator('#page-help-close').click();assert(await page.locator('#panel-files').isVisible());await page.screenshot({path:path.join(captures,'biome-next-polished-files.png'),fullPage:true});
await page.locator('#tab-deliveries').click();await page.locator('#context-help').click();assert.equal(await page.locator('#page-help-title').textContent(),'Figer une version à transmettre');await page.locator('#page-help-close').click();
await page.locator('#nav-projects').click();await page.locator('#context-help').focus();await page.keyboard.press('Tab');await page.waitForTimeout(350);assert.equal(await page.evaluate(()=>document.activeElement.id),'new-project');assert(await page.locator('#action-tooltip').isVisible());await page.keyboard.press('Escape');
await page.setViewportSize({width:1100,height:850});assert(await page.locator('.project-list .table-wrap').evaluate(el=>el.scrollWidth<=el.clientWidth+1));
await page.setViewportSize({width:390,height:844});await page.screenshot({path:path.join(captures,'biome-next-polished-mobile.png'),fullPage:true});assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));await page.locator('#context-help').click();await page.screenshot({path:path.join(captures,'biome-next-polished-help-mobile.png')});assert(await page.locator('#page-help-dialog').evaluate(el=>el.getBoundingClientRect().right<=innerWidth));await page.locator('#page-help-close').click();
assert.deepEqual(errors,[]);assert(!requests.some(url=>!url.startsWith(origin)));console.log('PASS: embedded font, mouse/keyboard/dynamic tooltips, hover persistence, Escape, modal focus return, contextual content, unsaved draft, project tabs, table width and mobile layout.');await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
