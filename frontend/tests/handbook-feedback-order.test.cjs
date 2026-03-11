const fs = require('fs');
const path = require('path');

const root = process.cwd();
const file = fs.readFileSync(path.join(root, 'frontend/src/components/newsprint/HandbookFeedback.astro'), 'utf8');

const confusingIdx = file.indexOf("handbook-feedback-btn handbook-feedback-btn--confusing");
const helpfulIdx = file.indexOf("handbook-feedback-btn handbook-feedback-btn--helpful");

if (confusingIdx === -1 || helpfulIdx === -1) {
  throw new Error('Missing handbook feedback buttons');
}

if (!(confusingIdx < helpfulIdx)) {
  throw new Error('Expected confusing button to appear before helpful button');
}

console.log('handbook-feedback-order.test.cjs passed');
