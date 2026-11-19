import type {Locale} from './messages';
import type {DoctorScreening, FarmerContext} from './types';

export const initialFarmerContext: FarmerContext = {
  kind: 'leaf', onset: 'unknown', location: 'unknown', extent: 'unknown',
};

export const adviserSource = 'https://ais.gov.bd/pages/static-pages/6922df5e933eb65569e21833';
export const scoutingSource = 'https://extension.umn.edu/agriculture/specialty-crops/diagnostic-help-for-fruit-and-vegetable-farmers';
const blightSource = 'https://extension.umn.edu/agriculture/specialty-crops/vegetable-farming/disease-management/early-blight-in-tomato-and-potato';

type Phrase = {en: string; bn: string};
const phrase = (en: string, bn: string): Phrase => ({en, bn});

// Share the wording between the screen and the local speech clips.
const words = {
  retry: phrase('Take a clear photo of the part that concerns you in daylight.', 'যে অংশটি নিয়ে চিন্তা হচ্ছে, দিনের আলোয় তার পরিষ্কার ছবি তুলুন।'),
  showLeaf: phrase('Take a close photo of the leaf you meant to check.', 'যে পাতাটি পরীক্ষা করতে চান, সেটির কাছ থেকে ছবি তুলুন।'),
  showProduce: phrase('Take a close photo of the fruit, vegetable or tuber you meant to check.', 'যে ফল, সবজি বা কন্দটি পরীক্ষা করতে চান, সেটির কাছ থেকে ছবি তুলুন।'),
  different: phrase('The photo and the part you selected do not match.', 'ছবির সঙ্গে আপনার বেছে নেওয়া অংশটি মিলছে না।'),
  wrongCrop: phrase('The crop in the photo could not be matched to your selection.', 'ছবির ফসলটি আপনার বেছে নেওয়া ফসলের সঙ্গে মেলানো যায়নি।'),
  unclear: phrase('The photo gives too little detail to identify the problem.', 'ছবি দেখে সমস্যাটি বোঝার মতো যথেষ্ট তথ্য পাওয়া যায়নি।'),
  followConcern: phrase('If you still see damage, photograph that exact spot.', 'ক্ষতি চোখে পড়লে ঠিক সেই জায়গার ছবি তুলুন।'),
  notSeen: phrase('The screening found no obvious damage in this view.', 'ছবিতে স্পষ্ট ক্ষতি ধরা পড়েনি।'),
  legacy: phrase('This screening has no written description of visible signs.', 'এই পরীক্ষায় ছবির লক্ষণগুলোর বিবরণ নেই।'),
  leaf: phrase('Photograph both sides of the same leaf.', 'একই পাতার দুই পিঠের ছবি তুলুন।'),
  produce: phrase('Photograph where the damaged area meets the sound surface.', 'ফসলের নষ্ট অংশ আর ভালো অংশ যেখানে মিলেছে, সেই জায়গার ছবি তুলুন।'),
  internal: phrase('Photograph the edge of the damage on the exposed flesh.', 'আগেই কাটা অংশে ভালো ও নষ্ট শাঁসের সীমানার ছবি তুলুন।'),
  surface: phrase('Take a close photo of the growth on the surface.', 'ফসলের গায়ে যে আবরণ দেখা যাচ্ছে, কাছ থেকে তার ছবি তুলুন।'),
  blight: phrase('Check the oldest tomato leaves near the ground for round spots with rings.', 'মাটির কাছের পুরোনো টমেটো পাতায় গোল দাগের ভেতর বলয় আছে কি না দেখুন।'),
  blightReason: phrase('Ringed spots can fit early blight. An adviser can help confirm the cause.', 'দাগে বলয় থাকলে আগাম ধসা রোগের সম্ভাবনা থাকে। কারণ নিশ্চিত করতে কৃষি কর্মকর্তার সাহায্য নিন।'),
  perspective: phrase('A close view and a comparison can help an adviser narrow down the cause.', 'কাছ থেকে তোলা ছবি আর অন্য নমুনার সঙ্গে তুলনা করলে কৃষি কর্মকর্তার পক্ষে কারণ বোঝা সহজ হয়।'),
  firstToday: phrase('Keep today’s photo to compare with the same leaf later.', 'পরে একই পাতার সঙ্গে মিলিয়ে দেখতে আজকের ছবিটি রাখুন।'),
  days: phrase('Compare the leaf with how it looked a few days ago.', 'কয়েক দিন আগে পাতাটি কেমন ছিল, তার সঙ্গে মিলিয়ে দেখুন।'),
  week: phrase('Check whether newer leaves now show the same change.', 'নতুন পাতাতেও এখন একই পরিবর্তন দেখা যাচ্ছে কি না দেখুন।'),
  timeUnknown: phrase('Write down today’s date for the next check.', 'পরে মিলিয়ে দেখার জন্য আজকের তারিখ লিখে রাখুন।'),
  inField: phrase('Check produce on nearby plants in the field.', 'খেতে আশপাশের গাছের ফলনও দেখুন।'),
  inStorage: phrase('Check other produce from the same stored batch.', 'একই সঙ্গে রাখা অন্য ফল বা সবজিতেও এমন হয়েছে কি না দেখুন।'),
  locationUnknown: phrase('Ask where the damage was first noticed.', 'ক্ষতি প্রথম কোথায় চোখে পড়েছিল, খোঁজ নিন।'),
  onePlant: phrase('Compare the plant with a nearby plant.', 'গাছটির সঙ্গে পাশের একটি গাছ মিলিয়ে দেখুন।'),
  somePlants: phrase('Mark the affected plants and check their neighbors.', 'যে গাছগুলোতে লক্ষণ দেখেছেন সেগুলো চিহ্নিত করে পাশের গাছগুলো দেখুন।'),
  manyPlants: phrase('Take a wide photo showing the affected area.', 'খেতের কতটা অংশে লক্ষণ আছে বোঝাতে একটু দূর থেকে ছবি তুলুন।'),
  countPlants: phrase('Count how many nearby plants look similar.', 'আশপাশে কয়টি গাছে একই লক্ষণ আছে গুনে দেখুন।'),
  oneItem: phrase('Compare the affected item with one that looks sound.', 'নষ্ট নমুনাটির সঙ্গে দেখতে ভালো একটি নমুনা মিলিয়ে দেখুন।'),
  someItems: phrase('Count the affected items and note which ones were together.', 'কয়টিতে ক্ষতি আছে গুনুন আর কোনগুলো একসঙ্গে ছিল লিখে রাখুন।'),
  manyItems: phrase('Take a wide photo and estimate how many items are affected.', 'দূর থেকে একটি ছবি তুলুন আর আনুমানিক কয়টিতে ক্ষতি আছে লিখুন।'),
  countItems: phrase('Count how many items show the same change.', 'কয়টিতে একই পরিবর্তন দেখা যাচ্ছে গুনে দেখুন।'),
};

export const farmerGuidancePhrases = Object.values(words);

type Evidence = NonNullable<DoctorScreening['assessment']>;

function possibleEarlyBlight(result: DoctorScreening, a: Evidence) {
  const supportedNames = ['early blight', 'tomato early blight', 'possible early blight', 'আগাম ধসা', 'আগাম ধসা রোগ', 'আর্লি ব্লাইট'];
  return result.crop === 'tomato' && a.crop_match === 'match' && a.part === 'leaf'
    && a.outcome === 'possible_condition' && a.marker === 'concentric_rings'
    && !!a.distinguishing_sign?.trim() && supportedNames.includes(a.condition?.trim().toLowerCase() ?? '');
}

function assessmentGuidance(result: DoctorScreening) {
  const a = result.assessment;
  const c = result.farmer_context;
  const general = {source: scoutingSource, uncertain: true, useAnswers: false};
  if (!a) {
    const action = result.classification.abstained ? words.retry : words.leaf;
    const rejection = result.classification.rejection_reason;
    const reason = rejection === 'crop_mismatch' ? words.wrongCrop
      : rejection === 'low_confidence' || rejection === 'image_quality' ? words.unclear : words.legacy;
    return {...general, action: rejection === 'crop_mismatch' ? words.showLeaf : action, reason, useAnswers: c?.kind === 'leaf'};
  }
  if (a.crop_match === 'mismatch' || (result.crop !== 'auto' && a.crop_match === 'unknown')) {
    return {...general, action: words.retry, reason: words.wrongCrop};
  }
  if (a.outcome === 'unrelated' || a.part === 'unknown' || a.part === 'other') {
    return {...general, action: words.retry, reason: words.unclear};
  }
  if (c && c.kind !== a.part) {
    return {...general, action: c.kind === 'leaf' ? words.showLeaf : words.showProduce, reason: words.different};
  }
  if (a.outcome === 'uncertain' || result.classification.abstained) {
    return {...general, useAnswers: true, action: words.retry, reason: words.unclear};
  }
  if (a.outcome === 'no_visible_damage') {
    return {...general, uncertain: false, useAnswers: true, action: words.followConcern, reason: words.notSeen};
  }
  if (possibleEarlyBlight(result, a)) {
    return {source: blightSource, uncertain: true, useAnswers: true, action: words.blight, reason: words.blightReason};
  }
  let action = words.leaf;
  if (a.part === 'produce') {
    action = a.produce_finding === 'internal_breakdown' ? words.internal
      : a.produce_finding === 'surface_mold' ? words.surface : words.produce;
  }
  return {...general, action, reason: words.perspective, useAnswers: true,
    uncertain: a.part === 'produce' || !a.condition || !a.distinguishing_sign};
}

function contextChecks(c: FarmerContext): Phrase[] {
  if (c.kind === 'leaf') {
    const timing = {today: words.firstToday, days: words.days, week_plus: words.week, unknown: words.timeUnknown};
    const count = {one: words.onePlant, several: words.somePlants, many: words.manyPlants, unknown: words.countPlants};
    return [timing[c.onset], count[c.extent]];
  }
  const place = {field: words.inField, storage: words.inStorage, unknown: words.locationUnknown};
  const count = {one: words.oneItem, several: words.someItems, many: words.manyItems, unknown: words.countItems};
  return [place[c.location], count[c.extent]];
}

export function farmerGuidance(result: DoctorScreening, locale: Locale) {
  const advice = assessmentGuidance(result);
  const c = result.farmer_context;
  const steps = [advice.action];
  if (advice.useAnswers && c) {
    const [setting, extent] = contextChecks(c);
    if (c.kind === 'produce' && c.extent !== 'unknown' && result.assessment?.outcome === 'possible_condition') {
      steps.unshift(extent);
      steps.push(setting);
    } else {
      steps.push(setting, extent);
    }
  }
  const [action, ...checks] = steps.map(step => step[locale]);
  const reason = advice.reason[locale];
  return {
    action, checks, reason, source: advice.source,
    refer: advice.uncertain || c?.extent === 'several' || c?.extent === 'many',
    speech: [action, ...checks, reason].join(' '),
  };
}

const cropsBn: Record<string, string> = {
  apple: 'আপেল', cherry: 'চেরি', maize: 'ভুট্টা', grape: 'আঙুর', orange: 'কমলা', peach: 'পিচ',
  bell_pepper: 'ক্যাপসিকাম', potato: 'আলু', squash: 'স্কোয়াশ', strawberry: 'স্ট্রবেরি', tomato: 'টমেটো', rice: 'ধান',
};

const leafMarkersBn: Record<string, string> = {
  concentric_rings: 'দাগের ভেতরে বলয়', surface_growth: 'উপরের আবরণ', pustules: 'ছোট উঁচু ফুসকুড়ির মতো দাগ',
  insect_or_mine: 'পোকা বা পাতার ভেতরে আঁকাবাঁকা পথ', fruiting_bodies: 'ক্ষতের ওপর ছোট গঠন',
  distinct_damage_distribution: 'নির্দিষ্ট জায়গায় ক্ষতি',
};

const produceSignsBn: Record<string, string> = {
  surface_mold: 'ক্ষতিগ্রস্ত অংশের ওপর ছাঁচের মতো আবরণ', internal_breakdown: 'কাটা অংশের শাঁসে ক্ষতি',
  sunken_or_shriveled: 'বসে যাওয়া বা কুঁচকে যাওয়া অংশ', bruise_or_wound: 'থেঁতলানো বা ক্ষতের মতো দাগ',
  discoloration: 'রঙের পরিবর্তন',
};

function photoSummaryBn(a: DoctorScreening['assessment']): string {
  if (!a) return 'ছবির লক্ষণের বিবরণ লেখা নেই।';
  if (a.outcome === 'unrelated') return 'ছবি থেকে ফসলের লক্ষণ বোঝা যায়নি।';
  if (a.outcome === 'no_visible_damage') return 'ছবিতে স্পষ্ট ক্ষতি ধরা পড়েনি।';
  const signs = a.signs.map(s => s.trim()).filter(Boolean);
  const bangla = signs.find(s => /[\u0980-\u09ff]/u.test(s));
  if (bangla) return 'ছবির পরীক্ষায় লেখা আছে, “' + bangla + '”';
  let description: string | undefined;
  if (a.outcome === 'possible_condition') {
    if (a.part === 'leaf') description = leafMarkersBn[a.marker ?? ''];
    if (a.part === 'produce') description = produceSignsBn[a.produce_finding ?? ''];
  }
  if (description) return 'ছবির পরীক্ষায় ' + description + ' দেখা গেছে বলে জানানো হয়েছে।';
  if (!signs.length) return 'ছবির লক্ষণের বিবরণ লেখা নেই।';
  const gist = a.outcome === 'uncertain' ? 'ছবিতে কী সমস্যা তা স্পষ্ট নয়।' : 'ছবিতে পরিবর্তন ধরা পড়েছে, কারণ নিশ্চিত নয়।';
  return gist + ' ছবির মূল বিবরণে লেখা আছে, “' + signs[0] + '”';
}

// Keep the caller's reports distinct from observations attributed to the photo.
export function adviserSummaryBn(result: DoctorScreening): string {
  const c = result.farmer_context;
  let crop: string;
  if (result.crop && result.crop !== 'auto') {
    crop = 'আমি ফসল হিসেবে ' + (cropsBn[result.crop] ?? result.crop) + ' বেছে নিয়েছি।';
  } else if (result.assessment && result.assessment.outcome !== 'unrelated') {
    const subject = result.assessment.subject.trim();
    const cropKey = subject.toLowerCase().replace(/ (?:leaf|leaves|fruit|tuber|root|bulb)$/, '').replaceAll(' ', '_');
    crop = 'ছবির পরীক্ষায় ফসলের পরিচয় লেখা হয়েছে “' + (cropsBn[cropKey] ?? subject) + '”।';
  } else {
    crop = 'ফসলের নাম জানা নেই।';
  }
  const context: string[] = [];
  if (result.assessment?.crop_match === 'mismatch') context.push('ছবির সঙ্গে বেছে নেওয়া ফসল মেলেনি।');
  if (c) {
    context.push(c.kind === 'leaf' ? 'আমি পাতার কথা জানিয়েছি।' : 'আমি ফল, সবজি বা কন্দের কথা জানিয়েছি।');
    if (result.assessment && result.assessment.part !== c.kind && result.assessment.outcome !== 'unrelated') {
      context.push('ছবিতে এই অংশটি শনাক্ত করা যায়নি।');
    }
  }
  const onset = {
    today: 'আজ প্রথম খেয়াল করেছি।', days: 'কয়েক দিন আগে প্রথম খেয়াল করেছি।',
    week_plus: 'এক সপ্তাহ বা তারও আগে প্রথম খেয়াল করেছি।', unknown: 'কবে প্রথম দেখেছি তা লেখা নেই।',
  };
  const location = {field: 'প্রথম দেখেছি খেতে।', storage: 'প্রথম দেখেছি সংরক্ষণ করে রাখার সময়।', unknown: 'কোথায় প্রথম দেখা গেছে তা লেখা নেই।'};
  context.push(onset[c?.onset ?? 'unknown'], location[c?.location ?? 'unknown']);
  if (!c || c.extent === 'unknown') {
    context.push('কতগুলোতে লক্ষণ আছে তা জানা নেই।');
  } else {
    const count = {one: 'একটি', several: 'কয়েকটি', many: 'অনেক'};
    context.push(count[c.extent] + (c.kind === 'leaf' ? ' গাছে' : ' নমুনায়') + ' এমন দেখেছি।');
  }
  return [crop, ...context, photoSummaryBn(result.assessment)].join(' ');
}
