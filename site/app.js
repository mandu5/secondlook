// Recorded single trials; never a model call or a live estimate.
const cases = {
  jobs: {title: 'Job Radar · deadline truthfulness', before: '6 / 9', after: '9 / 9 checks', total: 9, cheapest: 'D',
    B: {cost: .0414374, tokens: 8642, calls: 1}, C: {cost: .0751372, tokens: 14298, calls: 2}, D: {cost: .034864, tokens: 5274, calls: 1}},
  ugv: {title: 'UGV-MON · truthful monitoring demo', before: '3 / 7', after: '7 / 7 checks', total: 7, cheapest: 'B',
    B: {cost: .0191834, tokens: 4214, calls: 1}, C: {cost: .0506852, tokens: 9526, calls: 2}, D: {cost: .033176, tokens: 4858, calls: 1}}
};
let selected = 'D';
let selectedCase = 'jobs';
const get = id => document.getElementById(id);
function render() {
  const data = cases[selectedCase];
  get('case-title').textContent = data.title;
  get('recorded-report').href = selectedCase === 'jobs' ? 'evidence/job/' : 'evidence/ugv/';
  get('baseline-score').textContent = data.before;
  get('candidate-score').textContent = data.after;
  document.querySelectorAll('[data-arm]').forEach(button => {
    const arm = button.dataset.arm;
    button.setAttribute('aria-pressed', String(arm === selected));
    get(`cost-${arm}`).textContent = `$${data[arm].cost.toFixed(4)}`;
  });
  get('tokens').textContent = data[selected].tokens.toLocaleString('en-US');
  get('calls').textContent = data[selected].calls;
  get('reading-note').textContent = `${data.cheapest} cost least on this task. All candidates passed the same ${data.total} checks. Selected ${selected}: $${data[selected].cost.toFixed(7)} API-equivalent.`;
}
document.querySelectorAll('[data-case]').forEach(button => button.addEventListener('click', () => {
  selectedCase = button.dataset.case;
  document.querySelectorAll('[data-case]').forEach(item => item.setAttribute('aria-pressed', String(item === button)));
  render();
}));
document.querySelectorAll('[data-arm]').forEach(button => button.addEventListener('click', () => { selected = button.dataset.arm; render(); }));
get('copy').addEventListener('click', async () => {
  try {
    await navigator.clipboard.writeText(get('commands').textContent);
    get('copy-status').textContent = 'Copied. After running, open first-look/report.html in your browser.';
  } catch {
    const range = document.createRange(); range.selectNodeContents(get('commands'));
    const selection = window.getSelection(); selection.removeAllRanges(); selection.addRange(range);
    get('copy-status').textContent = 'Commands selected. Use your browser’s copy command.';
  }
});
render();

// Frozen public synthetic fixture. Results are read from the saved report, not rerun here.
const checksReady = fetch('assets/demo-checks.json').then(response => {
  if (!response.ok) throw new Error('Check descriptions unavailable');
  return response.json();
});
// Catch immediately, including when no check is selected, to avoid an unhandled rejection.
checksReady.catch(() => { get('check-name').textContent = 'Check descriptions could not load. Open the interactive report below.'; });
let latestCheck = 0;
document.querySelectorAll('[data-check]').forEach(button => button.addEventListener('click', async () => {
  const request = ++latestCheck;
  try {
    const data = await checksReady;
    if (request !== latestCheck) return;
    const check = data.checks.find(item => item.id === button.dataset.check);
    if (!check) throw new Error('Unknown check');
    document.querySelectorAll('[data-check]').forEach(item => item.setAttribute('aria-pressed', String(item === button)));
    document.querySelectorAll('[data-branch]').forEach(path => path.classList.toggle('branch-selected', path.dataset.branch === check.id));
    get('check-name').textContent = check.name;
    get('check-result').textContent = `Original: ${check.originalPassed ? 'pass' : 'fail'}. Hand-authored reference: ${check.referencePassed ? 'pass' : 'fail'}.${check.held_out ? ' Held-out check.' : ''}`;
    get('assertion-content').textContent = JSON.stringify(check.assert, null, 2);
    get('check-assertion').hidden = false;
    document.querySelector('.check-detail').classList.add('selected');
  } catch {
    get('check-name').textContent = 'Check descriptions could not load. Open the interactive report below.';
  }
}));
