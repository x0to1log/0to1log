// frontend/tests/news-bold-normalize.test.mjs
import assert from 'node:assert/strict';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const { normalizeNewsBold, isLongBold } = await import(pathToFileURL(path.join(here, '../src/lib/newsBold.js')).href);

const eq = (input, expected, label) => assert.equal(normalizeNewsBold(input), expected, label);

// 짧은 용어는 <strong>으로 바뀐다. 한글이 바로 붙어도 깨지지 않는다.
eq('성공률은 **46%**다.', '성공률은 <strong>46%</strong>다.', 'short bold glued to Hangul');
eq('**Microsoft**가 발표했다.', '<strong>Microsoft</strong>가 발표했다.', 'short bold at line start');
eq('**작업당 비용은 2% 미만**이라고 밝힌다.', '<strong>작업당 비용은 2% 미만</strong>이라고 밝힌다.', 'short phrase stays bold');

// 문장 통째로 굵은 것은 보통 글씨로 푼다.
eq(
  '**Microsoft가 소프트웨어 개발, 사이버보안, 이미지 생성, 음성 처리 등에 쓰는 AI 모델 7종을 공개한다.** 공식 발표다.',
  'Microsoft가 소프트웨어 개발, 사이버보안, 이미지 생성, 음성 처리 등에 쓰는 AI 모델 7종을 공개한다. 공식 발표다.',
  'whole-sentence bold is unwrapped',
);

// 운영 화면에서 깨져 보이던 실제 문장: 긴 굵은 글씨라 풀리고 ** 가 남지 않는다.
const broken = '무개입 성공률은 **46%인 반면, AI 서비스를 실행하는 코드 작성의 성공률은 25%**다.';
assert(!normalizeNewsBold(broken).includes('**'), 'no literal ** left in the production case');

// 한 줄에 여러 쌍
eq('**A**와 **B**를 비교한다.', '<strong>A</strong>와 <strong>B</strong>를 비교한다.', 'two pairs on one line');

// 링크 전체가 굵으면 길이와 상관없이 굵게 남긴다.
eq(
  '**[아주 긴 라벨을 가진 링크 텍스트입니다 정말로](https://example.com/a/very/long/path)**는 유지된다.',
  '<strong>[아주 긴 라벨을 가진 링크 텍스트입니다 정말로](https://example.com/a/very/long/path)</strong>는 유지된다.',
  'bold link kept',
);

// 목록 라벨은 길이와 상관없이 굵게 남긴다.
eq(
  '- **비용 절감이 가장 큰 목표인 팀에서 예산을 다시 짜야 하는 조건이라면**: 정상 요금을 확인한다.',
  '- <strong>비용 절감이 가장 큰 목표인 팀에서 예산을 다시 짜야 하는 조건이라면</strong>: 정상 요금을 확인한다.',
  'long list label kept (colon)',
);
eq('- **46%** — 무개입 성공률. [1](https://example.com)', '- <strong>46%</strong> — 무개입 성공률. [1](https://example.com)', 'weekly number label kept (dash)');
eq('1. **첫째 조건**: 설명', '1. <strong>첫째 조건</strong>: 설명', 'ordered list label kept');

// 건드리지 않는 것
eq('가격은 `**not bold**` 그대로다.', '가격은 `**not bold**` 그대로다.', 'inline code untouched');
eq('수식 $$a**b$$ 는 그대로다.', '수식 $$a**b$$ 는 그대로다.', 'display math untouched');
eq('```\n**x**\n```', '```\n**x**\n```', 'fenced code untouched');
eq('~~~\n**x**\n~~~\n**y**', '~~~\n**x**\n~~~\n<strong>y</strong>', 'tilde fence untouched, text after it processed');
eq('짝이 없는 ** 하나', '짝이 없는 ** 하나', 'unpaired ** untouched');
eq('***굵은 기울임***은 그대로', '***굵은 기울임***은 그대로', 'triple asterisks untouched');
eq('이스케이프 \\*\\*x\\*\\* 는 그대로', '이스케이프 \\*\\*x\\*\\* 는 그대로', 'escaped asterisks untouched');
eq('** **', '** **', 'empty bold untouched');
eq('*기울임*은 그대로', '*기울임*은 그대로', 'single asterisks untouched');

// 여러 줄: 줄바꿈과 줄 수를 보존한다.
eq('**A**\n\n본문\n', '<strong>A</strong>\n\n본문\n', 'newlines preserved');
eq('', '', 'empty input');

// 판정 함수는 따로 내보낸다.
assert.equal(typeof isLongBold('x'), 'boolean', 'isLongBold returns a boolean');
assert.equal(isLongBold('GPT-6.1 Sol'), false, 'a product name is not long');
assert.equal(isLongBold('Microsoft가 소프트웨어 개발, 사이버보안, 이미지 생성, 음성 처리 등에 쓰는 AI 모델 7종을 공개한다.'), true, 'a full sentence is long');

console.log('news-bold-normalize.test.mjs passed');
