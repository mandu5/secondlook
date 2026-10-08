// Recorded single trials; never a model call or a live estimate.
const cases = {
  jobs: {title: 'Job Radar · deadline truthfulness', before: '6 / 9', after: '9 / 9 checks', total: 9, cheapest: 'D',
    B: {cost: .0414374, tokens: 8642, calls: 1}, C: {cost: .0751372, tokens: 14298, calls: 2}, D: {cost: .034864, tokens: 5274, calls: 1}},
  ugv: {title: 'UGV-MON · truthful monitoring demo', before: '3 / 7', after: '7 / 7 checks', total: 7, cheapest: 'B',
    B: {cost: .0191834, tokens: 4214, calls: 1}, C: {cost: .0506852, tokens: 9526, calls: 2}, D: {cost: .033176, tokens: 4858, calls: 1}}
};
let selected = 'D';
const get = id => document.getElementById(id);
function render() {
  const data = cases[get('case').value];
  get('case-title').textContent = data.title;
  get('recorded-report').href = get('case').value === 'jobs' ? 'evidence/job/' : 'evidence/ugv/';
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
get('case').addEventListener('change', render);
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
