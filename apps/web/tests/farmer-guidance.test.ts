import {describe, expect, it} from 'vitest';
import {adviserSummaryBn, farmerGuidance, farmerGuidancePhrases, initialFarmerContext, scoutingSource} from '../src/lib/farmer-guidance';
import type {DoctorScreening, FarmerContext} from '../src/lib/types';

const leaf: NonNullable<DoctorScreening['assessment']> = {
  outcome: 'possible_condition', subject: 'Tomato leaf', part: 'leaf', crop_match: 'match',
  condition: 'Early blight', marker: 'concentric_rings', distinguishing_sign: 'Rings inside the spots.',
  signs: ['Dark circular spots on the leaf.'], explanation: '', uncertainty: '', next_steps: [],
};
const base: DoctorScreening = {
  crop: 'tomato', status: 'completed', assessment: leaf, screening_locale: 'en',
  quality_flags: [], classification: {abstained: false, score: null, score_type: 'not_available', top_label: 'Early blight', alternatives: []},
  model: {version: 'test', available: true, field_validated: false, labels: [], metrics: null, limitations: []},
  advice: [], disclaimer: '', meta: {mode: 'test', source_name: 'test', is_simulated: false},
};
const forContext = (c: Partial<FarmerContext>, a: Partial<typeof leaf> = {}): DoctorScreening => ({
  ...base, farmer_context: {...initialFarmerContext, ...c}, assessment: {...leaf, ...a},
});

describe('farmer actions', () => {
  it('changes the scouting action for both answers on each path', () => {
    const leafChecks = (c: Partial<FarmerContext>) => farmerGuidance(forContext(c), 'en').checks;
    expect(leafChecks({onset: 'today', extent: 'one'})[0]).toMatch(/today/);
    expect(leafChecks({onset: 'week_plus', extent: 'one'})[0]).toMatch(/newer leaves/);
    expect(leafChecks({onset: 'week_plus', extent: 'many'})[1]).toMatch(/wide photo/);
    const produceAdvice = (c: Partial<FarmerContext>) => farmerGuidance(forContext(
      {kind: 'produce', ...c}, {part: 'produce', produce_finding: 'bruise_or_wound'}), 'en');
    const one = produceAdvice({location: 'storage', extent: 'one'});
    const many = produceAdvice({location: 'storage', extent: 'many'});
    expect(one.action).toMatch(/one that looks sound/);
    expect(many.action).toMatch(/estimate how many/);
    expect(one.checks.join(' ')).toMatch(/damaged area.*stored batch/);
    expect(produceAdvice({location: 'field', extent: 'one'}).checks.join(' ')).toMatch(/in the field/);
  });

  it('offers specific scouting only for a matching crop, label and ring evidence', () => {
    expect(farmerGuidance(base, 'en').source).toMatch(/early-blight/);
    for (const patch of [{crop_match: 'unknown'}, {marker: 'nonspecific'}, {distinguishing_sign: null}, {condition: 'Not early blight'}] as const) {
      expect(farmerGuidance(forContext({}, patch), 'en').source).toBe(scoutingSource);
    }
    expect(farmerGuidance({...base, crop: 'auto'}, 'en').source).toBe(scoutingSource);
  });

  it('sets aside field answers when a different part appears or the subject is unclear', () => {
    const different = farmerGuidance(forContext({kind: 'produce', location: 'storage'}, {part: 'leaf'}), 'en');
    expect(different.action).toMatch(/fruit, vegetable or tuber/);
    expect(different.checks).toEqual([]);
    expect(different.refer).toBe(true);
    for (const patch of [{part: 'unknown'}, {part: 'other'}, {outcome: 'unrelated'}, {crop_match: 'mismatch'}] as const) {
      const advice = farmerGuidance(forContext({onset: 'days'}, patch), 'en');
      expect(advice.checks).toEqual([]);
      expect(advice.refer).toBe(true);
    }
  });

  it('retains uncertainty and responds to extent even for a clear-looking photo', () => {
    expect(farmerGuidance(forContext({extent: 'one'}, {outcome: 'uncertain'}), 'bn').refer).toBe(true);
    expect(farmerGuidance(forContext({extent: 'one'}, {outcome: 'no_visible_damage'}), 'bn').refer).toBe(false);
    expect(farmerGuidance(forContext({extent: 'several'}, {outcome: 'no_visible_damage'}), 'bn').refer).toBe(true);
    expect(farmerGuidance(forContext({}, {part: 'leaf', condition: null}), 'en').refer).toBe(true);
  });

  it('keeps text playable in either language with no case text in the speech', () => {
    const result = forContext({kind: 'produce', location: 'storage', extent: 'many'}, {part: 'produce', produce_finding: 'internal_breakdown'});
    for (const locale of ['bn', 'en'] as const) {
      const advice = farmerGuidance(result, locale);
      for (const text of [advice.action, ...advice.checks, advice.reason]) {
        expect(farmerGuidancePhrases.some(phrase => phrase[locale] === text)).toBe(true);
      }
      expect(advice.speech).toBe([advice.action, ...advice.checks, advice.reason].join(' '));
    }
  });
});

describe('Bangla adviser summary', () => {
  it('distinguishes farmer answers and recorded visual evidence in an English case', () => {
    const summary = adviserSummaryBn(forContext({kind: 'produce', location: 'storage', extent: 'several'}, {part: 'produce', produce_finding: 'surface_mold'}));
    for (const detail of ['টমেটো', 'কবে প্রথম দেখেছি তা লেখা নেই', 'সংরক্ষণ', 'কয়েকটি নমুনায়', 'ছাঁচের মতো আবরণ']) {
      expect(summary).toContain(detail);
    }
    expect(summary).not.toContain('Dark circular spots');
    expect(adviserSummaryBn(forContext({onset: 'today', extent: 'one'}))).toContain('আজ প্রথম খেয়াল করেছি।');
  });

  it('retains the original sign when the pattern has no trusted Bangla equivalent', () => {
    const summary = adviserSummaryBn(forContext({}, {marker: 'nonspecific', condition: null}));
    expect(summary).toContain('ছবির মূল বিবরণে লেখা আছে');
    expect(summary).toContain(leaf.signs[0]);
    expect(summary).not.toContain('বলয়');
  });

  it('preserves Bengali signs and distinguishes the model subject from a crop selection', () => {
    const result = {...base, crop: 'auto', assessment: {...leaf, signs: ['বোঁটার পাশে কালো দাগ।']}};
    const summary = adviserSummaryBn(result);
    expect(summary).toContain('ফসলের পরিচয় লেখা হয়েছে “টমেটো”');
    expect(summary).toContain('বোঁটার পাশে কালো দাগ।');
    expect(summary).not.toContain('বেছে নিয়েছি');
  });

  it('supplies a usable legacy summary without inventing answers, leaf signs or diagnoses', () => {
    const saved = {...base, assessment: undefined};
    expect(farmerGuidance(saved, 'en').checks).toEqual([]);
    expect(farmerGuidance(saved, 'bn').refer).toBe(true);
    expect(adviserSummaryBn(saved)).toMatch(/কতগুলোতে লক্ষণ আছে তা জানা নেই.*লক্ষণের বিবরণ লেখা নেই/);
    expect(adviserSummaryBn(saved)).not.toMatch(/বলয়|আগাম ধসা/);
  });
});
