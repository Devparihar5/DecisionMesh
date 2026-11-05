import { Panel } from './Panel';
import { SCENARIOS } from '../data/scenarios';

interface Props {
  scenario: string;
  approval: boolean;
  running: boolean;
  awaitingReview: boolean;
  canRun: boolean;
  onScenario: (value: string) => void;
  onApproval: (value: boolean) => void;
  onRun: () => void;
  onCancel: () => void;
}

export function ScenarioComposer(props: Props) {
  return (
    <Panel index="01" title="Decision scenario" action={<span className="quiet-label">INPUT</span>}>
      <div className="scenario-templates" role="group" aria-label="Try a sample scenario">
        <span className="field-label">TRY A SCENARIO</span>
        <div>{SCENARIOS.map((sample) => <button key={sample.id} type="button" disabled={props.running || props.awaitingReview}
          aria-pressed={props.scenario === sample.scenario} title={sample.category} onClick={() => props.onScenario(sample.scenario)}>{sample.name}</button>)}</div>
      </div>
      <form onSubmit={(e) => { e.preventDefault(); if (props.canRun) props.onRun(); }}>
        <label className="field-label" htmlFor="scenario">WHAT’S HAPPENING?</label>
        <textarea id="scenario" value={props.scenario} disabled={props.running || props.awaitingReview} minLength={8} maxLength={6000} required
          placeholder="Describe an event, disruption, or decision that needs a coordinated response…"
          onChange={(e) => props.onScenario(e.target.value)} />
        <div className="scenario-footer">
          <span>{props.scenario.length} / 6000</span>
          <label className="toggle-wrap"><span>Require human review</span>
            <input type="checkbox" checked={props.approval} disabled={props.running || props.awaitingReview} onChange={(e) => props.onApproval(e.target.checked)} />
            <span className="toggle" aria-hidden="true" />
          </label>
        </div>
        {(props.running || props.awaitingReview)
          ? <button type="button" className="run-button cancel-button" onClick={props.onCancel}>■ Stop workflow</button>
          : <button className="run-button" disabled={!props.canRun}><span aria-hidden="true">▶</span>Run decision workflow<span className="shortcut">⌘ / Ctrl ↵</span></button>}
      </form>
    </Panel>
  );
}
