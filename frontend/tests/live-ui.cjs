/* Live Chrome checks. Starts no servers; creates QA records and uses real model calls. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const base = new URL(process.env.DECISIONMESH_UI_URL || 'http://127.0.0.1:5173/#/').origin;
const stamp = Date.now();
const outputDir = path.resolve(process.env.LIVE_UI_OUTPUT_DIR || path.join(__dirname, '../../data/ui-tests', String(stamp)));
fs.mkdirSync(outputDir, {recursive:true});
const reportPath = path.join(outputDir, 'results.json');
const marker = `DecisionMesh live QA ${stamp}`;
const entityId = `qa-live-${stamp}`;
const report = {url:base, marker, entityId, startedAt:new Date().toISOString(), checks:[], pageErrors:[], consoleErrors:[], artifacts:[]};
let browser, page;
const save = () => fs.writeFileSync(reportPath, JSON.stringify(report,null,2));
const pass = (name, detail) => {report.checks.push({name,detail});save();console.log('PASS '+name+(detail?' '+JSON.stringify(detail):''));};
const api = async (path, data, expected=200) => {const response = data === undefined ? await page.request.get(base+path) : await page.request.post(base+path,{data}); assert.equal(response.status(),expected,`${path}: ${await response.text()}`); return response.json();};
const screenshot = async (name) => {const path= require('node:path').join(outputDir, `${name}.png`);await page.screenshot({path,fullPage:true});report.artifacts.push(path);save();};
async function waitJob(id, maxSeconds=1800) {
 let last='';
 for(let poll=0;poll<maxSeconds/2;poll++) {
  const job=await api(`/api/research/jobs/${id}`);
  const recent=job.progress.at(-1); const text=`${job.status}: ${recent?.stage||'waiting'} ${recent?.agent||recent?.agent_id||''} ${recent?.scenario||''}`;
  if(text!==last){console.log('JOB '+id.slice(0,8)+' '+text);last=text;}
  if(job.status!=='running')return job;
  await new Promise(resolve=>setTimeout(resolve,2000));
 }
 throw Error(`Job ${id} did not finish before test deadline`);
}
(async()=>{
 browser=await chromium.launch({headless:true,channel:process.env.PLAYWRIGHT_CHANNEL || 'chrome'});
 page=await browser.newPage({viewport:{width:1440,height:1000}});page.setDefaultTimeout(20000);
 page.on('response', response=>{if(response.status()>=400)console.log('HTTP_ERROR '+response.status()+' '+response.url())});
 page.on('pageerror',error=>{report.pageErrors.push(error.message);save();console.log('PAGE_ERROR '+error.message)});
 page.on('console',message=>{if(message.type()==='error'){report.consoleErrors.push(message.text());save();console.log('CONSOLE_ERROR '+message.text())}});
 await page.goto(base+'/#/',{waitUntil:'networkidle'});
 const health=await api('/api/health');assert.equal(health.llm_online,true);report.model=health.default_model||health.models[0];
 pass('Live application and model discovery',{model:report.model});
 assert.equal(await page.locator('nav a').count(),5);
 const samples=page.getByRole('group',{name:'Try a sample scenario'}).getByRole('button');assert.equal(await samples.count(),6);const scenarios=new Set();
 for(let index=0;index<6;index++){await samples.nth(index).click();scenarios.add(await page.locator('#scenario').inputValue());}assert.equal(scenarios.size,6);pass('Six editable scenario presets');
 // Exercise agent CRUD entirely through the live UI.
 const agentName=`QA reviewer ${stamp}`;
 await page.getByRole('button',{name:'＋ Add agent',exact:true}).click();
 await page.locator('#agent-name').fill(agentName);await page.locator('#agent-role').fill('Customer impact');await page.locator('#agent-instructions').fill('Assess customer impact using only supplied facts and label assumptions.');
 await page.getByRole('button',{name:/Add to agent team/}).click();await page.getByRole('dialog').waitFor({state:'hidden'});
 await page.getByRole('button',{name:`Edit ${agentName}`,exact:true}).click();await page.locator('#agent-role').fill('Customer continuity');await page.getByRole('button',{name:/Save specialist/}).click();await page.getByRole('dialog').waitFor({state:'hidden'});
 await page.getByRole('button',{name:`Remove ${agentName}`,exact:true}).click();await page.getByRole('button',{name:`Remove ${agentName}`,exact:true}).waitFor({state:'detached'});pass('Agent creation, editing, and removal');
 // Seven real roles, explicit human checkpoint, persisted feedback and final brief.
 await page.locator('#scenario').fill(`${marker}. A supplier outage leaves 40 inventory units against demand of 140 units. Daily production capacity is 60 units; backup capacity is 60 units. Normal unit cost is 5, backup unit cost is 15, and remaining budget is 1500. Compare continuity, cost, risk, and policy. This is a hypothetical local simulation.`);
 await page.getByRole('checkbox',{name:'Require human review'}).check();
 await page.getByRole('button',{name:/Run decision workflow/}).click();console.log('RUN seven-agent workflow started');
 await page.getByRole('dialog',{name:/Your judgment/}).waitFor({timeout:600000});
 assert.equal(await page.locator('.finding-card.is-final').count(),0);
 let history=await api(`/api/runs?search=${encodeURIComponent(marker)}`);assert.equal(history.total,1);report.runId=history.items[0].id;
 let saved=await api(`/api/runs/${report.runId}`);assert.equal(saved.status,'awaiting_review');assert.equal(saved.agents.length,7);assert.equal(saved.executions.filter(e=>e.status==='complete').length,6);
 await screenshot('review-desktop');pass('Real seven-role workflow pauses before synthesis',{runId:report.runId});
 await page.locator('#review-feedback').fill('Prioritize customer delivery commitments. Stay within the 1500 budget and explicitly discuss the premium for backup supply.');
 await page.getByRole('button',{name:'Generate final brief →',exact:true}).click();
 await page.locator('.finding-card.is-final').waitFor({timeout:180000});saved=await api(`/api/runs/${report.runId}`);assert.equal(saved.status,'complete');assert.equal(saved.executions.filter(e=>e.status==='complete').length,7);assert.match(saved.review_feedback,/Prioritize customer delivery/);pass('Human suggestions persist and real final synthesis completes');
 await page.getByRole('link',{name:'Run history',exact:true}).click();await page.locator('#history-search').fill(marker);await page.getByRole('button',{name:new RegExp(marker)}).waitFor();pass('Saved run searchable in live history');
 await page.goto(base+'/#/analytics',{waitUntil:'networkidle'});await page.getByRole('heading',{name:'Agent-by-agent performance',exact:true}).waitFor();await page.locator('#analytics-period').selectOption('0');await screenshot('analytics');pass('Analytics and all-time filter render');
 // Create a dedicated twin using live React controls.
 await page.getByRole('link',{name:'Enterprise lab',exact:true}).click();
 await page.getByText('Create an inventory twin',{exact:true}).click();
 const creator=page.locator('.entity-creator');await creator.getByLabel('Entity ID',{exact:true}).fill(entityId);await creator.getByLabel('Name',{exact:true}).fill(`Live UI QA warehouse ${stamp}`);
 await creator.getByRole('button',{name:'Create twin',exact:true}).click();await page.getByRole('button',{name:'Supplier disruption',exact:true}).waitFor();
 await page.getByRole('button',{name:'Supplier disruption',exact:true}).click();await page.getByRole('region',{name:'Digital twin · compare candidate outcomes',exact:true}).waitFor();
 let snapshot=await api(`/api/enterprise/entities/${entityId}`);assert.equal(snapshot.entity.version,1);report.caseId=snapshot.cases[0].id;assert.equal(snapshot.cases[0].candidates.length,4);pass('Live entity creation, ingestion, state version, and twin outcomes');
 // Real proposal exchange and automatic arbitration, while navigation remains usable.
 const negotiationResponse=page.waitForResponse(response=>response.url().includes(`/cases/${report.caseId}/negotiate`)&&response.request().method()==='POST');
 await page.getByRole('button',{name:'Run agent negotiation →',exact:true}).click();let response=await negotiationResponse;assert.equal(response.status(),202,await response.text());let negotiation=await response.json();report.negotiationId=negotiation.id;save();console.log('RUN real negotiation '+negotiation.id);
 await page.getByRole('link',{name:'Research',exact:true}).click();await page.getByRole('heading',{name:'Measure the decision.',exact:true}).waitFor();
 negotiation=await waitJob(negotiation.id);report.negotiationResult={status:negotiation.status,proposalCount:negotiation.progress.filter(e=>e.stage==='proposal').length,errors:negotiation.progress.filter(e=>e.stage==='invalid_proposal'||e.stage==='agent_error')};save();
 assert.equal(negotiation.status,'complete',negotiation.error);assert.ok(report.negotiationResult.proposalCount>=2,'Model did not supply enough valid structured proposals');pass('Live Agno negotiation and navigation persistence',report.negotiationResult);
 await page.getByRole('link',{name:'Enterprise lab',exact:true}).click();await page.getByRole('combobox',{name:/^Inventory twin/}).selectOption(entityId);
 await page.getByRole('combobox',{name:/^Saved decision/}).selectOption(report.caseId);
 await page.getByRole('region',{name:'Digital twin · compare candidate outcomes',exact:true}).waitFor();await page.getByText('Agent round 1',{exact:false}).first().waitFor();
 snapshot=await api(`/api/enterprise/entities/${entityId}`);const decision=snapshot.cases.find(c=>c.id===report.caseId);assert.ok(decision.rounds.length>=2);
 const chosen=decision.candidates.find(c=>c.action===decision.selected_action);assert.equal(chosen.violations.length,0);
 await page.getByLabel(decision.selected_action,{exact:true}).check();
 await page.getByLabel('Reviewer name',{exact:true}).fill('DecisionMesh live QA');await page.getByLabel('Reason for choosing this action',{exact:true}).fill('Accept the feasible service/cost trade-off in this isolated local test.');
 await page.getByRole('button',{name:`Approve ${decision.selected_action} simulation`,exact:true}).click();await page.getByRole('button',{name:new RegExp(`Execute approved ${decision.selected_action} locally`)}).waitFor();
 const executionResponse=page.waitForResponse(res=>res.url().includes(`/cases/${report.caseId}/execute`)&&res.request().method()==='POST');await page.getByRole('button',{name:new RegExp(`Execute approved ${decision.selected_action} locally`)}).click();response=await executionResponse;assert.equal(response.status(),200,await response.text());const receipt=await response.json();report.executionId=receipt.id;
 assert.equal(receipt.after_version,2);const again=await api(`/api/enterprise/cases/${report.caseId}/execute`,{approval_id:receipt.approval.id,idempotency_key:receipt.idempotency_key});assert.equal(again.id,receipt.id);
 snapshot=await api(`/api/enterprise/entities/${entityId}`);assert.equal(snapshot.entity.version,2);assert.ok(snapshot.cases.some(c=>c.id===receipt.feedback_case_id));pass('UI approval, simulated execution, idempotent retry, and feedback',{executionId:receipt.id});
 await page.getByRole('button',{name:'Open outcome reassessment →',exact:true}).first().click();await page.getByRole('region',{name:'Digital twin · compare candidate outcomes',exact:true}).waitFor();await screenshot('enterprise');
 // Real external event JSON via UI, including replay of the exact event.
 const event={event_id:`qa-${stamp}`,source:'live-ui-qa',entity_id:entityId,occurred_at:new Date().toISOString(),changes:{inventory:55},description:'Live QA inventory reconciliation'};
 await page.getByText('Ingest an external event as JSON',{exact:true}).click();await page.locator('#enterprise-event-json').fill(JSON.stringify(event));await page.getByRole('button',{name:'Ingest event',exact:true}).click();await page.getByText(/Inventory drift: predicted/).waitFor();
 let duplicate=await api('/api/enterprise/events',event);assert.equal(duplicate.duplicate,true);snapshot=await api(`/api/enterprise/entities/${entityId}`);assert.equal(snapshot.entity.version,3);
 const stale=await api('/api/enterprise/events',{...event,event_id:`stale-${stamp}`,occurred_at:new Date(Date.now()-48*3600000).toISOString()});assert.equal(stale.status,'rejected');
 await api(`/api/enterprise/cases/${report.caseId}/approvals`,{action:'defer',state_version:1,reviewer:'Live QA',rationale:'Stale decision must be rejected'},409);pass('External JSON ingestion, drift, duplicate protection, freshness, and stale approval rejection');
 // Mobile navigation and overflow on every actual page.
 await page.setViewportSize({width:390,height:844});
 for(const hash of ['#/','#/history','#/analytics','#/enterprise','#/research']){await page.goto(base+'/'+hash,{waitUntil:'networkidle'});assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth),true,`Horizontal overflow at ${hash}`);}
 await screenshot('research-mobile');await page.setViewportSize({width:1440,height:1000});pass('Mobile layout and all five navigation destinations');
 // Full six-scenario live-model benchmark initiated by the real UI.
 await page.goto(base+'/#/research',{waitUntil:'networkidle'});
 const benchmarkResponse=page.waitForResponse(res=>res.url().endsWith('/api/research/benchmarks')&&res.request().method()==='POST');
 await page.getByRole('button',{name:'Run live-model benchmark →',exact:true}).click();response=await benchmarkResponse;assert.equal(response.status(),202,await response.text());const created=await response.json();report.benchmarkId=created.id;save();console.log('RUN full benchmark '+created.id);
 await page.getByRole('link',{name:'Analytics',exact:true}).click();let benchmark=await waitJob(created.id);report.benchmarkStatus=benchmark.status;report.benchmarkSummary=benchmark.result?.summary;save();
 assert.equal(benchmark.status,'complete',benchmark.error);assert.equal(benchmark.result.trials.length,12);assert.equal(benchmark.result.summary.centralized.samples,6);assert.equal(benchmark.result.summary.orchestrated.samples,6);
 await page.getByRole('link',{name:'Research',exact:true}).click();await page.getByText('Completed trials: 12.',{exact:false}).waitFor();await page.locator('.benchmark-card').first().waitFor();await screenshot('research-results');
 await page.reload({waitUntil:'networkidle'});await page.getByRole('combobox',{name:/^Experiment/}).selectOption(created.id);await page.locator('.benchmark-card').first().waitFor();
 const exported=await api(`/api/research/jobs/${created.id}/export`);assert.equal(exported.result.trials.length,12);assert.ok(exported.config.dataset_hash);pass('Complete live-model benchmark, saved results, and JSON export',benchmark.result.summary);
 assert.deepEqual(report.pageErrors,[]);assert.deepEqual(report.consoleErrors,[]);pass('No uncaught browser JavaScript errors');report.completedAt=new Date().toISOString();save();console.log('LIVE_UI_COMPLETE '+JSON.stringify({checks:report.checks.length,runId:report.runId,negotiationId:report.negotiationId,benchmarkId:report.benchmarkId,report:reportPath}));
})().catch(async error=>{report.failure=String(error.stack||error);save();console.error(error);if(page)await screenshot('failure').catch(()=>{});process.exitCode=1;}).finally(async()=>{await browser?.close()});
