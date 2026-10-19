// Exercise the validation actually used by the browser save form, not a copy.
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const page = fs.readFileSync(path.join(__dirname, 'index.html'), 'utf8');
const start = page.indexOf('const files=selectedFiles.map(x=>x.file);');
const end = page.indexOf('const attachments=await', start);
assert(start >= 0 && end > start, 'Notebook save validation must be identifiable');
const validate = new Function('selectedFiles', page.slice(start, end));
const file = (name, size) => ({file: {name, size}});
assert.doesNotThrow(() => validate([
  file('exchange.msg', 17995264), file('screenshot.png', 6078093),
  ...Array.from({length: 7}, (_, i) => file(`screenshot-${i}.png`, 1000000)),
]));
assert.doesNotThrow(() => validate([file('EXCHANGE.MSG', 50000000), file('image.png', 10000000)]));
assert.throws(() => validate([file('exchange.msg', 50000001)]));
assert.throws(() => validate([file('image.png', 10000001)]));
assert.throws(() => validate(Array.from({length: 101}, () => file('image.png', 1))));
assert.throws(() => validate([file('one.msg', 50000000), file('two.eml', 50000000), file('image.png', 1)]));
console.log('Notebook browser save validation: large email and screenshots accepted; boundaries enforced.');
