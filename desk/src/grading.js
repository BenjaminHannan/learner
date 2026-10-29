'use strict';
const fs = require('fs'), path = require('path'), crypto = require('crypto');
// Dev: repo/desk/src -> repo/sleepmlx. Packaged: resources/app/src -> resources/sleepmlx.
const historicalServedPolicy = Object.freeze({ general_n: 8, max_general_loss: 1, held_max: 12 });
let contract = null, binding = null, error = '';
try {
  const bytes = fs.readFileSync(path.join(__dirname, '../../sleepmlx/grading-contract.json'));
  contract = JSON.parse(bytes);
  if (contract.version !== 1 || typeof contract.grader !== 'string' || !/^strict-[1-9][0-9]*$/.test(contract.grader) || contract.head_words !== 12 ||
      !contract.served || Object.keys(contract.served).length !== 3 || contract.served.general_n !== 8 || contract.served.max_general_loss !== 1 || contract.served.held_max !== 12) throw Error('Unsupported grading contract.');
  binding = Object.freeze({ grader: contract.grader, grading_contract_sha256: crypto.createHash('sha256').update(bytes).digest('hex') });
  Object.freeze(contract.served); Object.freeze(contract);
} catch (failure) { contract = null; error = 'Grading contract is unavailable: ' + failure.message; }
const available = !!contract;
const servedPolicy = available ? contract.served : historicalServedPolicy;
const current = verdict => available && !!verdict && Object.entries(binding).every(([key, value]) => verdict[key] === value);
function validMetrics(verdict, heldCount) {
  if (!verdict || !Number.isInteger(heldCount) || heldCount < 1 || heldCount > servedPolicy.held_max ||
      !Number.isInteger(verdict.general_n) || verdict.general_n !== servedPolicy.general_n ||
      !Number.isInteger(verdict.held_n) || verdict.held_n !== heldCount) return false;
  return [['general_on', verdict.general_n], ['general_off', verdict.general_n], ['held_on', heldCount], ['held_off', heldCount]]
    .every(([key, count]) => Number.isInteger(verdict[key]) && verdict[key] >= 0 && verdict[key] <= count);
}
const passes = verdict => verdict.general_on >= verdict.general_off - servedPolicy.max_general_loss &&
  verdict.general_on * 2 >= verdict.general_off && verdict.held_on >= verdict.held_off;
const validDecision = (verdict, heldCount) => current(verdict) && validMetrics(verdict, heldCount) &&
  typeof verdict.ok === 'boolean' && !Object.hasOwn(verdict, 'failure_kind') && (!Object.hasOwn(verdict, 'pending') || verdict.pending === false) && verdict.ok === passes(verdict);
module.exports = { contract, binding, available, error, servedPolicy, current, validMetrics, passes, validDecision };
